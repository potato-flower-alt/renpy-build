# Source and relinking information

Ren'Py runtime binaries built by this repository include software under
multiple licenses, including the GNU Lesser General Public License (LGPL).
This repository is intended to provide the exact dependency versions, build
scripts, and link instructions needed to rebuild those binaries.

## Corresponding source

- Modified Ren'Py source: use the companion public `renpy` repository at the
  commit recorded by your release.
- Build and link scripts: this repository at the commit recorded by your
  release.
- FFmpeg 7.1.1 source: `source/ffmpeg-7.1.1.tar.gz`.
- dav1d 1.5.0 source: fetched from the public upstream tag by
  `tasks/dav1d.py`.
- Other dependency source archives and checkout locations are defined by the
  existing tasks and `source/` directory.

The FFmpeg configuration includes native `atempo` filtering and 24-bit PCM WAV
decoding. Native runtime links include `libavfilter`. These build changes use
the same FFmpeg 7.1.1 source archive listed above.

## Binary distributors

For every SDK, game, or runtime release:

1. Keep a permanent tag for both public repositories.
2. Publish the complete source corresponding to that binary release.
3. Include the Ren'Py license documentation and all third-party notices.
4. Because LGPL libraries are statically linked, also provide the source or
   object/relink materials required for recipients to rebuild the combined
   runtime with modified LGPL libraries.
5. Do not prohibit reverse engineering when it is needed to debug such
   modifications.

The exact compliance method depends on the release format and jurisdiction.
Obtain legal review before commercial distribution.
