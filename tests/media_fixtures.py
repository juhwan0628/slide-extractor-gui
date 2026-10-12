from fractions import Fraction
from pathlib import Path
import subprocess
import shutil
import pytest
from PIL import Image
from slide_core.media import probe_source, MediaError

def make_video(path,duration=4,fps=4,offset=0,bframes=0):
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi',
         '-i',f'testsrc2=size=96x64:rate={fps}:duration={duration}',
         '-vf',f'setpts=PTS+({offset})/TB' if offset else 'null',
         '-c:v','mpeg4','-g',str(int(fps)),'-bf',str(bframes),'-q:v','2',str(path)]
    subprocess.run(cmd,check=True,timeout=25)
    return probe_source(path)

def make_scene_video(path):
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y']
    for color in ('red','green','blue'):
        cmd+=['-f','lavfi','-i',f'color={color}:size=320x180:rate=4:duration=2']
    cmd+=['-filter_complex','[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]','-map','[v]',
          '-c:v','mpeg4','-g','2','-q:v','2',str(path)]
    subprocess.run(cmd,check=True,timeout=25)
    return path
