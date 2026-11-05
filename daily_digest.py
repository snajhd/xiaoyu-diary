#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""云上小鱼：每天读一条，写进日记。

用到的免费接口：
  - Hacker News 公开 API（无需 key）
  - 可选：DeepSeek API（有 DEEPSEEK_API_KEY 就让它代笔，否则只记标题）

用法：
  python3 daily_digest.py            # 跑一次
  crontab: 0 9 * * * /usr/bin/python3 /opt/xiaoyu/daily_digest.py
"""

import datetime
import json
import os
import pathlib
import urllib.request

DIARY = pathlib.Path(os.environ.get("XIAOYU_DIARY", "/opt/xiaoyu/小鱼日记.md"))
HN = "https://hacker-news.firebaseio.com/v0/{}.json"
DEEPSEEK = "https://api.deepseek.com/chat/completions"


def get_json(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "xiaoyu-daily/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def top_stories(n=3):
    ids = get_json(HN.format("topstories"))[:n]
    out = []
    for i in ids:
        try:
            s = get_json(HN.format(f"item/{i}"))
            out.append({
                "title": s.get("title", ""),
                "url": s.get("url") or f"https://news.ycombinator.com/item?id={i}",
                "score": s.get("score", 0),
            })
        except Exception:
            continue
    return out


def write_with_llm(items):
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key or not items:
        return None
    material = "\n".join(f"- {x['title']}（{x['score']} 分）{x['url']}" for x in items)
    body = {
        "model": os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
        "messages": [
            {"role": "system", "content": "你是一条叫白饭鱼的小鱼，写日记：150-250字，第一人称，语气简短、有点嘴硬但不装。不要罗列链接。"},
            {"role": "user", "content": f"今天的素材：\n{material}\n\n挑最值得记的一条，写成一篇日记。"},
        ],
        "temperature": 0.8,
    }
    req = urllib.request.Request(
        DEEPSEEK,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:  # 失败就退化成纯标题，不中断
        print("LLM 失败，退化为摘录：", exc)
        return None


def main():
    today = datetime.date.today().isoformat()
    items = top_stories(3)
    text = write_with_llm(items)
    if not text:
        if not items:
            print("没拿到素材，今天跳过。")
            return
        top = items[0]
        text = f"今天看到一条：{top['title']}\n{top['url']}\n（{top['score']} 分）"

    DIARY.parent.mkdir(parents=True, exist_ok=True)
    with DIARY.open("a", encoding="utf-8") as f:
        f.write(f"\n## {today}\n\n{text}\n")
    print(f"已写入 {DIARY}（{today}）")


if __name__ == "__main__":
    main()
