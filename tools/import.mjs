import { spawn } from "node:child_process";
import path from "node:path";

import { ROOT, pythonEnv, venvPythonPath } from "./lib.mjs";

const python = venvPythonPath();
const child = spawn(
  python,
  [path.join(ROOT, "backend", "scripts", "import_data.py"), ...process.argv.slice(2)],
  {
    cwd: ROOT,
    env: pythonEnv(),
    stdio: "inherit",
    windowsHide: false,
  }
);

child.once("error", (error) => {
  console.error(`[import] ${error.message}`);
  process.exit(1);
});
child.once("exit", (code) => process.exit(code ?? 1));
