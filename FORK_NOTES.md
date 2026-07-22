# Public fork notes

This branch is a clean, publication-ready reconstruction of the companion
Ren'Py build fork. It is based on upstream commit
`7c68c1b4b28b297fa1febdf305481d65c4da0452`.

## Main changes

- FFmpeg upgraded from 4.3.1 to 7.1.1.
- dav1d 1.5.0 added for AV1 decoding.
- Windows D3D11VA, Android MediaCodec, and Apple VideoToolbox integration.
- Additional ARM architecture mappings for dav1d.
- Updated Ren'Py/Python build and link tasks, including pthread fixes.
- Custom Ren'Py C/Cython modules are built and linked on supported platforms.

FFmpeg is explicitly configured with `--disable-gpl` and
`--disable-nonfree`. The resulting FFmpeg build remains under the LGPL.
FFmpeg, Fribidi, and other LGPL libraries are statically linked into some
runtime artifacts, so binary distributors must follow `SOURCE_OFFER.md`.

VMProtect and its SDK are not included, enabled, or linked by this public
branch. Generated Gradle caches are ignored.
