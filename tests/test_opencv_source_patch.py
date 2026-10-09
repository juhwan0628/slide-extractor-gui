import importlib.util
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location("opencv_builder",Path(__file__).parents[1]/"packaging/build_image_opencv.py")
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)

def test_pinned_patch_rejects_unexpected_upstream_source(tmp_path):
    (tmp_path/"setup.py").write_text("changed upstream")
    with pytest.raises(ValueError,match="pinned"):
        builder.patch_image_only_source(tmp_path)
