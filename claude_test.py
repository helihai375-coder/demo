# -*- coding: utf-8 -*-
"""claude_test.py - Claude连通性测试"""
import urllib.request, json, sys, time
sys.stdout.reconfigure(encoding="utf-8")

try:
    t0 = time.time()
    body = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 20,
        "messages": [{"role": "user", "content": "回OK"}],
        "thinking": {"type": "disabled"}
    }).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:15721/v1/messages",
        data=body,
        headers={"x-api-key": "PROXY_MANAGED", "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
    )
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read())
    text = "".join(i["text"] for i in data.get("content", []) if i.get("type") == "text")
    elapsed = (time.time() - t0) * 1000

    ok = "OK" in text.upper() or "好" in text
    print(f"{'✅' if ok else '⚠'} 连通  {elapsed:.0f}ms  模型: {data.get('model','?')}  回复: {text.strip()[:40]}")

except urllib.error.URLError as e:
    print(f"❌ 无法连接 127.0.0.1:15721 ({e.reason})")
    sys.exit(1)
except Exception as e:
    print(f"❌ 错误: {e}")
    sys.exit(1)
