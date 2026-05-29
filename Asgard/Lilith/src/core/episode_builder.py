import re
from datetime import datetime, timezone
from typing import List

from src.core.memory.legacy_adapter import Episode

_TAG_RULES = {
    "huggingface.co": ["huggingface", "modelos"],
    "news.ycombinator.com": ["hn", "news"],
    "github.com": ["github", "code"],
    "arxiv.org": ["arxiv", "research"],
    "reddit.com": ["reddit"],
    "stackoverflow.com": ["stackoverflow", "code"],
}


def infer_tags(url: str = "", summary: str = "") -> List[str]:
    tags: List[str] = []
    for domain, dtags in _TAG_RULES.items():
        if domain in (url or ""):
            tags.extend(dtags)
    lower = (summary or "").lower()
    if "error" in lower or "falló" in lower or "failed" in lower:
        tags.append("error")
    if "build" in lower:
        tags.append("build")
    if "deploy" in lower:
        tags.append("deploy")
    return list(set(tags))


def infer_project_id(channel_id: str = "", channel_name: str = "") -> str:
    name = (channel_name or channel_id or "general").strip().lower()
    name = re.sub(r"[^a-z0-9\-_]", "-", name)
    return name[:40] or "general"


def build_episode(
    summary: str,
    outcome: str,
    source: str,
    channel_id: str = "",
    channel_name: str = "",
    url: str = "",
    message_id: str = "",
    extra_tags: List[str] = [],
) -> Episode:
    tags = infer_tags(url, summary)
    for t in extra_tags:
        if t and t not in tags:
            tags.append(t)
    return Episode(
        timestamp=datetime.now(timezone.utc).isoformat(),
        summary=summary[:500],
        project_id=infer_project_id(channel_id, channel_name),
        outcome=outcome,
        tags=tags,
        source=source,
        channel_id=channel_id or None,
        message_id=message_id or None,
        url=url or None,
    )
