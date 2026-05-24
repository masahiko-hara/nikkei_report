from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def summarize_article(text):

    text = text[:8000]

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": """
あなたは金融アナリストです。

以下の形式で必ず出力してください：

<h3>概要</h3>
<p>記事の内容を簡潔に説明</p>

<h3>金融政策への影響</h3>
<p>日銀の政策・金利・為替への影響</p>

<h3>マーケットへの影響</h3>
<p>株式・債券・為替への影響</p>

短く、読みやすく書いてください。
"""
            },
            {
                "role": "user",
                "content": text
            }
        ]
    )

    return response.choices[0].message.content