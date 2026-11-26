"""YouTube link detection used for the media extra-context notes."""

import pytest

from cogaicog.media import youtube_ids

VIDEO_ID = "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (f"https://www.youtube.com/watch?v={VIDEO_ID}", [VIDEO_ID]),
        (f"https://youtube.com/watch?v={VIDEO_ID}", [VIDEO_ID]),
        (f"https://youtu.be/{VIDEO_ID}", [VIDEO_ID]),
        (f"https://youtube.com/shorts/{VIDEO_ID}", [VIDEO_ID]),
        (f"https://www.youtube.com/watch?t=30&v={VIDEO_ID}", [VIDEO_ID]),
        ("https://vimeo.com/dQw4w9WgXcQ", []),
        ("watch?v=short", []),
    ],
)
def test_youtube_ids_detects_supported_url_shapes(text, expected):
    assert youtube_ids(text) == expected


def test_youtube_ids_handles_multiple_links_and_empty_input():
    assert youtube_ids(
        "https://youtu.be/aaaaaaaaaaa and https://youtube.com/shorts/bbbbbbbbbbb"
    ) == ["aaaaaaaaaaa", "bbbbbbbbbbb"]
    assert youtube_ids("") == []
    assert youtube_ids(None) == []
