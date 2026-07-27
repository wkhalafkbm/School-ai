// Preflight for the test stack.
//
// vitest 4 (via vite and jsdom) needs Node's require(ESM) support, which was
// unflagged in 22.12. Below that line the run dies with an ERR_REQUIRE_ESM
// raised deep inside vitest's config loader or jsdom's dependency chain — a
// stack trace that names neither Node nor the version that caused it, and reads
// like a broken dependency rather than a wrong interpreter.
//
// So check here first and say the actual thing. Kept dependency-free and in
// plain ESM: this has to run correctly on the very versions it rejects.

const [major, minor] = process.versions.node.split(".").map(Number);

// Mirrors "engines.node" in package.json, which is vite's floor intersected
// with vitest's. 22.11 and below are the versions this exists to catch.
const supported =
  (major === 20 && minor >= 19) || (major === 22 && minor >= 12) || major >= 24;

if (!supported) {
  console.error(
    [
      "",
      `  Node ${process.versions.node} cannot run this test suite.`,
      "",
      "  Required: ^20.19.0 || ^22.12.0 || >=24",
      "  The suite needs require(ESM), which Node added in 22.12.",
      "",
      "  This repo pins a supported version in .nvmrc:",
      "",
      "      nvm use        # from the repo root",
      "",
    ].join("\n"),
  );
  process.exit(1);
}
