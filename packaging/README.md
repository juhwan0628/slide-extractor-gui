# Release licensing and packaging gate

Status: RELEASE HOLD. Actual Windows/macOS installer artifacts have not been built or approved.

## Decisions
- Windows x64: PyInstaller onedir, Inno Setup installer, optional portable ZIP.
- macOS arm64: PyInstaller .app plus DMG. Native runners for each platform.
- Qt/PySide6: dynamic LGPLv3 Qt libraries. Provide corresponding Qt source from under our control or compliant written offer, full license notices, and test replacement/relink and running modified libraries. A link to upstream alone is insufficient.
- FFmpeg/ffprobe: separate subprocess executables. Select actual LGPL-built binaries for each OS, without enable-gpl or enable-nonfree. Keep exact build flags, SHA256, source release matching binaries, modification and license notices. The Ubuntu server FFmpeg has enable-gpl and must NOT be copied to a release.
- OpenCV headless wheels have bundled LGPL FFmpeg; audit platform-specific wheels and LICENSE-3RD-PARTY.txt separately.
- qpdf is optional Apache-2.0 optimization. ReportLab BSD is PDF backend, never PyMuPDF.
- All wheels and native binaries must be pinned and inventoried per platform. Ship licenses, source access/offer, notices, and SBOM.

## Gate checklist
- [x] Remove unused SSIM/scikit-image dependency (2026-10-08).
- [x] Inspect GPL-enabled Ubuntu server FFmpeg and reject it as LGPL distribution build.
- [x] Set LGPL Qt and FFmpeg compliance requirements.
- [ ] Obtain and hash LGPL FFmpeg/ffprobe for Windows x64 and macOS arm64 and exact matching source.
- [ ] Confirm Qt modules, LGPLv3 notices, exact corresponding source and modified library replacement in actual installs.
- [ ] Audit OpenCV and every packaged DLL/dylib native dependency.
- [ ] Lock platform dependencies and generate SBOM and complete THIRD_PARTY_NOTICES.
- [ ] Package and smoke-test installed applications and verify original media never shipped.
- [ ] Review final build artifact for compliance and approve GitHub Releases.

Follow https://ffmpeg.org/legal.html and https://www.qt.io/development/open-source-lgpl-obligations .
Commercial status does not waive redistribution terms. This plan is not legal advice.
