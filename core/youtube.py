"""Shared YouTube URL normalisation.

Lives outside any single app's models so videos/news/liveblog/webstories can
all import it without creating a circular dependency between apps.
"""
import re
from urllib.parse import parse_qs, urlparse

_YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def youtube_embed_url(url):
    """Return an embeddable YouTube URL, or "" when no video id is found.

    Editors are often non-technical -- they paste whatever their phone's share
    sheet or browser address bar gives them: a watch URL, a youtu.be short
    link, a /live/ or /shorts/ URL, sometimes missing "https://" entirely, or
    even just the bare video id copied out of the middle of a link. Only the
    /embed/ form can be loaded in an iframe; the others are refused by
    YouTube's frame policy and render as a blank player with no error, so
    every real-world variant is normalised here rather than trusting the
    client to paste a "proper" embed link.
    """
    if not url:
        return ""
    url = url.strip()

    # A bare video id, with no URL around it at all (e.g. copied out of the
    # middle of a longer link by mistake).
    if _YOUTUBE_ID.match(url):
        return f"https://www.youtube-nocookie.com/embed/{url}"

    # Non-technical users frequently drop the scheme when pasting from an
    # address bar ("youtube.com/watch?v=..." instead of "https://...") --
    # without a scheme, urlparse puts the whole thing in .path instead of
    # .netloc and every check below silently fails.
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
        url = f"https://{url}"

    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.").removeprefix("m.")
    video_id = ""

    if host in {"youtu.be"}:
        video_id = parsed.path.lstrip("/").split("/")[0]
    elif host in {"youtube.com", "youtube-nocookie.com"}:
        segments = [segment for segment in parsed.path.split("/") if segment]
        if segments and segments[0] in {"embed", "v", "shorts", "live"}:
            video_id = segments[1] if len(segments) > 1 else ""
        else:
            video_id = (parse_qs(parsed.query).get("v") or [""])[0]

    if not _YOUTUBE_ID.match(video_id):
        return ""
    return f"https://www.youtube-nocookie.com/embed/{video_id}"
