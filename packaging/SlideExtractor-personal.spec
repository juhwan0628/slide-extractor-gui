# Personal build selects the same recipe with local FFmpeg inputs.
import os
from pathlib import Path
os.environ['SLIDE_BUILD_MODE'] = 'personal'
shared = Path(SPECPATH)/'SlideExtractor.spec'
exec(compile(shared.read_text(), str(shared), 'exec'), globals())
