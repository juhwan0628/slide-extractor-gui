"""Evidence required for a keyframe-only native release candidate."""
FORBIDDEN_MODULES=('legacy_fps','slide_core.export_v3','slide_core.timeline_json')
CHECKS=('pdf_only_checked','output_lock_cleanup_checked','background_preparation_checked',
        'save_options_checked','start_over_cache_cleanup_checked','manual_editing_checked',
        'keyboard_editing_checked','edited_export_checked','keyframe_json_v4_checked',
        'simple_json_checked','keyframe_only_checked','legacy_modules_absent_checked')

def verify_modules(module_names):
    forbidden=[name for name in module_names if any(name==prefix or name.startswith(prefix+'.')
               for prefix in FORBIDDEN_MODULES)]
    if forbidden:
        raise ValueError('Legacy modules in keyframe candidate: '+', '.join(sorted(forbidden)))

def validate_smoke(report, version, *, require_frozen=True, require_native=False):
    if report.get('status')!='success' or report.get('version')!=version:
        raise ValueError('Smoke status/version does not match candidate')
    if report.get('decoder_backend')!='cpu-keyframes':
        raise ValueError('Candidate must use keyframe decoder')
    for name in CHECKS:
        if report.get(name) is not True:
            raise ValueError('Missing verified smoke evidence: '+name)
    if require_native:
        for name in ('native_half_checked','native_lazy_edit_checked','native_json_v7_checked'):
            if report.get(name) is not True:raise ValueError('Missing native smoke evidence: '+name)
        if report.get('native_half_backend')!='native-idr' or report.get('native_half_policy')!='half':
            raise ValueError('Native half policy/backend mismatch')
    expected=True if require_frozen else False
    for name in ('frozen','bundled_tools_checked'):
        if report.get(name) is not expected:
            raise ValueError('Smoke execution scope mismatch: '+name)
