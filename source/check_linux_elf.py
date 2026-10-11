#!/usr/bin/env python3
"""Reject packaged ELF files incompatible with the Focal target runtime.

Run against the complete staged runtime, including proprietary libraries and
distribution tools. Resolution never consults the build host's loader cache.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess


MACHINES = {"x86_64": "Advanced Micro Devices X86-64", "aarch64": "AArch64"}


def readelf(path, option):
    return subprocess.check_output(["readelf", option, "--wide", str(path)], text=True, env={**os.environ, "LC_ALL": "C"})


def inspect(path):
    header = readelf(path, "-h")
    dynamic = readelf(path, "-d")
    versions = readelf(path, "-V")
    program = readelf(path, "-l")
    return {
        "path": str(path),
        "machine": re.search(r"Machine:\s*(.+)", header)[1].strip(),
        "class": re.search(r"Class:\s*(.+)", header)[1].strip(),
        "needed": re.findall(r"\(NEEDED\).*\[(.*?)\]", dynamic),
        "rpath": re.findall(r"\((?:RUNPATH|RPATH)\).*\[(.*?)\]", dynamic),
        "versions": sorted(set(re.findall(r"Name: (GLIBC(?:XX)?_[\w.]+|CXXABI_[\w.]+)", versions))),
        "interpreter": re.findall(r"Requesting program interpreter: (.*?)\]", program),
    }


def validate(root, sysroot, arch):
    root, sysroot = Path(root).resolve(), Path(sysroot).resolve()
    errors, records = [], []
    target_dirs = [sysroot / d for d in ("lib", "lib64", "usr/lib", "usr/lib64")]
    triple = "x86_64-linux-gnu" if arch == "x86_64" else "aarch64-linux-gnu"
    target_dirs.extend([sysroot / "lib" / triple, sysroot / "usr/lib" / triple])
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        with path.open("rb") as f:
            if f.read(4) != b"\x7fELF":
                continue
        if not path.resolve().is_relative_to(root):
            errors.append(f"{path}: packaged ELF symlink escapes staging directory")
        record = inspect(path)
        records.append(record)
        if record["machine"] != MACHINES[arch] or record["class"] != "ELF64":
            errors.append(f"{path}: wrong ELF architecture")
        for version in record["versions"]:
            if version.startswith("GLIBC_"):
                value = version.removeprefix("GLIBC_")
                if not re.fullmatch(r"\d+(?:\.\d+)+", value) or tuple(map(int, value.split("."))) > (2, 31):
                    errors.append(f"{path}: unsupported {version}")
        search = []
        for group in record["rpath"]:
            for entry in group.split(":"):
                if not entry.startswith(("$ORIGIN", "${ORIGIN}")):
                    errors.append(f"{path}: non-relative RPATH {entry!r}")
                    continue
                resolved = Path(entry.replace("${ORIGIN}", str(path.parent)).replace("$ORIGIN", str(path.parent))).resolve()
                if not resolved.is_relative_to(root):
                    errors.append(f"{path}: RPATH escapes package: {entry}")
                else:
                    search.append(resolved)
        for dependency in record["needed"]:
            if "/" in dependency:
                errors.append(f"{path}: absolute dependency {dependency}")
                continue
            found = next((directory / dependency for directory in search + target_dirs if (directory / dependency).is_file()), None)
            if found is None:
                errors.append(f"{path}: unresolved dependency {dependency}")
                continue
            allowed = root if found.is_relative_to(root) else sysroot
            if not found.resolve().is_relative_to(allowed):
                errors.append(f"{path}: dependency symlink escapes target: {found}")
            elif inspect(found)["machine"] != MACHINES[arch]:
                errors.append(f"{path}: wrong dependency architecture: {found}")
        for interpreter in record["interpreter"]:
            loader = sysroot / interpreter.lstrip("/")
            if not loader.is_file() or not loader.resolve().is_relative_to(sysroot):
                errors.append(f"{path}: invalid target interpreter {interpreter}")
    if not records:
        errors.append(f"{root}: no ELF files found")
    return {"arch": arch, "glibc_limit": "2.31", "files": records, "errors": errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--sysroot", type=Path, required=True)
    parser.add_argument("--arch", choices=MACHINES, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = validate(args.root, args.sysroot, args.arch)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for error in report["errors"]:
        print(error)
    print(f"Checked {len(report['files'])} ELF files for {args.arch}")
    raise SystemExit(bool(report["errors"]))


if __name__ == "__main__":
    main()
