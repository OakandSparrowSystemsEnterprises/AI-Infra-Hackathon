import { spawn, type ChildProcess } from "node:child_process";

const roles = ["planner", "builder", "reviewer"] as const;
const children = new Map<string, ChildProcess>();
let stopping = false;

function stopAll(exitCode = 0): void {
  if (stopping) return;
  stopping = true;

  for (const child of children.values()) {
    if (!child.killed) child.kill("SIGTERM");
  }

  setTimeout(() => process.exit(exitCode), 150).unref();
}

for (const role of roles) {
  const command = process.platform === "win32" ? "cmd.exe" : "pnpm";
  const args = process.platform === "win32"
    ? ["/d", "/s", "/c", "pnpm", "run", role]
    : ["run", role];

  const child = spawn(command, args, {
    cwd: process.cwd(),
    env: process.env,
    stdio: "inherit",
    windowsHide: true,
  });

  children.set(role, child);

  child.on("error", (error) => {
    console.error(role + " failed to start: " + error.message);
    stopAll(1);
  });

  child.on("exit", (code, signal) => {
    if (stopping) return;
    console.error(role + " stopped unexpectedly (code=" + String(code) + ", signal=" + String(signal) + ").");
    stopAll(code && code > 0 ? code : 1);
  });
}

process.on("SIGINT", () => stopAll(0));
process.on("SIGTERM", () => stopAll(0));

console.log("Dark Factory agents starting: Planner, Builder, Reviewer.");
console.log("Keep this process running while you use the BAND room.");
