"""Observe final bundle bytes independently of supplier inputs or approval."""
import hashlib
from pathlib import Path

def hashed(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def inventory(root,version,extension):
    root=Path(root)
    return {'candidate_version':version,
            'build_manifest_sha256':hashed(next(root.rglob('build-manifest.json'))),
            'tools':{name:{'bundle_sha256':hashed(next(path for path in root.rglob(name+extension) if path.is_file() and 'tools' in path.relative_to(root).parts))} for name in ('ffmpeg','ffprobe')}}
