#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""覆盖率阈值门禁：整体与核心业务包语句覆盖率必须达到阈值，不达标即以非零码退出。

题面对应：AGENTS.md Q-02「自编 Go 生产代码整体单元测试语句覆盖率 ≥85%，各核心业务包分别 ≥85%；
自编数据库访问、HTTP 处理代码不得自行排除」。本脚本把该要求固化为可执行判定，
避免流水线上「只统计覆盖率、不判断阈值」的缺陷。

用法：
    python scripts/coverage_gate.py --profile coverage.out
    python scripts/coverage_gate.py --profile coverage.out --overall 85 --pkg server/service:85
    python scripts/coverage_gate.py --profile coverage.out --json
    python scripts/coverage_gate.py --profile coverage.out --revision v1.8.0 --commit abc1234 \
        --manifest evidence/coverage/manifest.json

退出码：
    0  全部阈值达标
    1  任一阈值不达标（含 profile 缺失或不可解析）
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import time

# 核心业务包默认阈值；接入层不设阈值，仅统计展示。
DEFAULT_PACKAGES = [
    ('server/service', 85.0),
]


def parse_profile(path):
    """解析 go test -coverprofile 生成的 profile，返回 (整体, {包: (覆盖率, 语句数, 已覆盖数)})。

    注意：Go 的 mode:set profile 会把同一个代码块按测试运行次数重复写出，
    直接按行累加会把语句总数算成数倍。因此这里按「文件 + 起止位置」去重，
    语句数只计一次，命中次数取各次运行中的最大值（>0 即视为已覆盖），
    与 go tool cover -func 的口径一致。
    """
    blocks = {}
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('mode:'):
                continue
            # 形如 shop-trade/server/service/order_service.go:12.5,14.9 3 1
            try:
                loc, stmt_s, count_s = line.rsplit(' ', 2)
            except ValueError:
                continue
            try:
                stmt = int(stmt_s)
                count = int(count_s)
            except ValueError:
                continue
            prev = blocks.get(loc)
            if prev is None:
                blocks[loc] = (stmt, count)
            else:
                blocks[loc] = (prev[0], max(prev[1], count))

    total = 0
    covered = 0
    per_pkg = {}
    for loc, (stmt, count) in blocks.items():
        file_part = loc.rsplit(':', 1)[0]
        pkg = os.path.dirname(file_part).replace('\\', '/')
        # 去掉模块名前缀，便于与 --pkg server/service 形式比对
        for prefix in ('shop-trade/',):
            if pkg.startswith(prefix):
                pkg = pkg[len(prefix):]
        total += stmt
        if count > 0:
            covered += stmt
        acc = per_pkg.setdefault(pkg, [0, 0])
        acc[0] += stmt
        if count > 0:
            acc[1] += stmt
    packages = {}
    for pkg, (st, cv) in per_pkg.items():
        packages[pkg] = (round(cv * 100.0 / st, 2) if st else 0.0, st, cv)
    overall = round(covered * 100.0 / total, 2) if total else 0.0
    return overall, packages, total, covered


def main():
    ap = argparse.ArgumentParser(description='覆盖率阈值门禁')
    ap.add_argument('--profile', default='coverage.out', help='go test -coverprofile 产物路径')
    ap.add_argument('--overall', type=float, default=85.0, help='整体语句覆盖率阈值（%%）')
    ap.add_argument('--pkg', action='append', default=None,
                    help='核心包阈值，形如 server/service:85，可重复指定')
    ap.add_argument('--json', action='store_true', help='以 JSON 输出结果')
    ap.add_argument('--revision', default='', help='本轮交付版本号，写入报告头用于版本标注')
    ap.add_argument('--commit', default='', help='本轮对应的提交哈希，写入报告头')
    ap.add_argument('--manifest', default='', help='把结果另存为该 JSON 清单文件（版本标注）')
    args = ap.parse_args()

    profile = pathlib.Path(args.profile)
    if not profile.exists():
        msg = '覆盖率原始文件不存在：%s' % profile
        print(msg)
        return 1

    overall, packages, total, covered = parse_profile(profile)

    thresholds = []
    for item in (args.pkg if args.pkg is not None
                 else ['%s:%s' % (p, t) for p, t in DEFAULT_PACKAGES]):
        if ':' not in item:
            name, thr = item, 85.0
        else:
            name, thr = item.rsplit(':', 1)
            thr = float(thr)
        thresholds.append((name.strip().replace('\\', '/'), thr))

    rows = []
    failures = []
    if overall < args.overall:
        failures.append('整体覆盖率 %.2f%% < 阈值 %.2f%%' % (overall, args.overall))
    for name, thr in thresholds:
        if name not in packages:
            failures.append('核心包 %s 在覆盖率文件中不存在（无法核验阈值）' % name)
            continue
        pct, st, cv = packages[name]
        if pct < thr:
            failures.append('核心包 %s 覆盖率 %.2f%% < 阈值 %.2f%%' % (name, pct, thr))
        rows.append({'package': name, 'coverage': pct, 'statements': st,
                     'covered': cv, 'threshold': thr, 'pass': pct >= thr})

    result = {
        'profile': str(profile),
        'revision': args.revision,
        'commit': args.commit,
        'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'go_version': subprocess.run(['go', 'version'], capture_output=True,
                                     text=True, encoding='utf-8', errors='replace').stdout.strip(),
        'collect_command': 'go test -count=1 -coverpkg=./... -coverprofile=%s ./...' % profile,
        'overall_coverage': overall,
        'overall_threshold': args.overall,
        'overall_pass': overall >= args.overall,
        'statements': total,
        'covered_statements': covered,
        'packages': rows,
        'all_packages': {k: v[0] for k, v in sorted(packages.items())},
        'failures': failures,
        'pass': not failures,
    }

    if args.manifest:
        manifest_path = pathlib.Path(args.manifest)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n',
                                  encoding='utf-8')

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print('===== 覆盖率阈值门禁 =====')
        print('覆盖率文件：%s' % profile)
        if args.revision or args.commit:
            print('版本标注：%s%s' % (args.revision or '(未标注版本)',
                                     '（提交 %s）' % args.commit if args.commit else ''))
        print('生成时间：%s' % result['generated_at'])
        print('采集命令：%s' % result['collect_command'])
        print('整体语句覆盖率：%.2f%% （阈值 %.2f%%）→ %s'
              % (overall, args.overall, 'PASS' if overall >= args.overall else 'FAIL'))
        print('语句总数：%d，已覆盖：%d' % (total, covered))
        print('--- 核心业务包 ---')
        for r in rows:
            print('  %-18s %6.2f%%  (阈值 %.2f%%)  语句 %d / 覆盖 %d  → %s'
                  % (r['package'], r['coverage'], r['threshold'],
                     r['statements'], r['covered'], 'PASS' if r['pass'] else 'FAIL'))
        print('--- 其它包（仅统计）---')
        for name, pct in sorted(result['all_packages'].items()):
            if name not in [r['package'] for r in rows]:
                print('  %-18s %6.2f%%' % (name, pct))
        print('结论：%s' % ('PASS' if not failures else 'FAIL'))
        for f in failures:
            print('  未达标：%s' % f)
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main())
