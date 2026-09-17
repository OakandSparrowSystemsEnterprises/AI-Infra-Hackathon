import { createHash, randomUUID } from "node:crypto";
import { mkdir, readdir, readFile, writeFile } from "node:fs/promises";
import { basename, join, relative } from "node:path";

export type Verdict = "ALLOW" | "TRANSFORM" | "HOLD" | "DENY";

export interface AuthorityDecision {
  decision_id: string;
  verdict: Verdict;
  reason_codes: string[];
  candidate_sha: string;
  policy_version: string;
  source: "live" | "reference";
  evaluated_at_ms: number;
  receipt_path?: string;
}

interface ReleaseInput {
  actor: string;
  workspace: string;
  summary: string;
  testsPassed: boolean;
}

const IGNORED_DIRECTORIES = new Set([".git", "node_modules", "dist", ".dark-factory"]);
const VERDICTS = new Set<Verdict>(["ALLOW", "TRANSFORM", "HOLD", "DENY"]);

export async function hashWorkspace(root: string): Promise<string> {
  const files: string[] = [];

  async function walk(directory: string): Promise<void> {
    const entries = await readdir(directory, { withFileTypes: true });
    entries.sort((a, b) => a.name.localeCompare(b.name));

    for (const entry of entries) {
      if (entry.isSymbolicLink()) continue;
      if (entry.isDirectory() && IGNORED_DIRECTORIES.has(entry.name)) continue;

      const absolute = join(directory, entry.name);
      if (entry.isDirectory()) {
        await walk(absolute);
        continue;
      }

      if (!entry.isFile()) continue;
      const name = basename(absolute);
      if (name === ".env" || name.startsWith(".env.")) continue;
      files.push(absolute);
    }
  }

  await walk(root);

  const hash = createHash("sha256");
  for (const file of files) {
    const path = relative(root, file).replaceAll("\\", "/");
    hash.update(path);
    hash.update("\0");
    hash.update(await readFile(file));
    hash.update("\0");
  }
  return hash.digest("hex");
}

function hold(candidateSha: string, reason: string, source: "live" | "reference"): AuthorityDecision {
  return {
    decision_id: `df-${randomUUID()}`,
    verdict: "HOLD",
    reason_codes: [reason],
    candidate_sha: candidateSha,
    policy_version: source === "live" ? "gatekeeper-unavailable" : "reference-local",
    source,
    evaluated_at_ms: Date.now(),
  };
}

async function liveEvaluate(
  candidateSha: string,
  actor: string,
  summary: string,
  testsPassed: boolean,
): Promise<AuthorityDecision> {
  const baseUrl = process.env.GATEKEEPER_URL?.trim();
  if (!baseUrl) throw new Error("GATEKEEPER_URL is required for live evaluation");

  const path = process.env.GATEKEEPER_PATH?.trim() || "/v1/evaluate";
  const timeoutMs = Number(process.env.GATEKEEPER_TIMEOUT_MS || "2000");
  const id = randomUUID();

  const body = {
    evidence: {
      evidence_id: `ev-${id}`,
      candidate_sha: candidateSha,
      tests_passed: testsPassed,
      summary,
      observed_at_ms: Date.now(),
    },
    action: {
      action_id: `act-${id}`,
      actor_id: actor,
      action_type: "release_candidate",
      target: "workspace",
      candidate_sha: candidateSha,
    },
  };

  const headers: Record<string, string> = { "content-type": "application/json" };
  const token = process.env.GATEKEEPER_TOKEN?.trim();
  if (token) headers.authorization = `Bearer ${token}`;

  try {
    const response = await fetch(new URL(path, baseUrl), {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(Number.isFinite(timeoutMs) && timeoutMs > 0 ? timeoutMs : 2000),
    });

    if (!response.ok) return hold(candidateSha, `GATEKEEPER_HTTP_${response.status}`, "live");

    const raw = (await response.json()) as Record<string, unknown>;
    const rawVerdict = typeof raw.verdict === "string" ? raw.verdict.toUpperCase() : "";
    if (!VERDICTS.has(rawVerdict as Verdict)) return hold(candidateSha, "GATEKEEPER_RESPONSE_INVALID", "live");

    const authorizedAction = raw.authorized_action;
    if (authorizedAction && typeof authorizedAction === "object") {
      const boundSha = (authorizedAction as Record<string, unknown>).candidate_sha;
      if (typeof boundSha === "string" && boundSha !== candidateSha) {
        return hold(candidateSha, "AUTHORIZED_ARTIFACT_MISMATCH", "live");
      }
    }

    const reasons = Array.isArray(raw.reason_codes)
      ? raw.reason_codes.filter((item): item is string => typeof item === "string")
      : [];

    return {
      decision_id: typeof raw.decision_id === "string" ? raw.decision_id : `df-${id}`,
      verdict: rawVerdict as Verdict,
      reason_codes: reasons,
      candidate_sha: candidateSha,
      policy_version: typeof raw.policy_version === "string" ? raw.policy_version : "gatekeeper-live",
      source: "live",
      evaluated_at_ms: typeof raw.evaluated_at_ms === "number" ? raw.evaluated_at_ms : Date.now(),
    };
  } catch {
    return hold(candidateSha, "GATEKEEPER_UNAVAILABLE", "live");
  }
}

function referenceEvaluate(candidateSha: string, testsPassed: boolean): AuthorityDecision {
  return {
    decision_id: `ref-${randomUUID()}`,
    verdict: testsPassed ? "ALLOW" : "HOLD",
    reason_codes: [testsPassed ? "REFERENCE_TESTS_PASS" : "REFERENCE_TESTS_REQUIRED"],
    candidate_sha: candidateSha,
    policy_version: "reference-local",
    source: "reference",
    evaluated_at_ms: Date.now(),
  };
}

async function persistDecision(workspace: string, decision: AuthorityDecision): Promise<AuthorityDecision> {
  const receiptDirectory = join(workspace, ".dark-factory", "receipts");
  await mkdir(receiptDirectory, { recursive: true });
  const safeId = decision.decision_id.replace(/[^a-zA-Z0-9._-]/g, "_");
  const receiptPath = join(receiptDirectory, `${safeId}.json`);
  const persisted = { ...decision, receipt_path: receiptPath };
  await writeFile(receiptPath, `${JSON.stringify(persisted, null, 2)}\n`, "utf8");
  return persisted;
}

export async function evaluateRelease(input: ReleaseInput): Promise<AuthorityDecision> {
  const candidateSha = await hashWorkspace(input.workspace);
  const decision = process.env.GATEKEEPER_URL?.trim()
    ? await liveEvaluate(candidateSha, input.actor, input.summary, input.testsPassed)
    : referenceEvaluate(candidateSha, input.testsPassed);

  return persistDecision(input.workspace, decision);
}
