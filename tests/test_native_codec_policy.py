import runpy
from pathlib import Path
import pytest

MODULE=Path(__file__).resolve().parents[1]/'packaging/native_codec_policy.py'

def policy():
    return runpy.run_path(str(MODULE))['validate_image_only_opencv']

def test_rejects_original_video_enabled_wheel(tmp_path):
    (tmp_path/'libavcodec.61.dylib').write_bytes(b'--enable-gpl --enable-libx264')
    with pytest.raises(ValueError,match='video|codec'):
        policy()(tmp_path,'OpenCV 5.0.0\n  Video I/O:\n    FFMPEG: YES\n',has_video_capture=True)

def test_rejects_codec_even_if_module_reports_disabled(tmp_path):
    (tmp_path/'opencv_videoio_ffmpeg500_64.dll').write_bytes(b'codec')
    with pytest.raises(ValueError,match='codec'):
        policy()(tmp_path,'OpenCV 5.0.0\n To be built: core imgproc imgcodecs python3\n',has_video_capture=False)

def test_accepts_only_image_processing_libraries(tmp_path):
    (tmp_path/'cv2.pyd').write_bytes(b'image processing library')
    policy()(tmp_path,'OpenCV 5.0.0\n To be built: core imgproc imgcodecs python3\n',has_video_capture=False)
