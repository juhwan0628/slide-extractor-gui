"""Preliminary fail-closed release gate; not a license compliance certificate."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def audit(root, ffmpeg, manifest):
    errors = []
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if data.get("status") != "APPROVED":
        errors.append("manifest not approved")
    files = []
    if not root.is_dir():
        errors.append("bundle folder missing")
    else:
        files = [p for p in root.rglob("*") if p.is_file()]
        if not any(p.name == "THIRD_PARTY_NOTICES.md" for p in files):
            errors.append("notices missing")
        if any(any(key in p.name.lower() for key in ('pymupdf','fitz','pytest','test_lecture')) for p in files):
            errors.append("Unapproved development, test media, or PyMuPDF component bundled")
        if not any(p.name in ('SlideExtractor.exe','SlideExtractor') for p in files):
            errors.append('Built application executable missing')
    # Assertions in the supplier manifest never substitute for actual materials.
    licenses=[p for p in files if 'licenses' in p.relative_to(root).parts and p.stat().st_size]
    if not licenses:
        errors.append('Actual nonempty license copies missing')
    replacement=[p for p in files if p.name=='SOURCE_AND_REPLACEMENT.md' and p.stat().st_size]
    if not replacement:
        errors.append('Actual source/replacement instructions missing')
    sboms=[p for p in files if p.name=='SBOM.json']
    if not sboms:
        errors.append('Actual SBOM missing')
    else:
        try:
            sbom=json.loads(sboms[0].read_text(encoding='utf-8'))
            components=sbom.get('components', [])
            names={str(item.get('name','')).lower() for item in components}
            if not {'ffmpeg','python'}.issubset(names) or not names.intersection({'qt','pyside6','pyside6-essentials'}):
                errors.append('Actual SBOM expected components missing')
        except (OSError,ValueError,TypeError,AttributeError):
            errors.append('Actual SBOM invalid')
    build_files=[p for p in files if p.name=='build-manifest.json']
    bundle=data.get('bundle', {})
    if not build_files or not bundle.get('build_manifest_sha256'):
        errors.append('Reviewed build provenance missing')
    else:
        build_file=build_files[0]
        if sha256(build_file)!=bundle['build_manifest_sha256']:
            errors.append('Build provenance hash mismatch')
        try:
            build=json.loads(build_file.read_text(encoding='utf-8'))
            if not bundle.get('candidate_version') or build.get('version')!=bundle['candidate_version']:
                errors.append('Candidate version/provenance mismatch')
            for name in ('ffmpeg','ffprobe'):
                if not data.get(name,{}).get('sha256') or build.get('tools',{}).get(name,{}).get('sha256')!=data[name]['sha256']:
                    errors.append(name+' supplier provenance mismatch')
        except (OSError,ValueError,TypeError,AttributeError):
            errors.append('Build provenance invalid')
    ff = data.get("ffmpeg", {})
    if not ffmpeg.is_file():
        errors.append("FFmpeg missing")
    else:
        try:
            result = subprocess.run([str(ffmpeg), "-version"], capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.TimeoutExpired) as exc:
            errors.append(f"FFmpeg version cannot execute: {exc}")
        else:
            if result.returncode:
                errors.append("FFmpeg version failed")
            if "--enable-gpl" in result.stdout or "--enable-nonfree" in result.stdout:
                errors.append("FFmpeg GPL/nonfree flags found")
            if not ff.get("configure") or ff["configure"] not in result.stdout:
                errors.append("FFmpeg configure not validated")
        if not ff.get("bundle_sha256"):
            errors.append("FFmpeg reviewed bundle hash missing")
        elif sha256(ffmpeg) != ff["bundle_sha256"]:
            errors.append("FFmpeg bundle hash mismatch")
    probes=[p for p in files if p.name in ('ffprobe','ffprobe.exe')]
    probe_expected=data.get('ffprobe',{}).get('bundle_sha256')
    if not probes or not probe_expected:
        errors.append('FFprobe reviewed bundle hash missing')
    elif any(sha256(p)!=probe_expected for p in probes):
        errors.append('FFprobe bundle hash mismatch')
    for key in ("supplier", "version", "corresponding_source_url", "source_sha256"):
        if not ff.get(key):
            errors.append("FFmpeg field missing: " + key)
    for kind,component in (("FFmpeg",ff),("Qt",data.get("qt", {}))):
        path=component.get('source_archive_local')
        expected=component.get('source_sha256')
        if not path or not Path(path).is_file() or not expected or sha256(Path(path))!=expected:
            errors.append(f'{kind} exact corresponding source archive not verified')
    qt = data.get("qt", {})
    if not qt.get("modules") or not qt.get("replacement_verified"):
        errors.append("Qt modules/replacement not verified")
    for key in ("version", "corresponding_source_url", "source_sha256"):
        if not qt.get(key):
            errors.append("Qt field missing: " + key)
    for key in ("third_party_notices_included", "license_copies_included", "sbom_included", "pymupdf_absent",
                "clean_machine_smoke_verified", "native_installer_verified", "signed_or_notarization_state_recorded"):
        if not data.get("bundle", {}).get(key):
            errors.append("bundle check incomplete: " + key)
    return errors

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--ffmpeg", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument('--report',type=Path)
    parser.add_argument('--installer',type=Path)
    for name in ('version','commit','run-id','platform'):parser.add_argument('--'+name)
    args = parser.parse_args()
    if args.report and not all((args.installer,args.version,args.commit,args.run_id,args.platform)):
        parser.error('--report requires --installer, --version, --commit, --run-id and --platform')
    errors = audit(args.root, args.ffmpeg, args.manifest)
    if args.report:
        if not args.installer.is_file():errors.append('Reviewed installer missing')
        report={'status':'BLOCKED' if errors else 'PASSED','errors':errors,'version':args.version,
                'commit':args.commit,'run_id':args.run_id,'platform':args.platform,
                'installer_sha256':sha256(args.installer) if args.installer.is_file() else None,
                'manifest_sha256':sha256(args.manifest)}
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    for item in errors:
        print("FAIL:", item)
    print("RELEASE BLOCKED" if errors else "PRELIMINARY GATE PASSED; manual review required")
    return bool(errors)

if __name__ == "__main__":
    raise SystemExit(main())
