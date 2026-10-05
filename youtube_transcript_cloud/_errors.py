"""Exception names from youtube-transcript-api, so existing ``except`` blocks keep working."""


class CouldNotRetrieveTranscript(Exception):
    def __init__(self, video_id, message=""):
        self.video_id = video_id
        super().__init__(f"Could not retrieve a transcript for the video {video_id}. {message}".strip())


class YouTubeTranscriptApiException(CouldNotRetrieveTranscript):
    pass


class VideoUnavailable(CouldNotRetrieveTranscript):
    pass


class InvalidVideoId(CouldNotRetrieveTranscript):
    pass


class TranscriptsDisabled(CouldNotRetrieveTranscript):
    pass


class NoTranscriptFound(CouldNotRetrieveTranscript):
    def __init__(self, video_id, requested_language_codes=(), transcript_data=None, message=""):
        self.requested_language_codes = list(requested_language_codes)
        super().__init__(video_id, message or f"No transcript found for {', '.join(self.requested_language_codes) or 'the requested languages'}.")


class RequestBlocked(CouldNotRetrieveTranscript):
    """Kept for compatibility. The hosted service handles YouTube's IP blocks, so you shouldn't see it."""


class IpBlocked(RequestBlocked):
    pass


class ApifyRequestFailed(CouldNotRetrieveTranscript):
    """The hosted service couldn't be reached or rejected the request (token, credit, network)."""
