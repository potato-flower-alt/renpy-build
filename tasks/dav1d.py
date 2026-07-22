# Copyright 2026 The Ren'Py fork contributors
# SPDX-License-Identifier: MIT

from renpybuild.context import Context
from renpybuild.task import task

version = "1.5.0"


@task(kind="host", platforms="all")
def download(c: Context):

    if c.path("{{ tmp }}/source/dav1d").exists():
        c.chdir("{{ tmp }}/source/dav1d")
        c.run("git checkout master")
        c.run("git pull")
        c.run("git checkout " + version)
        return

    c.clean("{{ tmp }}/source/dav1d")
    c.chdir("{{ tmp }}/source")

    c.run("git clone https://code.videolan.org/videolan/dav1d.git")
    c.chdir("{{ tmp }}/source/dav1d")
    c.run("git checkout " + version)


@task(platforms="-web,ios")
def build(c: Context):
    c.clean()

    # Determine if we're cross-compiling. The build host is Linux x86_64.
    is_cross = not (c.platform == "linux" and c.arch == "x86_64")

    cross_arg = ""
    if is_cross:
        # Map platform/arch to meson system/cpu identifiers.
        system_map = {
            "windows": "windows",
            "linux": "linux",
            "mac": "darwin",
            "ios": "darwin",
            "android": "android",
        }
        cpu_family_map = {
            "x86_64": "x86_64",
            "aarch64": "aarch64",
            "arm64": "aarch64",
            "arm64_v8a": "aarch64",
            "armv7l": "arm",
            "armeabi_v7a": "arm",
        }
        cpu_map = {
            "x86_64": "x86_64",
            "aarch64": "aarch64",
            "arm64": "aarch64",
            "arm64_v8a": "aarch64",
            "armv7l": "armv7hl",
            "armeabi_v7a": "armv7hl",
        }

        meson_system = system_map.get(c.platform, "linux")
        cpu_family = cpu_family_map.get(c.arch, "x86_64")
        cpu = cpu_map.get(c.arch, "x86_64")

        cross_file = c.expand("{{ build }}/meson-cross.ini")
        with open(cross_file, "w") as f:
            f.write("[host_machine]\n")
            f.write(f"system = '{meson_system}'\n")
            f.write(f"cpu_family = '{cpu_family}'\n")
            f.write(f"cpu = '{cpu}'\n")
            f.write("endian = 'little'\n")

        cross_arg = f"--cross-file {cross_file}"

    c.var("dav1d_cross_arg", cross_arg)

    c.chdir("{{ tmp }}/source/dav1d")

    # Meson adds -Werror=unused-command-line-argument to test compilations,
    # which conflicts with -fuse-ld=lld in CC. Remove -fuse-ld=lld from CC
    # for the meson invocation (it's a linker flag, not a compiler flag).
    saved_cc = c.environ.get("CC", "")
    c.env("CC", saved_cc.replace("-fuse-ld=lld ", "").replace("-fuse-ld=lld", ""))

    c.run("""
        meson setup {{ build }}/dav1d-build {{ dav1d_cross_arg }} \
            --prefix={{ install }} \
            --buildtype=release \
            --default-library=static \
            -Denable_tools=false \
            -Denable_tests=false \
            -Denable_examples=false
        """)

    # Restore CC for subsequent tasks
    c.env("CC", saved_cc)

    c.run("ninja -C {{ build }}/dav1d-build")
    c.run("ninja -C {{ build }}/dav1d-build install")
