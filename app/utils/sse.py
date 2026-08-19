import json


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def sse_padding() -> str:
    """
    A ~2KB SSE comment frame (ignored by every SSE parser, per spec).

    Some proxies/CDNs buffer a streamed response until a minimum byte
    threshold is reached before flushing the first chunk to the client, which
    defeats incremental delivery for endpoints that emit many small frames.
    Sending this as the very first frame pushes past that threshold
    immediately so real events stream as they're produced instead of
    arriving all at once when the connection closes.
    """
    return ": " + ("padding " * 256) + "\n\n"
