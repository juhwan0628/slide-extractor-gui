"""Collect observed candidate inputs. This module never approves redistribution."""
import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parents[1]

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def download_verified(url,expected,destination):
    destination=Path(destination)
    if destination.is_file() and digest(destination)==expected:return destination
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=destination.with_name(destination.name+'.part')
    try:
        with urllib.request.urlopen(url,timeout=60) as incoming, temporary.open('wb') as outgoing:
            shutil.copyfileobj(incoming,outgoing,1024*1024)
        if digest(temporary)!=expected:raise ValueError('source hash mismatch: '+url)
        temporary.replace(destination)
    finally:temporary.unlink(missing_ok=True)
    return destination

def validate_configuration(output):
    line=next((line for line in output.splitlines() if line.startswith('configuration: ')),None)
    if line is None:raise ValueError('FFmpeg configuration missing')
    flags=shlex.split(line.removeprefix('configuration: '))
    required={'--disable-autodetect','--disable-gpl','--disable-nonfree','--disable-version3','--disable-shared','--enable-static'}
    if not required.issubset(flags):raise ValueError('FFmpeg expected configuration missing')
    if any(flag in ('--enable-gpl','--enable-nonfree','--enable-version3') or flag.startswith('--enable-lib') for flag in flags):
        raise ValueError('FFmpeg restricted or external configuration')
    return line.removeprefix('configuration: ')

def source_licenses(archive,destination,component):
    copied=[]
    with tarfile.open(archive,'r:*') as source:
        for member in source:
            path=PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts or '\\' in member.name:raise ValueError('unsafe source member')
            if not member.isfile():continue
            if not any(k in path.name.lower() for k in ('copying','license','notice','copyright','ofl')) and not any(part.lower()=='licenses' for part in path.parts):continue
            # Preserve complete original text and relative names, never extract archive paths directly.
            target=Path(destination)/component/Path(*path.parts)
            target.parent.mkdir(parents=True,exist_ok=True)
            with source.extractfile(member) as incoming,target.open('wb') as outgoing:shutil.copyfileobj(incoming,outgoing)
            copied.append(target)
    if not copied:raise ValueError('source license copies missing: '+component)
    return copied

def input_manifest(root,sources,output,extension=None):
    root=Path(root)
    extension=('.exe' if sys.platform=='win32' else '') if extension is None else extension
    ff=sources['ffmpeg']
    return {'status':'VERIFIED_INPUTS','public_release_approved':False,'target':platform.platform(),
            'ffmpeg':{'supplier':'Built from pinned upstream source by this repository','version':ff['version'],
                      'sha256':digest(root/('ffmpeg'+extension)),'configure':validate_configuration(output),
                      'corresponding_source_url':ff['url'],'source_sha256':ff['sha256'],
                      'license':'LGPL-2.1-or-later'},
            'ffprobe':{'sha256':digest(root/('ffprobe'+extension))},'sources':sources,
            'provenance':{k:os.environ[k] for k in ('GITHUB_SHA','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT') if k in os.environ}}

def collect(root):
    root=Path(root);sources=json.loads((ROOT/'packaging/native-sources.lock.json').read_text())
    source_dir=root/'sources';source_dir.mkdir(parents=True,exist_ok=True)
    for name,item in sources.items():
        archive=download_verified(item['url'],item['sha256'],source_dir/PurePosixPath(item['url']).name)
        source_licenses(archive,root/'licenses',name)
    packages=[];license_index=[]
    for distribution in sorted(importlib.metadata.distributions(),key=lambda d:d.metadata['Name'].lower()):
        name=distribution.metadata['Name']
        packages.append({'name':name,'version':distribution.version})
        safe=re.sub(r'[^a-zA-Z0-9_.-]','_',name)
        for index,item in enumerate(distribution.files or []):
            if not any(k in str(item).lower() for k in ('license','copying','notice')):continue
            original=Path(distribution.locate_file(item))
            if not original.is_file():continue
            target=root/'licenses'/'wheels'/safe/(str(index)+'-'+original.name)
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(original,target)
            license_index.append({'package':name,'wheel_path':str(item),'saved_path':target.relative_to(root).as_posix(),'sha256':digest(target)})
    import sysconfig
    python_license=next((p for p in (Path(sysconfig.get_path('stdlib'))/'LICENSE.txt',Path(sys.base_prefix)/'LICENSE.txt',Path(sys.base_prefix)/'LICENSE') if p.is_file()),Path('missing-python-license'))
    if not python_license.is_file():raise ValueError('Python runtime license not found')
    shutil.copyfile(python_license,root/'licenses'/'Python-LICENSE.txt')
    extension='.exe' if sys.platform=='win32' else ''
    output=subprocess.run([str((root/('ffmpeg'+extension)).resolve()),'-version'],capture_output=True,text=True,check=True,timeout=20).stdout
    data=input_manifest(root,sources,output)
    (root/'binary-manifest.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    (root/'SBOM.json').write_text(json.dumps({'status':'OBSERVED_INPUT_INVENTORY','components':packages+[{'name':'FFmpeg','version':sources['ffmpeg']['version']},{'name':'Python','version':platform.python_version()},{'name':'Qt','version':sources['qt']['version']}],'license_files':license_index},indent=2)+'\n',encoding='utf-8')
    shutil.copyfile(ROOT/'packaging/SOURCE_AND_REPLACEMENT.md',root/'SOURCE_AND_REPLACEMENT.md')
    if (ROOT/'build/opencv-build.json').is_file():
        shutil.copyfile(ROOT/'build/opencv-build.json',root/'opencv-build.json')
    return data

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--download-ffmpeg-only',action='store_true');a=p.parse_args()
    if a.download_ffmpeg_only:
        item=json.loads((ROOT/'packaging/native-sources.lock.json').read_text())['ffmpeg']
        download_verified(item['url'],item['sha256'],a.root/PurePosixPath(item['url']).name)
    else:collect(a.root)
