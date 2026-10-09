"""Prepare pinned Windows media tools locally; never installs system packages."""
import hashlib
import json
from pathlib import Path,PurePosixPath
import shutil
import tempfile
import urllib.request
import zipfile

URL='https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-8.1.2-essentials_build.zip'
SHA256='db580001caa24ac104c8cb856cd113a87b0a443f7bdf47d8c12b1d740584a2ec'

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def prepare(target,*,url=URL,expected_sha256=SHA256):
    target=Path(target)
    target.mkdir(parents=True,exist_ok=True)
    archive=target/'download.zip'
    if not archive.is_file() or digest(archive)!=expected_sha256:
        temporary=target/'download.partial'
        print('Downloading Windows FFmpeg and FFprobe automatically...',flush=True)
        try:
            with urllib.request.urlopen(url,timeout=60) as response,temporary.open('wb') as output:
                shutil.copyfileobj(response,output,1024*1024)
            if digest(temporary)!=expected_sha256:
                raise ValueError('FFmpeg archive SHA-256 mismatch')
            temporary.replace(archive)
        finally:
            temporary.unlink(missing_ok=True)
    with zipfile.ZipFile(archive) as z:
        entries=z.infolist()
        for item in entries:
            path=PurePosixPath(item.filename)
            mode=item.external_attr>>16
            if path.is_absolute() or '..' in path.parts or '\\' in item.filename or ':' in item.filename or mode&0o170000==0o120000:
                raise ValueError('Unsafe media archive path')
        chosen={}
        for name in ('ffmpeg.exe','ffprobe.exe'):
            matches=[item for item in entries if PurePosixPath(item.filename).name==name and 'bin' in PurePosixPath(item.filename).parts]
            if len(matches)!=1:
                raise ValueError('Missing or ambiguous media executable: '+name)
            chosen[name]=matches[0]
        for item in entries:
            name=PurePosixPath(item.filename).name
            if name in ('LICENSE','LICENSE.txt','README.txt'):
                chosen[name]=item
        with tempfile.TemporaryDirectory(prefix='media-extract-',dir=target) as temp:
            temp=Path(temp)
            for name,item in chosen.items():
                with z.open(item) as source,(temp/name).open('wb') as output:
                    shutil.copyfileobj(source,output)
            for name in chosen:(temp/name).replace(target/name)
    record={'supplier_url':url,'archive_sha256':expected_sha256,
            'files':{name:digest(target/name) for name in chosen}}
    (target/'download-manifest.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    return {name:target/(name+'.exe') for name in ('ffmpeg','ffprobe')}
