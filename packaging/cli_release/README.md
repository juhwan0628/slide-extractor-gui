# Slide Extractor CLI @VERSION@

Extract slide PDFs from local lecture videos using the shared keyframe engine.

Requires Python 3.12+, FFmpeg and FFprobe on PATH. qpdf is optional.

```bash
python -m pip install .
slide-extractor lecture.mp4 --json detailed
slide-extractor first.mp4 second.mp4 --output-dir slides
```

Development source: https://github.com/juhwan0628/slide-extractor-gui
This repository is generated from a verified source commit. See source-manifest.json for provenance and file hashes. Make core changes in the development repository, then export a new snapshot.

Default Python wheels omit the native keyframe helper and use the existing CPU fallback when no helper is configured. See [CLI usage](docs/cli.md).
