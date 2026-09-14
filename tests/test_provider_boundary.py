import pytest

from rhythm_cut.providers.base import VideoWindow
from rhythm_cut.providers.gemini import GeminiVisionProvider


def test_gemini_is_explicitly_unwired():
    provider = GeminiVisionProvider()
    with pytest.raises(NotImplementedError):
        provider.analyze(VideoWindow("a1", "clip.mp4", 0, 1, 6), prompt_version="v1")
