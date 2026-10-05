"""Minimal versions of youtube-transcript-api's formatters."""
import json


def _items(transcript):
    return transcript.to_raw_data() if hasattr(transcript, "to_raw_data") else list(transcript)


def _ts(sec, sep):
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


class TextFormatter:
    def format_transcript(self, transcript, **kwargs):
        return "\n".join(i["text"] for i in _items(transcript))


class JSONFormatter:
    def format_transcript(self, transcript, **kwargs):
        return json.dumps(_items(transcript), **kwargs)


class SRTFormatter:
    def format_transcript(self, transcript, **kwargs):
        out = []
        for n, i in enumerate(_items(transcript), 1):
            out.append(f"{n}\n{_ts(i['start'], ',')} --> {_ts(i['start'] + i['duration'], ',')}\n{i['text']}\n")
        return "\n".join(out)


class WebVTTFormatter:
    def format_transcript(self, transcript, **kwargs):
        body = "\n".join(f"{_ts(i['start'], '.')} --> {_ts(i['start'] + i['duration'], '.')}\n{i['text']}\n" for i in _items(transcript))
        return f"WEBVTT\n\n{body}"
