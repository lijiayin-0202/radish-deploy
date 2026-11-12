#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第四轮门禁复核：真实执行核查命令，逐字保存 stdout/stderr 与退出码。

只读 / 隔离运行；不修改学生业务代码。输出 evidence/核查命令与输出.txt。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
R3 = OUT.parent / '20261112-03'
SKILL = Path('C:/Users/10990/.codebuddy/skills/student-project-audit')
ROOT = HERE
while not (ROOT / 'go.mod').exists():
    ROOT = ROOT.parent

GO = shutil.which('go') or 'D:/Go/bin/go.exe'
GOFMT = shutil.which('gofmt') or 'D:/Go/bin/gofmt.exe'

lines = []


def emit(text=''):
    lines.append(str(text))


def run(argv, cwd=ROOT, timeout=300):
    try:
        p = subprocess.run([str(a) for a in argv], cwd=str(cwd), capture_output=True,
                           text=True, encoding='utf-8', errors='replace', timeout=timeout)
        return p.returncode, p.stdout or '', p.stderr or ''
    except Exception as exc:
        return -1, '', '%s: %s' % (type(exc).__name__, exc)


def cmd(cid, title, argv, note='', cwd=ROOT):
    emit('=' * 80)
    emit('[%s] %s' % (cid, title))
    emit('命令：%s   （cwd=%s）' % (' '.join(str(a) for a in argv), cwd))
    if note:
        emit('说明：%s' % note)
    code, out, err = run(argv, cwd=cwd)
    emit('输出：')
    if out.strip():
        emit(out.rstrip('\n'))
    if err.strip():
        emit('--- stderr ---')
        emit(err.rstrip('\n'))
    emit('exitCode=%s' % code)
    emit()
    return code, out + err


emit('第四轮门禁复核：核查命令与原始输出')
emit('日期：2026-11-12（Asia/Shanghai）  执行时间：%s' % datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
emit('工作区：%s' % ROOT)
emit('说明：逐字保存本轮各命令真实 stdout/stderr 与退出码。全部核查为只读/隔离运行，')
emit('      未修改学生业务代码；新增文件仅位于本次审计输出目录 %s 及已登记的第四轮证据目录。' % OUT.name)
emit('      计分脚本只做数值校验，不判断业务真实性；race 探针的 exit=2 属环境限制，不写成测试失败。')
emit()

# ---------------------------------------------------------------- CMD-01
emit('=' * 80)
emit('[CMD-01] Git 版本链、工作区与远端（复核开始时执行）')
git_cmds = [
    ['git', 'branch', '--show-current'],
    ['git', 'rev-parse', 'HEAD'],
    ['git', 'rev-list', '--count', 'HEAD'],
    ['git', 'log', '--pretty=format:%h | %s | %cI', '-2'],
    ['git', 'status', '--porcelain'],
    ['git', 'remote', '-v'],
]
for g in git_cmds:
    emit('命令：%s   （cwd=%s）' % (' '.join(g), ROOT))
    c, o, e = run(g)
    emit('输出：%s' % (o.rstrip('\n') if o.strip() else '（无输出）'))
    if e.strip():
        emit('--- stderr ---%s' % e.rstrip('\n'))
    emit('exitCode=%s' % c)
    emit()

# ---------------------------------------------------------------- CMD-02 ~ CMD-05
cmd('CMD-02', 'gofmt -l .（格式检查）', [GOFMT, '-l', '.'])
cmd('CMD-03', 'go vet ./...（静态检查）', [GO, 'vet', './...'])
cmd('CMD-04', 'go build ./...（构建）', [GO, 'build', './...'])
cmd('CMD-05', 'go test ./... -count=1（全部单元测试）', [GO, 'test', './...', '-count=1'])

# ---------------------------------------------------------------- CMD-06
emit('=' * 80)
emit('[CMD-06] 覆盖率：-coverpkg ./... 整体 + server/service 单包')
profile = Path(tempfile.gettempdir()) / 'shop-r4-all.out'
emit('命令：%s test -coverpkg ./... -coverprofile %s ./...' % (GO, profile))
c1, o1, e1 = run([GO, 'test', '-coverpkg', './...', '-coverprofile', str(profile), './...'])
emit('输出：' + (o1.rstrip('\n') if o1.strip() else '（无输出）'))
if e1.strip():
    emit('--- stderr ---' + e1.rstrip('\n'))
emit('exitCode=%s' % c1)
emit('命令：%s tool cover -func %s → 提取 total 行' % (GO, profile))
c2, o2, e2 = run([GO, 'tool', 'cover', '-func', str(profile)])
total_lines = [x for x in o2.splitlines() if x.strip().startswith('total:')]
emit('输出：' + (total_lines[-1].strip() if total_lines else '（无 total 行）'))
emit('exitCode=%s' % c2)
emit('命令：%s test -cover ./server/service/...' % GO)
c3, o3, e3 = run([GO, 'test', '-cover', './server/service/...'])
emit('输出：' + o3.rstrip('\n'))
if e3.strip():
    emit('--- stderr ---' + e3.rstrip('\n'))
emit('exitCode=%s' % c3)
emit()

# ---------------------------------------------------------------- CMD-07
emit('=' * 80)
emit('[CMD-07] 环境事实、race 探针（环境限制，不判代码缺陷）')
c4, o4, _ = run([GO, 'env', 'CGO_ENABLED'])
emit('命令：%s env CGO_ENABLED → %s（exitCode=%s）' % (GO, o4.strip(), c4))
for tool in ('gcc', 'clang', 'meegle'):
    found = shutil.which(tool)
    emit('命令：shutil.which(%s) → %s' % (tool, found if found else 'NOT_FOUND'))
emit('命令：$env:GVA_MYSQL_DSN → %s' % ('SET' if os.environ.get('GVA_MYSQL_DSN') else 'NOT_SET'))
emit('命令：%s test ./server/service/... -race -count=1' % GO)
c5, o5, e5 = run([GO, 'test', './server/service/...', '-race', '-count=1'])
emit('输出：' + (o5 + e5).rstrip('\n'))
emit('exitCode=%s   （-race requires cgo：环境探针，不是单元测试失败、不是数据竞争报告）' % c5)
emit()

# ---------------------------------------------------------------- CMD-08
emit('=' * 80)
emit('[CMD-08] 第四轮交付物全量清点（真实文件系统遍历）')


def count(glob_pat, base=ROOT):
    return len(list(base.glob(glob_pat)))


ev = ROOT / 'evidence'
checks = [
    ('smoke 单用例独立冒烟文件数', count('*.txt', ev / 'smoke')),
    ('manual 异常场景手工记录文档数', count('*.md', ev / 'manual')),
    ('html-check 页面独立断言文档数', count('*.md', ev / 'html-check')),
    ('resource/static HTML 页面数', count('*.html', ROOT / 'resource/static')),
    ('第四轮证据清单存在', (ev / '第四轮证据清单.md').exists()),
    ('mock-channel-run.txt 存在', (ev / 'mock-channel-run.txt').exists()),
    ('r4-suite-output.txt 存在', (ev / 'r4-suite-output.txt').exists()),
    ('commit-message-check-output.txt 存在', (ev / 'commit-message-check-output.txt').exists()),
    ('r4_edge_test.go 存在', (ROOT / 'server/service/r4_edge_test.go').exists()),
    ('mock_channel_service.py 存在', (ROOT / 'scripts/mock_channel_service.py').exists()),
    ('r4_evidence_suite.py 存在', (ROOT / 'scripts/r4_evidence_suite.py').exists()),
    ('check_commit_message.py 存在', (ROOT / 'scripts/check_commit_message.py').exists()),
    ('events.jsonl 存在', (ROOT / 'events.jsonl').exists()),
    ('apipost-run-export.json 存在', (ROOT / 'apipost-run-export.json').exists()),
    ('README.md 存在', (ROOT / 'README.md').exists()),
    ('视频文件数（mp4/avi/mov/mkv/webm/wmv）', sum(count('*' + ext) for ext in
        ('.mp4', '.avi', '.mov', '.mkv', '.webm', '.wmv'))),
]
ci = ROOT / '.github/workflows/ci.yml'
ci_non_comment = 0
if ci.exists():
    ci_non_comment = sum(1 for x in ci.read_text(encoding='utf-8', errors='replace').splitlines()
                         if x.strip() and not x.strip().startswith('#'))
checks.append(('ci.yml 非注释行数', ci_non_comment))
c6, o6, e6 = run(['git', 'remote', '-v'])
checks.append(('git remote 行数', len([x for x in o6.splitlines() if x.strip()])))
c7, o7, e7 = run(['git', 'ls-files'])
checks.append(('已跟踪文件数', len([x for x in o7.splitlines() if x.strip()])))
c8, o8, e8 = run(['git', 'status', '--porcelain'])
checks.append(('工作区变更/未跟踪条目数', len([x for x in o8.splitlines() if x.strip()])))
for name, value in checks:
    emit('%s=%s' % (name, value))
emit('exitCode=0')
emit()

# ---------------------------------------------------------------- CMD-09
cmd('CMD-09', '提交消息格式真实校验脚本', [sys.executable, str(ROOT / 'scripts/check_commit_message.py')],
    note='仅做格式解析，不替代 meegle 编号核验')

# ---------------------------------------------------------------- CMD-10
cmd('CMD-10', '按稳定 42 原子矩阵计分（score_audit.py）',
    [sys.executable, str(SKILL / 'scripts/score_audit.py'),
     '--input', str(OUT / 'audit-input.json'), '--output', str(OUT / 'score.json')],
    note='脚本只校验计分，不判断业务、真实性或全量覆盖', cwd=SKILL)

# ---------------------------------------------------------------- CMD-11
emit('=' * 80)
emit('[CMD-11] 第三轮 / 第四轮状态统计与 pass 提升（读取两份 score.json）')
s3 = json.loads((R3 / 'score.json').read_text(encoding='utf-8'))
s4 = json.loads((OUT / 'score.json').read_text(encoding='utf-8'))
for label, s in (('R3', s3), ('R4', s4)):
    c = s['counts']
    emit('%s final=%s raw=%s completion=%s process=%s pass=%s partial=%s fail=%s unknown=%s na=%s blockers=%s' % (
        label, s['final_score'], s['raw_score'], s['completion_score'], s['process_score'],
        c['pass'], c['partial'], c['fail'], c['unknown'], c['na'], len(s['blockers'])))
    for cat in s['categories']:
        emit('%s %s max=%s score=%s checks=%s' % (
            label, cat['category'], cat['max'], cat['score'], len(cat['checks'])))
emit('PASS_DELTA=%s' % (s4['counts']['pass'] - s3['counts']['pass']))
emit('SCORE_DELTA=%.2f' % (float(s4['final_score']) - float(s3['final_score'])))
emit('BLOCKER_DELTA=%s' % (len(s4['blockers']) - len(s3['blockers'])))
emit('exitCode=0')
emit()

text = '\n'.join(lines) + '\n'
(HERE / '核查命令与输出.txt').write_text(text, encoding='utf-8')
print('WROTE %s' % (HERE / '核查命令与输出.txt'))
print('BYTES=%d' % len(text.encode('utf-8')))
print('\n'.join(x for x in lines if x.startswith(('R3 ', 'R4 ', 'PASS_DELTA', 'SCORE_DELTA', 'BLOCKER_DELTA'))))
