#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第四轮产物一致性校验：报告结构、E4 编号闭环、CSV 与 score.json 对应。"""
import csv
import json
import re
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent

report = (OUT / '检查报告.md').read_text(encoding='utf-8')
print('report_lines=%d' % len(report.splitlines()))
print('sections=%s' % re.findall(r'^## (\d)\.', report, re.M))
print('placeholders=%d' % report.count('<!-- PART'))

index = (OUT / 'evidence/E-索引.md').read_text(encoding='utf-8')
defined = set(re.findall(r'E4-\d{3}', index))
data = json.loads((OUT / 'audit-input.json').read_text(encoding='utf-8'))
used = set(e for c in data['checks'] for e in c['evidence'])
print('E4_defined=%d E4_used=%d undefined=%s' % (len(defined), len(used), sorted(used - defined)))

score = json.loads((OUT / 'score.json').read_text(encoding='utf-8'))
print('score=%s verdict=%s counts=%s blockers=%d' % (
    score['final_score'], score['verdict'], score['counts'], len(score['blockers'])))

with (OUT / '要求与评分明细.csv').open('r', encoding='utf-8-sig', newline='') as f:
    rows = list(csv.DictReader(f))
print('rubric_csv_rows=%d pass_in_csv=%d' % (len(rows), sum(1 for r in rows if r['状态'] == 'pass')))

with (OUT / '过程与提示词明细.csv').open('r', encoding='utf-8-sig', newline='') as f:
    proc = list(csv.DictReader(f))
print('process_csv_rows=%d last_step=%s' % (len(proc), proc[-1]['步骤']))

print('out_files=%s' % sorted(p.name for p in OUT.iterdir()))
print('evidence_files=%s' % sorted(p.name for p in (OUT / 'evidence').iterdir()))

ok = (
    len(re.findall(r'^## (\d)\.', report, re.M)) == 7
    and report.count('<!-- PART') == 0
    and not (used - defined)
    and len(rows) == 42
    and sum(1 for r in rows if r['状态'] == 'pass') == score['counts']['pass']
    and score['final_score'] == '7.27'
)
print('CONSISTENCY_CHECK=%s' % ('PASS' if ok else 'FAIL'))
