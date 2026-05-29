"""claude.py - 通过 cc-switch HTTP 代理调用 Claude/DeepSeek
用法: python claude.py "你的问题"
"""
import urllib.request, json, sys, os

def ask(prompt, model="claude-sonnet-4-20250514", max_tokens=4096):
    body = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
        "thinking": {"type": "disabled"}         # 关闭thinking避免400错误
    }).encode("utf-8")

    req = urllib.request.Request(
        "http://127.0.0.1:15721/v1/messages",
        data=body,
        headers={
            "x-api-key": "PROXY_MANAGED",
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
    )
    resp = urllib.request.urlopen(req, timeout=180)
    data = json.loads(resp.read())
    # 只取text类型的回复
    return "".join(item["text"] for item in data.get("content", []) if item.get("type") == "text")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python claude.py \"你的问题\"")
        sys.exit(1)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(ask(sys.argv[1]))
