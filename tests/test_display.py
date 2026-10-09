from fractions import Fraction
import subprocess
import shutil

import pytest

from slide_core.display import UnsupportedDisplayTransform, build_display_pipeline


@pytest.mark.parametrize('angle,dims',[(0,(120,80)),(90,(80,120)),(180,(120,80)),(270,(80,120))])
def test_rotation_and_sar_geometry(angle,dims):
    p=build_display_pipeline(width=90,height=80,sar=Fraction(4,3),rotation=angle)
    assert (p.transform.display_width,p.transform.display_height)==dims
    assert p.full_filter.endswith('format=rgb24')
    assert 'setsar=1' in p.full_filter
    assert p.cache_width<=640


def test_no_upscale_and_cache_aspect():
    small=build_display_pipeline(width=63,height=37,pixel_format='rgb24')
    assert (small.cache_width,small.cache_height)==(63,37)
    assert small.full_filter==small.cache_filter
    large=build_display_pipeline(width=1921,height=1081)
    assert large.cache_width==640
    assert large.cache_height==round(1081*640/1921)


@pytest.mark.parametrize('kwargs',[
    {'rotation':45}, {'transfer':'smpte2084'}, {'transfer':'arib-std-b67'},
    {'interlaced':True}, {'dynamic_dimensions':True},
    {'color_matrix':'bt2020nc'}, {'color_range':'unsupported'},
    {'sar':Fraction(0,1)},
])
def test_unsupported_display_policy(kwargs):
    with pytest.raises(UnsupportedDisplayTransform) as err:
        build_display_pipeline(width=120,height=80,**kwargs)
    assert err.value.code=='UnsupportedDisplayTransform'


def test_range_and_matrix_fallback():
    sd=build_display_pipeline(width=640,height=480)
    hd=build_display_pipeline(width=1280,height=720)
    assert 'bt601' in sd.full_filter and 'bt709' in hd.full_filter
    assert 'in_range=tv' in sd.full_filter
    assert 'assumed' in sd.color_warning
    explicit=build_display_pipeline(width=640,height=480,color_matrix='bt709',color_range='pc')
    assert 'in_color_matrix=bt709' in explicit.full_filter
    assert 'in_range=pc' in explicit.full_filter
    assert explicit.color_warning is None
    rgb=build_display_pipeline(width=640,height=480,pixel_format='rgb24')
    assert 'in_color_matrix' not in rgb.full_filter


@pytest.mark.skipif(shutil.which('ffmpeg') is None,reason='FFmpeg required')
@pytest.mark.parametrize('angle,expected',[(0,((255,0,0),(0,255,0))), (90,((0,0,255),(255,0,0))),
                                              (180,((255,255,0),(0,0,255))), (270,((0,255,0),(255,255,0)))])
def test_real_rotation_pixel_corners(angle,expected,tmp_path):
    from PIL import Image
    original=Image.new('RGB',(16,12))
    for y in range(12):
        for x in range(16):
            color=((255,0,0) if x<8 and y<6 else (0,255,0) if x>=8 and y<6
                   else (0,0,255) if x<8 else (255,255,0))
            original.putpixel((x,y),color)
    source=tmp_path/'quad.png';original.save(source)
    pipe=build_display_pipeline(width=16,height=12,rotation=angle,pixel_format='rgb24')
    result=tmp_path/'output.png'
    subprocess.run(['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-noautorotate',
                    '-i',str(source),'-vf',pipe.full_filter,'-frames:v','1','-y',str(result)],check=True)
    output=Image.open(result).convert('RGB')
    assert output.size==(pipe.transform.display_width,pipe.transform.display_height)
    assert output.getpixel((0,0))==expected[0]
    assert output.getpixel((output.width-1,0))==expected[1]
