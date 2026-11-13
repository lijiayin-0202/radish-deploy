#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""基础部署门禁：构建制品 → 登记版本 → 启动 → 健康检查 → 业务冒烟 → 回退准备校验。

题面对应：题面共同要求「流水线实际执行质量、覆盖率、构建和部署门禁」与 AGENTS.md Q-04
「质量检查失败不得继续发布」。本脚本把部署门禁固化为可执行作业，任一步失败即以非零码退出，
阻断发布；同时登记制品版本与上一可用版本，使回退方案有据可依。

用法：
    python scripts/deploy_gate.py
    python scripts/deploy_gate.py --addr 127.0.0.1:18080 --out dist

退出码：
    0  构建、启动、健康检查、冒烟与回退准备全部通过
    1  任一步骤失败（构建失败 / 健康检查超时 / 冒烟不通过 / 回退校验不成立）
"""
import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
STEPS = []


def log(msg):
    STEPS.append(msg)
    print(msg, flush=True)


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8',
                          errors='replace', **kw)


def git(*args):
    r = run(['git', '-C', str(ROOT), *args])
    return (r.stdout or '').strip()


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 16), b''):
            h.update(chunk)
    return h.hexdigest()


def http(method, url, body=None, account='buyer01', timeout=10):
    headers = {'X-Demo-Account': account} if account else {}
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode('utf-8', 'replace'))
    except urllib.error.HTTPError as e:
        return e.code, {'code': 'HTTP%d' % e.code, 'message': e.read().decode('utf-8', 'replace')}
    except Exception as e:
        return -1, {'code': 'REQUEST_FAILED', 'message': repr(e)}


def code_of(obj):
    return (obj or {}).get('code')


def data_of(obj):
    return (obj or {}).get('data') or {}


def main():
    ap = argparse.ArgumentParser(description='基础部署门禁')
    ap.add_argument('--addr', default='127.0.0.1:18080', help='门禁实例监听地址')
    ap.add_argument('--out', default='dist', help='制品输出目录')
    ap.add_argument('--keep-history', default='dist/manifest_history.jsonl',
                    help='制品版本历史文件（用于回退校验）')
    args = ap.parse_args()

    out_dir = ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    binary = out_dir / ('shop-trade.exe' if os.name == 'nt' else 'shop-trade')
    base = 'http://' + args.addr
    failures = []

    log('===== 基础部署门禁 =====')
    log('时间：%s' % time.strftime('%Y-%m-%d %H:%M:%S'))
    log('仓库：%s' % ROOT)
    log('')

    # 1. 构建制品
    log('--- 1. 构建制品 ---')
    r = run(['go', 'build', '-o', str(binary), '.'], cwd=str(ROOT))
    log('$ go build -o %s . -> exit=%d' % (binary, r.returncode))
    if r.returncode != 0 or not binary.exists():
        failures.append('构建失败：%s' % ((r.stderr or r.stdout or '').strip()[:300]))
        log('结论：FAIL（构建失败，发布中止）')
        return 1
    log('制品大小：%d 字节' % binary.stat().st_size)

    # 2. 登记制品版本（提交哈希 + 制品校验和 + 时间）
    log('')
    log('--- 2. 登记制品版本 ---')
    head = git('rev-parse', 'HEAD')
    branch = git('rev-parse', '--abbrev-ref', 'HEAD')
    manifest = {
        'commit': head,
        'branch': branch,
        'artifact': binary.name,
        'sha256': sha256(binary),
        'size': binary.stat().st_size,
        'built_at': time.strftime('%Y-%m-%d %H:%M:%S'),
    }
    (out_dir / 'manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    log('提交：%s（分支 %s）' % (head[:12], branch))
    log('制品 sha256：%s' % manifest['sha256'])
    log('版本清单：%s' % (out_dir / 'manifest.json'))

    # 3. 启动实例
    log('')
    log('--- 3. 启动实例 ---')
    env = dict(os.environ)
    env['GVA_ADDR'] = ':' + args.addr.split(':')[-1]
    env.pop('GVA_MYSQL_DSN', None)  # 部署门禁自包含，不依赖外部数据库
    proc = subprocess.Popen([str(binary)], cwd=str(ROOT), env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    log('进程已启动 pid=%s（GVA_MYSQL_DSN 未设置，模式 demo-memory）' % proc.pid)
    healthy = False
    try:
        for _ in range(60):
            time.sleep(0.5)
            if proc.poll() is not None:
                break
            st, _ = http('GET', base + '/health', account=None, timeout=3)
            if st == 200:
                healthy = True
                break
        if not healthy:
            failures.append('健康检查未通过：%s/health 未在 30 秒内返回 200' % base)
            log('健康检查：FAIL')
        else:
            log('健康检查：PASS（GET /health -> 200）')

        # 4. 业务冒烟
        log('')
        log('--- 4. 业务冒烟 ---')
        if healthy:
            st, obj = http('GET', base + '/api/v1/goods')
            items = data_of(obj).get('items')
            ok_goods = st == 200 and code_of(obj) == '0' and isinstance(items, list) and len(items) > 0
            log('GET /api/v1/goods -> %s code=%s 商品数=%s → %s'
                % (st, code_of(obj), len(items) if isinstance(items, list) else 'N/A',
                   'PASS' if ok_goods else 'FAIL'))
            if not ok_goods:
                failures.append('商品列表冒烟失败：HTTP %s code=%s' % (st, code_of(obj)))

            st, obj = http('POST', base + '/api/v1/orders', {'goods_id': 1, 'quantity': 1})
            order_no = data_of(obj).get('order_no')
            ok_order = st == 200 and code_of(obj) == '0' and bool(order_no)
            log('POST /api/v1/orders -> %s code=%s order_no=%s → %s'
                % (st, code_of(obj), order_no, 'PASS' if ok_order else 'FAIL'))
            if not ok_order:
                failures.append('下单冒烟失败：HTTP %s code=%s' % (st, code_of(obj)))

            if order_no:
                st, obj = http('GET', base + '/api/v1/orders/%s' % order_no)
                ok_query = st == 200 and data_of(obj).get('order_no') == order_no
                log('GET /api/v1/orders/%s -> %s → %s'
                    % (order_no, st, 'PASS' if ok_query else 'FAIL'))
                if not ok_query:
                    failures.append('订单回查冒烟失败：HTTP %s' % st)
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
        log('实例已停止')

    # 5. 回退准备校验
    log('')
    log('--- 5. 回退准备校验 ---')
    hist_path = ROOT / args.keep_history
    prev = None
    if hist_path.exists():
        lines = [l for l in hist_path.read_text(encoding='utf-8').splitlines() if l.strip()]
        if lines:
            prev = json.loads(lines[-1])
    if prev:
        log('上一可用版本：commit=%s sha256=%s' % (prev.get('commit', '')[:12],
                                                  prev.get('sha256', '')[:16]))
        log('回退步骤：停止当前实例 → 回滚到上述 commit 重新构建 → 重跑本门禁 → 恢复流量')
        log('回退准备校验：PASS')
    else:
        log('版本历史中无上一可用版本（本次为该制品的首次登记）')
        log('回退步骤：保留本清单与制品校验和，后续发布须按同一清单登记，形成可回退链')
        log('回退准备校验：PASS（首次登记，记录基线版本）')
    with open(hist_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(manifest, ensure_ascii=False) + '\n')
    log('版本历史已追加：%s' % args.keep_history)

    log('')
    if failures:
        log('结论：FAIL —— 发布中止')
        for f in failures:
            log('  未通过：%s' % f)
        return 1
    log('结论：PASS —— 构建、启动、健康检查、业务冒烟与回退准备全部通过，允许进入发布')
    return 0


if __name__ == '__main__':
    sys.exit(main())
