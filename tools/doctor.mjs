import fs from "node:fs";
import path from "node:path";

import {
  COMPOSE_FILE,
  ENV_EXAMPLE,
  ENV_FILE,
  IK_ZIP,
  REQUIREMENTS,
  ROOT,
  banner,
  c,
  detectDocker,
  detectPython,
  formatBytes,
  getJson,
  getSystemInfo,
  info,
  isPortFree,
  ok,
  pathExists,
  probeTcp,
  readEnv,
  readPackage,
  run,
  venvPythonPath,
  warn,
  fail,
  pythonPackagesOk,
  assertNodeVersion,
} from "./lib.mjs";

const env = {
  ...readEnv(ENV_EXAMPLE),
  ...readEnv(ENV_FILE),
};

const problems = [];

function check(label, passed, detail, critical = true) {
  if (passed) {
    ok(`${label}: ${detail}`);
  } else {
    (critical ? fail : warn)(`${label}: ${detail}`);
    if (critical) problems.push(label);
  }
}

async function main() {
  assertNodeVersion();
  const pkg = readPackage();
  const system = getSystemInfo();

  banner(
    `PolicySearcher ${pkg.version} · 环境诊断`,
    "npm run deploy 之前先确认 Node / Python / Docker / 端口"
  );

  console.log(c.bold("运行环境"));
  info(`平台: ${system.platform} ${system.arch} (${system.release})`);
  info(`Node: ${system.node}${system.npm ? ` · npm ${system.npm}` : ""}`);
  info(`CPU: ${system.cpus} 核 · 内存: ${formatBytes(system.memory)}`);
  info(`磁盘可用: ${system.diskFree == null ? "未知" : formatBytes(system.diskFree)}`);
  console.log("");

  console.log(c.bold("项目文件"));
  check("docker-compose.yml", pathExists(COMPOSE_FILE), COMPOSE_FILE);
  check("Python 依赖清单", pathExists(REQUIREMENTS), REQUIREMENTS);
  check("IK 插件包", pathExists(IK_ZIP), path.basename(IK_ZIP));
  check("前端入口", pathExists(path.join(ROOT, "frontend", "index.html")), "frontend/index.html");
  check(
    "MCP 入口",
    pathExists(path.join(ROOT, "mcp_server", "server.py")),
    "mcp_server/server.py"
  );
  check(
    "环境文件",
    pathExists(ENV_FILE),
    pathExists(ENV_FILE) ? ".env 已存在" : ".env 不存在（运行 npm run deploy 生成）",
    false
  );
  check(
    "管理员凭据",
    Boolean(env.ADMIN_PASSWORD_HASH) &&
      Boolean(env.JWT_SECRET) &&
      env.JWT_SECRET !== "change-me",
    Boolean(env.ADMIN_PASSWORD_HASH)
      ? "已配置"
      : "未配置，管理员登录不可用；请运行 npm run deploy",
    false
  );
  console.log("");

  console.log(c.bold("Python"));
  const python = detectPython();
  if (python) {
    const isVenv = python.source === "venv";
    ok(`Python ${python.version}（${python.source}）`);
    if (isVenv) {
      const dependenciesOk = pythonPackagesOk(python);
      check(
        "Python 依赖",
        dependenciesOk,
        dependenciesOk ? "已安装" : "缺少依赖，请运行 npm run deploy"
      );
    } else {
      warn("尚未创建 Python 虚拟环境，npm run deploy 会自动创建并安装依赖。");
    }
  } else {
    fail("未找到 Python 3.10+（python3 / python / py -3）。");
    problems.push("python");
  }
  console.log("");

  console.log(c.bold("Docker / Compose"));
  const docker = detectDocker(env);
  if (docker) {
    ok(`Docker: ${docker.label} · server ${docker.serverVersion}`);
    check(
      "Compose",
      Boolean(docker.composeCmd),
      docker.composeCmd ? docker.composeCmd.join(" ") : "未找到 Compose v2 插件"
    );
    if (docker.mode === "wsl") {
      info(`WSL 项目路径: ${docker.wslRoot}`);
    }
  } else {
    fail("未检测到可用的 Docker Engine。");
    info("Windows 可设置 DOCKER_MODE=wsl 并使用 WSL 内的 Docker；macOS/Linux 请启动 Docker。");
    problems.push("docker");
  }
  console.log("");

  console.log(c.bold("服务端口"));
  const appPort = Number(env.APP_PORT || 8000);
  const appHealth = await getJson(`http://127.0.0.1:${appPort}/api/health`, 2_000);
  if (appHealth) {
    ok(`应用 ${appPort}: ${appHealth.status} · ${appHealth.engine}`);
  } else if (await isPortFree(appPort)) {
    ok(`应用 ${appPort}: 空闲`);
  } else {
    warn(`应用 ${appPort}: 已被其他进程占用`);
  }

  const pgHost = env.POSTGRES_HOST || "127.0.0.1";
  const pgPort = Number(env.POSTGRES_PORT || 5432);
  check(
    `PostgreSQL ${pgHost}:${pgPort}`,
    await probeTcp(pgHost, pgPort),
    (await probeTcp(pgHost, pgPort)) ? "可连接" : "未连接（容器可能未启动）",
    false
  );

  const osPort = Number(env.OPENSEARCH_PORT || 9200);
  const osHealth = await getJson(
    `http://${env.OPENSEARCH_HOST || "127.0.0.1"}:${osPort}/_cluster/health`,
    3_000
  );
  check(
    `OpenSearch :${osPort}`,
    Boolean(osHealth),
    osHealth ? `集群 ${osHealth.status}` : "未连接（容器可能未启动）",
    false
  );
  console.log("");

  if (problems.length) {
    fail(`诊断未通过：${problems.join(", ")}`);
    process.exitCode = 1;
  } else {
    ok("环境诊断通过，可以运行 npm start。");
  }
}

main().catch((error) => {
  fail(error.stack || error.message);
  process.exitCode = 1;
});
