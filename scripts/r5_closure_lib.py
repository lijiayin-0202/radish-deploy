#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第五轮证据闭环采集：公共运行库。

口径（与 AGENTS.md 5 / P-01 一致）：
- 只做真实可复现的动作：本地 go build 实例 + 真实 HTTP 调用 + 真实 git / go / python 命令。
- 不冒充真实 MySQL(InnoDB) 行锁、不冒充 go test -race 探针、不冒充 CI / 远端 PR / 独立 Agent 会话。
- 环境或过程证据缺失的条目，如实保留为 partial，并在文档中写明解除条件。
"""
import datetime
import json
import os
import pathlib
import shutil
import subprocess
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(r'd:/Desktop/shop')
EV = ROOT / 'evidence'
PARTIAL_DIR = EV / 'partial-closure'
MANUAL2_DIR = EV / 'manual-round2'
HTMLCHECK_DIR = EV / 'html-check'
for _d in (PARTIAL_DIR, MANUAL2_DIR, HTMLCHECK_DIR):
    _d.mkdir(parents=True, exist_ok=True)

PORT = int(os.environ.get('R5_PORT', '18086'))
BASE = f'http://127.0.0.1:{PORT}'
EXE = pathlib.Path(os.environ.get('TEMP', '/tmp')) / 'shop-trade-r5.exe'
SCOPE = ('第五轮开发会话内真实执行；非独立测试 Agent 会话、非独立验收 Agent 会话、'
         '非 Apipost 运行导出、非浏览器截图、非真实 MySQL(InnoDB) 实例、'
         '非 go test -race 探针、非远端 CI / PR / 部署记录。')

ACCOUNTS = ('buyer01', 'buyer02', 'buyer03', 'ops01', 'warehouse01', 'cs01', 'mock01')


def now():
    return datetime.datetime.now().astimezone().isoformat()


def save(path, text):
    pathlib.Path(path).write_text(text, encoding='utf-8')


def call(method, path, account, body=None):
    headers = {'X-Demo-Account': account}
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read().decode('utf-8', 'replace')
            try:
                obj = json.loads(raw)
            except ValueError:
                obj = None
            return {'status': r.status, 'body': raw, 'obj': obj}
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'replace')
        try:
            obj = json.loads(raw)
        except ValueError:
            obj = None
        return {'status': e.code, 'body': raw, 'obj': obj}
    except Exception as e:  # noqa: BLE001
        return {'status': -1, 'body': str(e), 'obj': None}


def code_of(resp):
    obj = resp.get('obj')
    if isinstance(obj, dict):
        return str(obj.get('code'))
    return '(no-json)'


def data_of(resp):
    obj = resp.get('obj')
    if isinstance(obj, dict) and isinstance(obj.get('data'), dict):
        return obj['data']
    return {}


def build():
    r = subprocess.run(['go', 'build', '-o', str(EXE), '.'], cwd=str(ROOT),
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        raise RuntimeError('go build failed: ' + r.stderr)


def start_demo():
    env = dict(os.environ)
    env['GVA_ADDR'] = f':{PORT}'
    env.pop('GVA_MYSQL_DSN', None)
    p = subprocess.Popen([str(EXE)], cwd=str(ROOT), env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(80):
        r = call('GET', '/health', 'buyer01')
        if r['status'] == 200:
            return p
        time.sleep(0.3)
    p.terminate()
    raise RuntimeError('health timeout')


def stop_demo(p):
    p.terminate()
    try:
        p.wait(timeout=5)
    except subprocess.TimeoutExpired:
        p.kill()
    time.sleep(0.5)


def run(cmd, cwd=None):
    """执行真实命令并返回 (退出码, 合并 stdout/stderr 原文)。"""
    r = subprocess.run(cmd, cwd=cwd or str(ROOT), capture_output=True, text=True,
                       encoding='utf-8', errors='replace', shell=isinstance(cmd, str))
    return r.returncode, ((r.stdout or '') + (r.stderr or '')).strip()


def git(*args):
    return run(['git'] + list(args))


def block(text):
    return '```text\n' + (text or '(空输出)') + '\n```'


def case_lines(title, method, path, account, body, expect, resp):
    body_text = json.dumps(body, ensure_ascii=False) if body is not None else '(none)'
    got = code_of(resp)
    ok = (resp['status'] == 200 and got == expect)
    if expect == 'HTTP200':
        ok = resp['status'] == 200
    verdict = 'PASS（预期与实际一致）' if ok else 'DIFF（预期与实际不一致，边界行为如实登记，不改动业务代码）'
    return '\n'.join([
        f'#### {title}',
        '',
        f'- 请求：`{method} {path}`，`X-Demo-Account={account}`',
        f'- 入参：`{body_text}`',
        f'- 预期：`{expect}`',
        f'- 实际 HTTP：`{resp["status"]}`',
        f'- 实际响应：`{resp["body"]}`',
        f'- 判定：**{verdict}**',
        '',
    ]), ok


def md_table(rows, headers=('编号', '断言', '实际', '结论')):
    out = ['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join('---' for _ in headers) + ' |']
    for r in rows:
        out.append('| ' + ' | '.join(str(x) for x in r) + ' |')
    return '\n'.join(out)


def partial_doc(item_id, title, audit_reason, verdict, sections, gap, release, boundary):
    """统一生成 partial 闭环文档。"""
    parts = [
        f'# {item_id} 闭环核查：{title}',
        '',
        '| 项 | 内容 |',
        '| --- | --- |',
        f'| 核查项编号 | `{item_id}` |',
        '| 第四轮判定 | `partial` |',
        f'| 第四轮原始理由 | {audit_reason} |',
        f'| 本轮核查时间 | {now()} |',
        '| 本轮执行方式 | 本地 `go build` 实例 + 真实 HTTP / 真实命令，逐条留存原始输出 |',
        '| 判定口径 | 环境 / 过程证据缺失 → 不判代码缺陷；不虚构、不用内存仓储冒充真实 MySQL |',
        f'| 本轮结论 | **{verdict}** |',
        '',
        '## 1. 本轮真实执行的核查动作',
        '',
    ]
    parts.extend(sections)
    parts.extend([
        '',
        '## 2. 缺口说明（本轮为何仍不能升级为 `pass`）',
        '',
    ])
    parts.extend([f'- {g}' for g in gap])
    parts.extend([
        '',
        '## 3. 解除条件（可核查、可执行）',
        '',
    ])
    parts.extend([f'- {r}' for r in release])
    parts.extend([
        '',
        '## 4. 边界声明',
        '',
        f'- {SCOPE}',
        '- 本文件不冒充独立测试 / 验收 Agent 会话产物，不冒充真实 MySQL、race 探针、CI、PR 或部署记录。',
        '- 本轮**未改动任何生产代码**，仅新增测试与证据文档。',
        '',
        '## 5. 关联证据',
        '',
        '- 第四轮审核输入：`outputs/单题检查/shop-trade/01/20261112-04/audit-input.json`',
        '- 第四轮检查报告：`outputs/单题检查/shop-trade/01/20261112-04/检查报告.md`',
        '- 第五轮证据清单：`evidence/第五轮证据清单.md`',
        '',
    ])
    save(PARTIAL_DIR / f'{item_id}.md', '\n'.join(parts))
    return '\n'.join(parts)
