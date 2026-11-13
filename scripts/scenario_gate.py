#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""五组必演示场景门禁（TST-S1~S5）。

依据 AGENTS.md 2.5「五组场景均有实际执行结果」与需求文档的五组场景定义：
校验 evidence/demo-five-scenarios-output.txt 中
  1) 五组场景是否齐全；
  2) 每组场景的断言条数是否达到下限；
  3) 每组场景的关键失败路径是否真实命中题面要求的错误码。
任一缺失即以非零码退出，可直接作为 CI 门禁步骤。

用法：
  python -X utf8 scripts/scenario_gate.py
  python -X utf8 scripts/scenario_gate.py --evidence evidence/demo-five-scenarios-output.txt
  python -X utf8 scripts/scenario_gate.py --json
"""
import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_EVIDENCE = ROOT / 'evidence/demo-five-scenarios-output.txt'

# 每组场景：标题、断言条数下限、必须命中的失败码（与需求文档/原型文档一致）
REQUIRED = {
    'S1': {'title': '活动正常成交', 'min_cases': 4, 'codes': ['M-19']},
    'S2': {'title': '缺货与弃单（含库存释放与 20 次抢单）', 'min_cases': 3, 'codes': ['M-10']},
    'S3': {'title': '售前退款（渠道首次失败、再次成功）', 'min_cases': 6, 'codes': ['M-22', 'M-08']},
    'S4': {'title': '迟到支付（终态不变 + 异常核实退款）', 'min_cases': 8, 'codes': ['M-09', 'M-08']},
    'S5': {'title': '操作竞争、重复通知与越权', 'min_cases': 6, 'codes': ['M-22', 'M-20']},
}

# 非法错误码：这些不得出现在任何场景断言的业务码里
ILLEGAL_CODES = {'M-07'}


def read_text(path):
    """兼容 UTF-8 与 UTF-16（含 BOM）两种编码读取证据文件。

    Windows PowerShell 5.1 的 `>` 重定向默认写 UTF-16LE，历史证据文件存在该编码，
    门禁脚本不能因编码差异而误判，因此按 BOM 判定后再解码。
    """
    raw = path.read_bytes()
    if raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
        return raw.decode('utf-16')
    return raw.decode('utf-8', errors='replace')


def parse_scenarios(text):
    """把原始输出解析为 {场景号: {title, cases:[{id, code, line}]}}。"""
    scenarios = {}
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        header = re.match(r'^===\s*TST-(S\d)\s*(.*?)\s*===$', line)
        if header:
            current = header.group(1)
            scenarios[current] = {'title': header.group(2), 'cases': []}
            continue
        if not current:
            continue
        case = re.match(r'^\[(?P<id>S\d-\d+)\]\s*(?P<desc>.*)$', line)
        if not case:
            continue
        code = re.search(r'code=(?P<code>[A-Za-z0-9_-]+)', line)
        scenarios[current]['cases'].append({
            'id': case.group('id'),
            'desc': case.group('desc'),
            'code': code.group('code') if code else '',
        })
    return scenarios


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--evidence', default=str(DEFAULT_EVIDENCE), help='五组场景原始输出文件')
    ap.add_argument('--json', action='store_true', help='额外输出 JSON')
    args = ap.parse_args()

    path = pathlib.Path(args.evidence)
    print('===== 五组必演示场景门禁（TST-S1~S5）=====')
    print('证据文件：%s' % path)
    failures = []
    if not path.exists():
        print('FAIL：五组场景证据文件不存在')
        return 1
    text = read_text(path)
    scenarios = parse_scenarios(text)

    rows = []
    for key in sorted(REQUIRED):
        spec = REQUIRED[key]
        got = scenarios.get(key)
        if not got:
            failures.append('缺少场景 TST-%s（%s）' % (key, spec['title']))
            rows.append({'scenario': key, 'ok': False, 'cases': 0, 'detail': '场景缺失'})
            continue
        codes = [c['code'] for c in got['cases']]
        with_code = [c for c in codes if c]
        summary = len(codes) - len(with_code)
        missing = [c for c in spec['codes'] if c not in codes]
        illegal = sorted(set(codes) & ILLEGAL_CODES)
        problems = []
        if len(got['cases']) < spec['min_cases']:
            problems.append('断言仅 %d 条，低于下限 %d 条'
                            % (len(got['cases']), spec['min_cases']))
        if missing:
            problems.append('关键失败码未命中：%s' % ','.join(missing))
        if illegal:
            problems.append('出现不应返回的业务码：%s' % ','.join(illegal))
        if not with_code:
            problems.append('该场景没有任何可解析业务码的断言')
        ok = not problems
        if not ok:
            failures.append('TST-%s：%s' % (key, '；'.join(problems)))
        rows.append({'scenario': key, 'title': got['title'], 'ok': ok,
                     'cases': len(got['cases']), 'codes': sorted(set(codes)),
                     'summary_lines': summary,
                     'detail': '；'.join(problems) or '全部满足'})

    print('-' * 96)
    print('%-6s %-32s %-8s %-26s %s' % ('场景', '标题', '断言数', '命中业务码', '判定'))
    print('-' * 96)
    for row in rows:
        print('%-6s %-32s %-8d %-26s %s'
              % (row['scenario'], row.get('title', '-')[:32], row['cases'],
                 ','.join(row.get('codes', []))[:26] or '-',
                 'PASS' if row['ok'] else 'FAIL：' + row['detail']))
    print('-' * 96)
    total_cases = sum(r['cases'] for r in rows)
    print('场景数：%d / %d；断言总数：%d；不合格场景：%d'
          % (sum(1 for r in rows if r['ok']), len(REQUIRED), total_cases, len(failures)))
    for item in failures:
        print('  FAIL：%s' % item)
    print('结论：%s' % ('PASS 五组场景证据齐备且关键失败码命中' if not failures else 'FAIL'))
    if args.json:
        print(json.dumps({'rows': rows, 'failures': failures, 'pass': not failures},
                         ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main())
