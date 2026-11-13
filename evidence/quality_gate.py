#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""质量门禁与覆盖率复跑脚本（真实执行，输出原始命令输出）。

执行：gofmt -l / go vet / go build / go test -count=1 / go test -coverpkg 覆盖率统计
      / scripts/coverage_gate.py（阈值判定，输出带版本标注的逐包口径）。
输出：evidence/quality_gate_output.txt（原始输出）
      evidence/coverage-gate-func.txt（逐函数覆盖率原始表）
      evidence/coverage-gate.out（覆盖率原始 profile）

用法：python -X utf8 evidence/quality_gate.py [--revision v1.8.0] [--commit abc1234]
"""
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'evidence/quality_gate_output.txt'
RAW = ROOT / 'evidence/coverage-gate.out'
FUNC = ROOT / 'evidence/coverage-gate-func.txt'
LINES = []


def read_flag(name, default=''):
    if name in sys.argv:
        index = sys.argv.index(name)
        if index + 1 < len(sys.argv):
            return sys.argv[index + 1]
    return default


def log(text=''):
    LINES.append(text)
    print(text)


def run(cmd):
    log('')
    log('=' * 78)
    log('$ %s' % ' '.join(cmd))
    log('=' * 78)
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                          encoding='utf-8', errors='replace')
    out = (proc.stdout or '') + (proc.stderr or '')
    log(out.rstrip())
    log('[exit=%d]' % proc.returncode)
    return proc.returncode, out


def main():
    revision = read_flag('--revision', '')
    commit = read_flag('--commit', '')
    log('质量门禁复跑（题目 01 shop-trade）')
    log('时间：%s' % time.strftime('%Y-%m-%d %H:%M:%S'))
    log('仓库：%s' % ROOT)
    log('版本标注：%s%s' % (revision or '(未标注)', '（提交 %s）' % commit if commit else ''))
    log('Go：%s' % subprocess.run(['go', 'version'], capture_output=True, text=True).stdout.strip())
    code, _ = run(['gofmt', '-l', '.'])
    code2, _ = run(['go', 'vet', './...'])
    code3, _ = run(['go', 'build', './...'])
    code4, _ = run(['go', 'test', '-count=1', './...'])
    code5, cov_out = run(['go', 'test', '-count=1', '-coverpkg=./...',
                          '-coverprofile=%s' % RAW, './...'])
    func = subprocess.run(['go', 'tool', 'cover', '-func=%s' % RAW], cwd=ROOT, capture_output=True,
                          text=True, encoding='utf-8', errors='replace')
    FUNC.write_text(func.stdout, encoding='utf-8')
    log('')
    log('=' * 78)
    log('$ go tool cover -func=%s' % RAW.name)
    log('=' * 78)
    log(func.stdout.rstrip())
    gate_cmd = [sys.executable, '-X', 'utf8', 'scripts/coverage_gate.py',
                '--profile', str(RAW), '--overall', '85', '--pkg', 'server/service:85']
    if revision:
        gate_cmd += ['--revision', revision]
    if commit:
        gate_cmd += ['--commit', commit]
    gate = subprocess.run(gate_cmd, cwd=ROOT, capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
    log('')
    log('=' * 78)
    log('$ %s' % ' '.join(gate_cmd[1:]).replace(sys.executable, 'python'))
    log('=' * 78)
    log((gate.stdout or '').rstrip())
    log('[exit=%d]' % gate.returncode)
    total = re.search(r'total:\s+\(statements\)\s+([\d.]+)%', func.stdout)
    total_pct = float(total.group(1)) if total else 0.0
    pkgs = {}
    for line in cov_out.splitlines():
        m = re.match(r'ok\s+(\S+)\s+([\d.]+)s\s+coverage:\s+([\d.]+)% of statements', line.strip())
        if m:
            pkgs[m.group(1)] = float(m.group(3))
    OUT.write_text('\n'.join(LINES) + '\n', encoding='utf-8')
    print('written: %s' % OUT)
    print('gofmt/vet/build/test/coverage exit = %d/%d/%d/%d/%d'
          % (code, code2, code3, code4, code5))
    print('total_coverage=%.1f%%' % total_pct)
    for pkg, pct in sorted(pkgs.items()):
        print('  %-45s %5.1f%%' % (pkg, pct))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
