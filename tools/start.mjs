import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import {
  ENV_FILE,
  IS_WIN,
  ROOT,
  banner,
  c,
  detectDocker,
  fail,
  getJson,
  info,
  isPortFree,
  lanAddresses,
  ok,
  parseArgs,
  pythonEnv,
  readEnv,
  readPackage,
  runCompose,
  venvPythonPath,
  waitForHttp,
  waitForTcp,
  warn,
  assertNodeVersion,
} from "./lib.mjs";

function stopChild(child) {
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
    if (!child.killed) child.kill("SIGKILL");
  }, 5_000);
  timer.unref();
}

async function ensureInfra(env, args) {
  if (args["no-infra"] || process.env.SKIP_INFRA === "1") {
    info("已跳过容器启动（--no-infra / SKIP_INFRA=1）。");
    return;
  }

  const docker = detectDocker(env);
  if (!docker) {
    warn("未检测到 Docker，假设 PostgreSQL / OpenSearch 已由外部提供。");
    return;
  }

  if (!docker.composeCmd) {
    warn("Docker Compose 不可用，跳过容器启动。");
    return;
  }

  info(`确保容器运行：${docker.label}`);
  const result = await runCompose(docker, ["up", "-d"], { env });
  if (result.code !== 0) {
    throw new Error("docker compose up 失败，请运行 npm run infra:logs 查看日志。");
  }

  const pgHost = env.POSTGRES_HOST || "127.0.0.1";
  const pgPort = Number(env.POSTGRES_PORT || 5432);
  const osUrl = env.OPENSEARCH_URL || `http://${env.OPENSEARCH_HOST || "127.0.0.1"}:${env.OPENSEARCH_PORT || 9200}`;

  await waitForTcp(pgHost, pgPort, { timeoutMs: 90_000 });
  ok(`PostgreSQL 可连接 (${pgHost}:${pgPort})`);

  await waitForHttp(`${osUrl}/_cluster/health`, {
    timeoutMs: 120_000,
    predicate: (data) => ["green", "yellow"].includes(data?.status),
  });
  ok(`OpenSearch 就绪 (${osUrl})`);
}

async function main() {
  assertNodeVersion();
  const args = parseArgs();
  const pkg = readPackage();

  if (!fs.existsSync(ENV_FILE)) {
    throw new Error("缺少 .env，请先运行 npm run deploy。");
  }

  const env = readEnv(ENV_FILE);
  const python = venvPythonPath();
  if (!fs.existsSync(python)) {
    throw new Error("缺少 Python 虚拟环境，请先运行 npm run deploy。");
  }

  const host = String(args.host || env.APP_HOST || "127.0.0.1");
  const port = Number(args.port || env.APP_PORT || 8000);
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error("APP_PORT / --port 必须是 1-65535 之间的整数。");
  }

  let mcpEnabled = !args["no-mcp"] && env.MCP_AUTOSTART !== "false";
  const mcpHost = String(env.MCP_HOST || "127.0.0.1");
  const mcpPort = Number(env.MCP_PORT || 8765);
  const mcpPath = String(env.MCP_PATH || "/mcp");
  if (mcpEnabled) {
    if (!Number.isInteger(mcpPort) || mcpPort < 1 || mcpPort > 65535) {
      throw new Error("MCP_PORT 必须是 1-65535 之间的整数。");
    }
    if (mcpPort === port) {
      throw new Error("MCP_PORT 不能与 APP_PORT 相同。");
    }
    if (!mcpPath.startsWith("/")) {
      throw new Error("MCP_PATH 必须以 / 开头，例如 /mcp。");
    }
  }

  banner(
    `PolicySearcher ${pkg.version}`,
    `PostgreSQL 16 · OpenSearch 2.19 + IK · 端口 ${port}`
  );

  const already = await getJson(`http://127.0.0.1:${port}/api/health`, 1_500);
  if (already?.engine?.includes("opensearch")) {
    throw new Error(`端口 ${port} 已有 PolicySearcher 实例在运行，请先停止旧进程。`);
  }

  await ensureInfra(env, args);

  const backendDir = path.join(ROOT, "backend");
  if (!fs.existsSync(path.join(backendDir, "app", "main.py"))) {
    throw new Error("缺少 backend/app/main.py。");
  }

  info(`启动 FastAPI：${python} -m uvicorn app.main:app --host ${host} --port ${port}`);
  const appChild = spawn(
    python,
    ["-m", "uvicorn", "app.main:app", "--host", host, "--port", String(port)],
    {
      cwd: backendDir,
      env: pythonEnv(env),
      stdio: "inherit",
      windowsHide: false,
    }
  );

  let stopping = false;
  let mcpChild = null;
  const stop = (signal) => {
    if (stopping) return;
    stopping = true;
    console.log("");
    info(`收到 ${signal}，正在停止 FastAPI / MCP…（容器保持运行）`);
    if (mcpChild) stopChild(mcpChild);
    stopChild(appChild);
  };

  process.on("SIGINT", () => stop("SIGINT"));
  process.on("SIGTERM", () => stop("SIGTERM"));
  process.on("SIGHUP", () => stop("SIGHUP"));

  appChild.once("error", (error) => {
    fail(`启动 FastAPI 失败：${error.message}`);
    process.exitCode = 1;
  });

  appChild.once("exit", (code, signal) => {
    if (mcpChild) stopChild(mcpChild);
    if (stopping) {
      ok("FastAPI 已停止。");
      process.exit(0);
    }
    if (signal) {
      warn(`FastAPI 被信号 ${signal} 终止。`);
      process.exit(1);
    }
    process.exit(code ?? 0);
  });

  try {
    await waitForHttp(`http://127.0.0.1:${port}/api/health`, {
      timeoutMs: 60_000,
      predicate: (data) => Boolean(data?.status),
    });
  } catch (error) {
    stopChild(appChild);
    throw new Error(`FastAPI 未在预期时间内就绪：${error.message}`);
  }

  const localUrl = `http://127.0.0.1:${port}/`;
  ok(`FastAPI 已启动：${localUrl}`);
  info(`API 文档：${localUrl}docs`);

  if (mcpEnabled) {
    if (!(await isPortFree(mcpPort))) {
      warn(`MCP 端口 ${mcpPort} 已被占用，跳过 MCP 自动启动。`);
      mcpEnabled = false;
    }
  }

  if (mcpEnabled) {
    const mcpEnv = {
      ...pythonEnv(env),
      MCP_TRANSPORT: "streamable-http",
      MCP_HOST: mcpHost,
      MCP_PORT: String(mcpPort),
      MCP_PATH: mcpPath,
      MCP_STATELESS: env.MCP_STATELESS || "false",
      POLICY_API_URL: env.POLICY_API_URL || `http://127.0.0.1:${port}`,
    };
    info(`启动 MCP HTTP：http://127.0.0.1:${mcpPort}${mcpPath}`);
    mcpChild = spawn(python, ["-m", "mcp_server.server"], {
      cwd: ROOT,
      env: mcpEnv,
      stdio: "inherit",
      windowsHide: false,
    });
    mcpChild.once("error", (error) => {
      warn(`MCP 启动失败：${error.message}`);
      mcpChild = null;
    });
    mcpChild.once("exit", (code, signal) => {
      if (!stopping) {
        warn(`MCP 已退出（code=${code ?? "?"}, signal=${signal ?? "-"}）。`);
      }
      mcpChild = null;
    });
    try {
      await waitForTcp("127.0.0.1", mcpPort, { timeoutMs: 20_000 });
      ok(`MCP HTTP 就绪：http://127.0.0.1:${mcpPort}${mcpPath}`);
      if (env.MCP_AUTH_REQUIRED !== "false") {
        info("MCP 需要 Bearer Token；请在管理员入口创建 Token。");
      }
    } catch {
      warn(`MCP 端口 ${mcpPort} 未在预期时间内监听，请查看上方日志。`);
    }
  } else {
    info("已跳过 MCP 自动启动（--no-mcp / MCP_AUTOSTART=false）。");
  }

  if (host === "0.0.0.0" || host === "::") {
    for (const address of lanAddresses()) {
      info(`局域网访问：http://${address}:${port}/`);
    }
  }
  console.log(c.dim("  按 Ctrl+C 停止 FastAPI / MCP（PostgreSQL / OpenSearch 容器保持运行）"));
}

main().catch((error) => {
  fail(error?.stack || error?.message || String(error));
  console.error("");
  console.error(c.gray("  npm run doctor"));
  console.error(c.gray("  npm run infra:logs"));
  process.exitCode = 1;
});
