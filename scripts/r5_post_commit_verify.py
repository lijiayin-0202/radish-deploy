#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第五轮：提交后门禁复核原始输出落盘。

产出：
- evidence/r5-post-commit-verification.txt     （提交链 / 格式校验 / 单测 / gofmt / vet / 覆盖率 / 工作区状态）
- evidence/r5-commit-message-check-output.txt   （全部真实提交的格式校验原始输出）

只落盘真实执行结果，不做任何手工编辑；被复核的 HEAD 以执行时的真实值为准。
"""
import datetime
import pathlib
import subprocess

ROOT = pathlib.Path(r'd:/Desktop/shop')
EV = ROOT / 'evidence'


def run(cmd):
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    out = (r.stdout or '') + (r.stderr or '')
    return r.returncode, out.strip()


def now():
    return datetime.datetime.now().astimezone().isoformat()


head = run(['git', 'rev-parse', 'HEAD'])[1]

sections = [
    ('=== git branch --show-current ===', ['git', 'branch', '--show-current']),
    ('=== git log --format="%H|%h|%ad|%s" --date=iso -6 ===',
     ['git', 'log', '--format=%H|%h|%ad|%s', '--date=iso', '-6']),
    ('=== git rev-parse HEAD ===', ['git', 'rev-parse', 'HEAD']),
    ('=== git status --short ===', ['git', 'status', '--short']),
    ('=== git remote -v ===', ['git', 'remote', '-v']),
    ('=== python scripts/check_commit_message.py ===',
     ['python', 'scripts/check_commit_message.py']),
    ('=== go test ./... ===', ['go', 'test', './...']),
    ('=== gofmt -l . ===', ['gofmt', '-l', '.']),
    ('=== go vet ./... ===', ['go', 'vet', './...']),
    ('=== go test -cover ./server/service/... ===',
     ['go', 'test', '-cover', './server/service/...']),
    ('=== go test -coverpkg=./... -coverprofile=coverage-r5.out ./... ===',
     ['go', 'test', '-coverpkg=./...', '-coverprofile=coverage-r5.out', './...']),
    ('=== go tool cover -func=coverage-r5.out (overall) ===',
     ['go', 'tool', 'cover', '-func=coverage-r5.out']),
]

blocks = []
for title, cmd in sections:
    rc, out = run(cmd)
    if cmd[-1].endswith('coverage-r5.out'):
        out = '\n'.join(out.strip().splitlines()[-3:])
    if not out:
        out = '(无输出)'
    blocks.append(f'{title}\n{out}\n(exit={rc})')

text = '\n'.join([
    '# 第五轮提交后门禁复核原始输出',
    f'# EXECUTED_AT: {now()}',
    '# BRANCH: dev/01',
    f'# 被复核的 HEAD: {head}',
    '# 说明：以下全部为真实执行输出；race 探针的环境限制见 evidence/r5-quality-output.txt。',
    '# 本文件自身的提交哈希以 git log -1 为准，不在此写死。',
    '',
    '\n'.join(blocks),
    '',
])
(EV / 'r5-post-commit-verification.txt').write_text(text, encoding='utf-8')

rc, out = run(['python', 'scripts/check_commit_message.py'])
(EV / 'r5-commit-message-check-output.txt').write_text(
    '\n'.join([f'# 第五轮提交后提交格式校验原始输出',
               f'# EXECUTED_AT: {now()}',
               f'# 被校验的 HEAD: {head}',
               '# 说明：格式合规不等于 meegle 编号核验通过；首次基线提交的偏差按 P-08 保留历史，不改写。',
               out]) + '\n', encoding='utf-8')

print('post-commit verification written; HEAD =', head)
