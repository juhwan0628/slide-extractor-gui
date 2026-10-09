"""Ship a clean Windows-only wrapper around its internal build sources."""
from pathlib import Path
import hashlib
import zipfile

ROOT=Path(__file__).resolve().parents[1]
GUIDE="""슬라이드 이그젝터 — Windows 자동 빌드

1. 이 ZIP을 새 폴더에 풀어 주세요.
2. Python 3.12 64비트를 설치해 주세요. Python launcher도 포함합니다.
   공식 설치 안내: https://www.python.org/downloads/release/python-31210/
   이미 설치되어 있으면 다시 설치하지 않아도 됩니다.
3. BUILD-WINDOWS.bat를 더블클릭하세요.

FFmpeg를 찾거나 복사할 필요가 없습니다.
도구 다운로드·해시 검증·폴더 생성·빌드·자동 검증을 모두 처리합니다.
처음 실행에는 인터넷이 필요합니다.

성공하면 output 폴더가 열립니다.
그 안의 포터블 ZIP을 새 폴더에 풀고 VALIDATE-WINDOWS.bat로 검사한 다음 SlideExtractor.exe를 실행하세요.

실제 강의로 분석·편집·PDF 저장·취소·캐시 재사용을 확인해 주세요.
빌드 실패: _app/build/personal-windows/build.log
자동 검사: _app/build/personal-windows/installed-smoke.json
설치 후 검사: 앱 폴더의 validation-smoke.json

_app은 내부 파일 폴더이므로 그대로 두시면 됩니다.
이 패키지는 개인 검증용이며 Windows에서 실행 파일을 만듭니다.
"""
def build(output):
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    files=['app.py','requirements.txt','LICENSE_AUDIT.md','THIRD_PARTY_NOTICES.md','INSTALL-WINDOWS.md',
           'packaging/SlideExtractor.spec','packaging/build_manifest.py','packaging/build_windows_personal.py',
           'packaging/windows_media.py','packaging/desktop_entry.py','packaging/requirements-windows-x64.lock',
           'scripts/validate-windows-portable.bat']
    files.extend(p.relative_to(ROOT).as_posix() for folder in ('gui','slide_core') for p in sorted((ROOT/folder).glob('*.py')))
    launcher=(ROOT/'BUILD-WINDOWS.bat').read_bytes().decode('ascii')
    launcher=launcher.replace('cd /d "%~dp0"','set "SLIDE_WINDOWS_OUTPUT_DIR=%~dp0output"\r\ncd /d "%~dp0_app"')
    launcher=launcher.replace('echo Build failed. Check build\\personal-windows\\build.log','echo Build failed. Check _app\\build\\personal-windows\\build.log')
    launcher=launcher.replace('echo Build and bundled smoke succeeded. The portable ZIP is in dist.',
                              'echo Build and bundled smoke succeeded. The portable ZIP is in output.\r\n  start "" "%SLIDE_WINDOWS_OUTPUT_DIR%"')
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        prefix='SlideExtractor-Windows/'
        z.writestr(prefix+'BUILD-WINDOWS.bat',launcher.encode('ascii'))
        z.writestr(prefix+'사용안내.txt',GUIDE.encode('utf-8-sig'))
        for name in files:
            path=ROOT/name
            if not path.is_file() or path.is_symlink():raise ValueError('Missing/unsafe build source: '+name)
            z.write(path,prefix+'_app/'+name)
    with zipfile.ZipFile(output) as z:
        if z.testzip() is not None:raise ValueError('Corrupt kit ZIP')
    print(str(output),hashlib.sha256(output.read_bytes()).hexdigest())
if __name__=='__main__':
    import sys
    build(sys.argv[1])
