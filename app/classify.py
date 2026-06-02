"""根据消息中的 # 标签智能归类；无 # 时再按域名推断。"""

from __future__ import annotations

import re
from urllib.parse import urlparse

DEFAULT_CATEGORY = "未分类"

# 话题标签：# 后紧跟的字符（与 sync 抽取规则一致）
HASHTAG_RE = re.compile(r"#([\w\u4e00-\u9fff]{1,48})")

# 规范类目 → 同义词（# 去掉后与之匹配）。列表顺序 = 优先级（越靠前越具体）
TAG_BUCKETS: list[tuple[str, frozenset[str]]] = [
    (
        "AI",
        frozenset(
            {
                "ai",
                "gpt",
                "chatgpt",
                "openai",
                "claude",
                "copilot",
                "llm",
                "大模型",
                "机器学习",
                "深度学习",
                "神经网络",
                "人工智能",
                "aigc",
                "prompt",
                "提示词",
                "stable_diffusion",
                "stablediffusion",
                "midjourney",
                "mj",
                "sd",
                "ai工具",
                "ai神器",
            }
        ),
    ),
    (
        "安全",
        frozenset(
            {
                "安全",
                "security",
                "渗透",
                "黑客",
                "隐私",
                "加密",
                "漏洞",
                "ctf",
                "网络安全",
                "vpn",
                "机场",
                "节点",
                "科学上网",
                "翻墙",
                "代理",
            }
        ),
    ),
    (
        "学术",
        frozenset({"论文", "学术", "科研", "期刊", "sci", "study", "research", "arxiv"}),
    ),
    (
        "游戏",
        frozenset(
            {
                "游戏",
                "game",
                "gaming",
                "steam",
                "手游",
                "switch",
                "ps5",
                "主机",
                "电竞",
                "单机",
                "网游",
            }
        ),
    ),
    (
        "影音",
        frozenset(
            {
                "视频",
                "影视",
                "电影",
                "剧集",
                "纪录片",
                "youtube",
                "b站",
                "哔哩",
                "动漫",
                "番剧",
                "字幕",
                "综艺",
                "直播",
                "streaming",
                "追剧",
            }
        ),
    ),
    (
        "音乐",
        frozenset({"音乐", "music", "spotify", "歌曲", "音频", "播客", "podcast"}),
    ),
    (
        "设计",
        frozenset(
            {
                "设计",
                "design",
                "ui",
                "ux",
                "视觉",
                "交互",
                "动效",
                "插画",
                "海报",
                "banner",
                "配色",
                "字体",
                "排版",
                "icon",
                "图标",
                "品牌",
                "logo",
                "figma",
                "sketch",
                "素材",
            }
        ),
    ),
    (
        "产品",
        frozenset(
            {
                "产品",
                "pm",
                "prd",
                "产品经理",
                "需求",
                "原型",
                "增长",
                "运营",
                "数据分析",
                "埋点",
                "复盘",
                "私域",
                "电商",
            }
        ),
    ),
    (
        "开发",
        frozenset(
            {
                "开发",
                "dev",
                "developer",
                "编程",
                "程序员",
                "代码",
                "coder",
                "coding",
                "前端",
                "后端",
                "全栈",
                "客户端",
                "服务端",
                "开源",
                "opensource",
                "github",
                "gitlab",
                "npm",
                "pypi",
                "docker",
                "kubernetes",
                "k8s",
                "运维",
                "devops",
                "sre",
                "cloud",
                "aws",
                "gcp",
                "azure",
                "数据库",
                "sql",
                "nosql",
                "redis",
                "kafka",
                "微服务",
                "rpc",
                "graphql",
                "rest",
                "api",
                "sdk",
                "python",
                "javascript",
                "typescript",
                "java",
                "kotlin",
                "swift",
                "go",
                "golang",
                "rust",
                "cpp",
                "c语言",
                "csharp",
                "php",
                "ruby",
                "react",
                "vue",
                "angular",
                "nextjs",
                "nuxt",
                "nodejs",
                "node",
                "electron",
                "flutter",
                "rn",
                "reactnative",
                "android",
                "安卓",
                "ios",
                "小程序",
                "web",
                "wasm",
                "算法",
                "leetcode",
                "教程",
                "技术",
                "it",
            }
        ),
    ),
    (
        "工具",
        frozenset(
            {
                "工具",
                "tools",
                "tool",
                "神器",
                "利器",
                "插件",
                "扩展",
                "chrome",
                "浏览器",
                "油猴",
                "tampermonkey",
                "脚本",
                "自动化",
                "rss",
                "订阅",
                "软件",
                "app",
                "应用",
                "破解",
                "绿色",
                "便携",
            }
        ),
    ),
    (
        "效率",
        frozenset(
            {
                "效率",
                "生产力",
                "笔记",
                "notion",
                "备忘录",
                "todo",
                "清单",
                "日历",
                "番茄",
                "专注",
                "workflow",
                "协作",
                "办公",
            }
        ),
    ),
    (
        "资讯",
        frozenset(
            {
                "资讯",
                "新闻",
                "news",
                "日报",
                "周报",
                "周刊",
                "月报",
                "突发",
                "头条",
                "媒体",
                "行业",
                "趋势",
                "宏观",
                "政策",
                "快讯",
                "吃瓜",
            }
        ),
    ),
    (
        "阅读",
        frozenset(
            {
                "阅读",
                "读书",
                "书单",
                "文章",
                "blog",
                "博客",
                "专栏",
                "newsletter",
                "小说",
                "漫画",
                "电子书",
                "杂志",
            }
        ),
    ),
    (
        "资源",
        frozenset(
            {
                "资源",
                "合集",
                "汇总",
                "清单",
                "导航",
                "bookmark",
                "书签",
                "模板",
                "字体包",
                "图库",
                "壁纸",
                "pdf",
                "免费",
                "白嫖",
                "福利",
                "羊毛",
                "薅羊毛",
                "优惠",
                "折扣",
                "限免",
                "分享",
                "推荐",
                "精选",
                "宝藏",
            }
        ),
    ),
    (
        "社区",
        frozenset(
            {
                "社区",
                "论坛",
                "讨论",
                "reddit",
                "discord",
                "slack",
                "电报",
                "tg",
                "telegram",
                "群组",
                "频道",
            }
        ),
    ),
    (
        "职场",
        frozenset(
            {
                "职场",
                "求职",
                "面试",
                "简历",
                "远程",
                "freelance",
                "副业",
                "兼职",
                "薪酬",
                "跳槽",
                "实习",
                "考公",
            }
        ),
    ),
]

_BUCKET_INDEX: dict[str, int] = {name: i for i, (name, _) in enumerate(TAG_BUCKETS)}

# 去掉后不参与「原样作分类名」的泛化词
_GENERIC_TAGS: frozenset[str] = frozenset(
    {
        "推荐",
        "分享",
        "精选",
        "合集",
        "资源",
        "频道",
        "电报",
        "tg",
        "telegram",
        "每日",
        "今日",
        "update",
        "link",
        "links",
        "url",
    }
)

DOMAIN_RULES: list[tuple[str, str]] = [
    ("github.com", "开发"),
    ("gitlab.com", "开发"),
    ("gist.github.com", "开发"),
    ("npmjs.com", "开发"),
    ("pypi.org", "开发"),
    ("stackoverflow.com", "开发"),
    ("youtube.com", "影音"),
    ("youtu.be", "影音"),
    ("bilibili.com", "影音"),
    ("vimeo.com", "影音"),
    ("twitter.com", "资讯"),
    ("x.com", "资讯"),
    ("notion.so", "效率"),
    ("figma.com", "设计"),
    ("dribbble.com", "设计"),
    ("behance.net", "设计"),
    ("medium.com", "阅读"),
    ("reddit.com", "社区"),
    ("producthunt.com", "产品"),
    ("google.com", "搜索"),
    ("wikipedia.org", "百科"),
    ("arxiv.org", "学术"),
    ("openai.com", "AI"),
    ("anthropic.com", "AI"),
]


def extract_hashtags(text: str) -> list[str]:
    """按出现顺序提取 # 标签（去重，保留原始大小写/中文）。"""
    if not text:
        return []
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in HASHTAG_RE.findall(text):
        key = raw.lower() if raw.isascii() else raw
        if key in seen:
            continue
        seen.add(key)
        ordered.append(raw.strip())
    return ordered


def tags_to_csv(tags: list[str]) -> str:
    return ",".join(tags)


def _normalize_tag(raw: str) -> str:
    t = raw.strip().lstrip("#").strip()
    return t.lower() if t.isascii() else t


def _tag_segments(norm: str) -> list[str]:
    """拆分复合标签：#前端_工具 → 前端、工具。"""
    if not norm:
        return []
    parts = [norm]
    for sep in ("_", "-", "/", "·", " "):
        if sep in norm:
            parts = [p for chunk in parts for p in chunk.split(sep) if p]
    return list(dict.fromkeys(parts))


def _syn_matches(norm: str, sn_cmp: str) -> bool:
    if norm == sn_cmp:
        return True
    if not sn_cmp:
        return False

    if not sn_cmp.isascii():
        return len(sn_cmp) >= 2 and sn_cmp in norm

    sn_l = sn_cmp.lower()

    if not norm.isascii():
        nl = norm.lower()
        if len(sn_l) <= 2:
            return nl.startswith(sn_l)
        return sn_l in nl

    n = norm.lower()
    if len(sn_l) >= 4 and sn_l in n:
        return True
    if len(sn_l) == 3 and n.startswith(sn_l):
        return True
    return False


def _match_tag_to_bucket(norm: str) -> str | None:
    if not norm:
        return None

    for cat, syns in TAG_BUCKETS:
        for s in sorted(syns, key=len, reverse=True):
            sn = s.strip().lower() if s.isascii() else s.strip()
            if not sn:
                continue
            sn_cmp = sn.lower() if norm.isascii() and sn.isascii() else sn
            if _syn_matches(norm, sn_cmp):
                return cat
    return None


def _beautify_hashtag(raw: str) -> str:
    """无规则命中时，用 # 后的文字作为展示分类名。"""
    t = raw.strip().lstrip("#").strip()
    t = re.sub(r"[_\-/·]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > 40:
        t = t[:40]
    return t or DEFAULT_CATEGORY


def _is_generic_tag(norm: str) -> bool:
    return norm in _GENERIC_TAGS or norm.lower() in _GENERIC_TAGS


def category_from_hashtags(tags_csv: str) -> str | None:
    """
    智能归类（仅基于 #）：
    1. 遍历所有标签及其拆分片段，映射到规范类目（多标签时取优先级最高、且更靠前的标签）；
    2. 若无规则命中，用第一个「非泛化」标签原文作分类名；
    3. 若全是泛化词，用第一个标签原文。
    """
    parts = [x.strip() for x in (tags_csv or "").split(",") if x.strip()]
    if not parts:
        return None

    hits: list[tuple[int, int, str]] = []  # (bucket_priority, tag_order, category)

    for tag_order, raw in enumerate(parts):
        norm = _normalize_tag(raw)
        for seg in _tag_segments(norm):
            cat = _match_tag_to_bucket(seg)
            if cat:
                hits.append((_BUCKET_INDEX[cat], tag_order, cat))

    if hits:
        hits.sort(key=lambda x: (x[0], x[1]))
        return hits[0][2]

    for raw in parts:
        norm = _normalize_tag(raw)
        if norm and not _is_generic_tag(norm):
            return _beautify_hashtag(raw)

    return _beautify_hashtag(parts[0])


def infer_category(url: str, tags_csv: str, title: str = "") -> str:
    """有 # 时只根据标签归类；无 # 时才看域名。"""
    if tags_csv and tags_csv.strip():
        cat = category_from_hashtags(tags_csv)
        if cat:
            return cat

    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        host = ""
    if host.startswith("www."):
        host = host[4:]

    for needle, cat in DOMAIN_RULES:
        if needle in host:
            return cat

    _ = title
    return DEFAULT_CATEGORY
