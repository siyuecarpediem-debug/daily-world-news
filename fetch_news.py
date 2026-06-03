"""
每日新闻爬取 — 聚焦中美俄 (纯标准库，零依赖)
RSS 源全部来自权威媒体，关键词精准标记国家归属
"""
import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from html import unescape
from urllib.request import Request, urlopen
from urllib.error import URLError

# ============================================================
# RSS 源 — 全部聚焦中美俄，权威媒体
# ============================================================
RSS_FEEDS = [
    # ===== 美国 =====
    {
        "name": "BBC US & Canada",
        "url": "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml",
        "category": "国际新闻",
        "focus_country": "美国",
    },
    {
        "name": "The Guardian US",
        "url": "https://www.theguardian.com/us-news/rss",
        "category": "国际新闻",
        "focus_country": "美国",
    },
    # ===== 中国 =====
    {
        "name": "BBC China",
        "url": "https://feeds.bbci.co.uk/news/world/asia/china/rss.xml",
        "category": "国际新闻",
        "focus_country": "中国",
    },
    {
        "name": "SCMP China",
        "url": "https://www.scmp.com/rss/4/feed",
        "category": "国际新闻",
        "focus_country": "中国",
    },
    # ===== 俄罗斯 =====
    {
        "name": "BBC Europe",
        "url": "https://feeds.bbci.co.uk/news/world/europe/rss.xml",
        "category": "国际新闻",
        "focus_country": "俄罗斯",
    },
    {
        "name": "The Moscow Times",
        "url": "https://www.themoscowtimes.com/rss/news",
        "category": "国际新闻",
        "focus_country": "俄罗斯",
    },
    # ===== 综合国际（覆盖中美俄交叉议题）=====
    {
        "name": "BBC World",
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "category": "国际新闻",
        "focus_country": "中美俄综合",
    },
    {
        "name": "The Guardian World",
        "url": "https://www.theguardian.com/world/rss",
        "category": "国际新闻",
        "focus_country": "中美俄综合",
    },
    {
        "name": "Al Jazeera",
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
        "category": "国际新闻",
        "focus_country": "中美俄综合",
    },
]

OUTPUT_DIR = "output"
BEIJING_TZ = timezone(timedelta(hours=8))
USER_AGENT = "Mozilla/5.0 (compatible; DailyWorldNewsBot/1.0)"

# ============================================================
# 国家关键词 — 用于自动标记 focus 字段
# ============================================================
COUNTRY_KEYWORDS = {
    "美国": [
        # 英文
        "united states", "america", "u.s.", "us ", "usa", "washington",
        "white house", "pentagon", "congress", "senate", "trump",
        "biden", "republican", "democrat", "federal", "capitol",
        "new york", "california", "texas", "florida", "pentagon",
        "state department", "cia", "fbi", "homeland", "american",
        # 中文
        "美国", "华盛顿", "白宫", "五角大楼", "国会", "特朗普",
        "拜登", "共和党", "民主党", "纽约", "加州",
    ],
    "中国": [
        # 英文
        "china", "chinese", "beijing", "shanghai", "hong kong",
        "taiwan", "taipei", "xi jinping", "ccp", "communist party",
        "south china sea", "belt and road", "bri", "tibet", "xinjiang",
        "macau", "guangdong", "shenzhen", "pla", "people's liberation",
        # 中文
        "中国", "北京", "上海", "香港", "台湾", "习近平",
        "中共", "南海", "一带一路", "深圳", "广东",
    ],
    "俄罗斯": [
        # 英文
        "russia", "russian", "moscow", "putin", "kremlin",
        "st petersburg", "siberia", "chechnya", "ruble",
        "fsb", "state duma", "ukraine", "crimea", "donbas",
        "donetsk", "luhansk", "zaporizhzhia", "kyiv",
        "zelensky", "nato", "belarus", "lukashenko",
        # 中文
        "俄罗斯", "莫斯科", "普京", "克宫", "克里姆林宫",
        "乌克兰", "基辅", "北约", "白俄罗斯",
    ],
}


def strip_html(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    return text.strip()[:300]


def detect_focus(title, summary, source_focus):
    """
    根据标题+摘要自动判断新闻聚焦哪个国家。
    若来源已指定 focus_country 且文章也匹配该国关键词 → 确认归属。
    若文章命中多个国家 → 取命中关键词最多的那个。
    若都不命中 → 保留来源的 focus_country（综合类来源则为"国际其他"）。
    """
    text = ((title or "") + " " + (summary or "")).lower()
    scores = {}
    for country, keywords in COUNTRY_KEYWORDS.items():
        cnt = sum(1 for kw in keywords if kw.lower() in text)
        if cnt > 0:
            scores[country] = cnt

    if scores:
        return max(scores, key=scores.get)

    if source_focus in ("美国", "中国", "俄罗斯"):
        return source_focus
    return "国际其他"


def fetch_rss(feed_info):
    """抓取 RSS XML（也支持 JSON API）"""
    print(f"  Fetching {feed_info['name']}...")

    if feed_info.get("api_type") == "csdn_json":
        return []

    try:
        req = Request(feed_info["url"], headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=15) as resp:
            raw = resp.read()
        root = ET.fromstring(raw)

        articles = []
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        source_focus = feed_info.get("focus_country", "国际其他")

        # RSS 2.0
        for item in root.findall(".//item"):
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            desc = item.findtext("description", "")
            pub_date = item.findtext("pubDate", "")
            title_clean = strip_html(title or "")
            summary_clean = strip_html(desc or "")
            focus = detect_focus(title_clean, summary_clean, source_focus)
            articles.append({
                "title": title_clean,
                "link": link or "",
                "summary": summary_clean,
                "published": pub_date or "",
                "source": feed_info["name"],
                "category": feed_info.get("category", "国际新闻"),
                "focus": focus,
            })

        # Atom 备用
        if not articles:
            for entry in root.findall("atom:entry", ns):
                title = entry.findtext("atom:title", "")
                link_el = entry.find("atom:link")
                link = link_el.get("href", "") if link_el is not None else ""
                summary = entry.findtext("atom:summary", "")
                updated = entry.findtext("atom:updated", "")
                title_clean = strip_html(title or "")
                summary_clean = strip_html(summary or "")
                focus = detect_focus(title_clean, summary_clean, source_focus)
                articles.append({
                    "title": title_clean,
                    "link": link or "",
                    "summary": summary_clean,
                    "published": updated or "",
                    "source": feed_info["name"],
                    "category": feed_info.get("category", "国际新闻"),
                    "focus": focus,
                })

        print(f"    [OK] Got {len(articles)} articles")
        return articles

    except URLError as e:
        print(f"    [ERR] Network error: {e}")
        return []
    except ET.ParseError as e:
        print(f"    [ERR] XML parse error: {e}")
        return []
    except Exception as e:
        print(f"    [ERR] Unexpected error: {e}")
        return []


def main():
    print("=" * 60)
    print(f"  中美俄新闻采集 - {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    all_articles = []
    for feed_info in RSS_FEEDS:
        articles = fetch_rss(feed_info)
        all_articles.extend(articles)

    # 去重
    seen = set()
    unique = []
    for a in all_articles:
        key = a["title"][:80] if a["title"] else a.get("link", "")
        if key not in seen:
            seen.add(key)
            unique.append(a)

    # 按聚焦国家排序：中→美→俄→综合→其他
    focus_order = {"中国": 0, "美国": 1, "俄罗斯": 2, "中美俄综合": 3, "国际其他": 4}
    unique.sort(key=lambda a: focus_order.get(a.get("focus", "国际其他"), 5))

    # 统计
    focus_stats = {}
    for a in unique:
        f = a.get("focus", "国际其他")
        focus_stats[f] = focus_stats.get(f, 0) + 1

    print(f"\n总计: {len(unique)} 条（去重后，原始 {len(all_articles)} 条）")
    print("聚焦分布:")
    for k in ("中国", "美国", "俄罗斯", "中美俄综合", "国际其他"):
        if k in focus_stats:
            print(f"  {k}: {focus_stats[k]} 条")

    today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # JSON
    json_path = os.path.join(OUTPUT_DIR, f"news_{today}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)
    print(f"JSON saved: {json_path}")

    # Markdown
    md_path = os.path.join(OUTPUT_DIR, f"news_{today}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 中美俄要闻 - {today}\n\n")
        f.write(f"共 {len(unique)} 条 | 采集于 {datetime.now(BEIJING_TZ).strftime('%H:%M')} (北京时间)\n\n")
        f.write("## 聚焦分布\n\n")
        for k in ("中国", "美国", "俄罗斯", "中美俄综合", "国际其他"):
            if k in focus_stats:
                f.write(f"- {k}: {focus_stats[k]} 条\n")
        f.write("\n---\n\n")

        for i, a in enumerate(unique[:50], 1):
            f.write(f"### {i}. [{a['focus']}] {a['title']}\n\n")
            f.write(f"- 来源: {a['source']}\n")
            f.write(f"- 时间: {a['published']}\n")
            f.write(f"- 摘要: {a['summary'][:200]}\n")
            f.write(f"- [阅读全文]({a['link']})\n\n")

    print(f"Markdown saved: {md_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
