import { Agent, CodexAdapter, loadAgentConfigFromEnv } from "@band-ai/sdk";
import { z } from "zod";

import { evaluateRelease } from "./authority.js";

try {
  process.loadEnvFile(".env");
} catch {
  // Environment variables may be supplied by the shell or BAND runtime.
}

type FactoryRole = "planner" | "builder" | "reviewer";

function readRole(): FactoryRole {
  const role = (process.argv[2] || "").toLowerCase();
  if (role === "planner" || role === "builder" || role === "reviewer") return role;
  throw new Error("Role must be planner, builder, or reviewer");
}

const prompts: Record<FactoryRole, string> = {
  planner: [
    "You are Planner in a lightweight BAND software factory.",
    "Turn the human request into no more than three concrete implementation steps.",
    "Do not edit files, run destructive commands, commit, push, or deploy.",
    "Send the implementation handoff to @Builder and tell @Reviewer what acceptance check matters.",
    "Prefer the smallest change that finishes the task.",
  ].join("\n"),
  builder: [
    "You are Builder in a lightweight BAND software factory.",
    "Implement the Planner handoff in the configured workspace with the smallest reasonable diff.",
    "Run the relevant local tests or typecheck after the change.",
    "Do not commit, push, deploy, or claim authorization.",
    "When finished, report the changed files and exact verification command to @Reviewer.",
  ].join("\n"),
  reviewer: [
    "You are Reviewer in a lightweight BAND software factory.",
    "Independently inspect Builder's change and run the relevant verification command.",
    "If verification fails, send the failure back to @Builder and do not request release authority.",
    "If verification passes, call request_release_authority exactly once with a short summary and testsPassed=true.",
    "Report the returned verdict, candidate SHA, decision id, and whether the source is live or reference.",
    "Do not describe a reference decision record as a production Gatekeeper sealed receipt.",
  ].join("\n"),
};

const role = readRole();
const workspace = process.env.FACTORY_WORKSPACE?.trim() || process.cwd();

const releaseTool = {
  name: "request_release_authority",
  description: "Bind the reviewed workspace to a release decision after verification has completed.",
  schema: z.object({
    summary: z.string().min(1).max(500),
    testsPassed: z.boolean(),
  }),
  handler: async ({ summary, testsPassed }: { summary: string; testsPassed: boolean }) => {
    const decision = await evaluateRelease({
      actor: "reviewer",
      workspace,
      summary,
      testsPassed,
    });
    return JSON.stringify(decision);
  },
};

const adapter = new CodexAdapter({
  config: {
    cwd: workspace,
    approvalPolicy: "never",
    sandboxMode: "workspace-write",
    reasoningEffort: "medium",
    reasoningSummary: "concise",
    networkAccessEnabled: false,
    webSearchMode: "disabled",
    customSection: prompts[role],
  },
  customTools: role === "reviewer" ? [releaseTool] : [],
});

const config = loadAgentConfigFromEnv({ prefix: role.toUpperCase() });
const agent = Agent.create({ adapter, config });

await agent.run();
