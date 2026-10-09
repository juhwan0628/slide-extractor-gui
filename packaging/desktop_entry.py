"""Native app entry with a real bundled-tool/Qt/analysis/export smoke check."""
import json
import os
from pathlib import Path
import sys
import tempfile
import subprocess


def smoke(target):
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    from PySide6.QtWidgets import QApplication
    from gui.window import Window
    from slide_core.tools import executable
    from slide_core.media import probe_source
    from slide_core.analysis import analyze_project
    from slide_core.config import AnalysisSettings
    from slide_core.profiling import AnalysisProfile
    from slide_core.export_v3 import export_project
    from pypdf import PdfReader
    from slide_core.version import VERSION
    result={'version':VERSION,'frozen':bool(getattr(sys,'frozen',False)),'status':'failed'}
    try:
        tools={name:executable(name) for name in ('ffmpeg','ffprobe')}
        if result['frozen']:
            root=Path(sys._MEIPASS).resolve()
            assert all(Path(value).resolve().is_relative_to(root) for value in tools.values()), 'Bundled media tools missing'
        app=QApplication.instance() or QApplication([])
        window=Window();window.show();app.processEvents();window.close();app.processEvents()
        with tempfile.TemporaryDirectory(prefix='slide-installed-smoke-') as temp:
            temp=Path(temp);video=temp/'test.mp4'
            subprocess.run([tools['ffmpeg'],'-hide_banner','-loglevel','error','-y','-f','lavfi','-i',
                'testsrc2=size=320x180:rate=4:duration=4','-c:v','mpeg4','-q:v','2',str(video)],check=True,timeout=60)
            profile=AnalysisProfile()
            project,_=analyze_project(probe_source(video),AnalysisSettings(fps=0.5,roi_mode='full'),temp/'cache',profile=profile)
            pdf,side=export_project(project,temp/'test.pdf')
            assert len(project.samples)==2
            assert len(PdfReader(pdf).pages)==len(project.pages)>0
            assert profile.report()['decoder_backend']=='cpu-metadata'
            result.update(status='success',sample_count=len(project.samples),page_count=len(project.pages),
                          decoder_backend='cpu-metadata',bundled_tools_checked=result['frozen'])
    except Exception as exc:
        result['error']=type(exc).__name__+': '+str(exc)
        raise
    finally:
        Path(target).write_text(json.dumps(result,indent=2)+'\n')
    return 0


if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--smoke-report':
        raise SystemExit(smoke(sys.argv[2]))
    from app import main
    raise SystemExit(main())
