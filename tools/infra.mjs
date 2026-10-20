import fs from "node:fs";

import {
  ENV_FILE,
  banner,
  composeChecked,
  c,
  detectDocker,
  fail,
  info,
  parseArgs,
  readEnv,
  runCompose,
  assertNodeVersion,
} from "./lib.mjs";

async function main() {
  assertNodeVersion();
  const args = parseArgs();
  const command = String(args._[0] || "status").toLowerCase();

  if (!fs.existsSync(ENV_FILE)) {
    throw new Error("缺少 .env，请先运行 npm run deploy。");
  }
  const env = readEnv(ENV_FILE);
  const docker = detectDocker(env);
  if (!docker) throw new Error("未检测到可用的 Docker Engine。");
  if (!docker.composeCmd) throw new Error("Docker Compose 不可用。");

  banner(`PolicySearcher · ${command}`, docker.label);

  if (command === "up" || command === "start") {
    const composeArgs = ["up", "-d"];
    if (!args["no-build"]) composeArgs.push("--build");
    await composeChecked(docker, composeArgs, { env });
    info("容器已启动。");
  } else if (command === "down" || command === "stop") {
    const composeArgs = ["down"];
    if (args.volumes) composeArgs.push("--volumes");
    await composeChecked(docker, composeArgs, { env });
    info(args.volumes ? "容器和数据卷已删除。" : "容器已停止（数据卷保留）。");
  } else if (command === "restart") {
    await composeChecked(docker, ["restart"], { env });
    info("容器已重启。");
  } else if (command === "ps" || command === "status") {
    const result = await runCompose(docker, ["ps"], { env });
    if (result.code !== 0) process.exitCode = result.code ?? 1;
  } else if (command === "logs") {
    const tail = String(args.tail || 200);
    const composeArgs = ["logs", "--tail", tail];
    if (args.follow) composeArgs.push("-f");
    const result = await runCompose(docker, composeArgs, { env });
    if (result.code !== 0) process.exitCode = result.code ?? 1;
  } else if (command === "pull") {
    await composeChecked(docker, ["pull"], { env });
    info("镜像已更新；如需重建 IK 镜像请运行 npm run infra:up。");
  } else {
    console.log(c.bold("用法："));
    console.log("  npm run infra:up       启动并构建容器");
    console.log("  npm run infra:down     停止容器（保留数据卷）");
    console.log("  npm run infra:status   查看容器状态");
    console.log("  npm run infra:logs     查看最近日志");
    console.log("  npm run infra:restart  重启容器");
    console.log("  npm run infra:pull     拉取基础镜像");
    process.exitCode = 1;
  }
}

main().catch((error) => {
  const message = error?.stack || error?.message || String(error);
  fail(message);
  process.exitCode = 1;
});
