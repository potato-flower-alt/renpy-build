"""Prevent incremental builds from silently reusing legacy Linux dependencies."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("build_runtime", Path(__file__).with_name("build_runtime.py"))
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class DependencyRootsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.legacy = self.root / "legacy"
        self.focal = self.root / "focal"

    def make_focal(self):
        for arch, triple in (("x86_64", "x86_64-linux-gnu"), ("aarch64", "aarch64-linux-gnu")):
            sysroot = self.focal / "tmp" / f"sysroot.linux-{arch}"
            (sysroot / "etc").mkdir(parents=True)
            (sysroot / "etc/os-release").write_text('VERSION_ID="20.04"\n')
            (sysroot / "usr/include").mkdir(parents=True)
            (sysroot / "usr/include/stdio.h").touch()
            (sysroot / f"usr/lib/gcc/{triple}/9").mkdir(parents=True)

    def test_non_linux_build_keeps_compatible_dependencies(self):
        self.assertEqual(runtime.dependency_roots(self.legacy, None, ["windows"]),
                         {"windows": self.legacy.resolve()})

    def test_linux_requires_explicit_dependency_root(self):
        with self.assertRaisesRegex(ValueError, "--linux-dependencies"):
            runtime.dependency_roots(self.legacy, None, ["linux"])

    def test_linux_rejects_shared_legacy_dependency_root(self):
        with self.assertRaisesRegex(ValueError, "separate"):
            runtime.dependency_roots(self.legacy, self.legacy, ["linux"])

    def test_linux_rejects_non_focal_or_incomplete_sysroots(self):
        with self.assertRaisesRegex(ValueError, "20.04"):
            runtime.dependency_roots(self.legacy, self.focal, ["linux"])
        self.make_focal()
        release = self.focal / "tmp/sysroot.linux-aarch64/etc/os-release"
        release.write_text('VERSION_ID="24.04"\n')
        with self.assertRaisesRegex(ValueError, "20.04"):
            runtime.dependency_roots(self.legacy, self.focal, ["linux"])

    def test_linux_uses_focal_while_other_targets_keep_legacy_dependencies(self):
        self.make_focal()
        self.assertEqual(runtime.dependency_roots(self.legacy, self.focal, ["windows", "linux", "android"]),
                         {"windows": self.legacy.resolve(), "linux": self.focal.resolve(),
                          "android": self.legacy.resolve()})


if __name__ == "__main__":
    unittest.main()
