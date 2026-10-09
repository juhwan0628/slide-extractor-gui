# Additional native runtime notices

Python's SSL extension may include OpenSSL 3.x libraries (libcrypto and libssl). OpenSSL 3.x is licensed under Apache-2.0; the full original license text is supplied as OpenSSL-LICENSE.txt. Copyright is held by The OpenSSL Project Authors and individual contributors. Exact installed-library versions and hashes are recorded in the native audit evidence. This notice supplements THIRD_PARTY_NOTICES.md and does not alter the application's MIT license.

Windows NumPy's OpenBLAS/LAPACK runtime is covered by the wheel's original BSD notices and GCC Runtime Library Exception notices. The actual macOS candidate uses the system Accelerate build of NumPy and contains no libquadmath/libgfortran runtime libraries. The original wheel license texts are preserved in licenses/wheels.

The actual OpenCV module set is core, flann, geometry, imgcodecs, imgproc and python3. flann/geometry are dependencies of the requested image modules and come from the same pinned Apache-2.0 OpenCV source archive. No videoio or FFmpeg codec library is included in this build.
