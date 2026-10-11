import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("linux_elf", Path(__file__).with_name("check_linux_elf.py"))
elf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(elf)


class ReleaseGateTests(unittest.TestCase):
    def check(self, **changes):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "stage"
            sysroot = Path(temporary) / "focal"
            root.mkdir()
            sysroot.mkdir()
            binary = root / "python"
            binary.write_bytes(b"\x7fELF")
            info = dict(path=str(binary), machine=elf.MACHINES["x86_64"], **{"class": "ELF64"},
                        needed=[], rpath=["$ORIGIN"], versions=["GLIBC_2.31"], interpreter=[])
            info.update(changes)
            with patch.object(elf, "inspect", return_value=info):
                return elf.validate(root, sysroot, "x86_64")["errors"]

    def test_focal_limit(self):
        self.assertEqual(self.check(), [])
        self.assertTrue(self.check(versions=["GLIBC_2.32"]))
        self.assertTrue(self.check(versions=["GLIBC_PRIVATE"]))

    def test_wrong_arch_and_missing_dependencies(self):
        self.assertTrue(self.check(machine="AArch64"))
        self.assertTrue(self.check(needed=["libmissing.so"]))
        self.assertTrue(self.check(needed=["/usr/lib/libhost.so"]))

    def test_rpath_and_loader_must_stay_in_target(self):
        self.assertTrue(self.check(rpath=["/root/build/lib"]))
        self.assertTrue(self.check(rpath=["$ORIGIN/../host"]))
        self.assertTrue(self.check(interpreter=["/lib64/ld-linux-x86-64.so.2"]))
