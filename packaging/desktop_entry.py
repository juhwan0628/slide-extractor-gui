"""Native app entry with a real bundled-tool/Qt/analysis/export smoke check."""
import json
from contextlib import ExitStack
import os
from pathlib import Path
import sys
import tempfile
import subprocess


def verify_manual_editing(app,project,temp):
    """Exercise the installed editor, shortcuts and export after a real Merge."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from gui.window import Window
    from gui.state import State
    from slide_core.editing import add_page
    from slide_core.export_v3 import export_project
    from slide_core.pdf_only_export import export_pdf_only
    from slide_core.timeline_json import loads
    from pypdf import PdfReader
    for sample in project.samples:add_page(project,sample.actual_time)
    original=tuple(project.pages)
    assert len(original)>=2
    window=Window()
    try:
        window.controller.source=project.source
        window.controller.state=State.SOURCE_READY
        window.controller.begin_analysis('installed-edit')
        window._job_type='analysis'
        window._job_id='installed-edit'
        window._job_finished('installed-edit',(project,None),None)
        window.show();window.activateWindow();app.processEvents()
        first=window.page_model.index(0)
        last=window.page_model.index(len(original)-1)
        QTest.mouseClick(window.page_view.viewport(),Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.NoModifier,window.page_view.visualRect(first).center())
        QTest.mouseClick(window.page_view.viewport(),Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.ShiftModifier,window.page_view.visualRect(last).center())
        window.page_view.setFocus();app.processEvents()
        assert len(window.selected_page_ids())==len(original)
        def key(key,modifiers=Qt.KeyboardModifier.NoModifier):
            QTest.keyClick(window.page_view,key,modifiers);app.processEvents()
        key(Qt.Key.Key_M,Qt.KeyboardModifier.ControlModifier)
        assert project.pages==[original[-1]]
        assert window.current_index==len(project.samples)-1
        key(Qt.Key.Key_Z,Qt.KeyboardModifier.ControlModifier)
        assert tuple(project.pages)==original and len(window.selected_page_ids())==len(original)
        key(Qt.Key.Key_Up,Qt.KeyboardModifier.ShiftModifier)
        assert len(window.selected_page_ids())==len(original)-1
        key(Qt.Key.Key_Down,Qt.KeyboardModifier.ShiftModifier)
        assert len(window.selected_page_ids())==len(original)
        key(Qt.Key.Key_Z,Qt.KeyboardModifier.ControlModifier|Qt.KeyboardModifier.ShiftModifier)
        assert project.pages==[original[-1]]
        key(Qt.Key.Key_Delete)
        assert not project.pages and not window.export_button.isEnabled()
        key(Qt.Key.Key_Z,Qt.KeyboardModifier.ControlModifier)
        assert project.pages==[original[-1]]
        pdf,side=export_project(project,temp/'edited.pdf')
        value=loads(side.read_bytes(),pdf_bytes=pdf.read_bytes())
        assert len(PdfReader(pdf).pages)==1
        assert value['pages'][0]['page_id']==original[-1].page_id
        assert value['pages'][0]['representative_timestamp_s']==float(project.sample_time(original[-1].representative_sample_id))
        export_pdf_only(project,temp/'edited-only.pdf')
        assert len(PdfReader(temp/'edited-only.pdf').pages)==1
        assert not list(temp.glob('*.lock'))
    finally:
        window.controller.state=State.REVIEW_READY
        window.controller.pending_job=None
        window.close();app.processEvents()


def smoke(target):
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    from PySide6.QtCore import qVersion
    from PySide6.QtWidgets import QApplication
    from gui.window import Window
    from slide_core.tools import executable
    from slide_core.media import probe_source
    from slide_core.analysis import analyze_project
    from slide_core.config import AnalysisSettings
    from slide_core.profiling import AnalysisProfile
    from slide_core.export_v3 import export_project
    from slide_core.pdf_only_export import export_pdf_only
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
        with tempfile.TemporaryDirectory(prefix='slide-installed-smoke-') as temp, ExitStack() as cleanup:
            temp=Path(temp);video=temp/'test.mp4'
            subprocess.run([tools['ffmpeg'],'-hide_banner','-loglevel','error','-y','-f','lavfi','-i',
                'testsrc2=size=320x180:rate=4:duration=4','-c:v','mpeg4','-q:v','2',str(video)],check=True,timeout=60)
            profile=AnalysisProfile()
            project,_=analyze_project(probe_source(video),AnalysisSettings(fps=0.5,roi_mode='full'),temp/'cache',profile=profile)
            # The smoke owns this Project; end its pin before Windows temp deletion.
            cleanup.callback(project._cache_pin.close)
            pdf,side=export_project(project,temp/'test.pdf')
            assert len(project.samples)==2
            assert len(PdfReader(pdf).pages)==len(project.pages)>0
            assert not list(temp.glob('*.lock')), 'Paired export left output lock'
            pdf_only=temp/'PDF only 한글 경로.pdf'
            for overwrite in (False,True):
                export_pdf_only(project,pdf_only,overwrite=overwrite)
                assert len(PdfReader(pdf_only).pages)==len(project.pages)
                assert not pdf_only.with_suffix('.json').exists()
                assert not list(temp.glob('*.lock')), 'PDF-only export left output lock'
            assert profile.report()['decoder_backend']=='cpu-metadata'
            verify_manual_editing(app,project,temp)
            result.update(manual_editing_checked=True,keyboard_editing_checked=True,edited_export_checked=True)
            result.update(status='success',qt_runtime_version=qVersion(),sample_count=len(project.samples),page_count=len(project.pages),
                          decoder_backend='cpu-metadata',bundled_tools_checked=result['frozen'],
                          pdf_only_checked=True,output_lock_cleanup_checked=True)
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
