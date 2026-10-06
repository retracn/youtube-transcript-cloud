# youtube-transcript-cloud: youtube-transcript-api that works on servers

On AWS, Google Cloud, Azure, Vercel and most other hosts, youtube-transcript-api fails with `RequestBlocked` or `IpBlocked` ("YouTube is blocking requests from your IP"), because YouTube blocks most cloud-provider IPs. **youtube-transcript-cloud has the same interface, so your code doesn't change**. Transcripts come from a hosted API that handles YouTube's blocks for you.

```diff
- from youtube_transcript_api import YouTubeTranscriptApi
+ from youtube_transcript_cloud import YouTubeTranscriptApi
```

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/retracn/youtube-transcript-cloud/blob/main/examples/youtube_transcripts_in_colab.ipynb) Try it in a Colab notebook, where the original library is usually blocked.

## Install

```bash
pip install git+https://github.com/retracn/youtube-transcript-cloud
```

You need an Apify API token: create a [free Apify account](https://console.apify.com/sign-up), copy the token from [Settings → API & Integrations](https://console.apify.com/settings/integrations) and set `APIFY_TOKEN`, or pass `YouTubeTranscriptApi(apify_token="...")`.

## Use it exactly like youtube-transcript-api

```python
from youtube_transcript_cloud import YouTubeTranscriptApi

ytt_api = YouTubeTranscriptApi()
transcript = ytt_api.fetch("dQw4w9WgXcQ", languages=["de", "en"])
for snippet in transcript:
    print(snippet.start, snippet.text)

transcript.to_raw_data()                                  # [{"text", "start", "duration"}, ...]
ytt_api.list("dQw4w9WgXcQ").find_transcript(["en"])       # available transcripts
YouTubeTranscriptApi.get_transcript("dQw4w9WgXcQ")        # the 0.x class methods work too
ytt_api.fetch_many(["dQw4w9WgXcQ", "jNQXAC9IVRw"])        # many videos in one request
```

Supported, and the same as youtube-transcript-api:
- `fetch`, `list`, `find_transcript`, `find_manually_created_transcript` and `find_generated_transcript`
- the 0.x `get_transcript`, `get_transcripts` and `list_transcripts`
- the formatters in `youtube_transcript_cloud.formatters` (Text, JSON, SRT, WebVTT)
- the usual exceptions: `NoTranscriptFound`, `TranscriptsDisabled`, `VideoUnavailable`, `InvalidVideoId`

`proxy_config`, `proxies` and `cookies` are accepted and ignored, because you don't need them any more. Machine translation (`translate()`) isn't supported.

## Cost

Each request runs [YouTube Transcript Scraper](https://apify.com/automationnation/youtube-transcript-scraper) on your Apify account. It costs $1.50 per 1,000 transcripts, and videos without captions are free. Apify's free monthly credit covers about 3,300 transcripts. `fetch_many` handles a batch in one run, which is faster than a loop.

More: [Why youtube-transcript-api is blocked on servers, and the fix](https://retracn.github.io/automationnation-actors/guides/youtube-transcript-api-blocked/) · [YouTube transcript scrapers compared](https://retracn.github.io/automationnation-actors/compare/youtube-transcript-scrapers/)

Not affiliated with YouTube or the youtube-transcript-api authors. MIT licensed.
