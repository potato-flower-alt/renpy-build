#!/usr/bin/env python3

import pathlib
import sys
import os


def main():
    root = pathlib.Path(sys.argv[1]).resolve()

    for i in root.rglob("*"):
        if not i.is_symlink():
            continue

        target = os.readlink(i)

        if not target.startswith("/"):
            continue

        if target == str(root) or target.startswith(str(root) + "/"):
            destination = pathlib.Path(target)
        else:
            destination = root / target.lstrip("/")
        target = os.path.relpath(destination, i.parent)

        i.unlink()
        os.symlink(target, i)

        print(i, "->" , target)

    for link in root.rglob("*"):
        if link.is_symlink() and not link.resolve().is_relative_to(root):
            raise RuntimeError(f"Sysroot symlink escapes target: {link}")


if __name__ == "__main__":
    main()
