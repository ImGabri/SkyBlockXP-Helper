"""Tests of Rojo source resolution and the executor bundle's public behavior."""

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("suite_builder", ROOT / "scripts/build.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="pet-suite-build-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def source(self, name, contents):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")

    def test_init_and_module_resolve_different_relative_paths(self):
        self.source("init.client.luau", "return require(script.Config)\n")
        self.source("Config.luau", "return require(script.Parent.Group.Value)\n")
        self.source("Group/Value.luau", "return 42\n")
        result = builder.build_bundle(self.root)
        self.assertIn('return __require("Config.luau")', result)
        self.assertIn('return __require("Group/Value.luau")', result)

    def test_nested_init_uses_its_folder_instance(self):
        self.source("init.client.luau", 'return require(script:WaitForChild("Group"))\n')
        self.source("Group/init.luau", "return require(script.Value)\n")
        self.source("Group/Value.luau", 'return require(script.Parent.Parent["Config"])\n')
        self.source("Config.luau", "return 7\n")
        result = builder.build_bundle(self.root)
        self.assertIn('return __require("Group/init.luau")', result)
        self.assertIn('return __require("Group/Value.luau")', result)
        self.assertIn('return __require("Config.luau")', result)

    def test_comments_and_strings_are_not_rewritten(self):
        text = '''-- require(script.Missing)
--[=[ require(missing) ]=]
local quoted = "require(script.Missing)"
local long = [=[require(dynamic)]=]
return quoted .. long
'''
        self.source("init.client.luau", text)
        self.assertIn(text, builder.build_bundle(self.root))

    def test_missing_and_dynamic_requires_fail(self):
        for expression in ["script.Missing", "someVariable", "game.ReplicatedStorage.Library", 'script:WaitForChild(name)', "script.Parent.Config"]:
            with self.subTest(expression=expression):
                self.source("init.client.luau", f"return require({expression})\n")
                with self.assertRaises(builder.BuildError):
                    builder.build_bundle(self.root)

    def test_missing_intermediate_instance_is_not_hidden_by_parent(self):
        self.source("init.client.luau", "return require(script.Missing.Parent.Config)\n")
        self.source("Config.luau", "return {}\n")
        with self.assertRaisesRegex(builder.BuildError, "Unknown source Instance"):
            builder.build_bundle(self.root)

    def test_shorthand_require_is_rejected(self):
        for expression in ['"External"', "[[External]]", "{}"]:
            with self.subTest(expression=expression):
                self.source("init.client.luau", f"return require {expression}\n")
                with self.assertRaises(builder.BuildError):
                    builder.build_bundle(self.root)

    def test_duplicate_init_and_file_folder_collisions_fail(self):
        self.source("init.client.luau", "return nil\n")
        self.source("Config.luau", "return {}\n")
        self.source("Config/init.luau", "return {}\n")
        with self.assertRaisesRegex(builder.BuildError, "collision|Duplicate"):
            builder.build_bundle(self.root)

    def test_missing_entry_fails(self):
        self.source("Config.luau", "return {}\n")
        with self.assertRaisesRegex(builder.BuildError, "entry point"):
            builder.build_bundle(self.root)

    def test_bundle_is_deterministic_and_check_detects_stale_output(self):
        self.source("init.client.luau", "return require(script.Config)\n")
        self.source("Config.luau", "return 42\n")
        first = builder.build_bundle(self.root)
        self.assertEqual(first, builder.build_bundle(self.root))
        output = self.root / "dist/result.lua"
        arguments = ["--source-dir", str(self.root), "--output", str(output)]
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(builder.main(arguments + ["--check"]), 1)
            self.assertEqual(builder.main(arguments), 0)
            self.assertEqual(builder.main(arguments + ["--check"]), 0)
            self.source("Config.luau", "return 43\n")
            self.assertEqual(builder.main(arguments + ["--check"]), 1)

    def run_luau(self, source):
        executable = ROOT / ".tools/bin/luau"
        if not executable.is_file():
            self.skipTest("Luau CLI is not installed")
        output = self.root / "bundle.lua"
        output.write_text(source, encoding="utf-8")
        return subprocess.run([str(executable), str(output)], capture_output=True, text=True, timeout=10)

    def test_runtime_loads_modules_once_and_returns_result(self):
        self.source("init.client.luau", '''local first = require(script.Config)
local second = require(script.Config)
assert(first == second, "module was not cached")
assert(first.value == 42)
print("CACHE_OK")
''')
        self.source("Config.luau", "return { value = 42 }\n")
        result = self.run_luau(builder.build_bundle(self.root))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CACHE_OK", result.stdout)

    def test_runtime_reports_circular_dependencies(self):
        self.source("init.client.luau", "return require(script.First)\n")
        self.source("First.luau", "return require(script.Parent.Second)\n")
        self.source("Second.luau", "return require(script.Parent.First)\n")
        result = self.run_luau(builder.build_bundle(self.root))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Circular module dependency: First.luau", result.stderr)

    def test_runtime_annotates_failed_module(self):
        self.source("init.client.luau", "return require(script.Config)\n")
        self.source("Config.luau", 'error("fixture failure")\n')
        result = self.run_luau(builder.build_bundle(self.root))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Module Config.luau failed:", result.stderr)
        self.assertIn("fixture failure", result.stderr)


if __name__ == "__main__":
    unittest.main()
