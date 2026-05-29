"""微信消息抓取 v4 - 智能查找消息列表
用法: python wechat_scrape.py [输出文件] [最大分钟数]
"""
import uiautomation as auto
import time, sys, threading
import tkinter as tk

out = sys.argv[1] if len(sys.argv) > 1 else "wechat_output.txt"
max_minutes = int(sys.argv[2]) if len(sys.argv) > 2 else 10

state = {"paused": False, "count": 0, "running": True}

def build_panel():
    root = tk.Tk()
    root.title("爬取 - 空格暂停")
    root.geometry("240x90")
    root.attributes("-topmost", True)
    label = tk.Label(root, text="运行中  [空格]暂停", font=("微软雅黑", 10))
    label.pack(pady=15)
    def toggle(e=None):
        state["paused"] = not state["paused"]
        label.config(text=f"{'已暂停' if state['paused'] else '运行中'} ({state['count']}条)  [空格]")
    root.bind("<space>", toggle)
    def update():
        if state["running"]:
            label.config(text=f"{'已暂停' if state['paused'] else '运行中'} ({state['count']}条)  [空格]")
            root.after(500, update)
        else:
            label.config(text=f"完成! {state['count']}条")
    root.after(500, update)
    root.mainloop()

threading.Thread(target=build_panel, daemon=True).start()

# ── 查找消息列表（多策略）──
def find_msg_list(window):
    # 策略1：ListControl Name="消息"
    ml = window.ListControl(Name="消息")
    try:
        if ml.Exists(0, 0) and len(ml.GetChildren()) > 0:
            return ml
    except:
        pass
    # 策略2：遍历所有ListControl找最大的
    best, best_n = None, 0
    def walk(ctrl, d=0):
        nonlocal best, best_n
        if d > 5: return
        try:
            if "List" in ctrl.ControlTypeName:
                n = len(ctrl.GetChildren())
                if n > best_n:
                    best, best_n = ctrl, n
        except:
            pass
        for c in ctrl.GetChildren():
            walk(c, d+1)
    walk(window)
    return best

# ── 主循环 ──
window = auto.WindowControl(Name="微信")
window.SetActive()
time.sleep(1)
msg_list = find_msg_list(window)

if not msg_list:
    print("找不到消息列表！请确认群聊窗口已打开并显示消息。")
    state["running"] = False
else:
    print(f"找到消息列表: {len(msg_list.GetChildren())} 项")
    msg_list.Click()
    time.sleep(0.3)

seen = set()
all_msgs = []
no_new = 0
deadline = time.time() + max_minutes * 60

while time.time() < deadline and state["running"] and msg_list:
    while state["paused"] and state["running"]:
        time.sleep(0.3)

    items = msg_list.GetChildren()
    new = 0
    for item in items:
        text = item.Name.strip()
        if text and text not in seen:
            seen.add(text)
            all_msgs.append(text)
            new += 1
    state["count"] = len(all_msgs)

    if new:
        no_new = 0; print("+", end="", flush=True); time.sleep(1.2)
    else:
        no_new += 1; print(".", end="", flush=True)
        time.sleep(0.15 if no_new > 3 else 0.4)

    if no_new >= 25:
        print("\n到底了"); break

    if not state["paused"]:
        msg_list.WheelUp(200)

state["running"] = False
time.sleep(1)

if msg_list:
    print(f"\n共 {len(all_msgs)} 条 → {out}")
    with open(out, "w", encoding="utf-8") as f:
        for msg in reversed(all_msgs):
            f.write(msg + "\n\n")
