"""Regression coverage for T002 record validation at each public boundary."""
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
import math
import uuid

import pytest

from slide_core.models import (
    AnalysisRequest, AnalysisResult, DetectedSegment, DisplayTransform,
    ExportSnapshot, Project, Sample, SourceRef, Transition, make_export_snapshot,
)


BUILDERS = ('project', 'factory', 'direct', 'result')
INVALID_COUNTS = (math.nan, math.inf, -math.inf, -1, 1.5, 1.0,
                  True, Fraction(1), '1', None)


def source():
    return SourceRef(Path('/tmp/t002-contract-synthetic.mp4'), 10, 20, 0,
                     16, 16, DisplayTransform(16, 16))


def samples():
    # Actual times 0, 1, 2, 3; nominal times deliberately differ.
    return tuple(Sample(f's{i}', i, -90 + 30 * i, Fraction(1, 30),
                        Fraction(2 * i), f'{i}.jpg', 16, 16, pts_origin=-90)
                 for i in range(4))


def transition():
    return Transition('b1', 's1', 's2', 1, 2, 2, 'confirmed', 2)


def segment():
    return DetectedSegment('g1', 0, 4, 's0', 's3', 's1', 'b1')


def build(builder, *, samples=(), transitions=(), segments=(), revision=0):
    if builder == 'request':
        return AnalysisRequest(source(), None, samples)
    if builder == 'result':
        return AnalysisResult(samples, transitions, segments)
    if builder == 'project':
        return Project(source(), samples=samples, transitions=transitions,
                       segments=segments, revision=revision)
    if builder == 'factory':
        # Validate edited state, without letting Project construction mask bugs.
        project = Project(source(), revision=7)
        project.samples, project.transitions, project.segments = samples, transitions, segments
        project.revision = revision
        return make_export_snapshot(project)
    return ExportSnapshot(source(), None, samples, transitions, segments, (),
                          revision, str(uuid.uuid4()), 'cache', 'analysis')


@pytest.mark.parametrize('builder', (*BUILDERS, 'request'))
@pytest.mark.parametrize('defect', ('duplicate', 'reversed', 'equal_actual'))
def test_sample_ids_and_actual_times_validated_at_every_boundary(builder, defect):
    ss = samples()
    bad = {'duplicate': (ss[0], ss[0]),
           'reversed': tuple(reversed(ss)),
           'equal_actual': (ss[0], replace(ss[1], source_pts=-90))}[defect]
    with pytest.raises(ValueError):
        build(builder, samples=bad)


@pytest.mark.parametrize('builder', BUILDERS)
@pytest.mark.parametrize('changes', (
    {'left_sample_id': 'missing'}, {'right_sample_id': 'missing'},
    {'lower_time': 0}, {'lower_time': Fraction(3, 2)},
    {'upper_time': 3}, {'observed_time': Fraction(3, 2)},
    {'left_sample_id': 's2', 'lower_time': 2},
))
def test_transition_bounds_match_referenced_actual_times(builder, changes):
    bad = replace(transition(), **changes)
    with pytest.raises(ValueError):
        build(builder, samples=samples(), transitions=(bad,))


@pytest.mark.parametrize('builder', BUILDERS)
@pytest.mark.parametrize('side', ('left', 'right'))
def test_transition_references_cannot_regress_despite_increasing_stored_times(builder, side):
    first = Transition('b1', 's1', 's2', 1, 2, 2, 'confirmed', 2)
    second = Transition('b2', 's2', 's3', 2, 3, 3, 'confirmed', 2)
    if side == 'left':
        second = replace(second, left_sample_id='s0')
    else:
        first = replace(first, right_sample_id='s3')
        second = replace(second, right_sample_id='s2')
    with pytest.raises(ValueError):
        build(builder, samples=samples(), transitions=(first, second))


@pytest.mark.parametrize('builder', BUILDERS)
@pytest.mark.parametrize('changes', (
    {'first_sample_id': 'missing'}, {'last_sample_id': 'missing'},
    {'representative_sample_id': 'missing'}, {'start_boundary_id': 'missing'},
    {'first_sample_id': 's3', 'last_sample_id': 's0'},
    {'first_sample_id': 's2'},
    {'last_sample_id': 's0'},
))
def test_segment_references_and_representative_order(builder, changes):
    with pytest.raises(ValueError):
        build(builder, samples=samples(), transitions=(transition(),),
              segments=(replace(segment(), **changes),))


@pytest.mark.parametrize('builder', BUILDERS)
@pytest.mark.parametrize('kind', ('transition', 'segment'))
def test_detection_ids_are_unique(builder, kind):
    ts, gs = (transition(),), (segment(),)
    if kind == 'transition':
        ts *= 2
    else:
        gs *= 2
    with pytest.raises(ValueError):
        build(builder, samples=samples(), transitions=ts, segments=gs)


@pytest.mark.parametrize('builder', BUILDERS)
@pytest.mark.parametrize('kind', ('transition', 'segment'))
def test_detection_records_are_chronological(builder, kind):
    ts, gs = (transition(),), (segment(),)
    if kind == 'transition':
        ts = (Transition('b2', 's2', 's3', 2, 3, 3, 'confirmed', 2), ts[0])
    else:
        gs = (replace(gs[0], segment_id='g2', start_time=1), gs[0])
    with pytest.raises(ValueError):
        build(builder, samples=samples(), transitions=ts, segments=gs)


@pytest.mark.parametrize('builder', ('project', 'factory', 'direct'))
@pytest.mark.parametrize('value', INVALID_COUNTS)
def test_revision_requires_nonnegative_integer_at_every_boundary(builder, value):
    with pytest.raises(ValueError):
        build(builder, revision=value)


@pytest.mark.parametrize('value', INVALID_COUNTS)
def test_persistence_requires_nonnegative_integer(value):
    with pytest.raises(ValueError):
        replace(transition(), persistence_samples=value)


@pytest.mark.parametrize('builder', BUILDERS)
def test_consistent_actual_time_records_and_integer_edges_are_accepted(builder):
    for count in (0, 10**400):
        ts = (replace(transition(), persistence_samples=count),)
        record = build(builder, samples=samples(), transitions=ts,
                       segments=(segment(),), revision=count)
        assert record.samples[1].actual_time == Fraction(1)
        assert record.transitions[0].observed_time == Fraction(2)
        assert record.transitions[0].persistence_samples == count
        if builder != 'result':
            assert record.revision == count


def test_analysis_collections_detach_after_validation_and_keep_generations():
    ss, ts, gs = list(samples()), [transition()], [segment()]
    request = AnalysisRequest(source(), None, iter(ss), 'cache-id')
    result = AnalysisResult(iter(ss), iter(ts), iter(gs), 'analysis-id')
    ss.clear()
    ts.clear()
    gs.clear()
    assert len(request.samples) == len(result.samples) == 4
    assert request.cache_generation == 'cache-id'
    assert result.analysis_generation == 'analysis-id'
    assert result.transitions[0].transition_id == 'b1'
    assert result.segments[0].start_boundary_id == 'b1'


def test_rejected_edited_project_preserves_revision_and_prior_snapshot():
    project = Project(source(), samples=samples(), transitions=(transition(),), revision=7)
    snapshot = make_export_snapshot(project)
    project.transitions = (replace(transition(), observed_time=1),)
    with pytest.raises(ValueError):
        make_export_snapshot(project)
    assert project.revision == snapshot.revision == 7
    assert snapshot.transitions[0].observed_time == 2
