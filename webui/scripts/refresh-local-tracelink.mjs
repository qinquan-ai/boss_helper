import { spawnSync } from "node:child_process";
import { existsSync, lstatSync, mkdirSync, renameSync, rmSync, unlinkSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const boardDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const sdkDir = resolve(boardDir, "../../../debug_project/Trace_Link");
const packageDir = join(boardDir, ".local-packages");
const tarballPath = join(packageDir, "tracelink-dev.tgz");
const installedPackagePath = join(boardDir, "node_modules", "tracelink");
const npmCliPath = process.env.npm_execpath;

if (!existsSync(join(sdkDir, "package.json"))) {
  throw new Error(`TraceLink SDK not found: ${sdkDir}`);
}

function npm(args, cwd, captureOutput = false) {
  const npmCmd = npmCliPath ? process.execPath : (process.platform === "win32" ? "npm.cmd" : "npm");
  const npmArgs = npmCliPath ? [npmCliPath, ...args] : args;

  const result = spawnSync(npmCmd, npmArgs, {
    cwd,
    encoding: "utf8",
    stdio: captureOutput ? "pipe" : "inherit",
  });

  if (result.error) throw result.error;
  if (result.status !== 0) {
    if (captureOutput) {
      if (result.stdout) process.stdout.write(result.stdout);
      if (result.stderr) process.stderr.write(result.stderr);
    }
    process.exit(result.status ?? 1);
  }

  return result.stdout ?? "";
}

mkdirSync(packageDir, { recursive: true });

console.log("[sdk:refresh] build TraceLink");
npm(["run", "build"], sdkDir);

console.log("[sdk:refresh] pack TraceLink");
const output = npm(
  ["pack", sdkDir, "--silent", "--pack-destination", packageDir],
  boardDir,
  true,
);
const filename = output.trim().split(/\r?\n/).at(-1);
if (!filename?.endsWith(".tgz")) throw new Error("npm pack did not return a tarball");

rmSync(tarballPath, { force: true });
renameSync(join(packageDir, filename), tarballPath);

if (existsSync(installedPackagePath)) {
  if (lstatSync(installedPackagePath).isSymbolicLink()) {
    unlinkSync(installedPackagePath);
  } else {
    rmSync(installedPackagePath, { recursive: true, force: true });
  }
}

console.log("[sdk:refresh] install local tarball");
npm(["install", "--no-audit", "--no-fund"], boardDir);
