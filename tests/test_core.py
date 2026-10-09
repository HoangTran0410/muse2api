import pytest

from muse2api.core.models import resolve_model
from muse2api.core.prompt import flatten_messages, followup_text, message_turns
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


def test_followup_sends_only_new_user_text():
    first = message_turns([{"role": "user", "content": "hi"}])
    second = message_turns([
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
        {"role": "user", "content": "again"},
    ])
    assert followup_text(first, second) == "again"


def test_followup_rejects_a_different_history():
    first = message_turns([{"role": "user", "content": "hi"}])
    other = message_turns([{"role": "user", "content": "a different chat"}])
    edited = message_turns([
        {"role": "user", "content": "hi, edited"},
        {"role": "assistant", "content": "hello"},
        {"role": "user", "content": "again"},
    ])
    assert followup_text(first, other) is None
    assert followup_text(first, edited) is None
    assert followup_text(first, first) is None


def test_thread_url_ignores_the_new_thread_page():
    from muse2api.drivers.browser.driver import is_thread_url

    assert is_thread_url("https://muse.ai/thread/abc")
    assert not is_thread_url("https://muse.ai/thread/new")
    assert not is_thread_url("https://muse.ai/thread/new/")
    assert not is_thread_url("https://muse.ai/")


def test_resolve_model():
    assert resolve_model("gpt-4o", "chat").id == "muse-chat"
    assert resolve_model("unknown", "image").id == "muse-image"
    assert resolve_model(None, "video").id == "muse-video"
    with pytest.raises(InvalidRequest):
        resolve_model("muse-image", "chat")


def test_file_video_audio_parts_are_collected_with_names():
    flat = flatten_messages([{"role": "user", "content": [
        {"type": "text", "text": "tóm tắt"},
        {"type": "file", "file": {"file_data": "data:application/pdf;base64,QQ==", "filename": "a.pdf"}},
        {"type": "input_file", "file_data": "data:text/csv;base64,QQ==", "filename": "b.csv"},
        {"type": "video_url", "video_url": {"url": "https://x.test/v.mp4"}},
        {"type": "input_audio", "input_audio": {"data": "QQ==", "format": "wav"}},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,QQ=="}},
    ]}])
    assert flat.text == "tóm tắt"
    assert flat.images == [
        "data:application/pdf;base64,QQ==",
        "data:text/csv;base64,QQ==",
        "https://x.test/v.mp4",
        "data:audio/wav;base64,QQ==",
        "data:image/png;base64,QQ==",
    ]
    assert flat.names == ["a.pdf", "b.csv", "", "", ""]
