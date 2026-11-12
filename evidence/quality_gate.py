#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""质量门禁与覆盖率复跑脚本（真实执行，输出原始命令输出）。

执行：gofmt -l / go vet / go build / go test -count=1 / go test -coverpkg 覆盖率统计。
输出：evidence/quality_gate_output.txt（原始输出）
      evidence/coverage-gate-func.txt（逐函数覆盖率原始表）
"""
import pathlib
import re
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'evidence/quality_gate_output.txt'
RAW = ROOT / 'evidence/coverage-gate.out'
FUNC = ROOT / 'evidence/coverage-gate-func.txt'
LINES = []


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
    log('质量门禁复跑（题目 01 shop-trade）')
    log('时间：%s' % time.strftime('%Y-%m-%d %H:%M:%S'))
    log('仓库：%s' % ROOT)
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
