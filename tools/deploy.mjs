import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

import {
  ENV_FILE,
  ROOT,
  banner,
  c,
  composeChecked,
  createPrompter,
  detectDocker,
  detectPython,
  ensureVenv,
  fail,
  formatBytes,
  getJson,
  getSystemInfo,
  info,
  isPortFree,
  isValidIndexName,
  isValidPort,
  maskSecret,
  ok,
  parseArgs,
  pathExists,
  pythonEnv,
  randomPassword,
  readEnv,
  readPackage,
  runDocker,
  runStreamChecked,
  sleep,
  step,
  waitForHttp,
  waitForTcp,
  warn,
  writeEnv,
  assertNodeVersion,
} from "./lib.mjs";

const DEFAULTS = {
  APP_HOST: "127.0.0.1",
  APP_PORT: "8000",
  CORS_ORIGINS: "*",
  POSTGRES_HOST: "127.0.0.1",
  POSTGRES_PORT: "5432",
  POSTGRES_USER: "policy",
  POSTGRES_PASSWORD: "",
  POSTGRES_DB: "policy_search",
  DOCKER_MIRROR: "m.daocloud.io/docker.io",
  POSTGRES_IMAGE: "m.daocloud.io/docker.io/library/postgres:16-alpine",
  POSTGRES_CONTAINER: "policy-postgres",
  OPENSEARCH_HOST: "127.0.0.1",
  OPENSEARCH_PORT: "9200",
  OPENSEARCH_INDEX: "policy_documents",
  OPENSEARCH_IMAGE: "policysearcher/opensearch-ik:2.19.3",
  OPENSEARCH_BASE_IMAGE: "m.daocloud.io/docker.io/opensearchproject/opensearch:2.19.3",
  OPENSEARCH_JAVA_OPTS: "-Xms1g -Xmx1g",
  OPENSEARCH_CONTAINER: "policy-opensearch",
  SEED_COUNT: "320",
  SEED_ON_DEPLOY: "true",
  PIP_INDEX_URL: "https://pypi.tuna.tsinghua.edu.cn/simple",
  DOCKER_MODE: "auto",
  WSL_DISTRO: "Ubuntu",
  TZ: "Asia/Shanghai",
  MCP_TRANSPORT: "stdio",
  MCP_HOST: "127.0.0.1",
  MCP_PORT: "8765",
  MCP_PATH: "/mcp",
  MCP_STATELESS: "false",
  MCP_LOG_LEVEL: "INFO",
  MCP_AUTH_REQUIRED: "true",
  MCP_AUTOSTART: "true",
  POLICY_API_TOKEN: "",
  POLICY_API_URL: "",
  POLICY_API_TIMEOUT: "15",
  JWT_SECRET: "",
  JWT_ALGORITHM: "HS256",
  JWT_EXPIRE_MINUTES: "480",
  ADMIN_USERNAME: "admin",
  ADMIN_PASSWORD_HASH: "",
  API_TOKEN_EXPIRE_DAYS: "90",
  AUTH_REQUIRED: "false",
};

const TOTAL_STEPS = 7;

function configFrom(initial) {
  const config = {};
  for (const [key, value] of Object.entries(DEFAULTS)) {
    config[key] = initial[key] ?? value;
  }
  return config;
}

function buildDatabaseUrl(config) {
  const user = encodeURIComponent(config.POSTGRES_USER);
  const password = encodeURIComponent(config.POSTGRES_PASSWORD);
  const database = encodeURIComponent(config.POSTGRES_DB);
  return `postgresql+psycopg2://${user}:${password}@${config.POSTGRES_HOST}:${config.POSTGRES_PORT}/${database}`;
}

function applyDockerMirror(config) {
  const mirror = String(config.DOCKER_MIRROR || "").replace(/\/+$/, "");
  if (!mirror) return;

  const officialPostgres = new Set([
    "postgres:16-alpine",
    "library/postgres:16-alpine",
    "docker.io/library/postgres:16-alpine",
  ]);
  const officialOpenSearch = new Set([
    "opensearchproject/opensearch:2.19.3",
    "docker.io/opensearchproject/opensearch:2.19.3",
  ]);

  if (officialPostgres.has(config.POSTGRES_IMAGE)) {
    config.POSTGRES_IMAGE = `${mirror}/library/postgres:16-alpine`;
  }
  if (officialOpenSearch.has(config.OPENSEARCH_BASE_IMAGE)) {
    config.OPENSEARCH_BASE_IMAGE = `${mirror}/opensearchproject/opensearch:2.19.3`;
  }
}

function hashAdminPassword(password) {
  const iterations = 310_000;
  const salt = crypto.randomBytes(16);
  const digest = crypto.pbkdf2Sync(password, salt, iterations, 32, "sha256");
  return `pbkdf2_sha256:${iterations}:${salt.toString("base64url")}:${digest.toString("base64url")}`;
}

function buildValues(config, docker) {
  return {
    APP_HOST: config.APP_HOST,
    APP_PORT: config.APP_PORT,
    CORS_ORIGINS: config.CORS_ORIGINS,
    POSTGRES_HOST: config.POSTGRES_HOST,
    POSTGRES_PORT: config.POSTGRES_PORT,
    POSTGRES_USER: config.POSTGRES_USER,
    POSTGRES_PASSWORD: config.POSTGRES_PASSWORD,
    POSTGRES_DB: config.POSTGRES_DB,
    DOCKER_MIRROR: config.DOCKER_MIRROR,
    POSTGRES_IMAGE: config.POSTGRES_IMAGE,
    POSTGRES_CONTAINER: config.POSTGRES_CONTAINER,
    DATABASE_URL: buildDatabaseUrl(config),
    OPENSEARCH_HOST: config.OPENSEARCH_HOST,
    OPENSEARCH_PORT: config.OPENSEARCH_PORT,
    OPENSEARCH_URL: `http://${config.OPENSEARCH_HOST}:${config.OPENSEARCH_PORT}`,
    OPENSEARCH_INDEX: config.OPENSEARCH_INDEX,
    OPENSEARCH_IMAGE: config.OPENSEARCH_IMAGE,
    OPENSEARCH_BASE_IMAGE: config.OPENSEARCH_BASE_IMAGE,
    OPENSEARCH_JAVA_OPTS: config.OPENSEARCH_JAVA_OPTS,
    OPENSEARCH_CONTAINER: config.OPENSEARCH_CONTAINER,
    SEED_COUNT: config.SEED_COUNT,
    SEED_ON_DEPLOY: config.SEED_ON_DEPLOY,
    PIP_INDEX_URL: config.PIP_INDEX_URL,
    DOCKER_MODE: "auto",
    WSL_DISTRO: config.WSL_DISTRO || docker?.distro || "Ubuntu",
    TZ: config.TZ,
    MCP_TRANSPORT: config.MCP_TRANSPORT,
    MCP_HOST: config.MCP_HOST,
    MCP_PORT: config.MCP_PORT,
    MCP_PATH: config.MCP_PATH,
    MCP_STATELESS: config.MCP_STATELESS,
    MCP_LOG_LEVEL: config.MCP_LOG_LEVEL,
    MCP_AUTH_REQUIRED: config.MCP_AUTH_REQUIRED,
    MCP_AUTOSTART: config.MCP_AUTOSTART,
    POLICY_API_TOKEN: config.POLICY_API_TOKEN,
    POLICY_API_URL:
      config.POLICY_API_URL || `http://127.0.0.1:${config.APP_PORT}`,
    POLICY_API_TIMEOUT: config.POLICY_API_TIMEOUT,
    JWT_SECRET: config.JWT_SECRET,
    JWT_ALGORITHM: config.JWT_ALGORITHM,
    JWT_EXPIRE_MINUTES: config.JWT_EXPIRE_MINUTES,
    ADMIN_USERNAME: config.ADMIN_USERNAME,
    ADMIN_PASSWORD_HASH: config.ADMIN_PASSWORD_HASH,
    API_TOKEN_EXPIRE_DAYS: config.API_TOKEN_EXPIRE_DAYS,
    AUTH_REQUIRED: config.AUTH_REQUIRED,
  };
}

function existingPostgresPassword(infra, container) {
  const inspect = runDocker(
    infra,
    [
      "inspect",
      container,
      "--format",
      "{{range .Config.Env}}{{println .}}{{end}}",
    ],
    { timeout: 20_000 }
  );
  if (!inspect.ok) return null;
  const line = inspect.stdout
    .split(/\r?\n/)
    .map((item) => item.trim())
    .find((item) => item.startsWith("POSTGRES_PASSWORD="));
  return line ? line.slice("POSTGRES_PASSWORD=".length) : null;
}

function existingVolume(infra) {
  const result = runDocker(
    infra,
    ["volume", "ls", "--filter", "name=policysearcher_pgdata", "--format", "{{.Name}}"],
    { timeout: 20_000 }
  );
  return (
    result.ok &&
    result.stdout
      .split(/\r?\n/)
      .some((name) => name.trim() === "policysearcher_pgdata")
  );
}

function validateConfig(config) {
  if (!config.APP_HOST || !config.APP_HOST.trim()) {
    throw new Error("应用监听地址不能为空。");
  }
  for (const key of ["APP_PORT", "POSTGRES_PORT", "OPENSEARCH_PORT"]) {
    if (!isValidPort(config[key])) {
      throw new Error(`${key} 必须是 1-65535 之间的整数。`);
    }
  }
  const ports = [config.APP_PORT, config.POSTGRES_PORT, config.OPENSEARCH_PORT].map(Number);
  if (new Set(ports).size !== ports.length) {
    throw new Error("APP_PORT、POSTGRES_PORT、OPENSEARCH_PORT 不能重复。");
  }
  if (!config.POSTGRES_USER.trim()) throw new Error("PostgreSQL 用户不能为空。");
  if (!config.POSTGRES_PASSWORD) throw new Error("PostgreSQL 密码不能为空。");
  if (!config.POSTGRES_DB.trim()) throw new Error("PostgreSQL 数据库名不能为空。");
  if (!isValidIndexName(config.OPENSEARCH_INDEX)) {
    throw new Error("OpenSearch 索引名只能包含小写字母、数字、点、下划线和短横线。");
  }
  const seedCount = Number(config.SEED_COUNT);
  if (!Number.isInteger(seedCount) || seedCount < 0 || seedCount > 5000) {
    throw new Error("示例数据条数必须是 0-5000 之间的整数。");
  }
}

async function askPort(prompter, label, defaultValue) {
  for (;;) {
    const value = await prompter.ask(label, defaultValue);
    if (isValidPort(value)) return String(value);
    warn("端口必须是 1-65535 之间的整数，请重新输入。");
  }
}

async function askNonEmpty(prompter, label, defaultValue) {
  for (;;) {
    const value = await prompter.ask(label, defaultValue);
    if (value && value.trim()) return value.trim();
    warn("该项不能为空，请重新输入。");
  }
}

async function askIndexName(prompter, defaultValue) {
  for (;;) {
    const value = await prompter.ask("OpenSearch 索引名", defaultValue);
    if (isValidIndexName(value)) return value;
    warn("索引名只能包含小写字母、数字、点、下划线和短横线。");
  }
}

async function askSeedCount(prompter, defaultValue) {
  for (;;) {
    const value = await prompter.ask("示例数据条数（0 表示不导入）", defaultValue);
    const count = Number(value);
    if (Number.isInteger(count) && count >= 0 && count <= 5000) return String(count);
    warn("请输入 0-5000 之间的整数。");
  }
}

async function collectConfig(config, args) {
  if (args.port) config.APP_PORT = String(args.port);
  let overwrite = true;
  let generatedAdminPassword = null;

  if (!args.yes) {
    const prompter = await createPrompter();
    try {
      console.log(c.bold("交互式配置（直接回车使用括号内默认值）"));
      config.APP_HOST = await askNonEmpty(
        prompter,
        "应用监听地址（0.0.0.0 可供局域网访问）",
        config.APP_HOST
      );
      config.APP_PORT = await askPort(prompter, "应用端口", config.APP_PORT);
      config.POSTGRES_PORT = await askPort(
        prompter,
        "PostgreSQL 端口",
        config.POSTGRES_PORT
      );
      config.POSTGRES_USER = await askNonEmpty(
        prompter,
        "PostgreSQL 用户",
        config.POSTGRES_USER
      );
      const password = await prompter.ask(
        "PostgreSQL 密码（回车保留当前值/首次部署自动生成）",
        ""
      );
      if (password) config.POSTGRES_PASSWORD = password;
      config.POSTGRES_DB = await askNonEmpty(
        prompter,
        "PostgreSQL 数据库名",
        config.POSTGRES_DB
      );
      config.OPENSEARCH_PORT = await askPort(
        prompter,
        "OpenSearch 端口",
        config.OPENSEARCH_PORT
      );
      config.OPENSEARCH_INDEX = await askIndexName(
        prompter,
        config.OPENSEARCH_INDEX
      );
      config.SEED_COUNT = await askSeedCount(
        prompter,
        config.SEED_COUNT
      );
      config.SEED_ON_DEPLOY = (await prompter.confirm(
        "部署时导入示例数据？",
        config.SEED_ON_DEPLOY !== "false"
      ))
        ? "true"
        : "false";
      config.ADMIN_USERNAME = await askNonEmpty(
        prompter,
        "管理员用户名",
        config.ADMIN_USERNAME
      );
      const adminPassword = await prompter.ask(
        "管理员密码（回车保留当前值/首次部署自动生成）",
        ""
      );
      if (adminPassword) {
        config.ADMIN_PASSWORD_HASH = hashAdminPassword(adminPassword);
      }
      if (fs.existsSync(ENV_FILE) && !args.force) {
        overwrite = await prompter.confirm(".env 已存在，是否覆盖？", true);
      }
    } finally {
      prompter.close();
    }
  }

  if (!config.POSTGRES_PASSWORD) {
    config.POSTGRES_PASSWORD = randomPassword();
    info(`已生成随机 PostgreSQL 密码：${maskSecret(config.POSTGRES_PASSWORD)}`);
  }
  if (args.reset) config.SEED_ON_DEPLOY = "true";
  if (!config.JWT_SECRET) {
    config.JWT_SECRET = crypto.randomBytes(32).toString("base64url");
  }
  if (!config.ADMIN_PASSWORD_HASH) {
    generatedAdminPassword = randomPassword(18);
    config.ADMIN_PASSWORD_HASH = hashAdminPassword(generatedAdminPassword);
  }

  return { config, overwrite, generatedAdminPassword };
}

function printConfig(values) {
  info(`应用: http://127.0.0.1:${values.APP_PORT}/（监听 ${values.APP_HOST}）`);
  info(`PostgreSQL: ${values.POSTGRES_USER}@${values.POSTGRES_HOST}:${values.POSTGRES_PORT}/${values.POSTGRES_DB}`);
  info(`PostgreSQL 密码: ${maskSecret(values.POSTGRES_PASSWORD)}`);
  info(`OpenSearch: ${values.OPENSEARCH_URL} · 索引 ${values.OPENSEARCH_INDEX}`);
  info(`Docker 镜像前缀: ${values.DOCKER_MIRROR || "官方"}`);
  info(`Python 包镜像: ${values.PIP_INDEX_URL}`);
  info(`示例数据: ${values.SEED_ON_DEPLOY === "true" ? `${values.SEED_COUNT} 条` : "不导入"}`);
  if (/[\s$`"\\]/.test(values.POSTGRES_PASSWORD)) {
    warn("密码包含空白或 $ ` \" \\ 等字符，Compose 可能解析异常；建议使用字母、数字、- 和 _。");
  }
}

async function waitForPostgres(infra, config, timeoutMs = 120_000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const result = runDocker(
      infra,
      [
        "exec",
        config.POSTGRES_CONTAINER,
        "pg_isready",
        "-U",
        config.POSTGRES_USER,
        "-d",
        config.POSTGRES_DB,
      ],
      { timeout: 10_000 }
    );
    if (result.ok && /accepting connections/i.test(result.stdout)) return;
    await sleep(2_000);
  }
  warn("未能通过 pg_isready 确认 PostgreSQL 就绪，继续尝试迁移。");
}

async function main() {
  assertNodeVersion();
  const args = parseArgs();
  const pkg = readPackage();
  const system = getSystemInfo();

  banner(
    `PolicySearcher ${pkg.version} · 一键部署`,
    "Node 22 · PostgreSQL 16 · OpenSearch 2.19 + IK"
  );

  step(1, TOTAL_STEPS, "环境检测");
  info(`平台: ${system.platform} ${system.arch} · Node ${system.node}${system.npm ? ` · npm ${system.npm}` : ""}`);
  info(`CPU: ${system.cpus} 核 · 内存: ${formatBytes(system.memory)} · 磁盘可用: ${system.diskFree == null ? "未知" : formatBytes(system.diskFree)}`);

  const python = detectPython();
  if (!python) {
    throw new Error(
      "未找到 Python 3.10+。请安装 Python 3.10/3.12，并确保 python3、python 或 py -3 可用。"
    );
  }
  ok(`Python ${python.version}（${python.source}）`);
  if (!pathExists(path.join(ROOT, "backend", "requirements.txt"))) {
    throw new Error("缺少 backend/requirements.txt。");
  }
  if (!pathExists(path.join(ROOT, "deploy", "opensearch", "opensearch-analysis-ik-2.19.3.zip"))) {
    throw new Error("缺少 IK 插件包 deploy/opensearch/opensearch-analysis-ik-2.19.3.zip。");
  }

  const initial = readEnv(ENV_FILE);
  const config = configFrom(initial);
  applyDockerMirror(config);
  if (args.port) config.APP_PORT = String(args.port);

  const docker = detectDocker(config);
  if (!docker) {
    throw new Error(
      "未检测到可用的 Docker Engine。请启动 Docker Desktop/Engine；" +
        "Windows 也可使用 WSL 内的 Docker（设置 DOCKER_MODE=wsl，WSL_DISTRO=Ubuntu）。"
    );
  }
  if (!docker.composeCmd) {
    throw new Error("Docker Compose 不可用，请安装 Compose v2 插件。");
  }
  ok(`${docker.label} · server ${docker.serverVersion}`);
  info(`Compose: ${docker.composeCmd.join(" ")}`);

  const oldPassword = existingPostgresPassword(docker, config.POSTGRES_CONTAINER);
  if (!initial.POSTGRES_PASSWORD) {
    if (oldPassword) {
      config.POSTGRES_PASSWORD = oldPassword;
      warn("检测到已有 PostgreSQL 容器，沿用其密码以保持数据卷可访问。");
    } else if (existingVolume(docker)) {
      config.POSTGRES_PASSWORD = "policy";
      warn("检测到已有 pgdata 数据卷但容器不存在，沿用默认密码 policy；如不一致请手动恢复。");
    }
  } else if (oldPassword && oldPassword !== config.POSTGRES_PASSWORD) {
    warn(
      "现有 PostgreSQL 容器密码与 .env 不一致：容器会使用新密码启动，但旧数据卷仍保留原角色密码，可能导致认证失败。"
    );
    warn("请恢复原密码，或先备份并在容器内执行 ALTER ROLE，再删除/迁移数据卷。");
  }

  step(2, TOTAL_STEPS, "配置与 .env");
  const { config: configured, overwrite, generatedAdminPassword } =
    await collectConfig(config, args);
  validateConfig(configured);
  const values = buildValues(configured, docker);
  for (const [key, value] of Object.entries(initial)) {
    if (!(key in values)) values[key] = value;
  }

  if (!overwrite) {
    warn("已取消，未修改 .env。");
    return;
  }

  printConfig(values);
  writeEnv(values);
  ok(`写入 ${ENV_FILE}`);

  step(3, TOTAL_STEPS, "Python 环境与依赖");
  const venvPython = await ensureVenv({
    upgrade: Boolean(args.upgrade),
    skipInstall: Boolean(args["skip-install"]),
    pipIndexUrl: values.PIP_INDEX_URL,
  });

  step(4, TOTAL_STEPS, "启动 PostgreSQL / OpenSearch 容器");
  const composeArgs = ["up", "-d"];
  if (!args["skip-build"]) composeArgs.push("--build");
  try {
    await composeChecked(docker, composeArgs, { env: values });
  } catch (error) {
    throw new Error(
      `${error.message}\n\n` +
        "Docker 镜像拉取失败。若服务器无法访问 Docker Hub，请执行：\n" +
        "  1) 在 .env 设置 DOCKER_MIRROR=m.daocloud.io/docker.io\n" +
        "  2) 或直接设置 POSTGRES_IMAGE / OPENSEARCH_BASE_IMAGE 为可访问的镜像地址\n" +
        `\n当前 POSTGRES_IMAGE=${values.POSTGRES_IMAGE}\n` +
        `当前 OPENSEARCH_BASE_IMAGE=${values.OPENSEARCH_BASE_IMAGE}`
    );
  }
  ok("容器已启动，等待健康检查…");

  await waitForTcp(configured.POSTGRES_HOST, Number(configured.POSTGRES_PORT), {
    timeoutMs: 180_000,
  });
  await waitForPostgres(docker, configured, 180_000);
  ok(`PostgreSQL 可连接 (${configured.POSTGRES_HOST}:${configured.POSTGRES_PORT})`);

  await waitForHttp(`${values.OPENSEARCH_URL}/_cluster/health`, {
    timeoutMs: 240_000,
    predicate: (data) => ["green", "yellow"].includes(data?.status),
  });
  ok(`OpenSearch 就绪 (${values.OPENSEARCH_URL})`);

  step(5, TOTAL_STEPS, "数据库初始化 / 版本迁移");
  await runStreamChecked(venvPython, ["backend/scripts/migrate.py"], {
    cwd: ROOT,
    env: pythonEnv(values),
  });

  step(6, TOTAL_STEPS, "示例数据");
  if (args["skip-seed"]) {
    info("已指定 --skip-seed，跳过示例数据。");
  } else if (values.SEED_ON_DEPLOY !== "true" || Number(values.SEED_COUNT) === 0) {
    info("当前配置不导入示例数据。");
  } else {
    const seedArgs = ["backend/scripts/seed.py", values.SEED_COUNT];
    seedArgs.push(args.reset ? "--reset" : "--if-empty");
    await runStreamChecked(venvPython, seedArgs, {
      cwd: ROOT,
      env: pythonEnv(values),
    });
  }

  step(7, TOTAL_STEPS, "部署完成");
  const appPort = Number(values.APP_PORT);
  const appBusy = !(await isPortFree(appPort));
  if (appBusy) {
    const health = await getJson(`http://127.0.0.1:${appPort}/api/health`, 1_500);
    if (health?.engine?.includes("opensearch")) {
      warn(`应用端口 ${appPort} 已被当前实例占用；启动前请先停止旧进程。`);
    } else {
      warn(`应用端口 ${appPort} 已被其他进程占用，npm start 可能失败。`);
    }
  }

  ok(`配置已保存到 ${ENV_FILE}`);
  info(`应用入口: http://127.0.0.1:${values.APP_PORT}/`);
  info(`API 文档: http://127.0.0.1:${values.APP_PORT}/docs`);
  info(`OpenSearch: ${values.OPENSEARCH_URL}`);
  info(`管理员用户名: ${values.ADMIN_USERNAME}`);
  if (generatedAdminPassword) {
    console.log("");
    console.log(c.bold(c.yellow("初始管理员密码（只显示一次，请立即保存）：")));
    console.log(c.bold(c.yellow(`  ${generatedAdminPassword}`)));
  }
  console.log("");
  console.log(c.bold(c.green("下一步：npm start")));
  console.log(c.dim("  停止容器：npm run infra:down"));
  console.log(c.dim("  重新检查：npm run doctor"));
  console.log(
    c.dim(
      "  注意：npm 没有内置的 `npm deploy` 命令，请使用 `npm run deploy`；`npm start` 可直接使用。"
    )
  );
}

main().catch((error) => {
  fail(error?.stack || error?.message || String(error));
  console.error("");
  console.error(c.yellow("排查建议："));
  console.error(c.gray("  npm run doctor"));
  console.error(c.gray("  npm run infra:logs"));
  process.exitCode = 1;
});
