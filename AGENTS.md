# Build entry point

Read [BUILDING.md](BUILDING.md) before building this SDL2 fork. The Ubuntu 24.04
host and Ubuntu 20.04 Focal Linux targets have different dependency requirements.

After build-rule changes, run the `source/test_linux_elf.py` and
`tools/test_build_runtime.py` unittest suites with the dependency Python environment.
Use this checkout's `tools/build_runtime.py`, starting with `--check-only`.
Linux requires a separate explicit `--linux-dependencies` root; every ELF in
a complete release must satisfy GLIBC <= 2.31.

Select Windows, Linux, macOS, and Android explicitly. Historical helper scripts,
upstream reference checkouts, and cached rules are not current build instructions.
