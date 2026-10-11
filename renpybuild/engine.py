# Copyright 2026 The Ren'Py fork contributors
# SPDX-License-Identifier: MIT

"""Check that engine sources match this SDL2 fork before generating or building."""

from pathlib import Path


COMMON_FILES = (
    "setup.py", "src/Setup", "src/spectrum.c", "src/spectrum.h",
    "renpy/audio/renpysound.pyx", "renpy/gl2/gl2statecache.pyx",
    "renpy/gl2/gl2statecache.pxd",
)
DESKTOP_FILES = (
    "src/Setup.nativefiledialog", "src/nativefiledialog.cc", "src/nativefiledialog.h",
    "renpy/_nativefiledialog.pyx", "renpy/nativefiledialog.py",
)


def setup_modules(path):
    modules = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            fields = line.partition("#")[0].split()
            if fields:
                modules[fields[0]] = fields[1:]
    return modules


def validate_engine(engine, platforms):
    engine = Path(engine).resolve()
    required = list(COMMON_FILES)
    desktop = any(platform in ("windows", "linux", "mac") for platform in platforms)
    if desktop:
        required.extend(DESKTOP_FILES)
    if "mac" in platforms:
        required.append("src/nativefiledialog_mac.mm")
    problems = [f"missing {path}" for path in required if not (engine / path).is_file()]
    modules = setup_modules(engine / "src/Setup")
    if "renpy.gl2.gl2statecache" not in modules:
        problems.append("src/Setup does not register renpy.gl2.gl2statecache")
    if "spectrum.c" not in modules.get("renpy.audio.renpysound", ()):
        problems.append("src/Setup does not compile spectrum.c with renpy.audio.renpysound")
    if desktop:
        native = setup_modules(engine / "src/Setup.nativefiledialog")
        if "nativefiledialog.cc" not in native.get("renpy._nativefiledialog", ()):
            problems.append("src/Setup.nativefiledialog does not register the native file-dialog bridge")
    if problems:
        raise ValueError(
            f"Engine checkout {engine} does not match these SDL2 build rules:\n"
            + "\n".join(problems)
            + "\nSync the matching companion engine source. For incremental builds, pass its path with --engine."
        )
