from playwright.sync_api import sync_playwright
from summarizer import summarize_article

from datetime import datetime, timedelta
import os
import re


OUTPUT_DIR = "./docs"


KEYWORDS = [
    "日銀",
    "植田",
    "金融政策",
    "利上げ",
    "国債",
    "円安",
    "円高",
    "インフレ"
]


def calculate_score(title, text):

    score = 0

    combined = title + text

    for keyword in KEYWORDS:

        score += combined.count(keyword)

    return score


def is_recent_article(date_text):

    try:

        article_date = datetime.fromisoformat(date_text)

        now = datetime.now(article_date.tzinfo)

        today = now.date()

        yesterday = (now - timedelta(days=1)).date()

        return article_date.date() in [today, yesterday]

    except:

        return False


def create_html_report(results):

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    filepath = os.path.join(OUTPUT_DIR, "latest_report.html")

    html = f"""
    <html>

    <head>

        <meta charset="utf-8">

        <title>日銀ニュースレポート</title>

        <style>

            body {{
                font-family: sans-serif;
                background-color: #f5f5f5;
                margin: 40px;
                line-height: 1.8;
            }}

            .card {{
                background: white;
                padding: 20px;
                margin-bottom: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}

            a {{
                color: blue;
            }}

        </style>

    </head>

    <body>

    <h1>日銀ニュースレポート</h1>

    <p>生成日時: {datetime.now()}</p>

    """

    for r in results:

        summary = summarize_article(r["text"])

        html += f"""

        <div class="card">

        <h2>{r['title']}</h2>

        <p><b>投稿日:</b> {r['published']}</p>

        <p><b>スコア:</b> {r['score']}</p>

        <p>
            <a href="{r['url']}">
                記事リンク
            </a>
        </p>

        <h3>要約</h3>

        <p>{summary}</p>

        </div>

        """

    html += """

    </body>

    </html>

    """

    with open(filepath, "w", encoding="utf-8") as f:

        f.write(html)

    print("HTML保存完了")
    print(filepath)


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

    for item in links:

        href = item["href"]
        title = item["title"]

        if "/article/" in href and title.strip():

            article_urls.append({
                "title": title,
                "url": href
            })

    unique_articles = []

    seen = set()

    for article in article_urls:

        if article["url"] not in seen:

            unique_articles.append(article)

            seen.add(article["url"])

    results = []

    old_article_found = False

    for article in unique_articles:

        if old_article_found:

            break

        article_page = browser.new_page()

        article_page.goto(article["url"])

        article_page.wait_for_timeout(3000)

        paragraphs = article_page.locator("p").all_inner_texts()

        article_text = "\n".join(paragraphs)

        time_element = article_page.locator("time")

        published = ""

        if time_element.count() > 0:

            published = time_element.first.get_attribute("datetime")

        if not published:

            article_page.close()

            continue

        if not is_recent_article(published):

            print("一昨日以前の記事なので終了")

            old_article_found = True

            article_page.close()

            break

        score = calculate_score(article["title"], article_text)

        if score >= 5:

            results.append({
                "title": article["title"],
                "url": article["url"],
                "published": published,
                "score": score,
                "text": article_text
            })

        article_page.close()

    results.sort(key=lambda x: x["score"], reverse=True)

    print("===== 選定記事 =====")

    for r in results:

        print("-------------------")

        print("スコア:", r["score"])

        print("投稿日:", r["published"])

        print("タイトル:", r["title"])

        print("URL:", r["url"])

    create_html_report(results)

    input("\nEnterで終了")

    browser.close()