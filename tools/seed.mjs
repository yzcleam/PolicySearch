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
  const args = parseArgs();
  if (!fs.existsSync(ENV_FILE)) {
    throw new Error("缺少 .env，请先运行 npm run deploy。");
  }
  const python = venvPythonPath();
  if (!fs.existsSync(python)) {
    throw new Error("缺少 .venv，请先运行 npm run deploy。");
  }

  const env = readEnv(ENV_FILE);
  let count = "320";
  if (args._[0] && /^\d+$/.test(String(args._[0]))) count = String(args._[0]);
  if (args.count !== undefined) count = String(args.count);

  const scriptArgs = [String(count)];
  if (args.reset) scriptArgs.push("--reset");
  else scriptArgs.push("--if-empty");

  info(`运行示例数据脚本：count=${count}${args.reset ? " reset" : " if-empty"}`);
  await runStreamChecked(python, ["backend/scripts/seed.py", ...scriptArgs], {
    cwd: ROOT,
    env: pythonEnv(env),
  });
}

main().catch((error) => {
  fail(error?.stack || error?.message || String(error));
  process.exitCode = 1;
});
