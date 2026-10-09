from dataclasses import dataclass
from .models import Rect

PROCESS_TIMEOUTS = {"version": 5.0, "probe": 15.0, "preview": 15.0,
                    "frame": 60.0, "progress": 60.0,
                    "extraction": 120.0, "qpdf": 120.0}
PROCESS_CANCEL_POLL_S = 0.05
PROCESS_TERMINATE_GRACE_S = 2.0
PROCESS_STDERR_TAIL_BYTES = 64 * 1024


def analysis_timeout(duration_s: float) -> float:
    return max(300.0, float(duration_s) * 2)


def export_timeout(page_count: int) -> float:
    return max(300.0, int(page_count) * PROCESS_TIMEOUTS["extraction"])


@dataclass(frozen=True)
class AnalysisSettings:
    fps: float = 1.0
    roi_mode: str = "auto"
    effective_roi: Rect | None = None
    masks: tuple[Rect, ...] = ()
    detector: "DetectorConfig | None" = None
    settings_revision: int = 0

    def __post_init__(self):
        object.__setattr__(self, "masks", tuple(self.masks))
        if self.fps not in (0.5, 1.0) or self.roi_mode not in ("auto", "manual", "full") or self.settings_revision < 0:
            raise ValueError("invalid analysis settings")
        if self.roi_mode == "manual" and self.effective_roi is None:
            raise ValueError("manual ROI is required")

@dataclass(frozen=True)
class DetectorConfig:
    debounce_samples: int = 2
    candidate_mad: float = 0.005
    candidate_tile_mad: float = 0.025
    candidate_pixel_delta: int = 20
    candidate_changed_fraction: float = 0.0002
    tile_size: int = 20
    tile_stride: int = 10
    keep_unconfirmed: bool = True
