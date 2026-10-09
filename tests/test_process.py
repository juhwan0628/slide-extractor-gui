import os
import sys
import time
from pathlib import Path

import pytest

from slide_core.media import MediaError, _run_process
from slide_core.models import CancelToken


def py(code):
    return [sys.executable, "-c", code]


def test_drains_both_pipes_and_keeps_only_stderr_tail():
    result = _run_process(py("import sys; sys.stdout.write('o'*200000); sys.stderr.write('e'*200000)"),
                          tool="python", phase="flood", timeout=3)
    assert len(result.stdout) == 200000
    assert len(result.stderr_tail) == 65536
    assert result.stderr_tail == "e" * 65536


def test_nonzero_exit_has_code_tool_phase_and_stderr():
    with pytest.raises(MediaError) as caught:
        _run_process(py("import sys; print('bad', file=sys.stderr); sys.exit(7)"),
                     tool="fake", phase="probe", timeout=2)
    assert "7" in str(caught.value) and "fake" in str(caught.value)
    assert "probe" in str(caught.value) and "bad" in str(caught.value)
    assert (caught.value.code, caught.value.tool, caught.value.phase, caught.value.exit_code) == ("ProcessFailed", "fake", "probe", 7)


def test_timeout_reaps_hung_process():
    with pytest.raises(MediaError, match="Timeout"):
        _run_process(py("import time; time.sleep(10)"), tool="fake", phase="hang", timeout=.15)


def test_timeout_uses_injected_clock():
    ticks = iter(range(100))
    with pytest.raises(MediaError, match="Timeout"):
        _run_process(py("import time; time.sleep(10)"), tool="fake", phase="clock", timeout=2,
                     clock=lambda: next(ticks) * 10)


def test_cancel_with_full_output_is_observed_and_reaped():
    token = CancelToken()
    import threading
    threading.Timer(.1, token.cancel).start()
    started = time.monotonic()
    with pytest.raises(MediaError, match="cancel"):
        _run_process(py("import sys; [sys.stdout.write('x'*8192) for _ in iter(int, 1)]"),
                     tool="fake", phase="cancel", timeout=5, cancel_token=token)
    assert time.monotonic() - started < 3


@pytest.mark.skipif(os.name == "nt", reason="POSIX child signal behavior")
def test_ignores_terminate_then_is_killed():
    with pytest.raises(MediaError, match="Timeout"):
        _run_process(py("import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(10)"),
                     tool="fake", phase="kill", timeout=.1, terminate_grace=.1)


def test_missing_tool_is_structured_media_error():
    with pytest.raises(MediaError, match="MissingTool"):
        _run_process(["/path/that/does/not/exist"], tool="gone", phase="version", timeout=1)


def test_repeated_zero_progress_and_stderr_do_not_reset_stall():
    code = "import sys,time;\nwhile True: print('frame=0'); sys.stdout.flush(); print('warning',file=sys.stderr); sys.stderr.flush(); time.sleep(.01)"
    with pytest.raises(MediaError, match="Timeout"):
        _run_process(py(code), tool="fake", phase="frame", timeout=2, stall_timeout=.15)


def test_progress_receives_throttled_records():
    from slide_core.models import ProgressRecord
    records = []
    _run_process(py("print('frame=1'); print('out_time_us=1000000'); print('progress=end')"),
                 tool="fake", phase="frame", timeout=2, progress=records.append)
    assert records and all(isinstance(record, ProgressRecord) for record in records)
    assert records[-1].completed == 1


def test_frame_progress_advances_after_out_time_uses_consistent_frame_count():
    records = []
    code = "import time; print('out_time_us=1000000',flush=True); time.sleep(.12); print('frame=2',flush=True)"
    _run_process(py(code), tool="fake", phase="frame", timeout=2, stall_timeout=.18, progress=records.append)
    assert records[-1].completed == 2


def test_slow_callback_does_not_block_reader_or_cancel():
    import threading
    token = CancelToken()
    callback_entered = threading.Event()
    def callback(_):
        callback_entered.set()
        time.sleep(2)
    def cancel_after_callback():
        assert callback_entered.wait(1)
        token.cancel()
    threading.Thread(target=cancel_after_callback, daemon=True).start()
    started = time.monotonic()
    with pytest.raises(MediaError, match="Cancelled"):
        _run_process(py("import time; print('frame=1',flush=True); time.sleep(30)"), tool="fake", phase="frame",
                     timeout=5, cancel_token=token, progress=callback)
    assert time.monotonic() - started < 1


@pytest.mark.skipif(os.name == "nt", reason="POSIX process session behavior")
def test_exits_when_descendant_inherits_pipe_after_parent_exit():
    code = "import subprocess,sys; subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']); print('done')"
    started = time.monotonic()
    result = _run_process(py(code), tool="fake", phase="probe", timeout=2)
    assert result.stdout.strip() == "done"
    assert time.monotonic() - started < 2


def test_overall_budgets_follow_spec():
    from slide_core.config import analysis_timeout, export_timeout
    assert analysis_timeout(10) == 300
    assert analysis_timeout(400) == 800
    assert export_timeout(1) == 300
    assert export_timeout(4) == 480


def test_qpdf_uses_runner_and_accepts_exit_three(tmp_path, monkeypatch):
    from slide_core import pdf
    script = tmp_path / "fake-qpdf"
    script.write_text("#!/usr/bin/env python3\nimport pathlib,sys\npathlib.Path(sys.argv[-1]).write_bytes(pathlib.Path(sys.argv[-2]).read_bytes())\nsys.stderr.write('d'*200000)\nsys.exit(3)\n")
    script.chmod(0o755)
    source, output = tmp_path / "in.pdf", tmp_path / "out.pdf"
    source.write_bytes(b"synthetic")
    monkeypatch.setattr(pdf.shutil, "which", lambda name: str(script))
    assert pdf._run_qpdf_optimization(source, output)
    assert output.read_bytes() == b"synthetic"
