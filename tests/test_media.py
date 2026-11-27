"""YouTube link detection and inline image downscaling."""

import asyncio
import base64
import io
from types import SimpleNamespace

import pytest
from aioresponses import aioresponses
from PIL import Image

from gamoaicog.media import MediaPipeline, downscale_image, youtube_ids

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


def image_bytes(size=(2000, 1000), mode="RGB"):
    color = (200, 100, 50) if mode == "RGB" else (200, 100, 50, 128)
    buffer = io.BytesIO()
    Image.new(mode, size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def test_downscale_caps_longest_edge_and_shrinks_payload():
    original = image_bytes()

    data, mime = downscale_image(original, "image/png", 768)

    assert mime == "image/jpeg"
    assert len(data) < len(original)
    with Image.open(io.BytesIO(data)) as image:
        assert image.size == (768, 384)
        assert image.format == "JPEG"


def test_downscale_keeps_small_images_and_transparency():
    small, _ = downscale_image(image_bytes((100, 50)), "image/png", 768)
    with Image.open(io.BytesIO(small)) as image:
        assert image.size == (100, 50)

    data, mime = downscale_image(image_bytes((900, 300), "RGBA"), "image/png", 768)
    assert mime == "image/png"
    with Image.open(io.BytesIO(data)) as image:
        assert image.size == (768, 256)
        assert "A" in image.getbands()


def test_downscale_passes_unreadable_payload_through():
    assert downscale_image(b"not an image", "image/png") == (b"not an image", "image/png")


def test_prepare_inlines_a_downscaled_attachment(tmp_path):
    async def run():
        original = image_bytes()
        url = "https://cdn.test/big.png"
        message = SimpleNamespace(
            attachments=[
                SimpleNamespace(
                    url=url,
                    content_type="image/png",
                    filename="big.png",
                    size=len(original),
                )
            ]
        )
        with aioresponses() as mocked:
            mocked.get(url, body=original)
            async with MediaPipeline(tmp_path / "cache", max_image_edge=768) as pipeline:
                attachments = await pipeline.prepare(message)

        assert len(attachments) == 1
        assert attachments[0].mime == "image/jpeg"
        inline = attachments[0].as_image_part()["image_url"]["url"]
        assert inline.startswith("data:image/jpeg;base64,")
        decoded = base64.b64decode(inline.split(",", 1)[1])
        with Image.open(io.BytesIO(decoded)) as image:
            assert image.size == (768, 384)

    asyncio.run(run())
