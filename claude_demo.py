# -*- coding: utf-8 -*-
"""
claude_demo.py - Claude连接检测 + 演示
用法: python claude_demo.py
"""
import urllib.request, json, sys, time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API = "http://127.0.0.1:15721/v1/messages"
HEADERS = {
    "x-api-key": "PROXY_MANAGED",
    "anthropic-version": "2023-06-01",
    "Content-Type": "application/json"
}

def call(prompt, max_tokens=256, timeout=30):
    body = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
        "thinking": {"type": "disabled"}
    }).encode("utf-8")

    req = urllib.request.Request(API, data=body, headers=HEADERS)
    resp = urllib.request.urlopen(req, timeout=timeout)
    data = json.loads(resp.read())

    text_parts = []
    for item in data.get("content", []):
        if item.get("type") == "text":
            text_parts.append(item["text"])
    return "".join(text_parts), data.get("model", "?")

# ─── 检测 ───
print("=" * 50)
print("  Claude 连接检测")
print("=" * 50)

print("\n[1] 检测服务端口...", end=" ")
try:
    t0 = time.time()
    result, model = call("回复OK即可", max_tokens=20, timeout=15)
    elapsed = time.time() - t0
    print(f"✅ {elapsed:.1f}s")
    print(f"    模型: {model}")
    print(f"    回复: {result.strip()}")
except urllib.error.URLError as e:
    print(f"❌ 连接失败: {e.reason}")
    print("\n请检查 cc-switch 是否运行在 127.0.0.1:15721")
    sys.exit(1)
except Exception as e:
    print(f"❌ 错误: {e}")
    sys.exit(1)

# ─── 演示 ───
print("\n[2] 演示: 业绩数据分析...", end=" ")
try:
    prompt = (
        "以下是靓典美容店2026/4/29-5/27的业绩数据："
        "40单共76005元，日均约2714元。"
        "最高5月13日10单22000元，最低5月1日1单500元。"
        "主要客户：珍珍体雕、胡珍珍、小敏。"
        "请用中文简要总结（3句话内）。"
    )
    result, _ = call(prompt, max_tokens=256, timeout=60)
    print("✅")
    print(f"\n{result.strip()}")
except Exception as e:
    print(f"❌ {e}")

print("\n" + "=" * 50)
print("  Claude 可用，可以集成到记账脚本中")
print("=" * 50)
