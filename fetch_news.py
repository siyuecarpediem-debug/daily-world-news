"""
每日国际新闻爬取脚本 (纯标准库，零依赖)
从多个 RSS 源抓取国际新闻，输出 JSON + Markdown
"""
import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from html import unescape
from urllib.request import Request, urlopen
from urllib.error import URLError

# ========== 配置 ==========
RSS_FEEDS = [
    {
        "name": "BBC World",
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
    },
    {
        "name": "The Guardian - World",
        "url": "https://www.theguardian.com/world/rss",
    },
    {
        "name": "Al Jazeera",
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
    },
    {
        "name": "NHK World",
        "url": "https://www3.nhk.or.jp/nhkworld/en/news/rss/",
    },
    {
        "name": "VOA News",
        "url": "https://www.voanews.com/api/zyzr-zyvyy",
    },
]

OUTPUT_DIR = "output"
BEIJING_TZ = timezone(timedelta(hours=8))
USER_AGENT = "Mozilla/5.0 (compatible; DailyWorldNewsBot/1.0)"


def strip_html(text):
    """去除 HTML 标签"""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    return text.strip()[:300]


def fetch_rss(feed_info):
    """用标准库抓取 RSS XML"""
    print(f"  Fetching {feed_info['name']}...")
    try:
        req = Request(feed_info["url"], headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=15) as resp:
            raw = resp.read()
        root = ET.fromstring(raw)

        # RSS 2.0 或 Atom 两种格式
        articles = []
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        # 尝试 RSS 2.0 格式
        for item in root.findall(".//item"):
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            desc = item.findtext("description", "")
            pub_date = item.findtext("pubDate", "")
            articles.append({
                "title": strip_html(title or ""),
                "link": link or "",
                "summary": strip_html(desc or ""),
                "published": pub_date or "",
                "source": feed_info["name"],
            })

        # 如果没有 RSS item，尝试 Atom 格式
        if not articles:
            for entry in root.findall("atom:entry", ns):
                title = entry.findtext("atom:title", "")
                link_el = entry.find("atom:link")
                link = link_el.get("href", "") if link_el is not None else ""
                summary = entry.findtext("atom:summary", "")
                updated = entry.findtext("atom:updated", "")
                articles.append({
                    "title": strip_html(title or ""),
                    "link": link or "",
                    "summary": strip_html(summary or ""),
                    "published": updated or "",
                    "source": feed_info["name"],
                })

        print(f"    ✓ Got {len(articles)} articles")
        return articles

    except URLError as e:
        print(f"    ✗ Network error: {e}")
        return []
    except ET.ParseError as e:
        print(f"    ✗ XML parse error: {e}")
        return []
    except Exception as e:
        print(f"    ✗ Unexpected error: {e}")
        return []


def main():
    print("=" * 55)
    print(f"  每日国际新闻采集 - {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M')}")
    print("=" * 55)

    # 抓取所有源
    all_articles = []
    for feed_info in RSS_FEEDS:
        articles = fetch_rss(feed_info)
        all_articles.extend(articles)

    # 去重（按 title 前 80 字符）
    seen = set()
    unique = []
    for a in all_articles:
        key = a["title"][:80] if a["title"] else a.get("link", "")
        if key not in seen:
            seen.add(key)
            unique.append(a)

    print(f"\n总计: {len(unique)} 条（去重后，原始 {len(all_articles)} 条）")

    # 保存为 JSON
    today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    json_path = os.path.join(OUTPUT_DIR, f"news_{today}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)
    print(f"JSON saved: {json_path}")

    # 生成 Markdown
    md_path = os.path.join(OUTPUT_DIR, f"news_{today}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 每日国际新闻 - {today}\n\n")
        f.write(f"共 {len(unique)} 条 | 采集于 {datetime.now(BEIJING_TZ).strftime('%H:%M')} (北京时间)\n\n---\n\n")

        for i, a in enumerate(unique[:30], 1):
            f.write(f"### {i}. {a['title']}\n\n")
            f.write(f"- 来源: {a['source']}\n")
            f.write(f"- 时间: {a['published']}\n")
            f.write(f"- 摘要: {a['summary'][:200]}\n")
            f.write(f"- [阅读全文]({a['link']})\n\n")

        f.write(f"\n> 完整数据: [{json_path}]({json_path})\n")

    print(f"Markdown saved: {md_path}")
    print("=" * 55)


if __name__ == "__main__":
    main()
