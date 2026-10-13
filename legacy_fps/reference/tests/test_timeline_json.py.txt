import copy
import pytest

from slide_core.timeline_json import dumps, loads, validate


def payload():
    zero = "0" * 64
    samples = [dict(sample_id=f"s{i:06}", grid_index=i, nominal_timestamp_s=float(i), source_pts=i*10240,
                    timestamp_s=float(i), cache_width=160, cache_height=90) for i in range(4)]
    metrics = dict(global_mad=.4, max_tile_mad=.7, changed_fraction=.6)
    boundaries = [dict(boundary_id="b000001", left_sample_id="s000001", right_sample_id="s000002",
                       lower_s=1., upper_s=2., observed_at_s=2., true_boundary_s=None,
                       uncertainty_kind="sampling_and_detector", status="confirmed", persistence_samples=2,
                       adjacent_metrics=metrics, anchor_metrics=metrics)]
    segments = [dict(segment_id="g000000", start_s=0., end_s=2., first_sample_id="s000000", last_sample_id="s000001",
                     auto_representative_sample_id="s000001", start_boundary_id=None),
                dict(segment_id="g000001", start_s=2., end_s=4., first_sample_id="s000002", last_sample_id="s000003",
                     auto_representative_sample_id="s000003", start_boundary_id="b000001")]
    ids = ["11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222"]
    pages = [dict(page_id=ids[i], pdf_page=i+1, representative_sample_id=f"s{i*2+1:06}",
                  representative_timestamp_s=float(i*2+1), origin="auto", origin_segment_id=f"g{i:06}",
                  derived_segment_id=f"g{i:06}", last_edit="auto") for i in range(2)]
    return dict(schema_version=3, source=dict(basename="lecture.mp4", size_bytes=123456, mtime_ns=1,
         chunk_sha256=zero, stream_index=0, codec="h264", coded_width=160, coded_height=90,
         sar_num=1, sar_den=1, rotation_cw=0, display_width=160, display_height=90,
         time_base_num=1, time_base_den=10240, origin_pts=0, time_origin="first_display_frame"),
         duration_s=4., duration_kind="video_metadata",
         sampling=dict(algorithm="bucket-first-v1", fps=1., cache_max_width=640, jpeg_quality=90),
         roi=dict(x=0,y=0,width=160,height=90), ignore_masks=[],
         detector=dict(algorithm="masked-anchor-tile-v1", image_max_width=320, debounce_samples=2,
           global_mad=.005,tile_mad=.025,pixel_delta=20,changed_fraction=.0002,tile_size=20,tile_stride=10,
           min_tile_valid_fraction=.5,mask_dilation_px=1,keep_unconfirmed=True), samples=samples,
         detected_boundaries=boundaries, detected_segments=segments, pages=pages,
         navigation_ranges=[dict(page_id=ids[0],start_s=0.,end_s=3.,basis="representative_order",is_slide_boundary=False),
                            dict(page_id=ids[1],start_s=3.,end_s=4.,basis="representative_order",is_slide_boundary=False)],
         artifact=dict(export_id="33333333-3333-4333-8333-333333333333",project_revision=1,
           created_at="2026-10-08T00:00:00Z",generator_version="0.2.0",pdf_basename="lecture.slides.pdf",
           pdf_page_count=2,pdf_sha256=zero))


def test_roundtrip_validates_and_uses_utf8_newline():
    raw = dumps(payload())
    assert raw.endswith("\n") and "\\u" not in raw
    assert loads(raw) == payload()


def test_pdf_facts_are_cross_checked():
    import hashlib
    pdf = b"synthetic pdf bytes"
    value = payload()
    value["artifact"]["pdf_sha256"] = hashlib.sha256(pdf).hexdigest()
    assert loads(dumps(value), pdf_bytes=pdf, pdf_page_count=2,
                 pdf_export_id=value["artifact"]["export_id"])
    with pytest.raises(ValueError):
        loads(dumps(value), pdf_bytes=b"different bytes")


@pytest.mark.parametrize("mutate", [
    lambda p: p.update(extra=True),
    lambda p: p["source"].update(basename="/private/video.mp4"),
    lambda p: p["samples"].append(copy.deepcopy(p["samples"][0])),
    lambda p: p["detected_boundaries"][0].update(left_sample_id="s999999"),
    lambda p: p["detected_segments"][0].update(end_s=3.),
    lambda p: p["roi"].update(width=161),
    lambda p: p["artifact"].update(pdf_page_count=3),
    lambda p: p["artifact"].update(pdf_sha256="bad"),
    lambda p: p["samples"][1].update(timestamp_s=float("nan")),
])
def test_rejects_invalid_payload(mutate):
    value = payload(); mutate(value)
    with pytest.raises(ValueError):
        validate(value)


def test_rejects_bad_uuid_datetime_rounding_collision_and_unknown_nested_field():
    for path, key, val in [("artifact", "export_id", "nope"), ("artifact", "created_at", "yesterday")]:
        value=payload(); value[path][key]=val
        with pytest.raises(ValueError): validate(value)
    value=payload(); value["source"]["new"] = 1
    with pytest.raises(ValueError): validate(value)
    value=payload(); value["samples"][1]["timestamp_s"]=1.0000000004
    value["samples"][2]["timestamp_s"]=1.0000000003
    with pytest.raises(ValueError): dumps(value)


def test_first_late_representative_starts_navigation_at_zero_and_boundaries_survive_page_edit():
    value=payload(); before=copy.deepcopy(value["detected_boundaries"])
    value["pages"][0]["representative_sample_id"]="s000002"
    value["pages"][0]["representative_timestamp_s"]=2.
    value["pages"][0]["derived_segment_id"]="g000001"
    value["pages"][0]["origin"]="manual"; value["pages"][0]["origin_segment_id"]=None
    value["pages"][0]["last_edit"]="replace"
    value["pages"][1]["representative_sample_id"]="s000003"
    value["pages"][1]["representative_timestamp_s"]=3.
    value["navigation_ranges"][0]["end_s"]=3.
    value["navigation_ranges"][1]["start_s"]=3.
    validate(value)
    assert value["navigation_ranges"][0]["start_s"] == 0
    assert value["detected_boundaries"] == before


def test_auto_page_replace_preserves_creation_origin_and_boundary_track():
    value=payload(); before=copy.deepcopy(value["detected_boundaries"])
    p=value["pages"][0]
    p.update(representative_sample_id="s000002", representative_timestamp_s=2.,
             derived_segment_id="g000001", last_edit="replace")
    value["pages"][1].update(representative_sample_id="s000003",representative_timestamp_s=3.)
    value["navigation_ranges"][0]["end_s"]=3.
    value["navigation_ranges"][1]["start_s"]=3.
    validate(value)
    assert value["pages"][0]["origin"] == "auto"
    assert value["pages"][0]["origin_segment_id"] == "g000000"
    assert value["detected_boundaries"] == before


@pytest.mark.parametrize("path,key,value", [("roi","x",-1), ("roi","y",-1)])
def test_rectangles_reject_negative_coordinates(path,key,value):
    p=payload(); p[path][key]=value
    with pytest.raises(ValueError): validate(p)


def test_rejects_detector_crop_too_small_or_fully_masked():
    p=payload(); p["roi"]=dict(x=0,y=0,width=1,height=1)
    with pytest.raises(ValueError): validate(p)
    p=payload(); p["ignore_masks"]=[dict(x=0,y=0,width=160,height=90)]
    with pytest.raises(ValueError): validate(p)


@pytest.mark.parametrize("dims", [(160,1),(640,360)])
def test_cache_must_be_downscaled_full_display_aspect(dims):
    p=payload()
    for s in p["samples"]: s["cache_width"],s["cache_height"]=dims
    with pytest.raises(ValueError): validate(p)


@pytest.mark.parametrize("kind", ["codec","generator_version","ignore_masks","boundary_time","segment_time","page_time","navigation_time"])
def test_rejects_bad_schema_types_and_private_nested_paths(kind):
    p=payload()
    if kind=="codec": p["source"]["codec"]={"private_path":"/private/home/video.mp4"}
    elif kind=="generator_version": p["sampling"]["generator_version"]=["bad"]
    elif kind=="ignore_masks": p["ignore_masks"]={}
    elif kind=="boundary_time": p["detected_boundaries"][0]["observed_at_s"]=True
    elif kind=="segment_time": p["detected_segments"][0]["start_s"]=True
    elif kind=="page_time": p["pages"][0]["representative_timestamp_s"]=True
    else: p["navigation_ranges"][0]["start_s"]=True
    with pytest.raises(ValueError): validate(p)


def test_uuid_requires_canonical_format_and_rfc3339_accepts_offset():
    p=payload(); p["pages"][0]["page_id"]="11111111111141118111111111111111"
    with pytest.raises(ValueError): validate(p)
    p=payload(); p["artifact"]["created_at"]="2026-10-08T00:00:00-05:00"
    validate(p)
    p["artifact"]["created_at"]="2026-10-08Z"
    with pytest.raises(ValueError): validate(p)


def test_rejects_path_leaks_in_freeform_metadata():
    p=payload(); p["source"]["codec"]="/private/home/video.mp4"
    with pytest.raises(ValueError): validate(p)
    p=payload(); p["artifact"]["generator_version"]="/private/build/version"
    with pytest.raises(ValueError): validate(p)


def test_negative_value_is_rejected_before_rounding():
    p=payload(); p["detected_boundaries"][0]["adjacent_metrics"]["global_mad"]=-0.0000000004
    with pytest.raises(ValueError): dumps(p)


@pytest.mark.parametrize("stamp", [
    "2026-10-08T00:00:00+00:60",
    "2026-10-08T00:00:00+05:99",
    "2026-10-08T00:00:00-00:60",
])
def test_rejects_rfc3339_offsets_outside_clock_ranges(stamp):
    p=payload(); p["artifact"]["created_at"]=stamp
    with pytest.raises(ValueError): validate(p)


def test_rfc3339_accepts_lowercase_t_and_z():
    p=payload(); p["artifact"]["created_at"]="2026-10-08t00:00:00z"
    validate(p)


def test_sample_grid_is_derived_from_exact_source_pts_bucket():
    p=payload()
    p["samples"][2].update(grid_index=1, nominal_timestamp_s=1.,
                            source_pts=20480, timestamp_s=1.99999)
    with pytest.raises(ValueError): validate(p)


def test_roi_cache_scaling_clips_rounding_at_cache_edges():
    p=payload()
    p["source"].update(coded_width=1050, coded_height=117,
                       display_width=1050, display_height=117)
    p["roi"].update(width=1050, height=117)
    for sample in p["samples"]:
        sample.update(cache_width=640, cache_height=71)
    validate(p)
