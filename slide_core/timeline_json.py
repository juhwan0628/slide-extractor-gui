"""Strict, Qt-free validation and JSON encoding for timeline v3 payloads."""
from __future__ import annotations

from datetime import datetime
from fractions import Fraction
import hashlib
import json
import math
import re
import uuid


class InvalidTimeline(ValueError):
    """A v3 payload violates its structural or cross-reference contract."""


_SAMPLE = re.compile(r"s[0-9]{6,}\Z")
_SEGMENT = re.compile(r"g[0-9]{6,}\Z")
_BOUNDARY = re.compile(r"b[0-9]{6,}\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_RFC3339 = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)\Z", re.IGNORECASE)
_FIELDS = {
    "source": {"basename","size_bytes","mtime_ns","chunk_sha256","stream_index","codec","coded_width","coded_height","sar_num","sar_den","rotation_cw","display_width","display_height","time_base_num","time_base_den","origin_pts","time_origin"},
    "sampling": {"algorithm","fps","cache_max_width","jpeg_quality"},
    "detector": {"algorithm","image_max_width","debounce_samples","global_mad","tile_mad","pixel_delta","changed_fraction","tile_size","tile_stride","min_tile_valid_fraction","mask_dilation_px","keep_unconfirmed"},
    "sample": {"sample_id","grid_index","nominal_timestamp_s","source_pts","timestamp_s","cache_width","cache_height"},
    "metrics": {"global_mad","max_tile_mad","changed_fraction"},
    "boundary": {"boundary_id","left_sample_id","right_sample_id","lower_s","upper_s","observed_at_s","true_boundary_s","uncertainty_kind","status","persistence_samples","adjacent_metrics","anchor_metrics"},
    "segment": {"segment_id","start_s","end_s","first_sample_id","last_sample_id","auto_representative_sample_id","start_boundary_id"},
    "page": {"page_id","pdf_page","representative_sample_id","representative_timestamp_s","origin","origin_segment_id","derived_segment_id","last_edit"},
    "navigation": {"page_id","start_s","end_s","basis","is_slide_boundary"},
    "artifact": {"export_id","project_revision","created_at","generator_version","pdf_basename","pdf_page_count","pdf_sha256"},
}


def _obj(value, fields, name):
    if not isinstance(value, dict) or set(value) != fields:
        raise InvalidTimeline(f"{name}: required fields mismatch")


def _finite_tree(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise InvalidTimeline("numbers must be finite")
    if isinstance(value, dict):
        for x in value.values(): _finite_tree(x)
    elif isinstance(value, list):
        for x in value: _finite_tree(x)


def _rect(rect, width, height):
    _obj(rect, {"x","y","width","height"}, "rect")
    if any(type(rect[k]) is not int for k in rect) or min(rect["width"], rect["height"]) < 1 or min(rect["x"], rect["y"]) < 0 or rect["x"]+rect["width"] > width or rect["y"]+rect["height"] > height:
        raise InvalidTimeline("rectangle outside display bounds")


def _types(value, path=()):
    """Enforce JSON Schema primitive/container types (not Python coercions)."""
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str): raise InvalidTimeline("object keys must be strings")
            _types(v, path + (k,))
    elif isinstance(value, list):
        for v in value: _types(v, path)
    elif isinstance(value, bool) or value is None or isinstance(value, str):
        pass
    elif type(value) not in (int, float):
        raise InvalidTimeline("unsupported JSON value")


_STRING_FIELDS = {"basename","chunk_sha256","codec","time_origin","algorithm","sample_id","boundary_id","left_sample_id","right_sample_id","segment_id","page_id","representative_sample_id","derived_segment_id","origin","last_edit","basis","export_id","created_at","generator_version","pdf_basename","pdf_sha256"}
_BOOL_FIELDS = {"keep_unconfirmed","is_slide_boundary"}
_INT_FIELDS = {"size_bytes","mtime_ns","stream_index","coded_width","coded_height","sar_num","sar_den","rotation_cw","display_width","display_height","time_base_num","time_base_den","origin_pts","cache_max_width","jpeg_quality","image_max_width","debounce_samples","pixel_delta","tile_size","tile_stride","mask_dilation_px","grid_index","source_pts","cache_width","cache_height","persistence_samples","pdf_page","project_revision","pdf_page_count","x","y","width","height"}
_NUM_FIELDS = {"duration_s","fps","global_mad","tile_mad","changed_fraction","min_tile_valid_fraction","nominal_timestamp_s","timestamp_s","max_tile_mad","lower_s","upper_s","observed_at_s","start_s","end_s","representative_timestamp_s"}
_NULLABLE_STRING_FIELDS = {"origin_segment_id","start_boundary_id"}


def _schema_fields(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in _STRING_FIELDS and not isinstance(item, str): raise InvalidTimeline(f"{key} must be a string")
            if key in _NULLABLE_STRING_FIELDS and item is not None and not isinstance(item, str): raise InvalidTimeline(f"{key} must be a string or null")
            if key in _BOOL_FIELDS and type(item) is not bool: raise InvalidTimeline(f"{key} must be boolean")
            if key in _INT_FIELDS and type(item) is not int: raise InvalidTimeline(f"{key} must be integer")
            if key in _NUM_FIELDS and type(item) not in (int, float): raise InvalidTimeline(f"{key} must be a number")
            _schema_fields(item)
    elif isinstance(value, list):
        for item in value: _schema_fields(item)


def _uuid(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", value):
        raise InvalidTimeline("invalid UUID")
    uuid.UUID(value)


def _validate_information(roi, masks, source, cache):
    """Mirror §7.3 detector crop scaling and reject less than 64x36 valid pixels."""
    cw, ch = cache
    sx, sy = cw / source["display_width"], ch / source["display_height"]
    left, top = max(0, math.floor(roi["x"] * sx)), max(0, math.floor(roi["y"] * sy))
    right = min(cw, math.ceil((roi["x"] + roi["width"]) * sx))
    bottom = min(ch, math.ceil((roi["y"] + roi["height"]) * sy))
    rw, rh = right-left, bottom-top
    dw = min(320, rw)
    dh = max(1, round(rh * dw / rw))
    if dw < 64 or dh < 36: raise InvalidTimeline("detector crop must be at least 64x36")
    # Transform mask intersections to detector pixels, then apply the specified one-pixel dilation.
    valid = bytearray([1]) * (dw * dh)
    for mask in masks:
        ml=max(left, 0, math.floor(mask["x"]*sx)); mt=max(top, 0, math.floor(mask["y"]*sy))
        mr=min(right, cw, math.ceil((mask["x"]+mask["width"])*sx)); mb=min(bottom, ch, math.ceil((mask["y"]+mask["height"])*sy))
        if ml >= mr or mt >= mb: continue
        x0=max(0,math.floor((ml-left)*dw/rw)); y0=max(0,math.floor((mt-top)*dh/rh))
        x1=min(dw,math.ceil((mr-left)*dw/rw)); y1=min(dh,math.ceil((mb-top)*dh/rh))
        for y in range(max(0,y0-1),min(dh,y1+1)):
            a=y*dw
            for x in range(max(0,x0-1),min(dw,x1+1)): valid[a+x]=0
    if sum(valid) < max(64, math.ceil(.05 * dw * dh)): raise InvalidTimeline("insufficient valid detector pixels")


def validate(payload, *, pdf_bytes=None, pdf_page_count=None, pdf_export_id=None):
    """Validate and return a v3 payload; optional PDF facts verify artifact identity."""
    try:
        _types(payload); _schema_fields(payload)
        _finite_tree(payload)
        top={"schema_version","source","duration_s","duration_kind","sampling","roi","ignore_masks","detector","samples","detected_boundaries","detected_segments","pages","navigation_ranges","artifact"}
        _obj(payload,top,"payload")
        if type(payload["schema_version"]) is not int or payload["schema_version"] != 3: raise InvalidTimeline("schema_version must be 3")
        for key in ("samples","detected_boundaries","detected_segments","pages","navigation_ranges"):
            if not isinstance(payload[key],list): raise InvalidTimeline(f"{key} must be an array")
        s=payload["source"]; _obj(s,_FIELDS["source"],"source")
        if not isinstance(s["basename"],str) or not s["basename"] or "/" in s["basename"] or "\\" in s["basename"]: raise InvalidTimeline("source basename must be a basename")
        if not s["codec"] or "/" in s["codec"] or "\\" in s["codec"]: raise InvalidTimeline("invalid codec")
        if type(s["chunk_sha256"]) is not str or not _HASH.fullmatch(s["chunk_sha256"]): raise InvalidTimeline("invalid source hash")
        for k in ("size_bytes","coded_width","coded_height","sar_num","sar_den","display_width","display_height","time_base_num","time_base_den"):
            if type(s[k]) is not int or s[k] <= 0: raise InvalidTimeline(f"invalid source {k}")
        if type(s["mtime_ns"]) is not int or type(s["stream_index"]) is not int or s["stream_index"]<0 or type(s["origin_pts"]) is not int or s["rotation_cw"] not in (0,90,180,270) or not s["codec"] or s["time_origin"] != "first_display_frame": raise InvalidTimeline("invalid source metadata")
        dw=Fraction(s["coded_width"]*s["sar_num"],s["sar_den"]); dh=Fraction(s["coded_height"])
        if s["rotation_cw"] in (90,270): dw,dh=dh,dw
        if (s["display_width"],s["display_height"]) != (round(dw),round(dh)): raise InvalidTimeline("display dimensions mismatch transform")
        duration=payload["duration_s"]
        if type(duration) not in (float,int) or duration<=0 or payload["duration_kind"] not in ("video_metadata","container_estimate"): raise InvalidTimeline("invalid duration")
        _obj(payload["sampling"],_FIELDS["sampling"],"sampling"); sm=payload["sampling"]
        if sm != {"algorithm":"bucket-first-v1","fps":sm["fps"],"cache_max_width":640,"jpeg_quality":90} or sm["fps"] not in (1.0,.5): raise InvalidTimeline("invalid sampling settings")
        _obj(payload["detector"],_FIELDS["detector"],"detector")
        detector=payload["detector"]
        expected_detector={"algorithm":"masked-anchor-tile-v1","image_max_width":320,"debounce_samples":2,
            "global_mad":.005,"tile_mad":.025,"pixel_delta":20,"changed_fraction":.0002,"tile_size":20,
            "tile_stride":10,"min_tile_valid_fraction":.5,"mask_dilation_px":1,"keep_unconfirmed":True}
        if detector != expected_detector: raise InvalidTimeline("unsupported detector settings")
        _rect(payload["roi"],s["display_width"],s["display_height"])
        if not isinstance(payload["ignore_masks"],list) or len(payload["ignore_masks"])>1: raise InvalidTimeline("at most one ignore mask")
        for r in payload["ignore_masks"]: _rect(r,s["display_width"],s["display_height"])
        samples=payload["samples"]
        if not samples: raise InvalidTimeline("samples required")
        sample_map={}; prev_pts=prev_t=prev_grid=None; dims=None
        for x in samples:
            _obj(x,_FIELDS["sample"],"sample")
            if not isinstance(x["sample_id"],str) or not _SAMPLE.fullmatch(x["sample_id"]) or x["sample_id"] in sample_map: raise InvalidTimeline("invalid or duplicate sample id")
            if any(type(x[k]) is not int for k in ("grid_index","source_pts","cache_width","cache_height")) or x["grid_index"]<0 or not 1<=x["cache_width"]<=640 or x["cache_height"]<1: raise InvalidTimeline("invalid sample fields")
            t=x["timestamp_s"]; nominal=x["nominal_timestamp_s"]
            if any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in (t,nominal)): raise InvalidTimeline("invalid sample time")
            expected=(x["source_pts"]-s["origin_pts"])*s["time_base_num"]/s["time_base_den"]
            tol=max(1e-9,.5*s["time_base_num"]/s["time_base_den"])
            elapsed=Fraction((x["source_pts"]-s["origin_pts"])*s["time_base_num"],s["time_base_den"])
            fps=Fraction(str(sm["fps"]))
            bucket=(elapsed*fps).__floor__()
            if bucket!=x["grid_index"] or abs(t-expected)>tol or abs(nominal-x["grid_index"]/sm["fps"])>1e-9 or not nominal<=t<nominal+1/sm["fps"]: raise InvalidTimeline("sample PTS or bucket mismatch")
            if prev_pts is None and (x["grid_index"]!=0 or x["source_pts"]!=s["origin_pts"] or t!=0): raise InvalidTimeline("first sample must be origin")
            if prev_pts is not None and (x["source_pts"]<=prev_pts or t<=prev_t or x["grid_index"]<=prev_grid): raise InvalidTimeline("samples must increase")
            if t>=duration: raise InvalidTimeline("sample must precede duration")
            thisdims=(x["cache_width"],x["cache_height"])
            if dims is not None and dims!=thisdims: raise InvalidTimeline("cache dimensions changed")
            dims=thisdims; sample_map[x["sample_id"]]=x; prev_pts=x["source_pts"]; prev_t=t; prev_grid=x["grid_index"]
        expected_w=min(640,s["display_width"])
        expected_h=max(1,round(s["display_height"]*expected_w/s["display_width"]))
        if dims != (expected_w,expected_h): raise InvalidTimeline("cache must preserve full display aspect without enlargement")
        _validate_information(payload["roi"],payload["ignore_masks"],s,dims)
        boundaries=payload["detected_boundaries"]; bmap={}; prev=-1
        for b in boundaries:
            _obj(b,_FIELDS["boundary"],"boundary")
            if not isinstance(b["boundary_id"],str) or not _BOUNDARY.fullmatch(b["boundary_id"]) or b["boundary_id"] in bmap: raise InvalidTimeline("invalid boundary id")
            for key in ("adjacent_metrics","anchor_metrics"):
                _obj(b[key],_FIELDS["metrics"],"metrics")
                if any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in b[key].values()): raise InvalidTimeline("invalid metric")
            left=sample_map.get(b["left_sample_id"]); right=sample_map.get(b["right_sample_id"])
            if not left or not right or b["lower_s"]!=left["timestamp_s"] or b["upper_s"]!=right["timestamp_s"] or b["observed_at_s"]!=right["timestamp_s"] or not b["lower_s"]<b["upper_s"]<duration or b["observed_at_s"]<=prev or b["true_boundary_s"] is not None or b["uncertainty_kind"]!="sampling_and_detector": raise InvalidTimeline("invalid boundary reference or interval")
            if b["status"] not in ("confirmed","eof_unconfirmed") or b["persistence_samples"] != (2 if b["status"]=="confirmed" else 1) or (b["status"]=="eof_unconfirmed" and right is not samples[-1]): raise InvalidTimeline("invalid boundary status")
            prev=b["observed_at_s"]; bmap[b["boundary_id"]]=b
        segments=payload["detected_segments"]
        if len(segments)!=len(boundaries)+1: raise InvalidTimeline("segment/boundary count mismatch")
        assigned=[]
        for i,g in enumerate(segments):
            _obj(g,_FIELDS["segment"],"segment")
            if not isinstance(g["segment_id"],str) or not _SEGMENT.fullmatch(g["segment_id"]) or g["segment_id"] in [z["segment_id"] for z in segments[:i]]: raise InvalidTimeline("invalid segment id")
            start=0 if i==0 else boundaries[i-1]["observed_at_s"]; end=duration if i==len(segments)-1 else boundaries[i]["observed_at_s"]
            if g["start_s"]!=start or g["end_s"]!=end or end<=start or g["start_boundary_id"]!=(None if i==0 else boundaries[i-1]["boundary_id"]): raise InvalidTimeline("invalid segment interval")
            selected=[x for x in samples if start<=x["timestamp_s"]<end]
            if not selected or g["first_sample_id"]!=selected[0]["sample_id"] or g["last_sample_id"]!=selected[-1]["sample_id"] or g["auto_representative_sample_id"] not in {x["sample_id"] for x in selected}: raise InvalidTimeline("invalid segment samples")
            assigned.extend(x["sample_id"] for x in selected)
        if sorted(assigned)!=sorted(sample_map): raise InvalidTimeline("each sample belongs to one segment")
        pages=payload["pages"]; nav=payload["navigation_ranges"]
        if not pages or len(nav)!=len(pages): raise InvalidTimeline("pages and navigation required")
        ids=set(); reps=set(); segmap={g["segment_id"]:g for g in segments}; page_ids=[]
        for i,p in enumerate(pages):
            _obj(p,_FIELDS["page"],"page"); n=nav[i]; _obj(n,_FIELDS["navigation"],"navigation")
            try: uuid.UUID(p["page_id"])
            except Exception as exc: raise InvalidTimeline("invalid page UUID") from exc
            if p["page_id"] in ids or type(p["pdf_page"]) is not int or p["pdf_page"]!=i+1 or p["representative_sample_id"] in reps: raise InvalidTimeline("duplicate page or representative")
            sample=sample_map.get(p["representative_sample_id"]); g=segmap.get(p["derived_segment_id"])
            if not sample or not g or p["representative_timestamp_s"]!=sample["timestamp_s"] or not g["start_s"]<=sample["timestamp_s"]<g["end_s"]: raise InvalidTimeline("invalid page sample")
            if p["origin"] not in ("auto","manual") or (p["origin"]=="manual") != (p["origin_segment_id"] is None) or (p["origin_segment_id"] is not None and p["origin_segment_id"] not in segmap) or p["last_edit"] not in ("auto","insert","replace") or (p["origin"]=="auto" and p["last_edit"]=="insert") or (p["origin"]=="manual" and p["last_edit"]=="auto"): raise InvalidTimeline("invalid page provenance")
            if page_ids and sample["timestamp_s"]<=sample_map[reps and pages[i-1]["representative_sample_id"]]["timestamp_s"]: raise InvalidTimeline("page times must increase")
            if n["page_id"]!=p["page_id"] or n["basis"]!="representative_order" or n["is_slide_boundary"] is not False: raise InvalidTimeline("navigation mismatch")
            start=0 if i==0 else sample["timestamp_s"]; end=(sample_map[pages[i+1]["representative_sample_id"]]["timestamp_s"] if i+1<len(pages) else duration)
            if n["start_s"]!=start or n["end_s"]!=end or end<=start: raise InvalidTimeline("invalid navigation range")
            ids.add(p["page_id"]); reps.add(p["representative_sample_id"]); page_ids.append(p["page_id"])
        a=payload["artifact"]; _obj(a,_FIELDS["artifact"],"artifact")
        try:
            _uuid(a["export_id"])
            if not isinstance(a["created_at"],str) or not _RFC3339.fullmatch(a["created_at"]): raise ValueError("not RFC3339")
            stamp=a["created_at"]
            if stamp[-1:] in ("Z","z"):
                stamp=stamp[:-1]+"+00:00"
            else:
                offset=stamp[-6:]
                if int(offset[1:3])>23 or int(offset[4:6])>59: raise ValueError("invalid UTC offset")
            datetime.fromisoformat(stamp.replace("t","T"))
        except Exception as exc: raise InvalidTimeline("invalid artifact UUID or date-time") from exc
        for p in pages: _uuid(p["page_id"])
        if type(a["project_revision"]) is not int or a["project_revision"]<0 or not a["generator_version"] or "/" in a["generator_version"] or "\\" in a["generator_version"] or len(a["pdf_basename"])<5 or "/" in a["pdf_basename"] or "\\" in a["pdf_basename"] or not a["pdf_basename"].endswith(".pdf") or a["pdf_page_count"]!=len(pages) or not _HASH.fullmatch(a["pdf_sha256"]): raise InvalidTimeline("invalid artifact metadata")
        if pdf_page_count is not None and pdf_page_count!=a["pdf_page_count"]: raise InvalidTimeline("PDF page count mismatch")
        if pdf_export_id is not None and pdf_export_id!=a["export_id"]: raise InvalidTimeline("PDF export UUID mismatch")
        if pdf_bytes is not None and hashlib.sha256(pdf_bytes).hexdigest()!=a["pdf_sha256"]: raise InvalidTimeline("PDF hash mismatch")
        return payload
    except (KeyError, TypeError, OverflowError, ZeroDivisionError) as exc:
        raise InvalidTimeline(f"malformed timeline: {exc}") from exc


def _rounded(value):
    if isinstance(value,float):
        result=round(value,9)
        return 0.0 if result==0 else result
    if isinstance(value,dict): return {k:_rounded(v) for k,v in value.items()}
    if isinstance(value,list): return [_rounded(v) for v in value]
    return value


def dumps(payload):
    """Validate, round serialized numbers to nine decimals, then revalidate."""
    validate(payload)
    value=_rounded(payload); validate(value)
    raw=json.dumps(value,ensure_ascii=False,allow_nan=False,indent=2)+"\n"
    loads(raw)
    return raw


def loads(raw, **pdf_facts):
    """Parse UTF-8 JSON text (or bytes) and validate its complete contract."""
    if isinstance(raw,bytes): raw=raw.decode("utf-8")
    try: value=json.loads(raw,parse_constant=lambda x: (_ for _ in ()).throw(InvalidTimeline(f"invalid number {x}")))
    except (json.JSONDecodeError,UnicodeDecodeError) as exc: raise InvalidTimeline(f"invalid JSON: {exc}") from exc
    return validate(value,**pdf_facts)
