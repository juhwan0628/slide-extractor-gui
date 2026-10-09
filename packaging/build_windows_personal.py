"""Build a personal Windows x64 portable candidate on the owner's device."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import struct
import subprocess
import sys
import traceback
import venv
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = runpy.run_path(str(ROOT/'slide_core/version.py'))['VERSION']

def find_tools(folder=None):
    folder = Path(folder) if folder is not None else None
    if folder is None and (ROOT/'vendor/personal/ffmpeg.exe').is_file():
        folder = ROOT/'vendor/personal'
    tools = {}
    for name in ('ffmpeg','ffprobe'):
        path = folder/(name+'.exe') if folder is not None else shutil.which(name+'.exe')
        if path is None or not Path(path).is_file():
            raise FileNotFoundError(f'{name}.exe missing. Put both tools in vendor/personal or pass --ffmpeg-dir.')
        tools[name] = Path(path).resolve()
    return tools

def stage_tools(tools, stage):
    stage = Path(stage)
    if any(path.parent.resolve()==stage.resolve() for path in tools.values()):
        raise ValueError('Choose source tools outside the generated staging folder')
    inputs = list(tools.values())
    for folder in {p.parent for p in inputs}:
        inputs.extend(p for p in folder.iterdir() if p.is_file() and p.suffix.lower()=='.dll')
    files = {}
    for source in inputs:
        key = source.name.casefold()
        if key in files and source.read_bytes()!=files[key].read_bytes():
            raise ValueError(f'Conflicting media DLLs: {source.name}')
        files[key] = source
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    for source in files.values():
        shutil.copy2(source, stage/source.name)
    return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in stage.iterdir()}

def run_smoke(exe, report):
    report = Path(report)
    report.parent.mkdir(parents=True,exist_ok=True)
    report.unlink(missing_ok=True)
    env = dict(os.environ, PATH='', QT_QPA_PLATFORM='offscreen')
    subprocess.run([str(Path(exe).resolve()),'--smoke-report',str(report.resolve())],
                   env=env,check=True,timeout=180)
    if not report.is_file():
        raise ValueError('Bundled smoke report missing; the executable did not complete validation')
    result = json.loads(report.read_text(encoding='utf-8'))
    if (result.get('status')!='success' or result.get('frozen') is not True or
            result.get('bundled_tools_checked') is not True or result.get('version')!=VERSION):
        raise ValueError(f'Bundled smoke validation failed: {result}')
    return result

def portable_zip(bundle, output):
    bundle,output = Path(bundle),Path(output)
    if not (bundle/'SlideExtractor.exe').is_file():
        raise FileNotFoundError('Built SlideExtractor.exe missing')
    output.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/'scripts/validate-windows-portable.bat',bundle/'VALIDATE-WINDOWS.bat')
    shutil.copy2(ROOT/'INSTALL-WINDOWS.md',bundle/'INSTALL-WINDOWS.md')
    archive = output/f'SlideExtractor-v{VERSION}-Windows-x64-personal.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in sorted(bundle.rglob('*')):
            if path.is_file():
                z.write(path,Path('SlideExtractor')/path.relative_to(bundle))
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError('Portable archive corrupted')
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.zip.sha256').write_text(f'{digest}  {archive.name}\n',encoding='utf-8')
    return archive

def build(folder=None):
    if sys.platform!='win32' or struct.calcsize('P')!=8 or sys.version_info[:2]!=(3,12):
        raise RuntimeError('Run with Windows x64 Python 3.12')
    work = ROOT/'build/personal-windows'
    work.mkdir(parents=True,exist_ok=True)
    log_path = work/'build.log'
    with log_path.open('w',encoding='utf-8') as log:
        def say(message):
            print(message,flush=True);log.write(message+'\n');log.flush()
        def run(args,env=None):
            say(subprocess.list2cmdline([str(arg) for arg in args]))
            with subprocess.Popen([str(arg) for arg in args],cwd=ROOT,env=env,
                                  stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                  text=True,encoding='utf-8',errors='replace') as process:
                for line in process.stdout:
                    print(line,end='',flush=True);log.write(line);log.flush()
                if process.wait()!=0:
                    raise subprocess.CalledProcessError(process.returncode,args)
        try:
            if folder is None:
                say('Preparing pinned FFmpeg automatically; no manual folders or files needed.')
                prepare=runpy.run_path(str(ROOT/'packaging/windows_media.py'))['prepare']
                tools=prepare(ROOT/'vendor/automatic-ffmpeg-8.1.2')
            else:
                tools = find_tools(folder)
            stage = work/'tools'
            inputs = stage_tools(tools,stage)
            (work/'media-input-hashes.json').write_text(json.dumps(inputs,indent=2)+'\n',encoding='utf-8')
            build_env = ROOT/'.venv-native-windows-049rc1'
            python = build_env/'Scripts/python.exe'
            if not python.is_file():
                say('Creating isolated native build environment.')
                venv.EnvBuilder(with_pip=True).create(build_env)
            env = dict(os.environ, PERSONAL_FFMPEG_DIR=str(stage),
                       SLIDE_BUILD_MODE='personal',
                       SLIDE_BUILD_MANIFEST=str(work/'build-manifest.json'),
                       PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
            env['PATH'] = str(stage)+os.pathsep+env.get('PATH','')
            run([python,'-m','pip','install','-r',ROOT/'packaging/requirements-windows-x64.lock'],env)
            run([python,'-m','pip','check'],env)
            run([python,ROOT/'packaging/build_manifest.py','--tools',stage,'--mode','personal',
                 '--output',work/'build-manifest.json'],env)
            output=Path(os.environ.get('SLIDE_WINDOWS_OUTPUT_DIR',str(ROOT/'dist'))).resolve()
            run([python,'-m','PyInstaller','--clean','--noconfirm',
                 '--distpath',output/'app',
                 '--workpath',ROOT/'build/pyinstaller-windows-personal',
                 ROOT/'packaging/SlideExtractor.spec'],env)
            bundle = output/'app/SlideExtractor'
            say('Checking bundled Qt, FFmpeg, analysis and PDF export with empty PATH.')
            result = run_smoke(bundle/'SlideExtractor.exe',work/'installed-smoke.json')
            say(json.dumps(result))
            archive = portable_zip(bundle,output)
            say(f'Created: {archive}')
            say('Extract the portable ZIP into a new folder; run VALIDATE-WINDOWS.bat then SlideExtractor.exe.')
            return archive
        except Exception:
            log.write(traceback.format_exc());log.flush()
            say(f'Build failed. See {log_path}')
            raise

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ffmpeg-dir',type=Path,help='Folder containing ffmpeg.exe and ffprobe.exe')
    args = parser.parse_args()
    try:
        build(args.ffmpeg_dir)
    except Exception as exc:
        print(type(exc).__name__+': '+str(exc),file=sys.stderr)
        raise SystemExit(1)
