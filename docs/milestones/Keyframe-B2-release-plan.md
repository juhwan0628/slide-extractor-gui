# 0.5.0b2 public release

User authorization: 배포해 (2026-10-14 KST). Publish a new prerelease; preserve prior released assets. Half and frozen detector behavior remain unchanged from M10.

1. Update version/docs and verify source; integrate main history while preserving the verified M10 application tree and latest download statistics.
2. Build new version installers on the isolated candidate branch, collect actual run IDs and SHA256, run separate source/relink/installed audits on both OS.
3. Prepare release automation from the existing verified pipeline. Require same-commit successful source/native runs and matching audits; include LGPL helper source/object/static libraries, original source archives, licenses, checksum and evidence. Stage draft, verify uploaded SHA256 and publish prerelease. Then sync verified source/docs into main without replacing unrelated changes.

No extra user confirmation needed; publication explicitly authorized. Physical user-device lecture timings remain unmeasured. No claim that CI is user-device testing. Existing release approvals remain historical; new b2 records bind only new artifacts.
