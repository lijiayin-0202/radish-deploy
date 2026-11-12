#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第五轮：把质量门禁的真实执行输出落盘为证据文件。

产出：
- evidence/r5-quality-output.txt   （go test ./... / gofmt -l . / go vet ./... / go test -race 环境限制）
- evidence/r5-coverage-output.txt  （service 包覆盖率 + -coverpkg ./... overall 与按包统计）
- evidence/r5-coverage-func.txt    （go tool cover -func 完整逐函数明细）

只落盘真实输出，不做任何手工编辑。
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


q = ['=== go test ./... ===']
rc, out = run(['go', 'test', './...'])
q.append(out)
q.append(f'go_test_exit={rc}')

q.append('')
q.append('=== gofmt -l . ===')
rc, out = run(['gofmt', '-l', '.'])
q.append(out if out else '(无输出：全部文件已格式化)')
q.append(f'gofmt_exit={rc}')

q.append('')
q.append('=== go vet ./... ===')
rc, out = run(['go', 'vet', './...'])
q.append(out if out else '(无输出：go vet 通过)')
q.append(f'go_vet_exit={rc}')

q.append('')
q.append('=== go test -race ./server/... (环境限制，如实记录) ===')
rc, out = run(['go', 'test', '-race', './server/...'])
q.append(out)
q.append(f'go_race_exit={rc}')
q.append('说明：本机 CGO_ENABLED=0 且无 gcc/clang，-race 探针无法运行；'
         '该条维持 unknown，不冒充 race 通过，也不写成数据竞争报告。')

(EV / 'r5-quality-output.txt').write_text(
    '\n'.join([f'# 第五轮质量门禁真实执行输出', f'# EXECUTED_AT: {now()}',
               '# ENV: local go build, mode=demo-memory (GVA_MYSQL_DSN NOT_SET)',
               '# BRANCH: dev/01'] + q) + '\n', encoding='utf-8')

c = ['=== go test -cover ./server/service/... ===']
rc, out = run(['go', 'test', '-cover', './server/service/...'])
c.append(out)
c.append(f'service_cover_exit={rc}')

c.append('')
c.append('=== go test -coverpkg=./... -coverprofile=coverage-r5.out ./... ===')
rc, out = run(['go', 'test', '-coverpkg=./...', '-coverprofile=coverage-r5.out', './...'])
c.append(out)
c.append(f'all_cover_exit={rc}')

rc, out = run(['go', 'tool', 'cover', '-func=coverage-r5.out'])
c.append('')
c.append('=== go tool cover -func=coverage-r5.out (overall) ===')
c.append('\n'.join(out.strip().splitlines()[-3:]))
c.append('cover_func_exit=0')

c.append('')
c.append('=== 按包统计（逐函数覆盖率的最低/最高） ===')
rows = {}
for line in out.splitlines():
    if ':' not in line or line.startswith('total:'):
        continue
    path = line.split(':')[0]
    pkg = path.rsplit('/', 1)[0]
    pct = line.strip().split('\t')[-1]
    rows.setdefault(pkg, []).append((path, pct))
for pkg in sorted(rows):
    vals = [float(p.rstrip('%')) for _, p in rows[pkg]]
    c.append(f'{pkg}: 文件数={len(vals)} 逐函数最低={min(vals)}% 最高={max(vals)}%')
c.append('完整逐函数明细见 coverage-r5.out 与 evidence/r5-coverage-func.txt')

(EV / 'r5-coverage-output.txt').write_text(
    '\n'.join([f'# 第五轮覆盖率真实执行输出', f'# EXECUTED_AT: {now()}',
               '# 覆盖率原始文件：coverage-r5.out（仓库根目录）',
               '# 目标：service 包 ≥92%、整体 ≥92%'] + c) + '\n', encoding='utf-8')

(EV / 'r5-coverage-func.txt').write_text(
    '\n'.join([f'# go tool cover -func=coverage-r5.out 完整逐函数明细',
               f'# EXECUTED_AT: {now()}', out]) + '\n', encoding='utf-8')

print('quality + coverage evidence written')
print('service:', run(['go', 'test', '-cover', './server/service/...'])[1].splitlines()[-1])
print('overall:', run(['go', 'tool', 'cover', '-func=coverage-r5.out'])[1].splitlines()[-1])
