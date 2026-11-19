"use strict";

const path = require("node:path");
const { spawnSync } = require("node:child_process");

function resolveNativeHelperPath({ platform, projectRoot }) {
  const executable =
    platform === "win32" ? "avatar-audio-listener.exe" : "avatar-audio-listener";
  const platformPath = platform === "win32" ? path.win32 : path.posix;
  return platformPath.join(projectRoot, "native", "bin", platform, executable);
}

function testNative(platform = process.platform) {
  if (!["darwin", "win32"].includes(platform)) {
    console.log("Gillie Avatar's Linux listener is covered by the Node test suite.");
    return;
  }
  const executable = resolveNativeHelperPath({
    platform,
    projectRoot: path.join(__dirname, ".."),
  });
  const result = spawnSync(executable, ["--self-test"], {
    encoding: "utf8",
    windowsHide: true,
  });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    throw new Error(result.stderr || `Native self-test exited with ${result.status}.`);
  }
  const message = JSON.parse(result.stdout.trim());
  if (message.type !== "ready") throw new Error("Native self-test returned an invalid response.");
  console.log(`${message.source} passed.`);
}

if (require.main === module) {
  try {
    testNative();
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}

module.exports = { testNative };
