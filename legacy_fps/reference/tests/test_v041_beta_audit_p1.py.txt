"""P1 regression contracts; known defects deliberately fail (no xfail).

All media and outputs are synthetic and live under tmp_path. Crash tests exit a
child at a named rename boundary; other injections avoid timing/RSS thresholds.
Windows directory-open behavior is emulated, not a native Windows run.
"""

import errno
import json
import os
from pathlib import Path
import subprocess
import sys
from fractions import Fraction
from uuid import uuid4

import numpy as np
from PIL import Image
from pypdf import PdfReader
import pytest

from slide_core import export, media, pdf, pdf_only_export, pts
from slide_core.config import AnalysisSettings
from slide_core.models import DisplayTransform, Page, Project, Rect, Sample, SourceRef
from slide_core.transitions import streaming_detect


def _source(path, *, width=80, height=48):
    stat = path.stat()
    return SourceRef(
        path, stat.st_size, stat.st_mtime_ns, 0, width, height,
        DisplayTransform(width, height), media.fingerprint_source(path),
        metadata=(("time_base_num", 1), ("time_base_den", 4),
                  ("origin_pts", 0), ("duration_s", 3.0)),
    )


def _pair(destination):
    return tuple(p.read_bytes() if p.exists() else None
                 for p in (destination, destination.with_suffix(".json")))


@pytest.mark.parametrize("identical_json", [False, True], ids=["different-json", "identical-json"])
def test_interrupted_commit_preserves_original_pair(tmp_path, monkeypatch, identical_json):
    """Crash after PDF backup, before JSON backup; JSON may equal the new JSON."""
    source = tmp_path / "source.mp4"
    source.write_bytes(b"synthetic-source")
    destination = tmp_path / "slides.pdf"
    destination.write_bytes(b"old-pdf")
    sidecar = destination.with_suffix(".json")
    sidecar.write_bytes(b'{"slides":[]}')
    before = _pair(destination)
    child_script = tmp_path / "interrupt_commit.py"
    child_script.write_text(
        """
import os
from pathlib import Path
import sys
import pytest
from slide_core import export

source, destination = map(Path, sys.argv[1:3])
tx = export.ExportTransaction(source, export.snapshot_export(source, destination, overwrite=True))
new_json = destination.with_suffix('.json').read_bytes() if sys.argv[3] == 'same' else b'{"slides":[1]}'
tx.prepare(b'new-pdf', new_json)
original = export.os.replace

def exit_after_pdf_backup(src, dst, *args, **kwargs):
    result = original(src, dst, *args, **kwargs)
    if Path(src) == destination and Path(dst) == tx.stage / '0.old':
        os._exit(77)  # Bypass commit's exception rollback, like abrupt process death.
    return result

with pytest.MonkeyPatch.context() as patch:
    patch.setattr(export.os, 'replace', exit_after_pdf_backup)
    tx.commit()
raise AssertionError('Named interruption boundary was not reached')
""", encoding="utf-8",
    )
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    # Make the subprocess import independent of pytest's invocation directory.
    monkeypatch.setenv("PYTHONPATH", str(Path(__file__).resolve().parents[1]))
    child = subprocess.run(
        [sys.executable, str(child_script), str(source), str(destination),
         "same" if identical_json else "different"],
        capture_output=True, timeout=20,
    )
    assert child.returncode == 77, child.stderr.decode(errors="replace")
    journals = list(tmp_path.glob(".slide-export-*.journal.json"))
    assert len(journals) == 1
    record = json.loads(journals[0].read_text(encoding="utf-8"))
    assert record["phase"] == "COMMITTING"
    stage = tmp_path / f".slide-export-{record['export_id']}"
    assert (stage / "0.old").read_bytes() == before[0]
    assert not (stage / "1.old").exists()
    assert sidecar.read_bytes() == before[1]

    recovery_error = None
    try:
        reports = export.recover_export(tmp_path)
    except export.RecoveryRequired as exc:
        recovery_error = exc
    assert _pair(destination) == before, (
        f"Recovery lost original bytes; error={recovery_error!r}"
    )
    assert recovery_error is None
    assert reports == ((record["export_id"], "rolled_back"),)
    assert export.recover_export(tmp_path) == ()


@pytest.mark.parametrize("directory_errno", [errno.EINVAL, errno.EACCES],
                         ids=["unsupported-einval", "windows-eacces"])
def test_directory_sync_unavailable_still_publishes_pair(tmp_path, monkeypatch, directory_errno):
    """Windows CRT may reject opening a directory before fsync is even called."""
    source = tmp_path / "source.mp4"
    source.write_bytes(b"synthetic-source")
    destination = tmp_path / "slides.pdf"
    tx = export.ExportTransaction(source, export.snapshot_export(source, destination))
    original_open = export.os.open
    rejected = []

    def open_without_directory_handles(path, flags, *args, **kwargs):
        if isinstance(path, (str, os.PathLike)) and Path(path).is_dir() and flags == os.O_RDONLY:
            rejected.append(Path(path))
            exc = OSError(directory_errno, "injected directory handle unavailable", str(path))
            if directory_errno == errno.EACCES:
                exc.winerror = 5
            raise exc
        return original_open(path, flags, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(export.os, "open", open_without_directory_handles)
        tx.prepare(b"new-pdf", b'{"slides":[]}')
        record = json.loads(tx.journal_path.read_text(encoding="utf-8"))
        assert record["directory_sync_supported"] is False
        tx.commit()
    assert rejected
    assert _pair(destination) == (b"new-pdf", b'{"slides":[]}')
    assert export.recover_export(tmp_path) == ((tx.export_id, "committed"),)


@pytest.mark.parametrize("phase", ["construct", "commit"])
def test_export_source_identity_does_not_read_entire_video(tmp_path, monkeypatch, phase):
    """Reject only source.read_bytes; permit bounded fingerprint and output reads."""
    source_path = tmp_path / "sparse-source.mp4"
    with source_path.open("wb") as stream:
        stream.truncate(8 * 1024 * 1024)
    source = _source(source_path)
    destination = tmp_path / "slides.pdf"
    snapshot = export.snapshot_export(source_path, destination)
    tx = None
    if phase == "commit":
        tx = export.ExportTransaction(source_path, snapshot)
        tx.prepare(b"new-pdf", b'{"slides":[]}')
    original_read_bytes = Path.read_bytes

    def forbid_whole_source_read(path):
        if path == source_path:
            raise AssertionError(f"{phase}: source.read_bytes() allocates the entire video")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", forbid_whole_source_read)
    assert media.source_matches(source), "Bounded identity control must remain usable"
    if phase == "construct":
        tx = export.ExportTransaction(source_path, snapshot)
        tx.prepare(b"new-pdf", b'{"slides":[]}')
    tx.commit()
    assert export.recover_export(tmp_path) == ((tx.export_id, "committed"),)


def test_pts_extraction_stops_before_unrequested_eof(tmp_path, monkeypatch):
    """Real FFmpeg decode: extracting PTS zero must not audit the complete tail."""
    path = tmp_path / "twelve-frames.mkv"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
         "-f", "lavfi", "-i", "color=c=red:size=80x48:rate=4:duration=3",
         "-c:v", "ffv1", str(path)],
        check=True, capture_output=True, timeout=20,
    )
    source = media.probe_source(path)
    origin = dict(source.metadata)["origin_pts"]
    audited_pts = []
    original_audit = pts._AUDIT

    class RecordingAudit:
        def search(self, line):
            match = original_audit.search(line)
            if match:
                audited_pts.append(int(match[2]))
            return match

    monkeypatch.setattr(pts, "_AUDIT", RecordingAudit())
    result = pts.extract_selected(source, [origin], tmp_path / "extracted")
    assert len(result) == 1
    with Image.open(result[0]) as image:
        assert image.size == (80, 48)
        assert image.getpixel((0, 0))[0] > 200
    assert audited_pts and audited_pts[0] == origin
    # Last source frame is at 2.75 s; do not use elapsed-time performance assertions.
    tb = Fraction(dict(source.metadata)["time_base_num"], dict(source.metadata)["time_base_den"])
    assert max(audited_pts) * tb < origin * tb + Fraction(11, 4), (
        f"Extracting only origin audited through EOF: {len(audited_pts)} frames, "
        f"last PTS={max(audited_pts)}"
    )


@pytest.mark.parametrize("times,expected", [
    ([0, 1, 2, 3, 4, 5], [2]),
    ([0, 1, 2, 5], []),
    ([0, 1, 2, 5, 6, 7], [5]),
], ids=["uniform-control", "gap-only-unconfirmed-control", "stable-after-vfr-gap"])
def test_vfr_gap_does_not_suppress_later_stable_transition(tmp_path, times, expected):
    """Two close B observations after a gap must eventually create a B segment."""
    samples = []
    for i, timestamp in enumerate(times):
        image_path = tmp_path / f"sample-{i}.png"
        Image.new("L", (80, 48), 20 if i < 2 else 180).save(image_path)
        samples.append(Sample(f"s{i}", timestamp, timestamp, Fraction(1),
                              Fraction(timestamp), str(image_path), 80, 48))

    def frames():
        for sample in samples:
            with Image.open(sample.cache_path) as image:
                yield np.array(image, dtype=np.uint8)

    # No clocks or metrics are mocked: actual masked tile/anchor comparisons run.
    transitions, segments = streaming_detect(samples, frames(), duration=times[-1] + 1)
    assert [t.observed_time for t in transitions] == list(map(Fraction, expected)), (
        f"Stable state after times={times} disappeared: {len(segments)} segment(s)"
    )
    assert len(segments) == len(expected) + 1
    if expected:
        assert transitions[0].reason == "confirmed"
        assert transitions[0].persistence_samples == 2
        assert samples[2].sample_id != segments[-1].representative_sample_id
        assert segments[-1].first_sample_id == samples[times.index(expected[0])].sample_id


@pytest.mark.parametrize("consumer", ["sample_stream", "extract_selected"])
def test_probed_color_metadata_reaches_decode_pipeline(tmp_path, monkeypatch, consumer):
    """Tagged SD BT.709/full-range must retain probe's explicit display filter."""
    path = tmp_path / "tagged-source.mp4"
    path.write_bytes(b"synthetic-tagged-source")
    stream = {
        "index": 0, "codec_type": "video", "codec_name": "h264",
        "width": 80, "height": 48, "time_base": "1/4", "duration": "3",
        "sample_aspect_ratio": "1:1", "color_space": "bt709",
        "color_range": "pc", "color_transfer": "bt709", "pix_fmt": "yuv444p",
    }

    def probe(argv, **kwargs):
        payload = ({"streams": [stream], "format": {}} if "-show_streams" in argv
                   else {"frames": [{"best_effort_timestamp": "0"}]})
        return media._ProcessResult(json.dumps(payload), "", 0)

    monkeypatch.setattr(media, "_run_process", probe)
    source = media.probe_source(path)
    expected_filter = dict(source.metadata)["display_filter"]
    assert "in_color_matrix=bt709:in_range=pc" in expected_filter
    pipelines = []
    original_build = pts.build_display_pipeline

    def record_pipeline(**kwargs):
        pipeline = original_build(**kwargs)
        pipelines.append((kwargs, pipeline))
        return pipeline

    def decoded(source, vf, width, height, **kwargs):
        yield 0, bytes((120, 50, 20)) * (width * height)

    monkeypatch.setattr(pts, "build_display_pipeline", record_pipeline)
    monkeypatch.setattr(pts, "_decode_stream", decoded)
    if consumer == "sample_stream":
        samples, session = pts.sample_stream(source, tmp_path / "cache")
        assert len(samples) == 1 and session.is_dir()
        assert Path(samples[0].cache_path).is_file()
    else:
        frames = pts.extract_selected(source, [0], tmp_path / "frames")
        assert len(frames) == 1 and frames[0].is_file()
    assert len(pipelines) == 1
    kwargs, pipeline = pipelines[0]
    assert pipeline.full_filter == expected_filter, (
        f"{consumer} dropped probe color tags: kwargs={kwargs}"
    )
    assert kwargs["color_matrix"] == "bt709"
    assert kwargs["color_range"] == "pc"
    assert kwargs["transfer"] == "bt709"
    assert kwargs["pixel_format"] == "yuv444p"


def test_cancel_after_pdf_publish_reports_success(tmp_path, monkeypatch):
    """Run real PDF exporter and Worker.run; cancel at final published validation."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    from gui.workers import Worker

    qt = QApplication.instance() or QApplication([])
    source_path = tmp_path / "source.mp4"
    source_path.write_bytes(b"synthetic-source")
    source = _source(source_path)
    cache = tmp_path / "cache.png"
    Image.new("RGB", (80, 48), (120, 50, 20)).save(cache)
    sample = Sample("s0", 0, 0, Fraction(1, 4), Fraction(0), str(cache), 80, 48)
    page = Page(str(uuid4()), sample.sample_id, "manual", None, None, "insert")
    project = Project(source, AnalysisSettings(roi_mode="full", effective_roi=Rect(0, 0, 80, 48)),
                      samples=(sample,), pages=[page])
    destination = tmp_path / "published.pdf"

    def extract(source, selections, output_root, **kwargs):
        assert len(selections) == 1
        frame = Path(output_root) / "frame.png"
        with Image.open(cache) as image:
            image.save(frame)
        return (frame,)

    monkeypatch.setattr(pdf_only_export, "extract_selected", extract)
    monkeypatch.setattr(pdf, "_run_qpdf_optimization", lambda *args, **kwargs: False)
    worker = Worker(pdf_only_export.export_pdf_only, project, destination)
    original_validate = pdf_only_export.validate_slides_pdf
    published_validations = []

    def cancel_after_final_validation(path, *args, **kwargs):
        result = original_validate(path, *args, **kwargs)
        if Path(path) == destination:
            published_validations.append(Path(path))
            worker.cancel_token.cancel()
        return result

    monkeypatch.setattr(pdf_only_export, "validate_slides_pdf", cancel_after_final_validation)
    outcomes = []
    worker.outcome.connect(lambda *args: outcomes.append(args), Qt.ConnectionType.DirectConnection)
    # Synchronous run exercises identical worker logic without thread/event-loop races.
    worker.run()
    assert qt is not None
    assert published_validations == [destination]
    assert destination.is_file() and len(PdfReader(destination).pages) == 1
    assert worker.cancel_token.cancelled
    assert len(outcomes) == 1
    job_id, result, error = outcomes[0]
    assert job_id == worker.job_id
    assert (result, error) == ((destination,), None), (
        f"Valid published PDF misreported: result={result!r}, error={error!r}"
    )
