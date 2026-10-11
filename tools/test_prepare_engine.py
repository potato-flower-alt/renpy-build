"""Exercise companion checkout preparation with local Git repositories."""

import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("prepare_engine", Path(__file__).with_name("prepare_engine.py"))
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


class PrepareEngineTests(unittest.TestCase):
    def setUp(self):
        from renpybuild.engine import COMMON_FILES, DESKTOP_FILES

        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.origin = self.root / "origin"
        self.engine = self.root / "engine"
        self.origin.mkdir()
        self.run_git(self.origin, "init", "-b", "main")
        self.run_git(self.origin, "config", "user.name", "Engine Test")
        self.run_git(self.origin, "config", "user.email", "engine-test@example.invalid")
        for relative in (*COMMON_FILES, *DESKTOP_FILES, "src/nativefiledialog_mac.mm"):
            path = self.origin / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        (self.origin / "src/Setup").write_text(
            "renpy.audio.renpysound audio.c spectrum.c\nrenpy.gl2.gl2statecache state.c\n")
        (self.origin / "src/Setup.nativefiledialog").write_text(
            "renpy._nativefiledialog native.cc nativefiledialog.cc\n")
        self.commit("initial")

    def run_git(self, root, *args):
        return subprocess.check_output(["git", "-C", str(root), *args], text=True, stderr=subprocess.PIPE).strip()

    def commit(self, message):
        self.run_git(self.origin, "add", ".")
        self.run_git(self.origin, "-c", "commit.gpgsign=false", "commit", "-m", message)

    def prepare(self):
        prepare.prepare_engine(self.engine, str(self.origin))

    def test_clone_uses_companion_main_and_updates_fast_forward(self):
        self.prepare()
        self.assertEqual(self.run_git(self.engine, "branch", "--show-current"), "main")
        self.assertEqual(self.run_git(self.engine, "rev-parse", "HEAD"), self.run_git(self.origin, "rev-parse", "HEAD"))
        (self.origin / "new-source.txt").write_text("new engine source")
        self.commit("update")
        self.prepare()
        self.assertEqual((self.engine / "new-source.txt").read_text(), "new engine source")

    def test_wrong_origin_is_rejected_without_changing_checkout(self):
        self.prepare()
        previous = self.run_git(self.engine, "rev-parse", "HEAD")
        self.run_git(self.engine, "remote", "set-url", "origin", str(self.root / "unrelated"))
        with self.assertRaisesRegex(ValueError, "different origin"):
            self.prepare()
        self.assertEqual(self.run_git(self.engine, "rev-parse", "HEAD"), previous)

    def test_local_changes_are_preserved(self):
        self.prepare()
        source = self.engine / "src/spectrum.c"
        source.write_text("local source edits")
        with self.assertRaisesRegex(ValueError, "local changes"):
            self.prepare()
        self.assertEqual(source.read_text(), "local source edits")

    def test_incomplete_engine_is_rejected_after_clone(self):
        (self.origin / "src/Setup.nativefiledialog").unlink()
        self.commit("old engine")
        with self.assertRaisesRegex(ValueError, "Setup.nativefiledialog"):
            self.prepare()

    def test_existing_non_git_sources_are_preserved(self):
        self.engine.mkdir()
        source = self.engine / "private-source.txt"
        source.write_text("preserve")
        with self.assertRaisesRegex(ValueError, "not a Git checkout"):
            self.prepare()
        self.assertEqual(source.read_text(), "preserve")

    def test_diverged_history_is_not_reset(self):
        self.prepare()
        self.run_git(self.engine, "config", "user.name", "Engine Test")
        self.run_git(self.engine, "config", "user.email", "engine-test@example.invalid")
        (self.engine / "local.txt").write_text("local commit")
        self.run_git(self.engine, "add", ".")
        self.run_git(self.engine, "-c", "commit.gpgsign=false", "commit", "-m", "local")
        previous = self.run_git(self.engine, "rev-parse", "HEAD")
        (self.origin / "remote.txt").write_text("remote commit")
        self.commit("remote")
        with self.assertRaises(subprocess.CalledProcessError):
            self.prepare()
        self.assertEqual(self.run_git(self.engine, "rev-parse", "HEAD"), previous)
        self.assertEqual((self.engine / "local.txt").read_text(), "local commit")


if __name__ == "__main__":
    unittest.main()
