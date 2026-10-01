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
- Native FFmpeg `atempo` filtering and `libavfilter` runtime links.
- 24-bit PCM WAV decoding on native platforms and the web.
- Android SDL text-input fix for ordinary, non-password input fields.
- LLVM lipo 18 and target-aware dav1d/Python linker fixes.
- Pinned pyobjus source downloads and optional Steamworks SDK 165 support,
  including Linux ARM64 redistributables.

## October 2026 synchronization

Source changes through build revision `aa1725b` were synchronized on
2026-10-01, together with engine changes through `294bdcb12`. The existing
public history, FFmpeg source archive, licensing flags, and publication
cleanup are retained. Generated Gradle caches and commercial SDK binaries
remain excluded.

FFmpeg is explicitly configured with `--disable-gpl` and
`--disable-nonfree`. The resulting FFmpeg build remains under the LGPL.
FFmpeg, Fribidi, and other LGPL libraries are statically linked into some
runtime artifacts, so binary distributors must follow `SOURCE_OFFER.md`.

VMProtect and its SDK are not included, enabled, or linked by this public
branch. Generated Gradle caches are ignored.
