Tars
====

Public dependency sources
-------------------------

The public fork builds FFmpeg 7.1.1. Its exact corresponding source archive
is committed as ``source/ffmpeg-7.1.1.tar.gz`` and is also available from:

https://ffmpeg.org/releases/ffmpeg-7.1.1.tar.gz

SHA-256: ``bfb2261a9b46e71880aeb2d0caa3f8a8205fce606ee53b25c351f04fa7809e96``

dav1d is checked out by ``tasks/dav1d.py`` from its public upstream repository
at tag ``1.5.0``. Neither dependency is locally patched by this fork.

The following proprietary platform SDKs are optional and are not committed.

This directory is for source files too big (or too poorly licensed) to go
into github. Right now, it needs:

Xcode
-----

* MacOSX12.3.sdk.tar.bz2

Created as described at https://github.com/tpoechtrager/osxcross#packaging-the-sdk .
This old version is required to ensure that Ren'Py runs on older versions of
macOS.

* iPhoneOS14.0.sdk.tar.gz
* iPhoneSimulator14.0.sdk.tar.gz

Run ./ios_toolchains.sh /path/to/Xcode.app

Android NDK
-----------

* android-ndk-r27c-linux.zip

Downloaded from https://developer.android.com/ndk/downloads .

Live2D Cubism SDK for Native
----------------------------

* CubismSDKforNative-4-r.6.2.zip

Downloaded from https://www.live2d.com/en/download/cubism-sdk/ .

Steamworks SDK
--------------

* steamworks_sdk_165.zip

Downloaded from https://partner.steamgames.com/doc/sdk , which is only
available to Steam partners. Ren'Py will build without the Steamworks
SDK.
