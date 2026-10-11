from renpybuild.task import task


@task(kind="python", platforms="linux", archs="x86_64,aarch64", always=True)
def check_release(c):
    """Gate all Linux runtime ELF files, including distribution tools."""
    c.run("python3 {{source}}/check_linux_elf.py {{dlpa}} --sysroot {{sysroot}} --arch {{c.arch}} --report {{dlpa}}/elf-compatibility.json")
