import re
from collections import defaultdict
from pathlib import PurePosixPath
from urllib.parse import unquote, urlparse


URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
TOPIC_PREFIX_PATTERN = re.compile(r"^\[(?P<topic>[^\[\]]+)\]\s*(?P<title>.*)$")


def normalize_text(text: str) -> str:
    text = (text or "").replace("_", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def sanitize_topic_name(topic: str) -> str:
    topic = normalize_text(topic)
    topic = re.sub(r"[\\/:*?\"<>|#]+", " ", topic)
    topic = re.sub(r"\s+", " ", topic).strip(" .-_")
    return topic[:120] if topic else "General"


def forum_topic_short_name(topic: str) -> str:
    """
    Short label for forum thread + captions: [Advance/Number System] -> Advance
    (matches Natking-style forum names like 'Advance', 'Arithmetic'.)
    """
    t = sanitize_topic_name(topic)
    if not t:
        return "General"
    if "/" in t:
        t = t.split("/", 1)[0].strip()
    return sanitize_topic_name(t) if t else "General"


def title_from_url(url: str) -> str:
    parsed = urlparse(url)
    candidate = unquote(PurePosixPath(parsed.path).name)
    candidate = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", candidate)
    candidate = re.sub(r"[-_]+", " ", candidate)
    candidate = normalize_text(candidate)
    return candidate or "Untitled"


def split_topic_and_title(text: str):
    text = normalize_text(text)
    if not text:
        return "General", "Untitled"

    match = TOPIC_PREFIX_PATTERN.match(text)
    if match:
        topic = sanitize_topic_name(match.group("topic"))
        title = normalize_text(match.group("title")) or topic
        return topic, title

    for divider in ("topic -", "topic:", "topic =>", "topic="):
        if divider in text.lower():
            idx = text.lower().find(divider)
            suffix = text[idx + len(divider):].strip()
            if suffix:
                return sanitize_topic_name(suffix), text

    return "General", text


def parse_upload_entries(lines):
    entries = []
    clean_lines = [normalize_text(line) for line in lines if normalize_text(line)]
    index = 0

    while index < len(clean_lines):
        line = clean_lines[index]
        url_match = URL_PATTERN.search(line)
        if not url_match:
            index += 1
            continue

        url = url_match.group(0).strip()
        inline_title = normalize_text(line.replace(url, "").strip(" -:|"))
        title_line = inline_title

        # Title on line above URL (common: "[Arithmetic] Class 1" then URL on next line)
        if not title_line and index > 0:
            prev_line = clean_lines[index - 1]
            if not URL_PATTERN.search(prev_line):
                title_line = prev_line

        if not title_line and index + 1 < len(clean_lines):
            next_line = clean_lines[index + 1]
            if not URL_PATTERN.search(next_line):
                title_line = next_line
                index += 1

        topic, clean_title = split_topic_and_title(title_line or title_from_url(url))
        entries.append(
            {
                "url": url,
                "raw_title": title_line or clean_title,
                "title": clean_title,
                "topic": topic,
            }
        )
        index += 1

    return entries


class TopicUtils:
    def __init__(self):
        self.topic_cache = {}

    def detect_topic(self, text):
        topic, _ = split_topic_and_title(text)
        return topic

    def group_topics(self, topics):
        grouped = defaultdict(list)
        for topic in topics:
            grouped[sanitize_topic_name(topic)].append(topic)
        return dict(grouped)

    def format_caption(self, text):
        return normalize_text(text).title()

    def cache_topic(self, user_id, topics):
        self.topic_cache[user_id] = topics

    def get_cached_topics(self, user_id):
        return self.topic_cache.get(user_id, [])


def build_upload_captions(
    index_num: int,
    title: str,
    batch: str,
    credit: str,
    topic_wise: bool,
    topic: str,
):
    """
    Returns (cc, cc1, ccimg, cczip, ccm, cchtml) for video/pdf/image/zip/audio/html.
    When topic_wise is True, uses Natking / screenshot-style layout: Index, Title, Topic→, Batch→, Credit.
    """
    idx = str(index_num).zfill(3)
    if topic_wise:
        t = sanitize_topic_name(topic)
        cc = (
            f"<b>⬢ Index:</b> {idx}\n\n"
            f"<b>🎬</b> <code>{title}</code>\n\n"
            f"<blockquote><b>⬡ Topic →</b> {t}</blockquote>\n"
            f"<blockquote><b>⬡ Batch →</b> {batch}</blockquote>\n\n"
            f"<b>⬢ Credit»</b> {credit}"
        )
        cc1 = (
            f"<b>⬢ Index:</b> {idx}\n\n"
            f"<b>📑</b> <code>{title}</code>\n\n"
            f"<blockquote><b>⬡ Topic →</b> {t}</blockquote>\n"
            f"<blockquote><b>⬡ Batch →</b> {batch}</blockquote>\n\n"
            f"<b>⬢ Credit»</b> {credit}"
        )
        ccimg = (
            f"<b>⬢ Index:</b> {idx}\n\n"
            f"<b>🖼️</b> <code>{title}</code>\n\n"
            f"<blockquote><b>⬡ Topic →</b> {t}</blockquote>\n"
            f"<blockquote><b>⬡ Batch →</b> {batch}</blockquote>\n\n"
            f"<b>⬢ Credit»</b> {credit}"
        )
        cczip = (
            f"<b>⬢ Index:</b> {idx}\n\n"
            f"<b>📁</b> <code>{title}</code>\n\n"
            f"<blockquote><b>⬡ Topic →</b> {t}</blockquote>\n"
            f"<blockquote><b>⬡ Batch →</b> {batch}</blockquote>\n\n"
            f"<b>⬢ Credit»</b> {credit}"
        )
        ccm = (
            f"<b>⬢ Index:</b> {idx}\n\n"
            f"<b>🎵</b> <code>{title}</code>\n\n"
            f"<blockquote><b>⬡ Topic →</b> {t}</blockquote>\n"
            f"<blockquote><b>⬡ Batch →</b> {batch}</blockquote>\n\n"
            f"<b>⬢ Credit»</b> {credit}"
        )
        cchtml = (
            f"<b>⬢ Index:</b> {idx}\n\n"
            f"<b>🌐</b> <code>{title}</code>\n\n"
            f"<blockquote><b>⬡ Topic →</b> {t}</blockquote>\n"
            f"<blockquote><b>⬡ Batch →</b> {batch}</blockquote>\n\n"
            f"<b>⬢ Credit»</b> {credit}"
        )
        return cc, cc1, ccimg, cczip, ccm, cchtml

    cc = (
        f"<b>🏷️ Iɴᴅᴇx ID  :</b> {idx}\n\n"
        f"<b>🎞️  Tɪᴛʟᴇ :</b> {title} \n\n"
        f"<blockquote>📚  𝗕ᴀᴛᴄʜ : {batch}</blockquote>"
        f"\n\n<b>🎓  Uᴘʟᴏᴀᴅ Bʏ : {credit}</b>"
    )
    cc1 = (
        f"<b>🏷️ Iɴᴅᴇx ID :</b> {idx}\n\n"
        f"<b>📑  Tɪᴛʟᴇ :</b> {title} \n\n"
        f"<blockquote>📚  𝗕ᴀᴛᴄʜ : {batch}</blockquote>"
        f"\n\n<b>🎓  Uᴘʟᴏᴀᴅ Bʏ : {credit}</b>"
    )
    ccimg = (
        f"<b>🏷️ Iɴᴅᴇx ID <b>: {idx} \n\n"
        f"<b>🖼️  Tɪᴛʟᴇ</b> : {title} \n\n"
        f"<blockquote>📚  𝗕ᴀᴛᴄʜ : {batch}</blockquote>"
        f"\n\n<b>🎓  Uᴘʟᴏᴀᴅ Bʏ : {credit}</b>"
    )
    cczip = (
        f'[📁]Zip Id : {idx}\n**Zip Title :** `{title} .zip`\n<blockquote><b>Batch Name :</b> {batch}</blockquote>\n\n**Extracted by➤**{credit}\n'
    )
    ccm = (
        f'[🎵]Audio Id : {idx}\n**Audio Title :** `{title} .mp3`\n<blockquote><b>Batch Name :</b> {batch}</blockquote>\n\n**Extracted by➤**{credit}\n'
    )
    cchtml = (
        f'[🌐]Html Id : {idx}\n**Html Title :** `{title} .html`\n<blockquote><b>Batch Name :</b> {batch}</blockquote>\n\n**Extracted by➤**{credit}\n'
    )
    return cc, cc1, ccimg, cczip, ccm, cchtml
