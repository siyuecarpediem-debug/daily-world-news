# 🌍 每日国际新闻采集

自动从多个国际新闻源抓取最新资讯，由 GitHub Actions 每天定时运行。

## 新闻来源

| 来源 | RSS |
|------|-----|
| BBC World | feeds.bbci.co.uk/news/world/rss.xml |
| The Guardian | theguardian.com/world/rss |
| Al Jazeera | aljazeera.com/xml/rss/all.xml |
| NHK World | nhk.or.jp/nhkworld/en/news/rss/ |

## 自动运行

- **频率**: 每天北京时间 8:00
- **输出**: `output/` 目录下 JSON + Markdown

## 本地测试

```bash
pip install -r requirements.txt
python fetch_news.py
```
