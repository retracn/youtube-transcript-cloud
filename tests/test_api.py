import json
from pathlib import Path

import pytest

from youtube_transcript_cloud import NoTranscriptFound, TranscriptsDisabled, VideoUnavailable, YouTubeTranscriptApi
from youtube_transcript_cloud.formatters import SRTFormatter, TextFormatter

FIX = Path(__file__).parent / "fixtures"


@pytest.fixture
def api(monkeypatch):
    calls = []
    plan = {"dQw4w9WgXcQ": "ok.json", "xxxxxxxxxxx": "no_de.json", "nocaptions1": "no_captions.json", "gone1234567": "unavailable.json"}

    def fake_run(self, video_ids, language):
        calls.append((list(video_ids), language))
        rows = []
        for v in video_ids:
            rows += json.loads((FIX / plan[v]).read_text())
        return rows

    monkeypatch.setattr(YouTubeTranscriptApi, "_run", fake_run)
    a = YouTubeTranscriptApi(apify_token="test")
    a.calls = calls
    return a


def test_fetch_returns_snippets(api):
    t = api.fetch("dQw4w9WgXcQ", languages=["en"])
    assert t.video_id == "dQw4w9WgXcQ" and t.language_code == "en" and t.is_generated is False
    assert len(t) > 10
    first = t.to_raw_data()[0]
    assert set(first) == {"text", "start", "duration"} and first["start"] == 1.36


def test_legacy_get_transcript(api, monkeypatch):
    monkeypatch.setattr(YouTubeTranscriptApi, "__init__", lambda self, *a, **k: setattr(self, "token", "t") or setattr(self, "wait_secs", 10))
    rows = YouTubeTranscriptApi.get_transcript("dQw4w9WgXcQ")
    assert isinstance(rows, list) and rows[0]["text"]


def test_errors_map_to_youtube_transcript_api_names(api):
    with pytest.raises(NoTranscriptFound, match="Available: en, fr"):
        api.fetch("xxxxxxxxxxx", languages=["de"])
    with pytest.raises(TranscriptsDisabled):
        api.fetch("nocaptions1")
    with pytest.raises(VideoUnavailable):
        api.fetch("gone1234567")


def test_language_fallback_order(api):
    with pytest.raises(NoTranscriptFound):
        api.fetch("xxxxxxxxxxx", languages=["de", "it"])
    assert [c[1] for c in api.calls] == ["de", "it"]


def test_formatters(api):
    t = api.fetch("dQw4w9WgXcQ")
    assert "never gonna give you up" in TextFormatter().format_transcript(t).lower()
    assert "00:00:01,360 -->" in SRTFormatter().format_transcript(t)


def test_missing_token_is_a_clear_error(monkeypatch):
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    monkeypatch.delenv("APIFY_API_TOKEN", raising=False)
    with pytest.raises(Exception, match="APIFY_TOKEN"):
        YouTubeTranscriptApi().fetch("dQw4w9WgXcQ")
