"""
微信聊天记账 - 简洁版
三个模块：解析消息 → 提取金额 → 输出CSV
用法: python wechat_accounting.py 聊天记录.txt [账单.csv]
"""
import sys, re, csv, os
from collections import defaultdict

# ═══════════════ 第一步：解析消息 ═══════════════

def parse_messages(file_path):
    """解析微信导出txt，返回 [(时间, 发言人, 内容), ...]"""
    with open(file_path, encoding='utf-8') as f:
        text = f.read().replace('\r\n', '\n').replace('\r', '\n')
    lines = text.split('\n')

    # 跳过文件头，定位第一条消息
    start = 0
    ts_re = r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (.+?)(?:\([^)]*\))?$'
    for i, line in enumerate(lines):
        if re.match(ts_re, line):
            start = i
            break
    else:
        return []

    messages = []
    cur_dt = None
    cur_sp = None
    cur_lines = []

    for line in lines[start:]:
        line = line.strip()
        m = re.match(ts_re, line)
        if m:
            # 保存上一条
            if cur_dt and cur_sp and cur_lines:
                content = '\n'.join(cur_lines).strip()
                if content:
                    messages.append((cur_dt, cur_sp, content))
            cur_dt = m.group(1)
            cur_sp = m.group(2).strip()
            cur_lines = []
        else:
            if line and cur_dt:
                cur_lines.append(line)

    # 最后一条
    if cur_dt and cur_sp and cur_lines:
        content = '\n'.join(cur_lines).strip()
        if content:
            messages.append((cur_dt, cur_sp, content))

    return messages

# ═══════════════ 第二步：提取金额 ═══════════════

# 金额正则: 200 / 35.5 / 1,299 / ¥200.00
AMT = r'[¥]?(\d{1,3}(?:,?\d{3})*(?:\.\d{1,2})?)'

PATTERNS = [
    (rf'\[转账\].*?{AMT}',        '转账'),
    (rf'转账\s*{AMT}',           '转账'),
    (rf'红包\s*{AMT}',           '红包'),
    (rf'打车.*?{AMT}',           '交通'),
    (rf'地铁.*?{AMT}',           '交通'),
    (rf'公交.*?{AMT}',           '交通'),
    (rf'加油.*?{AMT}',           '交通'),
    (rf'高铁.*?{AMT}',           '交通'),
    (rf'机票.*?{AMT}',           '交通'),
    (rf'淘宝.*?{AMT}',           '购物'),
    (rf'京东.*?{AMT}',           '购物'),
    (rf'拼多多.*?{AMT}',         '购物'),
    (rf'外卖.*?{AMT}',           '餐饮'),
    (rf'奶茶.*?{AMT}',           '餐饮'),
    (rf'咖啡.*?{AMT}',           '餐饮'),
    (rf'吃了?.*?{AMT}',          '餐饮'),
    (rf'饭.*?{AMT}',             '餐饮'),
    (rf'餐.*?{AMT}',             '餐饮'),
    (rf'花了\s*{AMT}',           None),  # 后判
    (rf'付款\s*{AMT}',           None),
    (rf'消费\s*{AMT}',           None),
    (rf'人均\s*{AMT}',           None),
    (rf'AA\s*{AMT}',             None),
    (rf'{AMT}\s*[元块]',         None),  # 兜底
]

def classify(text):
    if re.search(r'吃|饭|餐|外卖|奶茶|咖啡|聚餐|烧烤|火锅', text):
        return '餐饮'
    if re.search(r'打车|地铁|公交|加油|高铁|机票|出行', text):
        return '交通'
    if re.search(r'淘宝|京东|拼多多|买了|购买', text):
        return '购物'
    if re.search(r'转账|转给', text):
        return '转账'
    if re.search(r'红包', text):
        return '红包'
    return '其他'


def extract_amounts(messages):
    records = []
    seen = set()

    for dt, speaker, content in messages:
        if re.search(r'加入|退出|撤回|邀请|修改群名', content):
            continue

        for regex, cat in PATTERNS:
            for m in re.finditer(regex, content):
                amt_str = m.group(1).replace(',', '').replace('¥', '')
                try:
                    amt = float(amt_str)
                except ValueError:
                    continue
                if not (0 < amt <= 1000000):
                    continue

                category = cat or classify(content)
                key = (dt, speaker, amt, category)
                if key in seen:
                    continue
                seen.add(key)

                date, time = dt.split(' ')
                records.append((date, time, speaker, category, amt, content))

    return records


# ═══════════════ 第三步：输出 ═══════════════

def save_csv(records, path):
    records.sort(key=lambda r: (r[0], r[1]))

    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['日期', '时间', '发言人', '类别', '金额', '备注'])
        for r in records:
            w.writerow([r[0], r[1], r[2], r[3], f'{r[4]:.2f}', r[5][:80]])

    if not records:
        print('未提取到财务记录')
        return

    cat_sum = defaultdict(lambda: [0, 0.0])
    person_sum = defaultdict(lambda: [0, 0.0])
    for _, _, sp, cat, amt, _ in records:
        cat_sum[cat][0] += 1;    cat_sum[cat][1] += amt
        person_sum[sp][0] += 1;  person_sum[sp][1] += amt

    total_n = len(records)
    total_a = sum(v[1] for v in cat_sum.values())

    print(f'\n提取 {total_n} 条记录，合计 {total_a:.2f} 元\n')
    print(f'{"类别":<8} {"笔数":>4}  {"金额":>8}')
    print('-' * 26)
    for cat in ['转账', '红包', '餐饮', '交通', '购物', '其他']:
        if cat_sum[cat][0]:
            print(f'{cat:<8} {cat_sum[cat][0]:>4}  {cat_sum[cat][1]:>8.2f}')
    print('-' * 26)
    print(f'{"合计":<8} {total_n:>4}  {total_a:>8.2f}')

    print(f'\n{"发言人":<8} {"笔数":>4}  {"金额":>8}')
    print('-' * 26)
    for sp, (n, a) in sorted(person_sum.items(), key=lambda x: -x[1][1]):
        print(f'{sp:<8} {n:>4}  {a:>8.2f}')


# ═══════════════ 入口 ═══════════════

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        print('用法: python wechat_accounting.py <input.txt> [output.csv]')
        sys.exit(0)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else '账单.csv'

    if not os.path.exists(input_file):
        print(f'错误: "{input_file}" 不存在')
        sys.exit(1)

    print(f'解析: {input_file}')
    msgs = parse_messages(input_file)
    print(f'读取 {len(msgs)} 条消息')

    recs = extract_amounts(msgs)
    print(f'找到 {len(recs)} 笔账目')

    save_csv(recs, output_file)
    print(f'已保存: {output_file}')
