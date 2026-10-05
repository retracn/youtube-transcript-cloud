"""Drop-in replacement for youtube-transcript-api that works from cloud servers (no RequestBlocked / IpBlocked).

    from youtube_transcript_cloud import YouTubeTranscriptApi   # was: from youtube_transcript_api import YouTubeTranscriptApi
"""

from ._api import FetchedTranscript, FetchedTranscriptSnippet, Transcript, TranscriptList, YouTubeTranscriptApi
from ._errors import (
    CouldNotRetrieveTranscript,
    InvalidVideoId,
    IpBlocked,
    NoTranscriptFound,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
    YouTubeTranscriptApiException,
)

__all__ = ["YouTubeTranscriptApi", "FetchedTranscript", "FetchedTranscriptSnippet", "Transcript", "TranscriptList",
           "CouldNotRetrieveTranscript", "InvalidVideoId", "IpBlocked", "NoTranscriptFound", "RequestBlocked",
           "TranscriptsDisabled", "VideoUnavailable", "YouTubeTranscriptApiException"]
__version__ = "0.1.0"
