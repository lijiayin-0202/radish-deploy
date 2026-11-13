#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查者对第 7 轮新增门禁脚本的本地实测（正向、反向、可执行性）。

实测四条：
  1) 真实覆盖率文件 → 阈值判定必须 PASS（exit 0）
  2) 低覆盖样本     → 阈值判定必须 FAIL（exit 1），证明阈值不是摆设
  3) 核心包缺失     → 必须判为不可核验并 FAIL（exit 1）
  4) 部署门禁       → 构建/启动/健康检查/业务冒烟/回退准备必须全流程 PASS（exit 0）

输出：outputs/单题检查/shop-trade/01/20261113-07/evidence/gate_scripts_verify.txt
"""
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(r'd:/Desktop/shop')
OUT = ROOT / 'outputs/单题检查/shop-trade/01/20261113-07/evidence/gate_scripts_verify.txt'
LINES = []


def log(t=''):
    LINES.append(t)
    print(t)


def run(label, args, expect_zero, note):
    log('')
    log('=' * 78)
    log(label)
    log('命令：%s' % ' '.join(args))
    log('预期：%s' % note)
    log('=' * 78)
    p = subprocess.run(args, cwd=str(ROOT), capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    log((p.stdout or '') + (p.stderr or ''))
    ok = (p.returncode == 0) == expect_zero
    log('退出码：%d（%s）' % (p.returncode, '符合预期' if ok else '不符合预期'))
    log('判定：%s' % ('PASS' if ok else 'FAIL'))
    return ok


def main():
    results = []
    log('===== 第 7 轮新增门禁脚本本地实测 =====')
    log('时间：%s' % time.strftime('%Y-%m-%d %H:%M:%S'))
    log('仓库：%s' % ROOT)

    results.append(run(
        '用例 1（正向）：真实覆盖率文件必须通过阈值判定',
        [sys.executable, '-X', 'utf8', 'scripts/coverage_gate.py',
         '--profile', 'evidence/coverage-gate.out', '--overall', '85', '--pkg', 'server/service:85'],
        True,
        'exit 0；整体与核心业务包 server/service 均达标'))

    results.append(run(
        '用例 2（反向）：低覆盖样本必须被阈值判定拦下',
        [sys.executable, '-X', 'utf8', 'scripts/coverage_gate.py',
         '--profile', 'outputs/单题检查/shop-trade/01/20261113-07/evidence/low_coverage_sample.out',
         '--overall', '85', '--pkg', 'server/service:85'],
        False,
        'exit 1；证明阈值判定会真实阻断，而非只统计不判定'))

    results.append(run(
        '用例 3：核心业务包缺失时必须被判为不可核验并失败',
        [sys.executable, '-X', 'utf8', 'scripts/coverage_gate.py',
         '--profile', 'evidence/coverage-gate.out', '--pkg', 'server/nonexistent:85'],
        False,
        'exit 1；核心包不存在时不得静默放过'))

    results.append(run(
        '用例 4：基础部署门禁必须全流程通过',
        [sys.executable, '-X', 'utf8', 'scripts/deploy_gate.py',
         '--addr', '127.0.0.1:18080', '--out', 'dist'],
        True,
        'exit 0；构建、启动、健康检查、业务冒烟与回退准备全部通过'))

    log('')
    log('===== 实测汇总 =====')
    for i, ok in enumerate(results, 1):
        log('用例 %d：%s' % (i, 'PASS' if ok else 'FAIL'))
    log('合计 %d 个用例，PASS %d 个，FAIL %d 个'
        % (len(results), sum(1 for r in results if r), sum(1 for r in results if not r)))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text('\n'.join(LINES) + '\n', encoding='utf-8')
    print('written: %s' % OUT)
    return 0 if all(results) else 1


if __name__ == '__main__':
    sys.exit(main())
