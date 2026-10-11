# SDL2 fork build and release guide

Updated 2026-10-11. This is the build entry point for this public fork.
The build host is Ubuntu 24.04; Linux target runtimes use Ubuntu 20.04 Focal.

## Source and targets

Use matching revisions of the public [engine](https://github.com/potato-flower-alt/renpy)
and [build system](https://github.com/potato-flower-alt/renpy-build).
The 2026-10-11 synchronization includes engine source through `3abc3712dab2`
and build source through `539ec99` from the local SDL2 branch.

This fork uses SDL2, Python 3.12, FFmpeg 7.1.1, the legacy GL2/GLSL renderer,
and its own media and Live2D implementations. Upstream SDL3 nightly binaries
cannot replace the matching runtime.

Explicitly select the intended platforms:

- Windows x86_64.
- Linux x86_64 and aarch64.
- macOS universal x86_64 and arm64.
- Android arm64-v8a, armeabi-v7a, and x86_64.

The generic build command also defaults to iOS and Web. Put CLI options before
the subcommand, for example `./build.sh --platform windows rebuild librenpy renpython`.
Commercial SDKs are not distributed here. Follow `FORK_NOTES.md`, the engine's
`SECURITY_BUILD.md`, and `SOURCE_OFFER.md` when preparing your own private build.

## Dependency boundaries

Prepare two independent dependency roots using these build rules:

- A compatible dependency build for host tooling and Windows/macOS/Android.
- An isolated Focal dependency build for all Linux target libraries and CPython.

Every packaged Linux ELF must require GLIBC <= 2.31. Linux targets use Focal
GCC 9 and its C++ runtime with restricted sysroot, pkg-config, and CMake searches.
x86_64 uses GNU ld; aarch64 uses LLD. Host tools continue using the host environment.
`tasks/sysroot.py` repairs and validates sysroot links; never remove the sysroot
to work around pthread linker errors.

Changing the toolchain, sysroot, or dependency configuration requires a complete
target dependency rebuild in a new isolated directory. Reuse only host tools,
source archives, download caches, and separately obtained compatible Cubism headers.
Do not reuse legacy Linux target libraries or task completion markers.

Review `prepare.sh` before running it: it modifies the host and clones sources.
Use this fork's rules and matching engine source rather than the current upstream
branch. In a prepared isolated Linux dependency root, the dependency phase can
run `python -m renpybuild --platform linux --stop zsync`. Engine compilation and
release validation are separate steps.

## Incremental native builds

Run the checked-out `tools/build_runtime.py` with the dependency build's Python
environment. Do not invoke stale build rules from a dependency cache. Set these
example paths to your own existing prepared directories:

```bash
export PATH=/path/to/compatible-dependencies/renpy/.venv/bin:$PATH
export PYTHONHASHSEED=0
BUILD_ENGINE=/path/to/public/renpy
BUILD_RULES=/path/to/public/renpy-build
BUILD_DEPS=/path/to/compatible-dependencies
BUILD_FOCAL=/path/to/isolated-focal-dependencies
BUILD_OUT=/path/to/new-runtime-output
BUILD_STAGE=/path/to/new-runtime-stage

python "$BUILD_RULES/tools/build_runtime.py" \
  --dependencies "$BUILD_DEPS" --linux-dependencies "$BUILD_FOCAL" \
  --engine "$BUILD_ENGINE" --output "$BUILD_OUT" --stage "$BUILD_STAGE" \
  --platforms windows,linux,mac,android --jobs 2 --check-only
```

After the input check passes, rerun the same command without `--check-only`.
For Windows alone, use `--platforms windows` and omit `--linux-dependencies`.
The tool regenerates static Cython, builds the affected extensions, and stages
runtimes without replacing installed dependency archives or installing an SDK.
Output and staging directories must not overlap sources, dependencies, or each other.

Changes to `.pyx`, `.pxd`, Setup files, or module registration require generation;
do not copy `--skip-generate` from historical commands. Linux staged runtimes are
checked automatically, and a failed compatibility check produces no success marker.
The engine's older `scripts/nativefiledialog_build.py` is a historical helper;
use this entry point for current builds.

## Release checks and SDK deployment

Assemble a complete candidate with matching dependency libraries, optional
Cubism/Steam libraries, distribution tools, and the Python standard library.
Linux distribution tools and target libraries must come from the Focal build.
Check the complete candidate, including libraries and tools beyond the new engine:

```bash
python "$BUILD_RULES/source/check_linux_elf.py" "$BUILD_STAGE/linux-x86_64" \
  --sysroot "$BUILD_FOCAL/tmp/sysroot.linux-x86_64" --arch x86_64 \
  --report "$BUILD_STAGE/elf-linux-x86_64.json"
python "$BUILD_RULES/source/check_linux_elf.py" "$BUILD_STAGE/linux-aarch64" \
  --sysroot "$BUILD_FOCAL/tmp/sysroot.linux-aarch64" --arch aarch64 \
  --report "$BUILD_STAGE/elf-linux-aarch64.json"
```

Verify both architectures and dependency paths for every macOS universal runtime.
Verify Android ELF LOAD alignment of at least 16 KiB and matching offset/address
alignment. Verify Windows PE architecture and imports.

Validate Linux x86_64 startup and modules in Focal userspace, and aarch64 under
QEMU/Focal if hardware is unavailable. Validate Windows GL2/ANGLE2 media, fonts,
meshes, shaders, Live2D pixels, and context reconstruction. Record macOS/Android
device testing separately; cross-compilation is not device runtime validation.

Only then copy selected files into an SDK: matching Python/common sources,
desktop runtimes, macOS application runtimes, Android project/prototype jniLibs,
and Android symbols. Keep the underscore in the x86_64 ABI directory name.
Preserve SDK Android version/name settings and `renpy/vc_version.py`; an SDK's
directory name does not identify its source version. Do not replace entire
lib/rapt trees or create automatic backups. Record source revisions, tests,
logs, and deployed file SHA-256 values.

Live2D requires a separately obtained compatible Cubism Core for each target.
macOS distribution also requires signing and notarization on macOS.

## Tests

With the prepared WSL/Linux dependency Python environment:

```bash
cd /path/to/public/renpy-build
python -m unittest discover -s source -p test_linux_elf.py
python -m unittest discover -s tools -p test_build_runtime.py
```

Engine tests need the matching native runtime:

```bash
cd /path/to/public/renpy
python -m unittest discover -s unittests
python renpy.py testcases test
```

A generic system Python missing native extensions is not a regression result.
The built-in test command is `test`, not `--test`. Lint changed files against
the existing diagnostic baseline and run `git diff --check`. Avoid unrelated
formatting and never copy whole trees over a build's venv, tmp, generated files,
or libraries.
