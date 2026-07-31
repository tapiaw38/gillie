"use strict";

const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

test("the app launches the real listener runtime, never a demo one", () => {
  const projectRoot = path.join(__dirname, "..");
  const packageJson = JSON.parse(
    fs.readFileSync(path.join(projectRoot, "package.json"), "utf8"),
  );
  const mainProcess = fs.readFileSync(
    path.join(projectRoot, "electron", "main", "index.ts"),
    "utf8",
  );

  assert.equal(packageJson.scripts.dev, "electron-vite dev");
  assert.equal(packageJson.scripts.build, "electron-vite build");
  assert.doesNotMatch(mainProcess, /--demo|demoMode|startDemo/);
});
