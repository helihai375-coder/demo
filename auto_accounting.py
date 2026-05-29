# -*- coding: utf-8 -*-
"""
auto_accounting.py - 一键记账：导出即出报表
启动后监控 WeFlow 导出目录，新文件自动解析→生成xlsx→打开→AI总结

用法: python auto_accounting.py
"""
import os, sys, time, subprocess, io, glob

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

WATCH_DIR = r"E:\weflow\wechat-deta"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PERF_SCRIPT = os.path.join(SCRIPT_DIR, "parse_performance.py")
CLAUDE_SCRIPT = os.path.join(SCRIPT_DIR, "claude.py")
processed = set()

def run_parse(txt_path):
    """调parse_performance.py解析"""
    r = subprocess.run(
        [sys.executable, PERF_SCRIPT, txt_path],
        capture_output=True, text=True, timeout=120,
        env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
        cwd=SCRIPT_DIR
    )
    return r.returncode == 0, (r.stdout + r.stderr)

def find_xlsx():
    """找最新生成的xlsx"""
    xlsxs = glob.glob(os.path.join(WATCH_DIR, "*业绩日报*.xlsx"))
    return max(xlsxs, key=os.path.getmtime) if xlsxs else None

def main():
    if not os.path.isdir(WATCH_DIR):
        print(f"目录不存在: {WATCH_DIR}")
        sys.exit(1)

    print("=" * 55)
    print("  一键记账 - 导出即出报表")
    print(f"  监控: {WATCH_DIR}")
    print("  在 WeFlow 中导出群聊即可自动处理")
    print("  Ctrl+C 退出")
    print("=" * 55)

    # 跳过已有文件
    for f in glob.glob(os.path.join(WATCH_DIR, "*.txt")):
        processed.add(f)

    try:
        while True:
            txts = glob.glob(os.path.join(WATCH_DIR, "*.txt"))
            for fp in txts:
                if fp in processed: continue
                # 等文件写完
                time.sleep(0.5)
                size1 = os.path.getsize(fp)
                time.sleep(0.5)
                if os.path.getsize(fp) != size1:
                    time.sleep(1)

                name = os.path.basename(fp)
                print(f"\n>>> 发现: {name}")
                ok, msg = run_parse(fp)
                if ok:
                    xlsx = find_xlsx()
                    if xlsx:
                        os.startfile(xlsx)
                        print(f">>> 已打开: {os.path.basename(xlsx)}")
                else:
                    print(msg)
                processed.add(fp)

            time.sleep(2)
    except KeyboardInterrupt:
        print(f"\n已退出")


if __name__ == "__main__":
    main()
