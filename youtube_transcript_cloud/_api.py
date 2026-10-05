"""youtube-transcript-api-compatible client backed by a hosted transcript API.

YouTube blocks most cloud-provider IPs, so youtube-transcript-api raises ``RequestBlocked``/``IpBlocked`` on
AWS, Google Cloud, Azure and similar hosts. This client keeps the same interface, but each request runs
AutomationNation's YouTube Transcript Scraper on Apify, which deals with YouTube's blocks for you.
Set ``APIFY_TOKEN`` (free account: https://console.apify.com/sign-up) or pass ``apify_token``.
"""

import os
import re
from dataclasses import dataclass, field
from typing import Iterable, List, Optional

import requests

from ._errors import ApifyRequestFailed, CouldNotRetrieveTranscript, InvalidVideoId, NoTranscriptFound, TranscriptsDisabled, VideoUnavailable

ACTOR = "automationnation~youtube-transcript-scraper"
API = "https://api.apify.com/v2"


@dataclass
class FetchedTranscriptSnippet:
    text: str
    start: float
    duration: float


@dataclass
class FetchedTranscript:
    snippets: List[FetchedTranscriptSnippet]
    video_id: str
    language: str
    language_code: str
    is_generated: bool
    title: Optional[str] = None

    def __iter__(self):
        return iter(self.snippets)

    def __getitem__(self, i):
        return self.snippets[i]

    def __len__(self):
        return len(self.snippets)

    def to_raw_data(self):
        return [{"text": s.text, "start": s.start, "duration": s.duration} for s in self.snippets]


@dataclass
class Transcript:
    video_id: str
    language: str
    language_code: str
    is_generated: bool
    _api: "YouTubeTranscriptApi" = field(repr=False, default=None)
    is_translatable: bool = False
    translation_languages: list = field(default_factory=list)

    def fetch(self, preserve_formatting=False):
        return self._api.fetch(self.video_id, languages=[self.language_code])


class TranscriptList:
    def __init__(self, video_id, transcripts):
        self.video_id = video_id
        self._transcripts = transcripts

    def __iter__(self):
        return iter(self._transcripts)

    def _find(self, language_codes, generated=None):
        for code in language_codes:
            for t in self._transcripts:
                if _same_language(t.language_code, code) and (generated is None or t.is_generated == generated):
                    return t
        raise NoTranscriptFound(self.video_id, language_codes)

    def find_transcript(self, language_codes):
        try:
            return self._find(language_codes, generated=False)
        except NoTranscriptFound:
            return self._find(language_codes)

    def find_manually_created_transcript(self, language_codes):
        return self._find(language_codes, generated=False)

    def find_generated_transcript(self, language_codes):
        return self._find(language_codes, generated=True)


def _same_language(a, b):
    a, b = (a or "").lower(), (b or "").lower()
    return a == b or a.split("-")[0] == b.split("-")[0]


class YouTubeTranscriptApi:
    """Same interface as youtube-transcript-api 1.x (fetch/list), plus the 0.x class methods."""

    def __init__(self, apify_token=None, proxy_config=None, http_client=None, wait_secs=300):
        self.token = apify_token or os.environ.get("APIFY_TOKEN") or os.environ.get("APIFY_API_TOKEN")
        self.wait_secs = min(int(wait_secs), 300)

    # -- 1.x API -----------------------------------------------------------------------------------------

    def fetch(self, video_id, languages: Iterable[str] = ("en",), preserve_formatting=False) -> FetchedTranscript:
        languages = list(languages) or ["en"]
        available = []
        for lang in languages:
            row = self._run([video_id], lang)[0]
            status = row.get("status")
            if status == "ok" and row.get("segments") is not None:
                if not row.get("isTranslated") and not _same_language(row.get("transcriptLanguage"), lang):
                    available.append(row.get("transcriptLanguage"))
                    continue
                return _fetched(row, video_id)
            if status != "no_transcript":
                raise _error(row, video_id, languages)
            available += re.findall(r"[a-z]{2,3}(?:-[A-Za-z0-9]+)?", (row.get("error") or "").split("available:")[-1]) if "available:" in (row.get("error") or "") else []
            if "no captions" in (row.get("error") or "").lower():
                raise TranscriptsDisabled(video_id, "This video has no captions.")
        raise NoTranscriptFound(video_id, languages, message=f"No transcript in {', '.join(languages)}." + (f" Available: {', '.join(dict.fromkeys(available))}." if available else ""))

    def fetch_many(self, video_ids, languages: Iterable[str] = ("en",)):
        """One run for many videos (faster and cheaper than a loop). Returns {video_id: FetchedTranscript or exception}."""
        languages = list(languages) or ["en"]
        out = {}
        for vid, row in zip(video_ids, self._run(list(video_ids), languages[0])):
            out[vid] = _fetched(row, vid) if row.get("status") == "ok" else _error(row, vid, languages)
        return out

    def list(self, video_id) -> TranscriptList:
        row = self._run([video_id], "en")[0]
        if row.get("status") not in ("ok", "no_transcript"):
            raise _error(row, video_id, ["en"])
        langs = row.get("availableLanguages") or []
        if not langs and row.get("status") == "no_transcript":
            codes = re.findall(r"[a-z]{2,3}(?:-[A-Za-z0-9]+)?", (row.get("error") or "").split("available:")[-1]) if "available:" in (row.get("error") or "") else []
            langs = [{"languageCode": c, "languageName": c, "isAutoGenerated": False} for c in codes]
        return TranscriptList(video_id, [Transcript(video_id, l.get("languageName") or l.get("languageCode"), l.get("languageCode"), bool(l.get("isAutoGenerated")), self) for l in langs])

    # -- 0.x class methods -------------------------------------------------------------------------------

    @classmethod
    def get_transcript(cls, video_id, languages=("en",), proxies=None, cookies=None, preserve_formatting=False):
        return cls().fetch(video_id, languages).to_raw_data()

    @classmethod
    def get_transcripts(cls, video_ids, languages=("en",), continue_after_error=False, proxies=None, cookies=None, preserve_formatting=False):
        data, failed = {}, []
        for vid, res in cls().fetch_many(list(video_ids), languages).items():
            if isinstance(res, Exception):
                if not continue_after_error:
                    raise res
                failed.append(vid)
            else:
                data[vid] = res.to_raw_data()
        return data, failed

    @classmethod
    def list_transcripts(cls, video_id, proxies=None, cookies=None):
        return cls().list(video_id)

    # -- internals ---------------------------------------------------------------------------------------

    def _run(self, video_ids, language):
        if not self.token:
            raise ApifyRequestFailed(", ".join(video_ids), "No Apify API token: set APIFY_TOKEN or pass YouTubeTranscriptApi(apify_token=...). "
                                     "Free account: https://console.apify.com/sign-up, token: https://console.apify.com/settings/integrations")
        inp = {"videos": list(video_ids), "language": language, "includeTimestamps": True, "includeAutoGenerated": True, "maxVideosPerChannel": 1}
        res = requests.post(f"{API}/acts/{ACTOR}/run-sync-get-dataset-items", params={"timeout": self.wait_secs, "clean": "true"},
                            json=inp, headers={"Authorization": f"Bearer {self.token}", "User-Agent": "youtube-transcript-cloud"}, timeout=self.wait_secs + 30)
        if res.status_code >= 400:
            hint = {401: "Apify rejected the API token (check APIFY_TOKEN).", 402: "Your Apify account has no credit left: https://console.apify.com/billing"}.get(res.status_code)
            raise ApifyRequestFailed(", ".join(video_ids), hint or f"HTTP {res.status_code}: {res.text[:200]}")
        rows = res.json() if isinstance(res.json(), list) else []
        by_id = {r.get("videoId"): r for r in rows}
        # Rows come back per video; match them to the inputs (IDs or URLs).
        return [by_id.get(_video_id(v)) or (rows[i] if i < len(rows) else {"status": "failed", "error": "No result returned."}) for i, v in enumerate(video_ids)]


def _video_id(v):
    m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/|live/)([A-Za-z0-9_-]{11})", v)
    return m.group(1) if m else v


def _fetched(row, video_id):
    return FetchedTranscript(
        snippets=[FetchedTranscriptSnippet(s.get("text", ""), float(s.get("start", 0)), float(s.get("duration", 0))) for s in row.get("segments") or []],
        video_id=row.get("videoId") or video_id,
        language=row.get("transcriptLanguageName") or row.get("transcriptLanguage") or "",
        language_code=row.get("transcriptLanguage") or "",
        is_generated=bool(row.get("isAutoGenerated")),
        title=row.get("title"),
    )


def _error(row, video_id, languages) -> CouldNotRetrieveTranscript:
    status, msg = row.get("status"), row.get("error") or ""
    if status == "no_transcript":
        return TranscriptsDisabled(video_id, msg) if "no captions" in msg.lower() else NoTranscriptFound(video_id, languages, message=msg)
    if status == "unavailable":
        return VideoUnavailable(video_id, msg)
    if status == "invalid":
        return InvalidVideoId(video_id, msg)
    return CouldNotRetrieveTranscript(video_id, msg)
