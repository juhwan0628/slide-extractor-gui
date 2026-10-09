"""Reject accidental codec bundles; video decoding belongs to pinned FFmpeg tools."""
from pathlib import Path
import re

FORBIDDEN=('avcodec','avformat','avdevice','avfilter','x264','x265','opencv_videoio_ffmpeg')

def verify_no_extra_codecs(root):
    for path in Path(root).rglob('*'):
        if path.is_file() and any(name in path.name.lower() for name in FORBIDDEN):
            raise ValueError('Unexpected bundled codec library: '+str(path))

def validate_image_only_opencv(root,build_information,*,has_video_capture):
    if has_video_capture or re.search(r'(FFMPEG|GStreamer)\s*:\s*YES',build_information,re.I):
        raise ValueError('OpenCV video decoding must be disabled')
    verify_no_extra_codecs(root)

if __name__=='__main__':
    import sys
    verify_no_extra_codecs(sys.argv[1])
