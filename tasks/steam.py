from renpybuild.context import Context
from renpybuild.task import task
import zipfile


STEAMWORKS_SDK = "steamworks_sdk_165.zip"

STEAM_DLLS = {
    ("linux", "x86_64"): "{{ host }}/steam/sdk/redistributable_bin/linux64/libsteam_api.so",
    ("linux", "aarch64"): "{{ host }}/steam/sdk/redistributable_bin/linuxarm64/libsteam_api.so",
    ("windows", "x86_64"): "{{ host }}/steam/sdk/redistributable_bin/win64/steam_api64.dll",
    ("mac", "x86_64"): "{{ host }}/steam/sdk/redistributable_bin/osx/libsteam_api.dylib",
    ("mac", "arm64"): "{{ host }}/steam/sdk/redistributable_bin/osx/libsteam_api.dylib",
}


@task(kind="host", platforms="all")
def unpack_sdk(c: Context):

    c.clean("{{ install }}/steam")

    sdk = c.path("{{ tars }}/" + STEAMWORKS_SDK)

    if not sdk.exists():
        return

    with zipfile.ZipFile(sdk) as zf:
        zf.extractall(c.path("{{ install }}/steam"))


@task(kind="host", platforms="all")
def patch_sdk(c: Context):

    if not c.path("{{host}}/steam/sdk").exists():
        return

    c.chdir("{{ install }}/steam/sdk")
    # c.patch("steam-cdecl.diff")


@task(kind="python", platforms="linux,windows,mac", always=True)
def build(c: Context):

    if not c.path("{{host}}/steam/sdk").exists():
        return

    steamdll = STEAM_DLLS.get((c.platform, c.arch))
    if steamdll is None:
        return

    c.var("steamdll", steamdll)
    c.run("cp {{steamdll}} {{dlpa}}")

    c.run("install -d {{pytmp}}/steam")
    c.run("{{ root }}/steamapi/generate.py {{ host }}/steam/sdk/public/steam/steam_api.json {{ pytmp }}/steam/steamapi.py")

    c.run("cp {{ pytmp }}/steam/steamapi.py {{renpy}}/steamapi.py")
