"""Convert OpenAI-style message lists into a single prompt for the muse web chat.

muse.ai's web UI is a single text box, so multi-turn context and system prompts
are serialised into one message. Image/file/video/audio parts are extracted
separately so that drivers can attach them as files.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

ROLE_LABELS = {
    "system": "System",
    "developer": "System",
    "user": "User",
    "assistant": "Assistant",
    "tool": "Tool",
}


@dataclass
class FlatPrompt:
    text: str
    images: list[str] = field(default_factory=list)
    """Attachment references (data URLs or http(s) URLs) found in the messages, in order."""
    names: list[str] = field(default_factory=list)
    """File name for each entry of ``images`` ("" when the request gave none)."""


def _nested_url(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("url")
    return value or None


def _file_part(part: dict[str, Any]) -> tuple[str | None, str]:
    """(reference, filename) from a Chat Completions ``file`` or Responses ``input_file`` part."""
    inner = part.get("file") if isinstance(part.get("file"), dict) else part
    ref = inner.get("file_data") or inner.get("file_url")
    return ref, inner.get("filename") or ""


def _content_to_text(content: Any, images: list[str], names: list[str] | None = None) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for part in content:
        if not isinstance(part, dict):
            parts.append(str(part))
            continue
        ptype = part.get("type")
        if ptype in ("text", "input_text", "output_text"):
            parts.append(part.get("text", ""))
        else:
            ref, name = None, ""
            if ptype in ("image_url", "input_image"):
                ref = _nested_url(part.get("image_url"))
            elif ptype == "video_url":
                ref = _nested_url(part.get("video_url"))
            elif ptype in ("file", "input_file"):
                ref, name = _file_part(part)
            elif ptype == "input_audio":
                audio = part.get("input_audio") or {}
                if audio.get("data"):
                    ref = f"data:audio/{audio.get('format', 'mp3')};base64,{audio['data']}"
            if ref:
                images.append(ref)
                if names is not None:
                    names.append(name)
    return "\n".join(p for p in parts if p)


def message_turns(messages: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """Role/text pairs, using the same text extraction as ``flatten_messages``."""
    turns: list[tuple[str, str]] = []
    for msg in messages:
        text = _content_to_text(msg.get("content"), []).strip()
        if text:
            turns.append((msg.get("role", "user"), text))
    return turns


def followup_text(previous: list[tuple[str, str]], incoming: list[tuple[str, str]]) -> str | None:
    """Text to send when ``incoming`` continues a conversation already on the page.

    Returns only the new user text. ``None`` means the histories do not line up, so the
    caller must open a fresh thread and send the full prompt instead.
    """
    if not previous or len(incoming) <= len(previous):
        return None
    if incoming[: len(previous)] != list(previous):
        return None
    extra = list(incoming[len(previous) :])
    while extra and extra[0][0] in ("assistant", "tool"):
        extra = extra[1:]
    user_text = []
    for role, text in extra:
        if role != "user":
            return None
        user_text.append(text)
    if not user_text:
        return None
    return "\n\n".join(user_text)


def flatten_messages(messages: list[dict[str, Any]]) -> FlatPrompt:
    images: list[str] = []
    names: list[str] = []
    turns: list[tuple[str, str]] = []
    for msg in messages:
        role = msg.get("role", "user")
        text = _content_to_text(msg.get("content"), images, names).strip()
        if text:
            turns.append((role, text))

    if not turns:
        return FlatPrompt(text="", images=images, names=names)

    # A lone user turn is sent verbatim; anything richer gets role headers.
    if len(turns) == 1 and turns[0][0] == "user":
        return FlatPrompt(text=turns[0][1], images=images, names=names)

    blocks = [f"[{ROLE_LABELS.get(role, role.title())}]\n{text}" for role, text in turns]
    blocks.append(
        "[Instruction]\nContinue the conversation above and reply as the Assistant to the last "
        "User message. Output only the reply."
    )
    return FlatPrompt(text="\n\n".join(blocks), images=images, names=names)
