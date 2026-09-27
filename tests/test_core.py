import pytest

from muse2api.core.models import resolve_model
from muse2api.core.prompt import flatten_messages
from muse2api.errors import InvalidRequest


def test_single_user_message_verbatim():
    assert flatten_messages([{"role": "user", "content": "hi"}]).text == "hi"


def test_multi_turn_has_roles_and_images():
    flat = flatten_messages([
        {"role": "system", "content": "be brief"},
        {"role": "user", "content": [
            {"type": "text", "text": "what is this"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}},
        ]},
    ])
    assert "[System]\nbe brief" in flat.text
    assert "[User]\nwhat is this" in flat.text
    assert flat.images == ["data:image/png;base64,AAAA"]


def test_resolve_model():
    assert resolve_model("gpt-4o", "chat").id == "muse-chat"
    assert resolve_model("unknown", "image").id == "muse-image"
    assert resolve_model(None, "video").id == "muse-video"
    with pytest.raises(InvalidRequest):
        resolve_model("muse-image", "chat")
