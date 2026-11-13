#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 与 Skill 记录齐备性门禁（只读校验）。

依据 AGENTS.md 2.5「AI 与 Skill 记录：会话导出、Skill 使用记录、skill-usage.md 齐全」
与第 6 章交接材料与证据索引：校验过程类记录文件是否存在、是否非空、是否达到最小内容行数。

本脚本只做「记录是否存在」的齐备性检查，不对记录内容做任何验收判断。

用法：python -X utf8 scripts/record_gate.py
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# (相对路径, 说明, 最小行数)
REQUIRED = [
    ('skill-usage.md', 'Skill 调用记录', 5),
    ('evidence/AI使用说明.md', 'AI 使用与过程说明', 10),
    ('evidence/会话导出说明.md', '会话导出说明', 10),
    ('evidence/事件清单说明.md', '事件清单说明', 10),
    ('evidence/agent-rules-load-log.md', 'AGENTS 约束加载登记', 10),
    ('evidence/门禁自查汇总.md', '门禁自查汇总', 10),
    ('evidence/交付证据说明.md', '交付证据说明', 10),
    ('evidence/验收报告说明.md', '验收报告归档说明', 5),
    ('evidence/CI流水线说明.md', '流水线说明', 5),
    ('evidence/quality_gate_output.txt', '质量门禁原始输出', 20),
    ('evidence/race_raw_output.txt', '竞态检测原始输出', 1),
    ('evidence/demo-five-scenarios-output.txt', '五组场景原始输出', 30),
    ('evidence/error_code_enumeration.txt', '错误码穷举原始输出', 40),
]


def read_text(path):
    """兼容 UTF-8 与 UTF-16（含 BOM）两种编码。"""
    raw = path.read_bytes()
    if raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
        return raw.decode('utf-16')
    return raw.decode('utf-8', errors='replace')


def main():
    print('===== AI 与 Skill 记录齐备性门禁 =====')
    print('仓库：%s' % ROOT)
    failures = []
    rows = []
    for rel, desc, min_lines in REQUIRED:
        path = ROOT / rel
        if not path.exists():
            failures.append('缺少记录：%s（%s）' % (rel, desc))
            rows.append((rel, desc, 0, 'FAIL：文件不存在'))
            continue
        lines = [l for l in read_text(path).splitlines() if l.strip()]
        if len(lines) < min_lines:
            failures.append('记录内容过少：%s（%s）仅 %d 行，下限 %d 行'
                            % (rel, desc, len(lines), min_lines))
            rows.append((rel, desc, len(lines), 'FAIL：内容不足 %d 行' % min_lines))
        else:
            rows.append((rel, desc, len(lines), 'PASS'))
    print('-' * 96)
    print('%-46s %-22s %-8s %s' % ('文件', '说明', '有效行数', '判定'))
    print('-' * 96)
    for rel, desc, count, verdict in rows:
        print('%-46s %-22s %-8d %s' % (rel, desc, count, verdict))
    print('-' * 96)
    print('记录项：%d；通过：%d；不通过：%d'
          % (len(REQUIRED), len(REQUIRED) - len(failures), len(failures)))
    for item in failures:
        print('  FAIL：%s' % item)
    print('结论：%s' % ('PASS 过程类记录齐备' if not failures else 'FAIL'))
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main())
