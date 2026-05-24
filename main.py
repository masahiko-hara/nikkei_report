from playwright.sync_api import sync_playwright
from summarizer import summarize_article

from datetime import datetime, timedelta
import os

OUTPUT_DIR = "./docs"

KEYWORDS = [
    "日銀", "植田", "金融政策", "利上げ",
    "国債", "円安", "円高", "インフレ"
]


# =========================
# スコアリング（軽めに調整）
# =========================
def calculate_score(title, text):
    combined = title + text

    title_weight = 3
    text_weight = 1

    score = 0

    for kw in KEYWORDS:
        score += title.count(kw) * title_weight
        score += text.count(kw) * text_weight

    return score


def is_recent_article(date_text):
    try:
        article_date = datetime.fromisoformat(date_text.replace("Z", "+00:00"))
        now = datetime.now(article_date.tzinfo)

        today = now.date()
        yesterday = (now - timedelta(days=1)).date()

        return article_date.date() in [today, yesterday]
    except:
        return False


# =========================
# HTML生成
# =========================
def create_html_report(results):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    today_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{today_str}.html"
    filepath = os.path.join(OUTPUT_DIR, filename)

    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>日銀ニュース {today_str}</title>

        <style>
            body {{
                font-family: sans-serif;
                background: #f5f5f5;
                margin: 40px;
                line-height: 1.6;
            }}

            .card {{
                background: white;
                padding: 20px;
                margin-bottom: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.1);
            }}

            a {{ color: #1a73e8; }}

            .summary h3 {{
                margin-top: 20px;
                border-left: 4px solid #4a90e2;
                padding-left: 8px;
            }}

            .summary p {{
                margin: 6px 0 14px 0;
            }}
        </style>
    </head>

    <body>
        <h1>日銀ニュース {today_str}</h1>
        <p><a href="index.html">← 一覧へ戻る</a></p>
    """

    for r in results:
        summary = summarize_article(r["text"])

        html += f"""
        <div class="card">
            <h2>{r['title']}</h2>
            <p><b>投稿日:</b> {r['published']}</p>
            <p><b>スコア:</b> {r['score']}</p>
            <a href="{r['url']}">記事リンク</a>

            <div class="summary">
                {summary}
            </div>
        </div>
        """

    html += "</body></html>"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    print("日別ページ作成:", filepath)

    update_index(today_str, filename, len(results))


# =========================
# index更新
# =========================
def update_index(date_str, filename, count):
    index_path = os.path.join(OUTPUT_DIR, "index.html")

    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = """
        <html>
        <head>
            <meta charset="utf-8">
            <title>日銀ニュース一覧</title>
        </head>
        <body>
        <h1>日銀ニュース一覧</h1>
        """

    block = f"""
    <div class="card">
        <h2>{date_str}</h2>
        <p>記事数: {count}</p>
        <a href="{filename}">読む</a>
    </div>
    """

    content = content.replace("</body>", block + "</body>")

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("index更新:", index_path)


# =========================
# メイン処理
# =========================
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    search_url = "https://www.nikkei.com/search?keyword=%E6%97%A5%E9%8A%80"
    page.goto(search_url)
    page.wait_for_timeout(5000)

    links = page.locator("a").evaluate_all("""
        elements => elements.map(el => ({
            title: el.innerText,
            href: el.href
        }))
    """)

    article_urls = []
    seen = set()

    for item in links:
        href = item["href"]
        title = item["title"]

        if href and "/article/" in href and title and title.strip():
            if href not in seen:
                article_urls.append({
                    "title": title,
                    "url": href
                })
                seen.add(href)

    results = []
    old_article_found = False

    for article in article_urls:
        if old_article_found:
            break

        page2 = browser.new_page()
        page2.goto(article["url"])
        page2.wait_for_timeout(3000)

        paragraphs = page2.locator("p").all_inner_texts()
        text = "\n".join(paragraphs)

        time_element = page2.locator("time")
        published = ""

        if time_element.count() > 0:
            published = time_element.first.get_attribute("datetime")

        page2.close()

        if not published:
            continue

        if not is_recent_article(published):
            print("古い記事検出 → 終了")
            old_article_found = True
            break

        score = calculate_score(article["title"], text)

        # ⭐ここが重要：緩和
        if score >= 2:
            results.append({
                "title": article["title"],
                "url": article["url"],
                "published": published,
                "score": score,
                "text": text
            })

    # ⭐最低5件は見せる（UX改善）
    results.sort(key=lambda x: x["score"], reverse=True)
    results = results[:5]

    print("===== 記事 =====")
    for r in results:
        print(r["score"], r["title"])

    create_html_report(results)

    input("Enterで終了")
    browser.close()