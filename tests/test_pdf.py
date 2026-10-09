from pathlib import Path

import pytest
from PIL import Image
from slide_core.models import SlideImage
from slide_core.pdf import write_slides_pdf


def test_pdf_pages_and_dimensions(tmp_path):
    from pypdf import PdfReader
    imgs = []
    for index, (width, height) in enumerate([(320, 180), (100, 220), (640, 360)]):
        source = tmp_path / f"{index}.png"
        Image.new("RGB", (width, height), ("red", "green", "blue")[index]).save(source)
        imgs.append(SlideImage(source, float(index)))
    output = tmp_path / "slides.pdf"
    write_slides_pdf(imgs, output)
    reader = PdfReader(output)
    assert len(reader.pages) == 3
    for page, dims in zip(reader.pages, [(320, 180), (100, 220), (640, 360)]):
        assert (float(page.mediabox.width), float(page.mediabox.height)) == dims


def test_qpdf_absent_still_writes_pdf(tmp_path, monkeypatch):
    from slide_core import pdf
    monkeypatch.setattr(pdf.shutil, "which", lambda name: None)
    source = tmp_path / "sample.png"
    Image.new("RGB", (30, 20), "white").save(source)
    out = tmp_path / "out.pdf"
    write_slides_pdf([SlideImage(source, 0.0)], out)
    assert out.read_bytes().startswith(b"%PDF-")


def test_empty_pages_are_rejected(tmp_path):
    with pytest.raises(ValueError):
        write_slides_pdf([], tmp_path / "empty.pdf")

def test_pdf_subject_uuid_and_pixel_identity(tmp_path, monkeypatch):
    import uuid
    from pypdf import PdfReader
    from slide_core import pdf
    monkeypatch.setattr(pdf.shutil, "which", lambda _name: None)
    pixels=Image.new("RGB",(41,37))
    for y in range(37):
        for x in range(41):
            pixels.putpixel((x,y), ((7*x+5*y)%256, (3*x+9*y)%256, (x*11+y)%256))
    path=tmp_path/"pixels.png";pixels.save(path)
    output=tmp_path/"strict.pdf"
    export_id=str(uuid.uuid4())
    write_slides_pdf([SlideImage(path,0)],output,export_id=export_id)
    reader=PdfReader(output)
    assert reader.metadata.subject == f"slide-extractor:export_id={export_id}"
    assert list(reader.pages[0].images)
    decoded=reader.pages[0].images[0].image.convert("RGB")
    assert decoded.tobytes()==pixels.tobytes()
    from slide_core.pdf import validate_slides_pdf
    assert validate_slides_pdf(output,[SlideImage(path,0)],export_id=export_id)==export_id


def test_corrupt_optimization_falls_back_to_valid_raw_pdf(tmp_path,monkeypatch):
    from slide_core import pdf
    from pypdf import PdfReader
    source=tmp_path/"src.png";Image.new("RGB",(42,38),"red").save(source)
    def corrupt(_source,destination,**kwargs):
        destination.write_bytes(b"not-a-pdf")
        return True
    monkeypatch.setattr(pdf,"_run_qpdf_optimization",corrupt)
    out=tmp_path/"out.pdf"
    write_slides_pdf([SlideImage(source,0)],out)
    assert len(PdfReader(out).pages)==1
    assert not list(tmp_path.glob(".*.raw.pdf"))


def test_optimizer_cannot_replace_export_identity(tmp_path,monkeypatch):
    from slide_core import pdf
    source=tmp_path/"src.png";Image.new("RGB",(42,38),"green").save(source)
    real_pdf=pdf.write_slides_pdf
    other=tmp_path/"other.pdf"
    real_pdf([SlideImage(source,0)],other,export_id="00000000-0000-4000-8000-000000000001")
    def invalid(_src,dst,**kwargs):
        dst.write_bytes(other.read_bytes())
        return True
    monkeypatch.setattr(pdf,"_run_qpdf_optimization",invalid)
    out=tmp_path/"out.pdf"
    real_pdf([SlideImage(source,0)],out,export_id="00000000-0000-4000-8000-000000000002")
    assert pdf.validate_slides_pdf(out,[SlideImage(source,0)])=="00000000-0000-4000-8000-000000000002"


def test_pdf_invalid_page_count_and_identifier(tmp_path):
    from slide_core.pdf import validate_slides_pdf,InvalidSlidePDF
    source=tmp_path/"src.png";Image.new("RGB",(32,18),"blue").save(source)
    out=tmp_path/"out.pdf";write_slides_pdf([SlideImage(source,0)],out)
    with pytest.raises(InvalidSlidePDF):
        validate_slides_pdf(out,[SlideImage(source,0),SlideImage(source,1)])
    with pytest.raises(InvalidSlidePDF):
        validate_slides_pdf(out,[SlideImage(source,0)],export_id="00000000-0000-4000-8000-000000000001")


def test_cancelled_pdf_never_overwrites_existing_output(tmp_path):
    from slide_core.models import CancelToken
    from slide_core.models import CancelledError
    source=tmp_path/"src.png";Image.new("RGB",(32,18),"blue").save(source)
    out=tmp_path/"out.pdf";out.write_bytes(b"unchanged")
    token=CancelToken();token.cancel()
    with pytest.raises(CancelledError):
        write_slides_pdf([SlideImage(source,0)],out,cancel_token=token)
    assert out.read_bytes()==b"unchanged"


def test_no_lossy_qpdf_optimization_flag(tmp_path,monkeypatch):
    from slide_core import pdf
    from slide_core.media import _ProcessResult
    commands=[]
    monkeypatch.setattr(pdf.shutil, "which", lambda name: "/usr/bin/qpdf")
    def runner(cmd,**kw):
        commands.append(cmd)
        Path(cmd[-1]).write_bytes(Path(cmd[-2]).read_bytes())
        return _ProcessResult("","",3)
    monkeypatch.setattr(pdf,"_run_process",runner)
    source=tmp_path/"src.pdf";source.write_bytes(b"X")
    assert pdf._run_qpdf_optimization(source,tmp_path/"dest.pdf")
    assert "--optimize-images" not in commands[0]
    assert "--recompress-flate" in commands[0]
