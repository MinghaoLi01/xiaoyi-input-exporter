"""Extract user queries from public Huawei Xiaoyi conversation share pages."""
from __future__ import annotations

import json
import re
from urllib.parse import urlsplit

import requests
from bs4 import BeautifulSoup

MAX_HTML_BYTES = 8 * 1024 * 1024
MAX_URLS = 20
ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{4,128}$")


class ExtractionError(Exception):
    """A user-visible extraction error."""


def validate_share_url(raw_url: str) -> tuple[str, str]:
    """Only permit HTTPS requests to Xiaoyi's exact share-page host."""
    url = raw_url.strip()
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ExtractionError("链接格式不正确。") from exc
    if (parsed.scheme != "https" or host != "xiaoyi.huawei.com"
            or parsed.username or parsed.password or port not in (None, 443)):
        raise ExtractionError("仅支持 https://xiaoyi.huawei.com/s/ 开头的分享链接。")
    if parsed.query or parsed.fragment:
        raise ExtractionError("链接不应包含查询参数或片段。")
    parts = parsed.path.split("/")
    if len(parts) != 3 or parts[1] != "s" or not ID_PATTERN.fullmatch(parts[2]):
        raise ExtractionError("分享链接路径格式不正确，应为 /s/分享ID。")
    share_id = parts[2]
    return f"https://xiaoyi.huawei.com/s/{share_id}", share_id


def parse_input_urls(multiline: str) -> list[tuple[str, str]]:
    """Accept newline-separated URLs, retain order, remove duplicate URLs."""
    lines = [line.strip() for line in multiline.splitlines() if line.strip()]
    if not lines:
        raise ExtractionError("请至少输入一条分享链接。")
    if len(lines) > MAX_URLS:
        raise ExtractionError(f"一次最多处理 {MAX_URLS} 条链接。")
    unique = {}
    for number, line in enumerate(lines, 1):
        try:
            url, share_id = validate_share_url(line)
        except ExtractionError as exc:
            raise ExtractionError(f"第 {number} 行：{exc}") from exc
        unique.setdefault(url, share_id)
    return list(unique.items())


def _record_lists(data: object):
    """Find arrays under 'content' that contain objects with a 'query' key."""
    if isinstance(data, dict):
        records = data.get("content")
        if isinstance(records, list) and any(
            isinstance(r, dict) and isinstance(r.get("query"), str)
            for r in records
        ):
            yield records
        for child in data.values():
            yield from _record_lists(child)
    elif isinstance(data, list):
        for child in data:
            yield from _record_lists(child)


def extract_queries_from_html(html: str) -> list[str]:
    """Only parse JSON embedded in script tags; preserve question order/duplicates."""
    soup = BeautifulSoup(html, "html.parser")
    found: list[str] = []
    matched = False
    for script in soup.find_all("script"):
        raw = (script.string or script.get_text() or "").strip()
        if '"query"' not in raw:
            continue
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            continue
        for records in _record_lists(data):
            matched = True
            for record in records:
                if not isinstance(record, dict):
                    continue
                query = record.get("query")
                if isinstance(query, str):
                    # Each original user input becomes exactly one TXT line.
                    normalized = " ".join(query.split())
                    if normalized:
                        found.append(normalized)
    if not matched:
        raise ExtractionError("页面中没有找到包含 query 字段的聊天 JSON，可能页面结构已变化。")
    if not found:
        raise ExtractionError("找到聊天数据，但没有非空的用户输入。")
    return found


def fetch_queries(url: str) -> list[str]:
    safe_url, _ = validate_share_url(url)
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    try:
        # Never follow redirects to other hosts (SSRF avoidance).
        with requests.get(safe_url, headers=headers, timeout=(8, 20),
                          allow_redirects=False, stream=True) as response:
            if 300 <= response.status_code < 400:
                raise ExtractionError("服务器返回重定向，已为安全起见停止请求。")
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()
            if "text/html" not in content_type:
                raise ExtractionError("服务器未返回 HTML 页面。")
            chunks = []
            total = 0
            for chunk in response.iter_content(chunk_size=65536):
                total += len(chunk)
                if total > MAX_HTML_BYTES:
                    raise ExtractionError("页面超过 8 MB，已停止读取。")
                chunks.append(chunk)
            response.encoding = response.encoding or "utf-8"
            html = b"".join(chunks).decode(response.encoding, errors="replace")
    except requests.RequestException as exc:
        raise ExtractionError(f"请求失败：{type(exc).__name__}，请检查链接是否公开可访问。") from exc
    return extract_queries_from_html(html)


def queries_to_txt(queries: list[str]) -> bytes:
    return ("\n".join(queries) + "\n").encode("utf-8-sig")
