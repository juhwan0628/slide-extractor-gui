"""PTS-aware desktop editor for analysis, page editing and verified export."""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4
import subprocess,sys
from PySide6.QtCore import Qt,QTimer,QSignalBlocker,QSize,QSettings
from PySide6.QtGui import QPixmap,QImage,QKeySequence,QShortcut,QIcon
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,
   QPushButton,QLabel,QComboBox,QFileDialog,QMessageBox,QListView,QSlider,QSplitter,
   QProgressBar,QStackedWidget,QMenu,QToolButton,QCheckBox,QDialog,QDialogButtonBox,QFormLayout)
from slide_core.config import AnalysisSettings
from slide_core.analysis import analyze_project,requires_reanalysis
from slide_core.profiling import profile_directory
from slide_core.media import probe_source
from slide_core.models import Rect,CancelledError
from slide_core.export import recover_export,RecoveryRequired,OutputOverwriteRequired,snapshot_export,snapshot_pdf
from slide_core.export_v3 import export_project
from slide_core.pdf_only_export import export_pdf_only
from slide_core.editing import add_page,delete_page,replace_page
from .state import Controller,State
from .workers import JobCoordinator
from .images import ImageLoader
from .page_model import PageModel
from slide_core.editing import navigate
from .playback import PlaybackClock
from .regions import RegionDialog
from .preparation import prepare_first_frame
from .timeline import Timeline
from .history import EditHistory,Snapshot

class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1250,800);self.setMinimumSize(960,640)
        self.setWindowTitle('Slide Extractor · PTS Editor')
        self.controller=Controller();self.settings=AnalysisSettings(fps=0.5)
        self._first_frame=None;self._suggested_roi=None;self._auto_roi=None;self._first_frame_warning=None
        self.jobs=JobCoordinator(self);self.jobs.done.connect(self._job_finished)
        self.jobs.progress.connect(self._job_progress)
        self.images=ImageLoader(self);self.images.ready.connect(self._image_ready)
        self.page_model=PageModel(self)
        self._thumb_cursor=0
        self.current_index=0;self.player=None;self._current_image=None
        self._job_type=None;self._close_later=False
        self.history=EditHistory()
        self._undo_delete=None
        self.json_enabled=False;self.json_format='simple'
        self.tick_timer=QTimer(self);self.tick_timer.setInterval(25)
        self.tick_timer.timeout.connect(self._tick)
        root=QWidget(self);self.setCentralWidget(root)
        layout=QVBoxLayout(root)
        top=QHBoxLayout();layout.addLayout(top)
        self.open_button=QPushButton('Open video');self.open_button.clicked.connect(self.choose_file);top.addWidget(self.open_button)
        self.crop_button=QPushButton('Slide ROI');self.crop_button.clicked.connect(lambda:self.choose_region(False));top.addWidget(self.crop_button)
        self.reset_roi=QPushButton('Auto ROI');self.reset_roi.clicked.connect(self._reset_roi);top.addWidget(self.reset_roi)
        self.mask_button=QPushButton('Ignore mask');self.mask_button.clicked.connect(lambda:self.choose_region(True));top.addWidget(self.mask_button)
        self.clear_mask=QPushButton('Clear mask');self.clear_mask.clicked.connect(self._clear_mask);top.addWidget(self.clear_mask)
        self.fps=QComboBox();self.fps.addItems(['1 FPS','0.5 FPS']);self.fps.setCurrentIndex(1);self.fps.currentIndexChanged.connect(self._fps_changed);top.addWidget(self.fps)
        self.analyze_button=QPushButton('Analyze');self.analyze_button.clicked.connect(self.analyze);top.addWidget(self.analyze_button)
        self.cancel_button=QPushButton('Cancel');self.cancel_button.clicked.connect(self.cancel);top.addWidget(self.cancel_button)
        self.advanced_button=QPushButton('Advanced…')
        self.advanced_button.clicked.connect(self.open_advanced)
        top.addWidget(self.advanced_button)
        self.review_filename=QLabel('')
        top.addWidget(self.review_filename,1)
        self.back_to_preparation=QPushButton('Change settings')
        self.back_to_preparation.clicked.connect(self.return_to_preparation)
        top.addWidget(self.back_to_preparation)
        self.export_button=QPushButton('Save PDF')
        self.export_button.setToolTip('Save selected slides as a verified PDF')
        self.export_button.clicked.connect(self.export_pending);top.addWidget(self.export_button)
        self.work_area=QStackedWidget()
        layout.addWidget(self.work_area,1)
        split=QSplitter();self.work_area.addWidget(split)
        self.review_split=split
        analysis_panel=QWidget();analysis_layout=QVBoxLayout(analysis_panel)
        analysis_layout.addStretch(1)
        self.analysis_title=QLabel('Finding slides…')
        self.analysis_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.analysis_title.setStyleSheet('font-size:20px;font-weight:600')
        analysis_layout.addWidget(self.analysis_title)
        self.analysis_progress=QProgressBar()
        self.analysis_progress.setRange(0,0)
        analysis_layout.addWidget(self.analysis_progress)
        self.analysis_cancel=QPushButton('Cancel analysis')
        self.analysis_cancel.clicked.connect(self.cancel)
        analysis_layout.addWidget(self.analysis_cancel,alignment=Qt.AlignmentFlag.AlignCenter)
        analysis_layout.addStretch(1)
        self.work_area.addWidget(analysis_panel)
        self.review_panel=analysis_panel
        self.export_panel=QWidget()
        export_layout=QVBoxLayout(self.export_panel)
        export_layout.addStretch(1)
        self.export_title=QLabel('Creating PDF…')
        self.export_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        export_layout.addWidget(self.export_title)
        self.export_progress=QProgressBar()
        self.export_progress.setRange(0,0)
        export_layout.addWidget(self.export_progress)
        self.export_cancel=QPushButton('Cancel export')
        self.export_cancel.clicked.connect(self.cancel)
        export_layout.addWidget(self.export_cancel,alignment=Qt.AlignmentFlag.AlignCenter)
        export_layout.addStretch(1)
        self.work_area.addWidget(self.export_panel)
        self.complete_panel=QWidget()
        complete_layout=QVBoxLayout(self.complete_panel)
        complete_layout.addStretch(1)
        self.complete_title=QLabel('PDF saved successfully')
        self.complete_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.complete_title.setStyleSheet('font-size:23px;font-weight:600')
        complete_layout.addWidget(self.complete_title)
        self.complete_details=QLabel()
        self.complete_details.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.complete_details.setWordWrap(True)
        complete_layout.addWidget(self.complete_details)
        self.open_folder_button=QPushButton('Open containing folder')
        self.open_folder_button.clicked.connect(self.open_export_folder)
        complete_layout.addWidget(self.open_folder_button,alignment=Qt.AlignmentFlag.AlignCenter)
        self.back_to_review_button=QPushButton('Back to editing')
        self.back_to_review_button.clicked.connect(self.return_to_review)
        complete_layout.addWidget(self.back_to_review_button,alignment=Qt.AlignmentFlag.AlignCenter)
        self.new_video_button=QPushButton('Open another video')
        self.new_video_button.clicked.connect(self.choose_file)
        complete_layout.addWidget(self.new_video_button,alignment=Qt.AlignmentFlag.AlignCenter)
        complete_layout.addStretch(1)
        self.work_area.addWidget(self.complete_panel)
        self._last_export=None
        left=QWidget();split.addWidget(left);ll=QVBoxLayout(left)
        self.preview=QLabel('Choose a local video');self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(480,280);self.preview.setStyleSheet('background:#20242a;color:white')
        ll.addWidget(self.preview,1)
        timeline_row=QHBoxLayout();ll.addLayout(timeline_row)
        self.time_label=QLabel('00:00 / 00:00')
        self.time_label.setMinimumWidth(110)
        timeline_row.addWidget(self.time_label)
        self.timeline=Timeline();self.timeline.seekRequested.connect(self.seek_seconds)
        self.timeline.markerClicked.connect(self._focus_marker);timeline_row.addWidget(self.timeline,1)
        # Retained as nonvisual compatibility controls: there is only one actual seek surface.
        self.play_button=QPushButton('Play',self);self.play_button.hide()
        self.slider=QSlider(Qt.Orientation.Horizontal,self);self.slider.hide()
        edits=QHBoxLayout();ll.addLayout(edits)
        self.add_button=QPushButton('Add current frame')
        self.add_button.clicked.connect(self.add_page);edits.addWidget(self.add_button)
        self.replace_button=QPushButton('Replace selected page')
        self.replace_button.clicked.connect(self.replace_page);edits.addWidget(self.replace_button)
        # Keep aliases for existing controllers/tests; only the fixed controls are visible.
        self.context_add=self.add_button
        self.context_replace=self.replace_button
        self.delete_button=QPushButton('Delete selected',self)
        self.delete_button.hide()
        self._edit_controls=edits
        right=QWidget();self.page_panel=right;rl=QVBoxLayout(right);split.addWidget(right)
        rl.addWidget(QLabel('Pages · chronological'))
        self.page_view=QListView();self.page_view.setModel(self.page_model)
        self.page_view.setIconSize(QSize(150,85))
        self.page_view.setUniformItemSizes(True)
        self.page_view.clicked.connect(self._page_clicked)
        self.page_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.page_view.customContextMenuRequested.connect(self._page_context_menu)
        rl.addWidget(self.page_view)
        self.page_menu=QToolButton(self)
        self.page_menu.hide()
        self.undo_button=QPushButton('Undo')
        self.undo_button.clicked.connect(self.undo_edit)
        self.redo_button=QPushButton('Redo')
        self.redo_button.clicked.connect(self.redo_edit)
        action_row=QHBoxLayout()
        action_row.addWidget(self.undo_button);action_row.addWidget(self.redo_button)
        rl.addLayout(action_row)
        edit_menu=self.menuBar().addMenu('Edit')
        self.undo_action=edit_menu.addAction('Undo')
        self.undo_action.setShortcuts([QKeySequence.StandardKey.Undo])
        self.undo_action.triggered.connect(self.undo_edit)
        self.redo_action=edit_menu.addAction('Redo')
        self.redo_action.setShortcuts([QKeySequence('Ctrl+Shift+Z'),QKeySequence('Ctrl+Y')])
        self.redo_action.triggered.connect(self.redo_edit)
        help_menu=self.menuBar().addMenu('Help')
        help_menu.addAction('About / Licenses…',self.show_about)
        split.setSizes([850,350])
        self.progress=QProgressBar();self.progress.setRange(0,1);self.progress.setValue(0)
        self.progress.hide()  # M8: only the analysis screen owns a visible progress indicator.
        self.info=QLabel('Source frames remain untouched.');layout.addWidget(self.info)
        QShortcut(QKeySequence(Qt.Key.Key_Left),self,activated=lambda:self.seek_index(self.current_index-1))
        QShortcut(QKeySequence(Qt.Key.Key_Right),self,activated=lambda:self.seek_index(self.current_index+1))
        QShortcut(QKeySequence(Qt.Key.Key_Up),self,activated=lambda:self.navigate_page(-1))
        QShortcut(QKeySequence(Qt.Key.Key_Down),self,activated=lambda:self.navigate_page(1))
        QShortcut(QKeySequence(Qt.Key.Key_Space),self,activated=self.toggle_play)
        self._set_stage("empty")
        self._refresh_actions()
        # Carry forward output recovery scope recorded by the legacy M1 GUI;
        # never scan arbitrary directories for crash journals.
        QTimer.singleShot(0,self._offer_prior_export_recovery)

    def _set_stage(self,stage):
        self.stage=stage
        self.work_area.setCurrentIndex({'empty':0,'preparation':0,'review':0,
                                        'analyzing':1,'exporting':2,'complete':3}[stage])
        reviewing=stage=='review'
        preparation=stage in ('empty','preparation')
        self.page_panel.setVisible(reviewing)

        for widget in (self.timeline,self.time_label,self.add_button,self.replace_button):
            widget.setVisible(reviewing)
        for widget in (self.crop_button,self.reset_roi,self.mask_button,self.clear_mask,
                       self.analyze_button):
            widget.setVisible(preparation)
        self.play_button.hide();self.slider.hide();self.delete_button.hide()
        self.fps.hide()
        self.export_button.setVisible(reviewing)
        self.review_filename.setVisible(reviewing)
        self.back_to_preparation.setVisible(reviewing)
        self.advanced_button.setVisible(preparation)
        self.open_button.setVisible(preparation)
        self.cancel_button.hide()

    def show_about(self):
        from slide_core.version import VERSION
        QMessageBox.about(self,'About Slide Extractor',
            f'<h3>Slide Extractor {VERSION}</h3>'
            '<p>Copyright © 2026 Juhwan Heo · MIT License.</p>'
            '<p>This app uses Qt/PySide6 under LGPLv3 and FFmpeg/FFprobe under LGPLv2.1 or later. '
            'You may modify and replace these libraries and tools.</p>'
            '<p>Original license texts are included in the app’s licenses folder. '
            'See SOURCE_AND_REPLACEMENT.md for replacement instructions.</p>'
            '<p><a href="https://github.com/juhwan0628/slide-extractor-gui/releases">'
            'Source archives and third-party notices</a></p>')

    def return_to_preparation(self):
        if self.stage!='review' or self.jobs.worker is not None:return
        self._stop_play()
        self._set_stage('preparation')
        self._show_preparation()
        self._refresh_actions()

    def return_to_review(self):
        if self.stage!='complete' or self.jobs.worker is not None:return
        if self.controller.project is None:return
        self._set_stage('review')
        self._refresh_actions()

    def open_export_folder(self):
        if self.stage!='complete' or not self._last_export:return
        folder=str(self._last_export[0].parent)
        if sys.platform=='darwin':argv=['open',folder]
        elif sys.platform=='win32':argv=['explorer',folder]
        else:argv=['xdg-open',folder]
        try:subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL,close_fds=True)
        except OSError as exc:QMessageBox.warning(self,'Unable to open folder',str(exc))

    def _finish_export_screen(self,paths):
        if not paths or not all(Path(p).is_file() for p in paths):
            raise ValueError('Export output missing after completion')
        self._last_export=tuple(Path(p) for p in paths)
        from pypdf import PdfReader
        pages=len(PdfReader(str(paths[0])).pages)
        if pages!=len(self.controller.project.pages):
            raise ValueError('Output page count mismatch')
        details=f'{Path(paths[0]).name}  •  {pages} pages\n{Path(paths[0]).parent}'
        if len(paths)>1:details+='\nAlso saved: '+', '.join(Path(p).name for p in paths[1:])
        self.complete_details.setText(details)
        self._set_stage('complete')

    @staticmethod
    def _cache_roi(project,sample):
        from math import floor,ceil
        roi=project.settings.effective_roi
        if roi is None:return None
        dw=project.source.transform.display_width
        dh=project.source.transform.display_height
        x=max(0,min(sample.width-1,floor(roi.x*sample.width/dw)))
        y=max(0,min(sample.height-1,floor(roi.y*sample.height/dh)))
        right=max(x+1,min(sample.width,ceil((roi.x+roi.width)*sample.width/dw)))
        bottom=max(y+1,min(sample.height,ceil((roi.y+roi.height)*sample.height/dh)))
        return (x,y,right-x,bottom-y)

    def open_advanced(self):
        if self.jobs.worker is not None:return
        dialog=QDialog(self);dialog.setWindowTitle('Advanced settings')
        form=QFormLayout(dialog)
        fps=QComboBox();fps.addItems(['0.5 FPS','1 FPS'])
        fps.setCurrentIndex(0 if self.settings.fps==0.5 else 1)
        form.addRow('Sampling rate',fps)
        sidecar=QCheckBox('Export JSON alongside PDF')
        sidecar.setChecked(self.json_enabled)
        form.addRow(sidecar)
        fmt=QComboBox()
        fmt.addItems(['Simple slide times','Detailed JSON v3'])
        fmt.setCurrentIndex(0 if self.json_format=='simple' else 1)
        fmt.setEnabled(sidecar.isChecked())
        sidecar.toggled.connect(fmt.setEnabled)
        form.addRow('JSON format',fmt)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|
                                  QDialogButtonBox.StandardButton.Cancel)
        form.addRow(buttons)
        buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        self.json_enabled=sidecar.isChecked()
        self.json_format='simple' if fmt.currentIndex()==0 else 'detailed'
        self.fps.setCurrentIndex(1 if fps.currentIndex()==0 else 0)
        self.export_button.setText('Save PDF + JSON' if self.json_enabled else 'Save PDF')

    def _offer_prior_export_recovery(self):
        if not self.isVisible():return
        settings=QSettings('SlideExtractor','SlideExtractor')
        paths=settings.value('export_parents',[])
        if isinstance(paths,str):paths=[paths]
        if not isinstance(paths,(tuple,list)):return
        for text in paths[-12:]:
            if not isinstance(text,str):continue
            parent=Path(text)
            if not parent.is_absolute() or not parent.is_dir():continue
            if not list(parent.glob('.slide-export-*.journal.json')):continue
            reply=QMessageBox.question(self,'Interrupted export',
                f'Recover only verified PDF/JSON files from:\n{parent}?',
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if reply!=QMessageBox.StandardButton.Yes:continue
            try:
                recovered=recover_export(parent)
                self.info.setText(f'Recovered {len(recovered)} interrupted export(s)')
            except (RecoveryRequired,OSError,ValueError) as exc:
                QMessageBox.warning(self,'Manual recovery required',str(exc))

    def _refresh_actions(self):
        a=self.controller.actions()
        self.open_button.setEnabled(a['open']);self.crop_button.setEnabled(a['region'])
        self.mask_button.setEnabled(a['region']);self.fps.setEnabled(a['region'])
        self.reset_roi.setEnabled(a['region']);self.clear_mask.setEnabled(a['region'])
        self.analyze_button.setEnabled(a['analyze']);self.cancel_button.setEnabled(a['cancel'])
        # Export only the validated READY project, never stale dirty settings.
        self.export_button.setEnabled(a['export'])
        self.advanced_button.setEnabled(self.jobs.worker is None)
        self.play_button.setEnabled(a['playback']);self.slider.setEnabled(a['playback'])
        self.delete_button.setEnabled(a['edit'] and bool(self.controller.focus_page_id))
        self._update_edit_buttons()
        self.page_menu.setEnabled(a['edit'] and bool(self.controller.focus_page_id))
        self.undo_button.setEnabled(a['edit'] and bool(self.history.undo_stack))
        self.redo_button.setEnabled(a['edit'] and bool(self.history.redo_stack))
        self.undo_action.setEnabled(a['edit'] and bool(self.history.undo_stack))
        self.redo_action.setEnabled(a['edit'] and bool(self.history.redo_stack))
        if self.controller.state==State.REVIEW_DIRTY:
            self.info.setText('Settings changed — reanalyze to apply before export')

    def _update_edit_buttons(self):
        project=self.controller.project
        ready=self.controller.actions()['edit'] and project is not None and bool(project.samples)
        sample=project.samples[self.current_index] if ready else None
        exists=bool(sample and any(p.representative_sample_id==sample.sample_id for p in project.pages))
        focused=next((p for p in project.pages if p.page_id==self.controller.focus_page_id),None) if ready else None
        self.add_button.setEnabled(ready and not exists)
        self.replace_button.setEnabled(ready and focused is not None and not exists)

    def _stop_play(self):
        self.tick_timer.stop()
        if self.player:self.player.pause()
        self.play_button.setText('Play')

    def choose_file(self):
        path,_=QFileDialog.getOpenFileName(self,'Open video','','Videos (*.mp4 *.mov *.mkv *.webm *.avi)')
        if not path:return
        self.open_source(Path(path))

    def open_source(self,path):
        self._stop_play();self.history.reset();self._undo_delete=None;self.controller.begin_probe();self._set_stage('empty');self._refresh_actions()
        self._job_type='probe'
        self._first_frame=None;self._suggested_roi=None
        self._job_id=self.jobs.start(self._prepare_source,path)

    @staticmethod
    def _prepare_source(path,*,cancel_token):
        source=probe_source(path,cancel_token=cancel_token)
        return source,prepare_first_frame(source,cancel_token=cancel_token)

    def _show_preparation(self):
        if self._first_frame is None:return
        from PySide6.QtGui import QPainter,QPen,QColor
        image=self._first_frame.copy()
        if self._suggested_roi is not None:
            sw=self.controller.source.transform.display_width
            sh=self.controller.source.transform.display_height
            r=self._suggested_roi
            painter=QPainter(image)
            painter.setPen(QPen(QColor('#29b6f6'),3))
            painter.drawRect(round(r.x*image.width()/sw),round(r.y*image.height()/sh),
                round(r.width*image.width()/sw),round(r.height*image.height()/sh))
            painter.end()
        self._paint(image)

    def _fps_changed(self,index):
        self.settings=replace(self.settings,fps=1. if index==0 else .5,
                              settings_revision=self.settings.settings_revision+1)
        self.controller.settings_changed(self.settings);self._refresh_actions()

    def _reset_roi(self):
        if not self.controller.actions()['region']:return
        self.settings=replace(self.settings,roi_mode='manual' if self._auto_roi else 'auto',effective_roi=self._auto_roi,
                              settings_revision=self.settings.settings_revision+1)
        self._suggested_roi=self._auto_roi
        self.controller.settings_changed(self.settings);self._show_preparation();self._refresh_actions()

    def _clear_mask(self):
        if not self.controller.actions()['region']:return
        self.settings=replace(self.settings,masks=(),settings_revision=self.settings.settings_revision+1)
        self.controller.settings_changed(self.settings);self._refresh_actions()

    def choose_region(self,is_mask):
        if not self.controller.source:return
        project=self.controller.project
        img=self._first_frame
        if img is None and project is not None and project.samples:
            key=self._image_key(0)
            img=self.images.cached(key)
            if img is None:
                self.images.request(key,project.samples[0].cache_path)
                self.info.setText('Loading preview; retry region editor shortly.')
                return
        if img is None:
            self.info.setText('First frame not yet available.')
            return
        sw=self.controller.source.transform.display_width
        sh=self.controller.source.transform.display_height
        existing=(self.settings.masks[0] if self.settings.masks else None) if is_mask else (
            self.settings.effective_roi or self._suggested_roi)
        initial=None
        if existing is not None:
            from math import floor,ceil
            x=floor(existing.x*img.width()/sw);y=floor(existing.y*img.height()/sh)
            right=ceil((existing.x+existing.width)*img.width()/sw)
            bottom=ceil((existing.y+existing.height)*img.height()/sh)
            initial=Rect(x,y,max(1,min(img.width(),right)-x),max(1,min(img.height(),bottom)-y))
        dialog=RegionDialog(img,'Ignore mask' if is_mask else 'Slide ROI',self)
        if hasattr(dialog,'view'):dialog.view.selection=initial
        if not dialog.exec():return
        r=dialog.value()
        if r is None:return
        from math import floor,ceil
        x=floor(r.x*sw/img.width());y=floor(r.y*sh/img.height())
        right=ceil((r.x+r.width)*sw/img.width())
        bottom=ceil((r.y+r.height)*sh/img.height())
        rect=Rect(x,y,max(1,min(sw,right)-x),max(1,min(sh,bottom)-y))
        if not is_mask:self._suggested_roi=rect
        self.settings=replace(self.settings,
           masks=(rect,) if is_mask else self.settings.masks,
           roi_mode=self.settings.roi_mode if is_mask else 'manual',
           effective_roi=self.settings.effective_roi if is_mask else rect,
           settings_revision=self.settings.settings_revision+1)
        self.controller.settings_changed(self.settings);self._show_preparation();self._refresh_actions()

    def analyze(self):
        if not self.controller.actions()['analyze']:return
        old=self.controller.project
        if old and old.pages and (old.revision or requires_reanalysis(old,self.settings)):
            answer=QMessageBox.question(self,'Replace edited pages?',
                'Reanalysis will reset manual page edits. Continue?',
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if answer!=QMessageBox.StandardButton.Yes:return
        self._stop_play();self._job_type='analysis'
        self._job_id=self.jobs.start(analyze_project,self.controller.source,self.settings,
                                    Path(gettempdir())/'slide-gui-cache',previous=old,_progress_enabled=True,
                                    profile_path=profile_directory(Path(__file__).resolve().parents[1])/f'analysis-{uuid4()}.json')
        self.controller.begin_analysis(self._job_id)
        self._set_stage('analyzing')
        self.analysis_title.setText('Preparing video analysis…')
        self.analysis_progress.setRange(0,0)
        self.progress.setRange(0,0);self.info.setText('Analyzing exact video PTS...')
        self._refresh_actions()

    def _job_progress(self,job_id,payload):
        if job_id!=self._job_id or self.stage not in ('analyzing','exporting'):return
        stage,done,total=payload
        labels={'sampling':'Sampling video frames','detecting':'Detecting slide changes',
                'assembling':'Building slide list','extracting':'Extracting original frames',
                'writing':'Writing PDF','verifying':'Verifying output',
                'publishing':'Saving files'}
        label=labels.get(stage,stage)
        indicator=self.analysis_progress if self.stage=='analyzing' else self.export_progress
        title=self.analysis_title if self.stage=='analyzing' else self.export_title
        if total is not None and total>0 and done is not None:
            value=max(0,min(100,int(done*100//total)))
            indicator.setRange(0,100);indicator.setValue(value)
            title.setText(f'{label} · {done:,} / {total:,} ({value}%)')
        else:
            indicator.setRange(0,0)
            title.setText(label+'…')

    def cancel(self):
        if self.controller.cancel():
            self.jobs.cancel();self.info.setText('Cancelling; finishing safe process cleanup...')
            if self.stage=='analyzing':self.analysis_title.setText('Cancelling safely…')
            if self.stage=='exporting':self.export_title.setText('Cancelling safely…')
            self._refresh_actions()

    def _job_finished(self,job_id,result,error):
        if job_id!=self._job_id:return
        if error is not None:
            was_cancelling=self.controller.state==State.CANCELLING
            if self._job_type=='probe':self.controller.fail_probe()
            else:self.controller.fail_job(job_id)
            cancelled=was_cancelling or isinstance(error,CancelledError) or self._close_later
            self.info.setText('Cancelled; previous project retained' if cancelled else str(error))
            if not cancelled:
                detail=str(error)
                if isinstance(error,RecoveryRequired):detail+='\nThe journal and verified backups were retained. Resolve before retrying.'
                QMessageBox.warning(self,'Operation failed',detail)
        elif self._job_type=='probe':
            self._stop_play();self.images.switch(None)
            source,first=result
            self.controller.complete_probe(source)
            self.history.reset()
            self.settings=AnalysisSettings(fps=self.settings.fps)
            self._first_frame=None;self._suggested_roi=None;self._auto_roi=None
            if first is not None:
                rgb,w,h,roi,warning=first
                self._first_frame=QImage(rgb,w,h,w*3,QImage.Format.Format_RGB888).copy()
                self._suggested_roi=roi
                self._auto_roi=roi
                self._first_frame_warning=warning
                if warning is None:
                    self.settings=replace(self.settings,roi_mode='manual',effective_roi=roi)
            self._thumb_cursor=0
            self.page_model.set_project(None);self.timeline.set_project(None)
            self.preview.clear()
            if self._first_frame is None:self.preview.setText(source.path.name)
            else:self._show_preparation()
            self._set_stage('preparation')
            self.info.setText(f'{source.path.name} | {source.width}×{source.height} | Review ROI / mask before Analyze'
                              + (' | Check automatic ROI manually' if self._first_frame_warning else ''))
        elif self._job_type=='export':
            self.controller.finish_export(job_id)
            try:
                self._finish_export_screen(result)
            except (OSError,ValueError) as exc:
                self._set_stage('review')
                QMessageBox.warning(self,'Export verification failed',str(exc))
                self.info.setText('Export verification failed: '+str(exc))
            else:
                self.info.setText('Export complete: '+', '.join(p.name for p in result))
        elif self._job_type=='analysis':
            project,_=result
            if self.controller.state==State.CANCELLING:
                self.controller.fail_job(job_id)
                self.info.setText('Analysis cancelled; previous project preserved')
                self._set_stage('review' if self.controller.project is not None else 'preparation')
            elif self.controller.finish_analysis(job_id,project):
                self.settings=project.settings
                self.history.reset(project)
                self._thumb_cursor=0
                self.page_model.set_project(project)
                self.timeline.set_project(project)
                self.images.switch(project.analysis_generation)
                times=[s.actual_time for s in project.samples]
                duration=float(dict(project.source.metadata)['duration_s'])
                self.player=PlaybackClock(times,duration)
                self.current_index=0
                with QSignalBlocker(self.slider):
                    self.slider.setRange(0,len(times)-1);self.slider.setValue(0)
                self.info.setText(f'{len(times)} frames · {len(project.pages)} pages')
                self._set_stage('review')
                self.review_filename.setText(f'{project.source.path.name}  ·  {len(project.pages)} pages')
                if project.pages:
                    first=project.pages[0]
                    self.page_view.setCurrentIndex(self.page_model.index(0))
                    self.current_index=next((i for i,sample in enumerate(project.samples)
                        if sample.sample_id==first.representative_sample_id),0)
                self._render_frame(self.current_index)
                self._prefetch_thumbs()
                self._pump_all_thumbs()
        self.progress.setRange(0,1);self.progress.setValue(1 if error is None else 0)
        if error is not None or self.controller.state==State.CANCELLING:
            self._set_stage('review' if self.controller.project is not None else
                            'preparation' if self.controller.source is not None else 'empty')
        self._refresh_actions()
        if self._close_later:
            self._close_later=False;self.close()

    def _prefetch_thumbs(self):
        project=self.controller.project
        if project is None:return
        lookup={s.sample_id:s for s in project.samples}
        start=0
        if self.controller.focus_page_id:
            start=next((i for i,p in enumerate(project.pages)
                if p.page_id==self.controller.focus_page_id),0)
        for p in project.pages[max(0,start-1):min(len(project.pages),start+4)]:
            sample=lookup[p.representative_sample_id]
            key=(project.analysis_generation,sample.sample_id,'thumb',1)
            image=self.images.request(key,sample.cache_path,kind='thumb',size=QSize(150,85),
                                      crop=self._cache_roi(project,sample))
            if image is not None:self.page_model.set_thumbnail(sample.sample_id,QIcon(QPixmap.fromImage(image)))

    def _pump_all_thumbs(self):
        # Submit one low-resolution page thumbnail at a time. This avoids
        # losing requests when the bounded image queue is already busy.
        project=self.controller.project
        if project is None or self.stage!='review':return
        lookup={s.sample_id:s for s in project.samples}
        while self._thumb_cursor<len(project.pages):
            page=project.pages[self._thumb_cursor]
            sample=lookup[page.representative_sample_id]
            key=(project.analysis_generation,sample.sample_id,'thumb',1)
            if self.page_model._thumbs.get(sample.sample_id):
                self._thumb_cursor+=1
                continue
            cached=self.images.cached(key,kind='thumb')
            if cached is not None:
                self.page_model.set_thumbnail(sample.sample_id,QIcon(QPixmap.fromImage(cached)))
                self._thumb_cursor+=1
                continue
            # The loader may already have this key queued; delivery triggers
            # the next pump. Keep the cursor here until the icon is visible.
            self.images.request(key,sample.cache_path,kind='thumb',
                                size=QSize(150,85),crop=self._cache_roi(project,sample))
            return

    def _image_key(self,index,kind='preview'):
        p=self.controller.project
        return (p.analysis_generation,p.samples[index].sample_id,kind,1)

    def _image_ready(self,key,image,error):
        self.images.ack()
        project=self.controller.project
        if project is None or key[0]!=project.analysis_generation:return
        if error:
            self._stop_play();self.info.setText(f'Cache image unavailable — reanalyze: {error}')
            # Block use of corrupt cache in export even if page metadata still exists.
            self.controller.state=State.REVIEW_DIRTY;self._refresh_actions();return
        if key==self._image_key(self.current_index):self._paint(image)
        if len(key)>=3 and key[2]=='thumb':
            icon=QIcon(QPixmap.fromImage(image))
            self.page_model.set_thumbnail(key[1],icon)
            self._pump_all_thumbs()

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if self._current_image is not None and hasattr(self,'preview'):
            self._paint(self._current_image)

    def _paint(self,image):
        self._current_image=image
        self.preview.setPixmap(QPixmap.fromImage(image).scaled(self.preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))

    def _render_frame(self,index):
        project=self.controller.project
        if not project or not project.samples:return
        self.current_index=max(0,min(index,len(project.samples)-1))
        sample=project.samples[self.current_index]
        key=self._image_key(self.current_index)
        image=self.images.request(key,sample.cache_path,crop=self._cache_roi(project,sample))
        if image is not None:self._paint(image)
        else:self.preview.clear()
        for i in [self.current_index-1,*range(self.current_index+1,self.current_index+4)]:
            if 0<=i<len(project.samples):
                other=project.samples[i]
                self.images.request(self._image_key(i),other.cache_path,crop=self._cache_roi(project,other))
        with QSignalBlocker(self.slider):self.slider.setValue(self.current_index)
        t=float(sample.actual_time);d=float(dict(project.source.metadata)['duration_s'])
        self.time_label.setText(f'{int(t//60):02d}:{int(t%60):02d} / {int(d//60):02d}:{int(d%60):02d}')
        self.timeline.set_position(self.player.target() if self.player else t)
        self._update_edit_buttons()
        # Playback follows active page but does not change the edit focus.
        for page in reversed(project.pages):
            if project.sample_time(page.representative_sample_id)<=sample.actual_time:
                self.controller.active_page_id=page.page_id;break

    def seek_index(self,index):
        if not self.player:return
        self._stop_play();self.player.seek_index(index);self._render_frame(self.player.index())

    def seek_seconds(self,seconds):
        if not self.player:return
        self._stop_play();self.player.seek_seconds(seconds);self._render_frame(self.player.index())

    def toggle_play(self):
        if not self.player or self.stage!='review':return
        if self.player.playing:self._stop_play()
        else:self.player.play();self.play_button.setText('Pause');self.tick_timer.start()

    def _tick(self):
        if not self.player:return
        idx=self.player.tick()
        if idx!=self.current_index:self._render_frame(idx)
        self.timeline.set_position(self.player.target())
        if not self.player.playing:self._stop_play()

    def navigate_page(self,delta):
        project=self.controller.project
        if self.stage!='review' or project is None:return
        page_id=navigate(project,self.controller.focus_page_id,delta)
        if page_id is not None:
            row=next(i for i,p in enumerate(project.pages) if p.page_id==page_id)
            self.page_view.setCurrentIndex(self.page_model.index(row))
            self._page_clicked(self.page_model.index(row))

    def _current_page_menu(self):
        index=self.page_view.currentIndex()
        if index.isValid():self._show_page_menu(self.page_menu.mapToGlobal(self.page_menu.rect().bottomLeft()),index)

    def _page_context_menu(self,pos):
        index=self.page_view.indexAt(pos)
        if index.isValid():
            self.page_view.setCurrentIndex(index)
            self._page_clicked(index)
            self._show_page_menu(self.page_view.mapToGlobal(pos),index)

    def _show_page_menu(self,position,index):
        if not self.controller.actions()['edit'] or not index.isValid():return
        menu=QMenu(self)
        deletion=menu.addAction('Delete page')
        chosen=menu.exec(position)
        if chosen is deletion:self.delete_page()

    def _snapshot(self):
        return Snapshot(tuple(self.controller.project.pages),self.controller.focus_page_id)

    def _restore_snapshot(self,snapshot):
        project=self.controller.project
        if not project or not self.controller.actions()['edit']:return
        from slide_core.models import Project,EditResult
        old_ids=[p.page_id for p in project.pages]
        Project(project.source,project.settings,project.samples,project.transitions,
                project.segments,list(snapshot.pages),project.revision+1,
                project.cache_generation,project.analysis_generation)
        project.pages=list(snapshot.pages)
        project.revision+=1
        self._update_after_edit(EditResult('changed',snapshot.focus,()),old_ids)
        if snapshot.focus:
            page=next((p for p in project.pages if p.page_id==snapshot.focus),None)
            if page:
                self.seek_seconds(float(project.sample_time(page.representative_sample_id)))
        self._refresh_actions()

    def undo_edit(self):
        if not self.controller.actions()['edit']:return
        snapshot=self.history.undo(self.controller.project)
        if snapshot is not None:self._restore_snapshot(snapshot)

    def redo_edit(self):
        if not self.controller.actions()['edit']:return
        snapshot=self.history.redo(self.controller.project)
        if snapshot is not None:self._restore_snapshot(snapshot)

    def undo_delete(self):
        # Compatibility for existing tests, but implemented through the shared history.
        self.undo_edit()

    def _focus_marker(self,page_id):
        project=self.controller.project
        if not project:return
        for index,page in enumerate(project.pages):
            if page.page_id==page_id:
                self.controller.focus_page_id=page_id
                self.page_view.setCurrentIndex(self.page_model.index(index))
                self._prefetch_thumbs()
                self._refresh_actions()
                break

    def _page_clicked(self,index):
        project=self.controller.project
        if project is None or not index.isValid():return
        page=project.pages[index.row()]
        self.controller.focus_page_id=page.page_id
        sec=project.sample_time(page.representative_sample_id)
        self.seek_seconds(float(sec));self._prefetch_thumbs();self._refresh_actions()

    def _update_after_edit(self,result,old_ids):
        if result.status!='changed':
            self.info.setText(result.code or result.status);return
        self.page_model.sync(old_ids)
        self.controller.adopted_edit(result.focus_page_id)
        self.timeline.update()
        if result.focus_page_id:
            row=next(i for i,p in enumerate(self.controller.project.pages) if p.page_id==result.focus_page_id)
            self.page_view.setCurrentIndex(self.page_model.index(row))
        else:self.page_view.clearSelection()
        self._prefetch_thumbs()
        self._thumb_cursor=0
        self._pump_all_thumbs()
        self.review_filename.setText(f'{self.controller.project.source.path.name}  ·  {len(self.controller.project.pages)} pages')
        self.info.setText(f'{len(self.controller.project.pages)} pages · revision {self.controller.project.revision}')
        self._refresh_actions()

    def add_page(self):
        if not self.controller.actions()['edit']:return
        project=self.controller.project
        old=[p.page_id for p in project.pages]
        before=self._snapshot()
        result=add_page(project,project.samples[self.current_index].actual_time)
        if result.status=='changed':self.history.record(project,before,Snapshot(tuple(project.pages),result.focus_page_id))
        self._update_after_edit(result,old)

    def replace_page(self):
        project=self.controller.project
        if not project or not self.controller.focus_page_id:return
        old=[p.page_id for p in project.pages]
        before=self._snapshot()
        result=replace_page(project,self.controller.focus_page_id,project.samples[self.current_index].actual_time)
        if result.status=='changed':self.history.record(project,before,Snapshot(tuple(project.pages),result.focus_page_id))
        self._update_after_edit(result,old)

    def delete_page(self):
        project=self.controller.project
        if not project or not self.controller.focus_page_id:return
        old=[p.page_id for p in project.pages]
        before=self._snapshot()
        result=delete_page(project,self.controller.focus_page_id)
        if result.status=='changed':
            self.history.record(project,before,Snapshot(tuple(project.pages),result.focus_page_id))
            self._undo_delete=(project,before.pages,before.focus)
        self._update_after_edit(result,old)

    def export_pending(self):
        if not self.controller.actions()['export'] or self.jobs.worker is not None:return
        file,_=QFileDialog.getSaveFileName(self,'Save PDF' + (' and JSON' if self.json_enabled else ''),'','PDF (*.pdf)')
        if not file:return
        destination=Path(file).with_suffix('.pdf')
        parent=destination.parent
        if list(parent.glob('.slide-export-*.journal.json')):
            approval=QMessageBox.question(self,'Interrupted export',
               f'Verified previous export recovery is required in {parent}. Recover first?',
               QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,
               QMessageBox.StandardButton.No)
            if approval!=QMessageBox.StandardButton.Yes:return
            try:recover_export(parent)
            except RecoveryRequired as exc:
                QMessageBox.warning(self,'Manual recovery required',f'{exc}\nJournal/backup files remain in {parent}')
                return
        try:
            approval_snapshot=(snapshot_export(self.controller.project.source.path,destination,overwrite=True)
                               if self.json_enabled else snapshot_pdf(destination))
        except (OSError,ValueError) as exc:
            QMessageBox.warning(self,'Invalid output',str(exc));return
        overwrite=False
        conflicts=[destination]
        if self.json_enabled:conflicts.append(destination.with_suffix('.json'))
        if any(path.exists() or path.is_symlink() for path in conflicts):
            approval=QMessageBox.question(self,'Replace existing output?',
                'This will replace: '+', '.join(str(path) for path in conflicts)+'\nContinue?',
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if approval!=QMessageBox.StandardButton.Yes:return
            overwrite=True
        self._stop_play()
        self._job_type='export'
        if self.json_enabled:
            self._job_id=self.jobs.start(export_project,self.controller.project,destination,
                                         overwrite=overwrite,sidecar_format=self.json_format,snapshot=approval_snapshot,_progress_enabled=True)
        else:
            self._job_id=self.jobs.start(export_pdf_only,self.controller.project,destination,
                                         overwrite=overwrite,snapshot=approval_snapshot,_progress_enabled=True)
        self.controller.begin_export(self._job_id)
        self._set_stage('exporting')
        self.export_title.setText('Preparing PDF export…')
        self.export_progress.setRange(0,0)
        self.progress.setRange(0,0)
        self.info.setText('Extracting exact PTS frames and verifying output…')
        self._refresh_actions()

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if self._current_image is not None:self._paint(self._current_image)

    def closeEvent(self,event):
        if not self.jobs.close_ready():
            event.ignore();self._close_later=True
            self.controller.close()
            self.jobs.cancel();self._stop_play();return
        if not self.controller.close():
            event.ignore();self._close_later=True
            self.jobs.cancel();self._stop_play();return
        self._stop_play()
        self.images.stop();self.page_model.set_project(None)
        self.preview.clear()
        super().closeEvent(event)
