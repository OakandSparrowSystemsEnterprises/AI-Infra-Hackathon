import { spawnSync } from "node:child_process";
import { stat } from "node:fs/promises";
import { resolve } from "node:path";

try {
  process.loadEnvFile(".env");
} catch {
  // The caller may provide environment variables directly.
}

const roles = ["PLANNER", "BUILDER", "REVIEWER"] as const;
const errors: string[] = [];
const notes: string[] = [];

for (const role of roles) {
  if (!process.env[role + "_AGENT_ID"]?.trim()) errors.push(role + "_AGENT_ID is missing");
  if (!process.env[role + "_API_KEY"]?.trim()) errors.push(role + "_API_KEY is missing");
}

const ids = roles
  .map((role) => process.env[role + "_AGENT_ID"]?.trim())
  .filter((value): value is string => Boolean(value));

if (new Set(ids).size !== ids.length) {
  errors.push("Each BAND role must use a different Agent UUID");
}

const workspace = resolve(process.env.FACTORY_WORKSPACE?.trim() || process.cwd());
try {
  const info = await stat(workspace);
  if (!info.isDirectory()) errors.push("FACTORY_WORKSPACE is not a directory: " + workspace);
} catch {
  errors.push("FACTORY_WORKSPACE does not exist: " + workspace);
}

const codexCommand = process.platform === "win32" ? "codex.cmd" : "codex";
const codex = spawnSync(codexCommand, ["--version"], {
  encoding: "utf8",
  windowsHide: true,
});

if (codex.error || codex.status !== 0) {
  errors.push("Codex CLI is not available. Install @openai/codex globally and run codex login");
} else {
  notes.push("Codex: " + ((codex.stdout || codex.stderr).trim() || "available"));
}

const gatekeeperUrl = process.env.GATEKEEPER_URL?.trim();
if (gatekeeperUrl) {
  try {
    const parsed = new URL(gatekeeperUrl);
    const loopback = ["localhost", "127.0.0.1", "::1"].includes(parsed.hostname);
    if (parsed.protocol !== "https:" && !(loopback && parsed.protocol === "http:")) {
      errors.push("GATEKEEPER_URL must use HTTPS except for loopback development");
    }
    notes.push("Authority: live endpoint configured at " + parsed.origin);
  } catch {
    errors.push("GATEKEEPER_URL is not a valid URL");
  }
} else {
  notes.push("Authority: local reference mode; no production Gatekeeper claim");
}

if (errors.length > 0) {
  console.error("\nDark Factory preflight failed:\n");
  for (const error of errors) console.error("  ERROR  " + error);
  console.error("\nFix the errors above, then run pnpm doctor again.\n");
  process.exit(1);
}

console.log("\nDark Factory preflight passed.");
console.log("Workspace: " + workspace);
for (const note of notes) console.log(note);
console.log("BAND credentials: Planner, Builder, Reviewer configured.\n");
