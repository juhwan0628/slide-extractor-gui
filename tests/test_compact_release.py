import hashlib
import importlib.util
from pathlib import Path
import zipfile
import pytest

def load():
    path=Path(__file__).parents[1]/"packaging/compact_release.py"
    assert path.exists(), "compact release implementation is missing"
    spec=importlib.util.spec_from_file_location("compact_release",path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def fixture(root):
    root.mkdir()
    files={"SlideExtractor-v0.4.9rc3-macOS-arm64.dmg":b"mac-installer",
           "SlideExtractor-v0.4.9rc3-Setup-Windows-x64.exe":b"windows-installer",
           "qt-source.tar.xz":b"source archive",
           "OpenSSL-LICENSE.txt":b"license"}
    for name,data in files.items():
        (root/name).write_bytes(data)
    (root/"SHA256SUMS.txt").write_text("".join(f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name,data in files.items()))
    return files

def test_all_support_bytes_preserved_and_only_four_public_files(tmp_path):
    files=fixture(tmp_path/"input")
    out=tmp_path/"output"
    load().compact_assets(tmp_path/"input",out,"0.4.9rc3")
    assert sorted(p.suffix for p in out.iterdir())==[".dmg",".exe",".txt",".zip"]
    with zipfile.ZipFile(next(out.glob("*.zip"))) as z:
        assert z.read("qt-source.tar.xz")==files["qt-source.tar.xz"]
        assert z.read("OpenSSL-LICENSE.txt")==files["OpenSSL-LICENSE.txt"]
        assert "README.txt" in z.namelist()
        assert z.read("ORIGINAL-SHA256SUMS.txt")== (tmp_path/"input/SHA256SUMS.txt").read_bytes()
        assert not any(n.endswith((".dmg",".exe")) for n in z.namelist())
    for line in (out/"SHA256SUMS.txt").read_text().splitlines():
        digest,name=line.split("  ",1)
        assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest
    assert len((out/"SHA256SUMS.txt").read_text().splitlines())==3

def test_changed_source_rejected_before_creating_output(tmp_path):
    fixture(tmp_path/"input")
    (tmp_path/"input/qt-source.tar.xz").write_bytes(b"changed")
    with pytest.raises(ValueError,match="hash"):
        load().compact_assets(tmp_path/"input",tmp_path/"output","0.4.9rc3")
    assert not (tmp_path/"output").exists()

def test_missing_license_rejected(tmp_path):
    fixture(tmp_path/"input")
    (tmp_path/"input/OpenSSL-LICENSE.txt").unlink()
    with pytest.raises(ValueError,match="inventory"):
        load().compact_assets(tmp_path/"input",tmp_path/"output","0.4.9rc3")

def test_unsafe_checksum_path_rejected(tmp_path):
    fixture(tmp_path/"input")
    with (tmp_path/"input/SHA256SUMS.txt").open("a") as f:
        f.write("0"*64+"  ../secret\n")
    with pytest.raises(ValueError,match="name"):
        load().compact_assets(tmp_path/"input",tmp_path/"output","0.4.9rc3")
