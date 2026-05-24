from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


def summarize_article(text):

    # 長すぎる記事対策（重要）
    text = text[:8000]

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": """
あなたは金融アナリストです。

以下の記事について：

・何が起きたか
・金融政策への影響
・マーケットへの影響

を簡潔に日本語で要約してください。
"""
            },
            {
                "role": "user",
                "content": text
            }
        ]
    )

    return response.choices[0].message.content