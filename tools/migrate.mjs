import fs from "node:fs";

import {
  ENV_FILE,
  ROOT,
  fail,
  info,
  parseArgs,
  pythonEnv,
  readEnv,
  runStreamChecked,
  venvPythonPath,
  assertNodeVersion,
} from "./lib.mjs";

async function main() {
  assertNodeVersion();
  parseArgs();
  if (!fs.existsSync(ENV_FILE)) {
    throw new Error("缺少 .env，请先运行 npm run deploy。");
  }
  const python = venvPythonPath();
  if (!fs.existsSync(python)) {
    throw new Error("缺少 .venv，请先运行 npm run deploy。");
  }
  const env = readEnv(ENV_FILE);
  info("检查并应用数据库迁移…");
  await runStreamChecked(python, ["backend/scripts/migrate.py"], {
    cwd: ROOT,
    env: pythonEnv(env),
  });
}

main().catch((error) => {
  fail(error?.stack || error?.message || String(error));
  process.exitCode = 1;
});
