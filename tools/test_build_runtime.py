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


class EngineSourceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.engine = Path(self.directory.name) / "engine"

    def make_engine(self, desktop=False, mac=False):
        from renpybuild.engine import COMMON_FILES, DESKTOP_FILES

        files = list(COMMON_FILES)
        if desktop:
            files.extend(DESKTOP_FILES)
        if mac:
            files.append("src/nativefiledialog_mac.mm")
        for relative in files:
            path = self.engine / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        (self.engine / "src/Setup").write_text(
            "renpy.audio.renpysound ../tmp/gen/audio.c spectrum.c\n"
            "renpy.gl2.gl2statecache ../tmp/gen/state.c\n")
        if desktop:
            (self.engine / "src/Setup.nativefiledialog").write_text(
                "renpy._nativefiledialog ../tmp/gen/native.cc nativefiledialog.cc\n")

    def test_old_engine_is_rejected_for_all_targets(self):
        for platform in ("windows", "linux", "mac", "android", "ios", "web"):
            with self.subTest(platform=platform), self.assertRaisesRegex(ValueError, "--engine"):
                runtime.validate_engine(self.engine, [platform])

    def test_desktop_requires_complete_bridge(self):
        self.make_engine()
        for platform in ("windows", "linux", "mac"):
            with self.subTest(platform=platform), self.assertRaisesRegex(ValueError, "Setup.nativefiledialog"):
                runtime.validate_engine(self.engine, [platform])
        self.make_engine(desktop=True)
        runtime.validate_engine(self.engine, ["windows", "linux"])
        with self.assertRaisesRegex(ValueError, "nativefiledialog_mac.mm"):
            runtime.validate_engine(self.engine, ["mac"])
        self.make_engine(desktop=True, mac=True)
        runtime.validate_engine(self.engine, ["windows", "linux", "mac"])

    def test_mobile_targets_require_new_common_engine_without_desktop_bridge(self):
        self.make_engine()
        runtime.validate_engine(self.engine, ["android", "ios", "web"])
        (self.engine / "src/spectrum.c").unlink()
        with self.assertRaisesRegex(ValueError, "spectrum.c"):
            runtime.validate_engine(self.engine, ["android"])

    def test_setup_registrations_are_required_even_when_files_exist(self):
        self.make_engine(desktop=True)
        (self.engine / "src/Setup").write_text("renpy.audio.renpysound audio.c\n")
        with self.assertRaisesRegex(ValueError, "register renpy.gl2.gl2statecache"):
            runtime.validate_engine(self.engine, ["linux"])
        self.make_engine(desktop=True)
        (self.engine / "src/Setup.nativefiledialog").write_text("# old or incomplete setup\n")
        with self.assertRaisesRegex(ValueError, "register the native file-dialog bridge"):
            runtime.validate_engine(self.engine, ["linux"])

    def test_task_entry_points_reject_before_running_any_commands(self):
        from types import SimpleNamespace
        from tasks import librenpy

        context = SimpleNamespace(renpy=self.engine, platform="android", python="3")
        for entry in (librenpy.gen_static3, librenpy.build):
            with self.subTest(entry=entry.__name__), self.assertRaisesRegex(ValueError, "matching companion engine"):
                entry(context)

    def test_check_only_rejects_old_engine_without_creating_outputs(self):
        import subprocess
        import sys

        root = self.engine.parent
        output, stage = root / "output", root / "stage"
        result = subprocess.run([
            sys.executable, str(Path(__file__).with_name("build_runtime.py")),
            "--dependencies", str(root / "dependencies"), "--engine", str(self.engine),
            "--output", str(output), "--stage", str(stage), "--platforms", "windows", "--check-only",
        ], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("does not match these SDL2 build rules", result.stderr)
        self.assertFalse(output.exists())
        self.assertFalse(stage.exists())


if __name__ == "__main__":
    unittest.main()
