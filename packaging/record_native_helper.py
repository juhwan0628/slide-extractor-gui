"""Record exact source, link inputs and binary bytes; no release approval."""
import hashlib,json,platform,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def record(output,sdk):
    output=Path(output);sdk=Path(sdk);extension='.exe' if sys.platform=='win32' else ''
    lock=json.loads((ROOT/'packaging/native-sources.lock.json').read_text())['ffmpeg']
    archive=ROOT/'build/native-sources'/('ffmpeg-'+lock['version']+'.tar.xz')
    if digest(archive)!=lock['sha256']:raise ValueError('FFmpeg source hash mismatch')
    libs=sorted((sdk/'lib').glob('*.a'))
    if not libs:raise ValueError('Static FFmpeg libraries missing')
    result=dict(schema_version=1,platform=platform.platform(),helper_sha256=digest(output/('slide-keyframe-decode'+extension)),
        helper_source_sha256=digest(ROOT/'native/keyframe_decode.cpp'),ffmpeg_source=lock,
        ffmpeg_libraries={p.name:digest(p) for p in libs},link_command=(output/'helper-relink/link-command.txt').read_text(),
        relink_object_sha256=digest(output/'helper-relink/keyframe_decode.o'),public_release_approved=False)
    (output/'native-helper-build.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':record(*sys.argv[1:])
