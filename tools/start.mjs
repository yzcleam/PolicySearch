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
  lanAddresses,
  ok,
  parseArgs,
  pythonEnv,
  readEnv,
  readPackage,
  runCompose,
  sleep,
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
    throw new Error("缺少 .venv，请先运行 npm run deploy。");
  }

  const host = String(args.host || env.APP_HOST || "127.0.0.1");
  const port = Number(args.port || env.APP_PORT || 8000);
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error("APP_PORT / --port 必须是 1-65535 之间的整数。");
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
  const child = spawn(
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
  const stop = (signal) => {
    if (stopping) return;
    stopping = true;
    console.log("");
    info(`收到 ${signal}，正在停止 FastAPI…（容器保持运行）`);
    stopChild(child);
  };

  process.on("SIGINT", () => stop("SIGINT"));
  process.on("SIGTERM", () => stop("SIGTERM"));
  process.on("SIGHUP", () => stop("SIGHUP"));

  child.once("error", (error) => {
    fail(`启动 FastAPI 失败：${error.message}`);
    process.exitCode = 1;
  });

  child.once("exit", (code, signal) => {
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

  await sleep(1_200);

  const localUrl = `http://127.0.0.1:${port}/`;
  console.log("");
  ok(`应用已启动：${localUrl}`);
  info(`API 文档：${localUrl}docs`);
  if (host === "0.0.0.0" || host === "::") {
    for (const address of lanAddresses()) {
      info(`局域网访问：http://${address}:${port}/`);
    }
  }
  console.log(c.dim("  按 Ctrl+C 停止 FastAPI（PostgreSQL / OpenSearch 容器保持运行）"));
}

main().catch((error) => {
  fail(error?.stack || error?.message || String(error));
  console.error("");
  console.error(c.gray("  npm run doctor"));
  console.error(c.gray("  npm run infra:logs"));
  process.exitCode = 1;
});
