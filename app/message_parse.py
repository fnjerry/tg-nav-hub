"""从 Telegram 频道正文解析「资源名称」与「简介」。"""

from __future__ import annotations

import re

from app.classify import HASHTAG_RE

# 🏵 **OpenClaw** - 个人设备AI助手 🍥 简介：……
_NAME_BLOCK_RE = re.compile(
    r"\*\*([^*]+)\*\*(?:\s*[-–—]\s*([^🍥🎈🗣\n]+?))?(?=\s*🍥|\s*简介[：:]|$)",
    re.UNICODE,
)
_INTRO_RE = re.compile(
    r"简介[：:]\s*(.+?)(?=\s*🎈|\s*🗣|\s*\[【|$)",
    re.DOTALL | re.UNICODE,
)
_HASHTAG_LINE_RE = re.compile(r"^[\s\W]*(?:#[\w\u4e00-\u9fff]+[\s\W]*)+$", re.UNICODE)
_EMOJI_RE = re.compile(
    r"[\U0001F300-\U0001F9FF\U0001FA00-\U0001FAFF\U00002600-\U000027BF]+",
    re.UNICODE,
)


def _clean_text(s: str) -> str:
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
    s = re.sub(r"[*_`]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _line_is_hashtag_header(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    if _HASHTAG_LINE_RE.match(s):
        return True
    without_tags = HASHTAG_RE.sub("", s).strip()
    without_tags = _EMOJI_RE.sub("", without_tags).strip()
    return len(without_tags) < 2


def parse_resource_title_desc(text: str) -> tuple[str, str]:
    """
    解析频道常见格式：
    首行 #标签 → 忽略；正文 **资源名** - 副标题 🍥 简介：……
    """
    if not (text or "").strip():
        return "", ""

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    body_lines = [ln for ln in lines if not _line_is_hashtag_header(ln)]
    body = "\n".join(body_lines) if body_lines else text
    flat = re.sub(r"\s+", " ", body.replace("\n", " ")).strip()

    title = ""
    desc = ""

    name_m = _NAME_BLOCK_RE.search(flat)
    if name_m:
        title = name_m.group(1).strip()
        if name_m.group(2):
            sub = _clean_text(name_m.group(2))
            if sub:
                title = f"{title} - {sub}"

    intro_m = _INTRO_RE.search(flat)
    if intro_m:
        desc = _clean_text(intro_m.group(1))

    if title and desc:
        return title[:200], desc[:500]

    # 仅有简介、无加粗名
    if intro_m and not title:
        before = flat[: intro_m.start()]
        before = _clean_text(_EMOJI_RE.sub(" ", before))
        if before and len(before) < 120:
            title = before
        return (title[:200] if title else ""), desc[:500]

    # 回退：首行非标签作标题，其余作简介
    if body_lines:
        title = _clean_text(body_lines[0])[:200]
        if len(body_lines) > 1:
            desc = _clean_text(" ".join(body_lines[1:]))[:500]
        return title, desc

    return "", ""
