from dataclasses import FrozenInstanceError
from fractions import Fraction
from pathlib import Path
import math
import uuid

import pytest

from slide_core.models import (
    AnalysisRequest, DetectedSegment, DisplayTransform, ExportSnapshot, Page,
    Project, Rect, Sample, SlideImage, SourceRef, Transition, make_export_snapshot,
)


def source():
    return SourceRef(Path('/tmp/video.mp4'), 10, 20, 1, 1920, 1080,
                     DisplayTransform(1920, 1080))


def fixture_project():
    samples = (Sample('s000000', 0, 0, Fraction(1), Fraction(0), '0.jpg', 10, 10),
               Sample('s000001', 1, 10, Fraction(1, 10), Fraction(1), '1.jpg', 10, 10))
    segments = (DetectedSegment('g000000', Fraction(0), Fraction(2),
                                's000000', 's000001', 's000001'),)
    page = Page(str(uuid.uuid4()), 's000001', 'auto', 'g000000', None, 'create')
    return Project(source(), samples=samples, segments=segments, pages=[page])


def test_export_snapshot_copies_nested_collections_and_is_frozen():
    project = fixture_project()
    mutable_setting = {'nested': [1, 2]}
    project.settings = mutable_setting
    snapshot = make_export_snapshot(project)
    original_id = snapshot.pages[0].page_id
    project.pages.clear()
    assert snapshot.pages[0].page_id == original_id
    assert isinstance(snapshot.pages, tuple)
    mutable_setting['nested'].append(3)
    assert snapshot.settings == (("nested", (1, 2)),)
    with pytest.raises((FrozenInstanceError, AttributeError)):
        snapshot.pages[0].sample_id = 's000000'


def test_rejects_duplicate_ids_unknown_references_and_bad_geometry():
    with pytest.raises(ValueError):
        Rect(0, 0, 0, 2)
    project = fixture_project()
    with pytest.raises(ValueError):
        Project(source(), samples=project.samples + (project.samples[0],),
                segments=project.segments, pages=[])
    with pytest.raises(ValueError):
        Project(source(), samples=project.samples, segments=project.segments,
                pages=[Page(str(uuid.uuid4()), 'missing', 'auto', None, None, 'create')])


def test_rejects_non_finite_or_non_monotonic_sample_times():
    with pytest.raises(ValueError):
        Sample('s000000', 0, 0, Fraction(1), math.nan, 'x.jpg', 10, 10)
    with pytest.raises(ValueError):
        Sample('s000001', 1, 1, Fraction(0), Fraction(0), 'x.jpg', 10, 10)


def test_sample_keeps_integer_pts_and_subtracts_source_origin():
    sample = Sample('s000000', 0, 90000, Fraction(1, 90000), Fraction(0),
                    'x.jpg', 10, 10, pts_origin=90000)
    assert sample.source_pts == 90000
    assert sample.actual_time == 0


def test_analysis_settings_and_snapshot_generation_are_independent():
    project = fixture_project()
    snap = make_export_snapshot(project)
    assert snap.cache_generation != snap.analysis_generation
    assert isinstance(AnalysisRequest, type)
    assert isinstance(ExportSnapshot, type)
    assert SlideImage(Path('/tmp/x.png'), Fraction(0)).timestamp == Fraction(0)


def test_pts_are_signed_integers_and_actual_time_is_nonnegative():
    for pts in (-1, 1.5, math.nan, math.inf):
        with pytest.raises(ValueError):
            Sample('s', 0, pts, Fraction(1), Fraction(0), 'x', 1, 1)
    with pytest.raises(ValueError):
        Sample('s', 0, 1, Fraction(1), Fraction(0), 'x', 1, 1, pts_origin=math.nan)
    sample = Sample('s', 0, -2, Fraction(1, 2), Fraction(0), 'x', 1, 1, pts_origin=-4)
    assert sample.actual_time == 1
    with pytest.raises(ValueError):
        Sample('s', 0, -4, Fraction(1), Fraction(0), 'x', 1, 1, pts_origin=-2)


def test_settings_are_deeply_frozen_and_direct_snapshot_copies_collections():
    from types import SimpleNamespace
    project = fixture_project()
    mutable = {'masks': [1, 2]}
    project.settings = mutable
    snapshot = make_export_snapshot(project)
    mutable['masks'].append(3)
    assert snapshot.settings == (('masks', (1, 2)),)
    request = AnalysisRequest(source(), {'masks': [1, 2]})
    assert request.settings == (('masks', (1, 2)),)
    from slide_core.config import AnalysisSettings
    assert AnalysisRequest(source(), AnalysisSettings()).settings.fps == 1.0
    with pytest.raises(ValueError):
        AnalysisRequest(source(), SimpleNamespace(masks=[1, 2]))
    valid_project = fixture_project()
    direct = ExportSnapshot(valid_project.source, {'masks': [1]}, valid_project.samples,
                            (), valid_project.segments, valid_project.pages,
                            0, str(uuid.uuid4()), valid_project.cache_generation,
                            valid_project.analysis_generation)
    valid_project.pages.clear()
    assert direct.pages and isinstance(direct.pages, tuple)


def test_detection_records_must_be_time_ordered():
    project = fixture_project()
    transitions = (Transition('b2', 's000000', 's000001', Fraction(1), Fraction(2), Fraction(1), 'confirmed', 1),
                   Transition('b1', 's000000', 's000001', Fraction(0), Fraction(1), Fraction(0), 'confirmed', 1))
    with pytest.raises(ValueError):
        Project(source(), samples=project.samples, transitions=transitions)
    segments = (DetectedSegment('g2', Fraction(1), Fraction(2), 's000000', 's000001', 's000001'),
                DetectedSegment('g1', Fraction(0), Fraction(1), 's000000', 's000001', 's000001'))
    with pytest.raises(ValueError):
        Project(source(), samples=project.samples, segments=segments)


def test_display_dimensions_are_positive_integers_and_zero_is_not_defaulted():
    for kwargs in ({'coded_width': 1.5}, {'coded_height': math.nan}, {'display_width': 0}):
        args = {'coded_width': 10, 'coded_height': 10}
        args.update(kwargs)
        with pytest.raises(ValueError):
            DisplayTransform(**args)


def test_frozen_settings_dataclasses_keep_their_public_types_and_attributes():
    from slide_core.config import AnalysisSettings, DetectorConfig
    settings = AnalysisSettings(masks=(Rect(0, 0, 2, 2),), detector=DetectorConfig())
    request = AnalysisRequest(source(), settings)
    snapshot = make_export_snapshot(Project(source(), settings=settings))
    assert isinstance(request.settings, AnalysisSettings)
    assert isinstance(request.settings.detector, DetectorConfig)
    assert request.settings.fps == 1.0
    assert snapshot.settings.masks[0].width == 2


@pytest.mark.parametrize('field,value', [('width', math.nan), ('height', 1.5)])
def test_source_and_sample_dimensions_must_be_positive_integers(field, value):
    args = dict(path=Path('/tmp/v.mp4'), size_bytes=1, mtime_ns=1, stream_index=0,
                width=10, height=10, transform=DisplayTransform(10, 10))
    args[field] = value
    with pytest.raises(ValueError):
        SourceRef(**args)
    sample_args = dict(sample_id='s', grid_index=0, source_pts=0, time_base=Fraction(1),
                       nominal_time=Fraction(0), cache_path='x', width=10, height=10)
    sample_args[field] = value
    with pytest.raises(ValueError):
        Sample(**sample_args)


def test_snapshot_constructor_runs_project_reference_and_order_validation():
    project = fixture_project()
    args = (project.source, None, project.samples, (), project.segments,
            project.pages, 0, str(uuid.uuid4()), project.cache_generation,
            project.analysis_generation)
    with pytest.raises(ValueError):
        ExportSnapshot(*args[:5], (project.pages[0], project.pages[0]), *args[6:])
    unknown = Page(str(uuid.uuid4()), 'missing', 'auto', None, None, 'create')
    with pytest.raises(ValueError):
        ExportSnapshot(*args[:5], (unknown,), *args[6:])
    reversed_pages = (project.pages[0], Page(str(uuid.uuid4()), 's000000', 'manual', None, None, 'create'))
    with pytest.raises(ValueError):
        ExportSnapshot(*args[:5], reversed_pages, *args[6:])


def test_transition_observed_and_sample_times_must_be_ordered():
    project = fixture_project()
    invalid = (Transition('b1', 's000000', 's000001', Fraction(0), Fraction(3), Fraction(3), 'confirmed', 1),
               Transition('b2', 's000000', 's000001', Fraction(1), Fraction(2), Fraction(2), 'confirmed', 1))
    with pytest.raises(ValueError):
        Project(source(), samples=project.samples, transitions=invalid)
