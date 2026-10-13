# Historical 0.4 M5: Native release validation

Candidate version: 0.4.12rc1.

Run M1–M4 regressions on macOS ARM64 and Windows x64 before building installers. Verify installed applications with an empty PATH, PDF export and Qt replacement. Audit the original installer bytes and corresponding sources/licenses before updating release approval. Historical approval records cannot approve this candidate. Physical device security policies remain outside hosted runner validation.

## Verified result

Local:706 passed. Candidate commit:c7bcc6cd06a13b3b07c97f47a888e3a72def6fe1. Source CI:38162688931. Native build:38162689003 (Mac90 passed, Windows88 passed2 POSIX skips). Both original bundles, installed apps and modified QtCore test copies passed their runtime/export smoke. Native path inventories unchanged. Installed-byte audit:38163506514, both PASSED. Publication:38163740185. Release installer hashes are bound to the actual downloaded audits in packaging/release-approval.json. Independent review found no remaining Critical/Important findings.

This historical approval does not qualify keyframe 0.5.0b1. See Keyframe-M5-plan.md for the new candidate.
