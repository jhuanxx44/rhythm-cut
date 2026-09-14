import pytest

from rhythm_cut.analysis.candidates import fixed_windows


def test_fixed_windows_are_frame_aligned_and_stable():
    windows = fixed_windows("asset-1", duration_s=1.0, fps=30, window_s=0.4, step_s=0.3)
    assert [(item.source_in_frame, item.source_out_frame) for item in windows] == [
        (0, 12),
        (9, 21),
        (18, 30),
    ]
    assert windows[-1].end_s == 1.0


def test_fixed_windows_drops_too_short_tail():
    windows = fixed_windows(
        "asset-1", duration_s=1.0, fps=30, window_s=0.4, step_s=0.4, min_duration_s=0.3
    )
    assert len(windows) == 2


def test_fixed_windows_requires_positive_parameters():
    with pytest.raises(ValueError, match="must be positive"):
        fixed_windows("asset-1", duration_s=0, fps=30, window_s=0.4)
