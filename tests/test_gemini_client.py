from pathlib import Path

import pytest

from rhythm_cut.providers.gemini_client import GeminiClient


def test_gemini_client_reads_project_env_names(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text(
        "GEMINI_API_KEY=test-key\n"
        "GEMINI_BASE_URL=https://example.invalid/v1\n"
        "GOOGLE_CLOUD_PROJECT=test-project\n"
        "GOOGLE_CLOUD_LOCATION=global\n"
    )
    client = GeminiClient(env_path=env)
    assert client.api_key == "test-key"
    assert client.base_url == "https://example.invalid/v1"


def test_gemini_client_requires_base_url(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text("GEMINI_API_KEY=test-key\n")
    with pytest.raises(ValueError, match="GEMINI_BASE_URL"):
        GeminiClient(env_path=env)
