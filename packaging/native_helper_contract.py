"""Fail closed when an approved half-capable bundle lacks its helper evidence."""
import hashlib
import json
import shlex
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def validate_helper_evidence(vendor,extension):
    vendor=Path(vendor);evidence=vendor/'native-helper-build.json'
    if not evidence.is_file():raise ValueError('Missing native helper evidence')
    data=json.loads(evidence.read_text())
    required={'schema_version','helper_sha256','helper_source_sha256','ffmpeg_source','ffmpeg_libraries','link_command','relink_object_sha256','public_release_approved'}
    if not required<=data.keys() or data['schema_version']!=1:raise ValueError('Incomplete helper evidence schema')
    lock=json.loads((ROOT/'packaging/native-sources.lock.json').read_text())['ffmpeg']
    if data['ffmpeg_source']!=lock:raise ValueError('Unpinned helper FFmpeg source')
    kit=vendor/'helper-relink'
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    checks={vendor/('slide-keyframe-decode'+extension):data['helper_sha256'],
            kit/'keyframe_decode.o':data['relink_object_sha256'],kit/'keyframe_decode.cpp':data['helper_source_sha256']}
    if data['helper_source_sha256']!=digest(ROOT/'native/keyframe_decode.cpp'):raise ValueError('Helper source mismatch')
    if not isinstance(data['ffmpeg_libraries'],dict) or not {'libavformat.a','libavcodec.a','libavfilter.a','libavutil.a'}<=data['ffmpeg_libraries'].keys():
        raise ValueError('Missing relink libraries')
    for name,value in data['ffmpeg_libraries'].items():
        if Path(name).name!=name or not name.endswith('.a'):raise ValueError('Unsafe relink library')
        checks[kit/'ffmpeg-libraries'/name]=value
    for path,value in checks.items():
        if path.is_symlink() or not path.is_file() or digest(path)!=value:raise ValueError('Helper evidence file/hash mismatch: '+path.name)
    command=kit/'link-command.txt'
    if not command.is_file() or not data['link_command'] or command.read_text()!=data['link_command']:raise ValueError('Missing/mismatched relink command')
    arguments=shlex.split(data['link_command'])
    archive_names={Path(arg).name for arg in arguments if arg.endswith('.a')}
    if not {'libavformat.a','libavcodec.a','libavfilter.a','libavutil.a'}<=archive_names:
        raise ValueError('Exact static library linkage missing')
    if any(arg in ('-lavformat','-lavcodec','-lavfilter','-lavutil') for arg in arguments):
        raise ValueError('Ambiguous static library linkage')
    return data

def bundle_tools(vendor,extension,*,approved):
    vendor=Path(vendor)
    names=['ffmpeg','ffprobe']
    helper=vendor/('slide-keyframe-decode'+extension)
    if approved or helper.is_file():
        if not helper.is_file():raise ValueError('Missing native helper')
        evidence=vendor/'native-helper-build.json'
        if approved and not evidence.is_file():raise ValueError('Missing native helper evidence')
        if approved:
            validate_helper_evidence(vendor,extension)
        elif evidence.is_file():
            data=json.loads(evidence.read_text())
            if data.get('helper_sha256')!=hashlib.sha256(helper.read_bytes()).hexdigest():
                raise ValueError('Native helper hash mismatch')
        names.append('slide-keyframe-decode')
    result=[(str(vendor/(name+extension)),'tools') for name in names]
    if not all(Path(p).is_file() for p,_ in result):raise ValueError('Missing media tools')
    return result
