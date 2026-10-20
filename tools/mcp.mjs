import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";

import { ENV_FILE, IS_WIN, ROOT, readEnv, venvPythonPath } from "./lib.mjs";

function fail(message) {
  console.error(`[mcp] ${message}`);
  process.exitCode = 1;
}

if (!fs.existsSync(ENV_FILE)) {
  fail("缺少 .env，请先运行 npm run deploy。");
  process.exit(1);
}

const python = venvPythonPath();
if (!fs.existsSync(python)) {
  fail("缺少 .venv，请先运行 npm run deploy。");
  process.exit(1);
}

const env = {
  ...readEnv(ENV_FILE),
  ...process.env,
  PYTHONUTF8: "1",
  PYTHONIOENCODING: "utf-8",
};
const flags = new Set(process.argv.slice(2));
if (flags.has("--http")) env.MCP_TRANSPORT = "streamable-http";
if (flags.has("--stdio")) env.MCP_TRANSPORT = "stdio";
const transport = String(env.MCP_TRANSPORT || "stdio").toLowerCase();
const upstream = env.POLICY_API_URL || "http://127.0.0.1:8000";

if (transport === "stdio") {
  // Never write to stdout here: stdout is the MCP JSON-RPC channel.
  console.error(`[mcp] stdio transport · upstream=${upstream}`);
} else {
  const host = env.MCP_HOST || "127.0.0.1";
  const port = env.MCP_PORT || "8765";
  const mcpPath = env.MCP_PATH || "/mcp";
  console.error(`[mcp] ${transport} transport · http://${host}:${port}${mcpPath} · upstream=${upstream}`);
}

const child = spawn(python, ["-m", "mcp_server.server"], {
  cwd: ROOT,
  env,
  stdio: "inherit",
  windowsHide: false,
});

let stopping = false;

function stopChild() {
  if (!child || child.killed) return;
  if (IS_WIN) {
    spawnSync("taskkill", ["/pid", String(child.pid), "/T", "/F"], {
      stdio: "ignore",
      windowsHide: true,
    });
    return;
  }
  child.kill("SIGTERM");
  const timer = setTimeout(() => {
    if (child.exitCode === null) child.kill("SIGKILL");
  }, 5_000);
  timer.unref();
}

function stop() {
  if (stopping) return;
  stopping = true;
  stopChild();
}

process.on("SIGINT", stop);
process.on("SIGTERM", stop);

child.once("error", (error) => {
  fail(`启动失败：${error.message}`);
  process.exit(1);
});

child.once("exit", (code, signal) => {
  if (stopping) process.exit(0);
  if (signal) {
    fail(`MCP server 被信号 ${signal} 终止。`);
    process.exit(1);
  }
  process.exit(code ?? 0);
});
