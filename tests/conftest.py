"""Make the repository root importable regardless of pytest's launch directory."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# aioresponses 0.7 builds ClientResponse objects without the ``stream_writer``
# argument that aiohttp 3.14 now requires. Supply a minimal writer so the
# mocked responses stay purely in-memory (no sockets, no live services).
import inspect

from aiohttp.client_reqrep import ClientResponse
import aioresponses.core


class _DummyStreamWriter:
    output_size = 0


if "stream_writer" in inspect.signature(ClientResponse.__init__).parameters:

    class _CompatClientResponse(ClientResponse):
        def __init__(self, *args, **kwargs):
            kwargs.setdefault("stream_writer", _DummyStreamWriter())
            super().__init__(*args, **kwargs)

else:  # older aiohttp: the stock response class already works
    _CompatClientResponse = ClientResponse

_original_build_response = aioresponses.core.RequestMatch._build_response


def _build_response(self, *args, **kwargs):
    if kwargs.get("response_class") is None:
        kwargs["response_class"] = _CompatClientResponse
    return _original_build_response(self, *args, **kwargs)


aioresponses.core.RequestMatch._build_response = _build_response
