#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""流水线门禁总控：按 .github/workflows/ci.yml 的顺序本地原样复跑全部门禁。

作用：
  1) 保证「CI 里跑的」与「本地能跑的」是同一套脚本、同一套口径；
  2) 汇总成一张门禁总表，缺失任一环节即以非零码退出。

用法：python -X utf8 scripts/pipeline_gates.py
输出：evidence/pipeline_gate_reports/（每个门禁的原始输出 + 门禁总表）
"""
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / 'evidence/pipeline_gate_reports'

# (门禁项, 脚本, 参数, 对应 AGENTS.md 2.5 门禁项)
GATES = [
    ('格式检查 gofmt', ['gofmt', '-l', '.'], '格式与静态检查'),
    ('静态检查 go vet', ['go', 'vet', './...'], '格式与静态检查'),
    ('编译 go build', ['go', 'build', './...'], '单元测试（同源构建）'),
    ('单元测试', ['go', 'test', '-count=1', './...'], '单元测试'),
    ('覆盖率阈值判定', [sys.executable, '-X', 'utf8', 'scripts/coverage_gate.py',
                        '--profile', 'evidence/coverage-gate.out', '--overall', '85',
                        '--pkg', 'server/service:85'], '覆盖率'),
    ('覆盖率证据一致性', [sys.executable, '-X', 'utf8', 'scripts/coverage_evidence_gate.py'],
     '覆盖率'),
    ('五组必演示场景', [sys.executable, '-X', 'utf8', 'scripts/scenario_gate.py'], '五组场景'),
    ('Git 流程', [sys.executable, '-X', 'utf8', 'scripts/git_process_gate.py'], 'Git 流程'),
    ('AI 与 Skill 记录齐备', [sys.executable, '-X', 'utf8', 'scripts/record_gate.py'],
     'AI 与 Skill 记录'),
    ('敏感信息扫描', [sys.executable, '-X', 'utf8', 'scripts/secret_scan_gate.py'],
     '敏感信息保护'),
]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print('===== 流水线门禁总控（与 .github/workflows/ci.yml 同源）=====')
    print('时间：%s' % time.strftime('%Y-%m-%d %H:%M:%S'))
    print('仓库：%s' % ROOT)
    rows = []
    for name, cmd, gate_item in GATES:
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                              encoding='utf-8', errors='replace')
        out = (proc.stdout or '') + (proc.stderr or '')
        file_name = re.sub(r'[^\w.-]+', '_', name) + '.txt'
        (OUT_DIR / file_name).write_text(
            '$ %s\n%s\n[exit=%d]\n' % (' '.join(cmd), out.rstrip(), proc.returncode),
            encoding='utf-8')
        ok = proc.returncode == 0
        if name == '格式检查 gofmt' and out.strip():
            ok = False
        rows.append({'gate': name, 'item': gate_item, 'exit': proc.returncode,
                     'ok': ok, 'file': 'evidence/pipeline_gate_reports/' + file_name})
        print('%-22s exit=%-3d %s' % (name, proc.returncode, 'PASS' if ok else 'FAIL'))
    lines = ['# 流水线门禁总表', '',
             '生成命令：python -X utf8 scripts/pipeline_gates.py',
             '生成时间：%s' % time.strftime('%Y-%m-%d %H:%M:%S'), '',
             '| 门禁项 | 对应 AGENTS.md 2.5 门禁 | 退出码 | 判定 | 原始输出 |',
             '| --- | --- | --- | --- | --- |']
    for row in rows:
        lines.append('| %s | %s | %d | %s | %s |'
                     % (row['gate'], row['item'], row['exit'],
                        'PASS' if row['ok'] else 'FAIL', row['file']))
    failed = [r for r in rows if not r['ok']]
    lines.append('')
    lines.append('门禁项：%d；通过：%d；不通过：%d' % (len(rows), len(rows) - len(failed), len(failed)))
    for row in failed:
        lines.append('- FAIL：%s（exit=%d）' % (row['gate'], row['exit']))
    (OUT_DIR / '门禁总表.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('-' * 60)
    print('门禁项：%d；通过：%d；不通过：%d' % (len(rows), len(rows) - len(failed), len(failed)))
    for row in failed:
        print('  FAIL：%s（exit=%d）' % (row['gate'], row['exit']))
    print('原始输出目录：%s' % OUT_DIR)
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
