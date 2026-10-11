"""Rebuild engine runtimes against existing dependencies, in isolated outputs.

Run with the dependency build's Python environment on Linux/WSL. This does not
build dependencies or install into an SDK. Non-Linux targets use --dependencies;
Linux requires separate --linux-dependencies with Focal sysroots and target
installs. See BUILDING.md for current target and release compatibility rules.
"""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from renpybuild.context import Context
from renpybuild.engine import validate_engine
from renpybuild.task import annotators
import renpybuild.run
import tasks.librenpy
import tasks.renpython
from source.check_linux_elf import validate as validate_linux_elf

TARGETS = {
    "windows": ["x86_64"],
    "linux": ["x86_64", "aarch64"],
    "mac": ["x86_64", "arm64"],
    "android": ["arm64_v8a", "armeabi_v7a", "x86_64"],
}


def dependency_roots(dependencies, linux_dependencies, platforms):
    """Select explicit dependency roots before creating or compiling outputs."""
    roots = {platform: dependencies.resolve() for platform in platforms}
    if "linux" not in platforms:
        return roots
    if linux_dependencies is None:
        raise ValueError("Linux requires --linux-dependencies pointing to an isolated Focal dependency build")
    focal = linux_dependencies.resolve()
    if focal == dependencies.resolve():
        raise ValueError("Linux dependencies must be separate from the legacy dependency build")
    for arch, triple in (("x86_64", "x86_64-linux-gnu"), ("aarch64", "aarch64-linux-gnu")):
        sysroot = focal / "tmp" / f"sysroot.linux-{arch}"
        release = sysroot / "etc/os-release"
        if not release.is_file() or 'VERSION_ID="20.04"' not in release.read_text():
            raise ValueError(f"Missing Ubuntu 20.04 sysroot: {sysroot}")
        for path in (sysroot / "usr/include/stdio.h", sysroot / f"usr/lib/gcc/{triple}/9"):
            if not path.exists() or not path.resolve().is_relative_to(sysroot.resolve()):
                raise ValueError(f"Missing or escaping Focal toolchain input: {path}")
    roots["linux"] = focal
    return roots


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dependencies", type=Path, required=True)
    parser.add_argument("--linux-dependencies", type=Path, help="isolated Ubuntu 20.04 target dependency build")
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--platforms", default=",".join(TARGETS))
    parser.add_argument("--skip-generate", action="store_true")
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--check-only", action="store_true", help="validate inputs without generating or compiling")
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    platforms = args.platforms.split(",")
    if any(p not in TARGETS for p in platforms):
        parser.error("supported platforms: " + ", ".join(TARGETS))
    deps, engine, output, stage = (
        p.resolve() for p in (args.dependencies, args.engine, args.output, args.stage)
    )
    runtime = Path(__file__).resolve().parents[1] / "runtime"
    try:
        validate_engine(engine, platforms)
        roots = dependency_roots(deps, args.linux_dependencies, platforms)
    except ValueError as error:
        parser.error(str(error))
    for dest in (output, stage):
        for protected in (engine, *roots.values()):
            if dest.is_relative_to(protected) or protected.is_relative_to(dest):
                parser.error("output/stage overlaps source or dependencies: " + str(dest))
    if output.is_relative_to(stage) or stage.is_relative_to(output):
        parser.error("output and stage must be separate directories")
    targets = [(p, a) for p in platforms for a in TARGETS[p]]
    for platform, arch in targets:
        install = roots[platform] / "tmp" / f"install.{platform}-{arch}"
        if not (install / "lib/libSDL2.a").is_file():
            parser.error("missing dependency install: " + str(install))
    if args.check_only:
        print(json.dumps({platform: str(root) for platform, root in roots.items()}, indent=2))
        return
    output.mkdir(parents=True, exist_ok=True)
    stage.mkdir(parents=True, exist_ok=True)
    # Limit compiler processes; do not modify the dependency build's task cache.
    slots = threading.Semaphore(args.jobs)
    original_command_run = renpybuild.run.RunCommand.run

    def limited_run(command):
        with slots:
            return original_command_run(command)

    renpybuild.run.RunCommand.run = limited_run
    build_args = SimpleNamespace(nostrip=False, sdl=False, experimental=False)

    def context(platform, arch, kind, task, name):
        dependency_root = roots[platform] if kind == "python" else deps
        c = Context(platform, arch, "3", dependency_root, build_args)
        c.renpy = engine
        c.var("renpy", engine)
        c.var("runtime", runtime)
        c.set_names(kind, task, name)
        c.build = output / f"{platform}-{arch}" / name
        c.build.mkdir(parents=True, exist_ok=True)
        c.cwd = c.build
        c.var("build", c.build)
        dest = stage / f"{platform}-{arch}"
        c.var("dlpa", dest)
        c.var("jniLibs", dest)
        abi = arch.replace("_", "-") if "arm" in arch else arch
        c.var("jni_unstripped", stage / "symbols" / abi)
        for annotate in annotators:
            annotate(c)
        original_run = c.run

        def run(command, *args, **kwargs):
            command = command.replace("{{ install }}/mac{{python}}", str(dest))
            return original_run(command, *args, **kwargs)

        c.run = run
        return c

    if not args.skip_generate:
        print("GENERATE STATIC CYTHON", flush=True)
        tasks.librenpy.gen_static3(
            context("linux", "x86_64", "host-python", "gen_static3", "librenpy")
        )
    for platform, arch in targets:
        key = f"{platform}-{arch}"
        marker = stage / (key + ".complete.json")
        marker.unlink(missing_ok=True)
        started = time.monotonic()
        print("BUILD START", key, flush=True)
        c = context(platform, arch, "python", "build", "librenpy")
        c.env("CFLAGS", "{{ CFLAGS }} -I{{ renpy }}/tmp/gen3-static")
        c.env("CXXFLAGS", "{{ CXXFLAGS }} -I{{ renpy }}/tmp/gen3-static")
        original_copy = c.copy

        def copy(src, dst):
            if dst == "{{ install }}/lib/librenpy.a":
                return  # Preserve installed dependency archives.
            return original_copy(src, dst)

        c.copy = copy
        tasks.librenpy.build(c)
        c = context(platform, arch, "python", "build", "renpython")
        c.env("LDFLAGS", "-L" + str(output / key / "librenpy") + " {{ LDFLAGS }}")
        if platform == "android":
            tasks.renpython.build_android(c)
        else:
            tasks.renpython.build(c)
        getattr(tasks.renpython, "link_" + platform)(c)
        if platform == "linux":
            report = validate_linux_elf(stage / key, roots[platform] / "tmp" / f"sysroot.linux-{arch}", arch)
            (stage / key / "elf-compatibility.json").write_text(json.dumps(report, indent=2) + "\n")
            if report["errors"]:
                raise RuntimeError("Linux release compatibility check failed:\n" + "\n".join(report["errors"]))
        seconds = time.monotonic() - started
        marker.write_text(json.dumps({"target": key, "seconds": seconds}, indent=2))
        print("BUILD COMPLETE", key, round(seconds, 1), "seconds", flush=True)
    if "mac" in platforms:
        universal = stage / "mac-universal"
        universal.mkdir(exist_ok=True)
        for name in ["librenpython.dylib", "python", "pythonw", "renpy"]:
            subprocess.run(
                [
                    "llvm-lipo-18",
                    "-create",
                    "-output",
                    str(universal / name),
                    str(stage / "mac-x86_64" / name),
                    str(stage / "mac-arm64" / name),
                ],
                check=True,
            )
        print("MAC UNIVERSAL COMPLETE", flush=True)
    print("REQUESTED BUILDS COMPLETE", flush=True)


if __name__ == "__main__":
    main()
