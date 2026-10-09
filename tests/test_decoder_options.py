from pathlib import Path
import pytest
from slide_core import pts
from slide_core.analysis import analyze_project
from slide_core.config import AnalysisSettings
from slide_core.profiling import AnalysisProfile
from tests.test_sampling import make_video

def test_videotoolbox_is_explicit_and_requires_hardware_frames(tmp_path):
    source=make_video(tmp_path/'video.mp4',duration=2,fps=4)
    cmd=pts._ffmpeg(source,'showinfo',decode_options={'backend':'videotoolbox'})
    assert cmd[cmd.index('-hwaccel')+1]=='videotoolbox'
    assert cmd[cmd.index('-hwaccel_output_format')+1]=='videotoolbox_vld'
    assert cmd.index('-hwaccel')<cmd.index('-i')
    assert cmd[cmd.index('-vf')+1].startswith('hwdownload,format=nv12,')

def test_cpu_thread_option_keeps_exact_pts_and_pages(tmp_path):
    source=make_video(tmp_path/'video.mp4',duration=4,fps=4)
    p=AnalysisProfile()
    a,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache1')
    b,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache2',profile=p,decode_options={'backend':'cpu','threads':2})
    assert [s.source_pts for s in a.samples]==[s.source_pts for s in b.samples]
    def times(project):
        lookup={s.sample_id:s.source_pts for s in project.samples}
        return [lookup[x.representative_sample_id] for x in project.pages]
    assert times(a)==times(b)
    import importlib.util
    spec=importlib.util.spec_from_file_location('benchmark',Path(__file__).resolve().parents[1]/'scripts/benchmark-analysis.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    comparison=module.compare(a,b)
    assert comparison['segments_equal']
    assert comparison['pixel_comparison']=='completed'
    assert comparison['jpeg_rgb_max_absolute_difference']==0
    assert p.report()['decoder_backend']=='cpu'
    assert p.report()['decoder_threads']==2

def test_invalid_decoder_option_is_rejected(tmp_path):
    source=make_video(tmp_path/'video.mp4',duration=1,fps=4)
    with pytest.raises(ValueError):pts._ffmpeg(source,'null',decode_options={'backend':'automatic-magic'})

def test_hardware_selection_precedes_download_but_retains_all_frame_audit(tmp_path):
    source=make_video(tmp_path/'video.mp4',duration=1,fps=4)
    vf="showinfo@audit,select='gt(pts,0)',showinfo@sample,scale=320:180"
    cmd=pts._ffmpeg(source,vf,decode_options={'backend':'videotoolbox-select'})
    filters=cmd[cmd.index('-vf')+1]
    assert filters.startswith("showinfo@audit=checksum=0,select='gt(pts,0)',hwdownload,format=nv12,showinfo@sample")
    assert cmd[cmd.index('-hwaccel_output_format')+1]=='videotoolbox_vld'

def test_metadata_only_cpu_preserves_full_analysis_output(tmp_path):
    source=make_video(tmp_path/'video.mp4',duration=4,fps=4)
    a,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache1')
    b,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache2',decode_options={'backend':'cpu-metadata'})
    import importlib.util
    spec=importlib.util.spec_from_file_location('benchmark',Path(__file__).resolve().parents[1]/'scripts/benchmark-analysis.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    result=module.compare(a,b)
    assert all(result[k] for k in ('sample_pts_equal','page_pts_equal','segments_equal'))
    assert result['jpeg_rgb_max_absolute_difference']==0

def test_default_analysis_uses_metadata_cpu_and_matches_explicit_baseline(tmp_path):
    source=make_video(tmp_path/'video.mkv',duration=4,fps=4,offset=8,bframes=2)
    profile=AnalysisProfile()
    baseline,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'baseline',decode_options={'backend':'cpu'})
    default,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'default',profile=profile)
    assert profile.report()['decoder_backend']=='cpu-metadata'
    assert profile.report()['decoder_threads']==0
    import importlib.util
    spec=importlib.util.spec_from_file_location('benchmark',Path(__file__).resolve().parents[1]/'scripts/benchmark-analysis.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    result=module.compare(baseline,default)
    assert all(result[k] for k in ('sample_pts_equal','page_pts_equal','segments_equal'))
    assert result['jpeg_rgb_max_absolute_difference']==0
