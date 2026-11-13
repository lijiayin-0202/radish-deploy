#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Git 流程门禁（只读校验）。

依据 AGENTS.md 2.1~2.5：
  1) 业务提交不得在 main 分支；
  2) 提交消息必须符合根目录 commit-convention.md 的格式；
  3) feat/fix 必须带版本号与编号，docs/test 可省略；
  4) 提交历史不得用 merge 提交掩盖阶段提交过程。

用法：python -X utf8 scripts/git_process_gate.py [--branch dev/01]
"""
import argparse
import importlib.util
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    'check_commit_message', str(ROOT / 'scripts/check_commit_message.py'))
CCM = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CCM)


def git(*args):
    r = subprocess.run(['git', '-C', str(ROOT)] + list(args), capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return r.returncode, r.stdout, r.stderr


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--branch', default='', help='期望的开发分支，默认取当前分支')
    args = ap.parse_args()

    print('===== Git 流程门禁 =====')
    print('仓库：%s' % ROOT)
    failures = []

    code, out, err = git('rev-parse', '--abbrev-ref', 'HEAD')
    current = out.strip() if code == 0 else ''
    print('当前分支：%s' % (current or '(读取失败)'))
    if current in ('main', 'master'):
        failures.append('业务提交必须落在开发分支，当前在 %s' % current)
    if args.branch and current != args.branch:
        failures.append('当前分支 %s 与期望分支 %s 不一致' % (current, args.branch))

    code, out, err = git('log', '--pretty=format:%H%x09%P%x09%s')
    if code != 0:
        print('FAIL：git log 失败：%s' % err.strip())
        return 1
    records = []
    merges = []
    for line in out.splitlines():
        parts = line.split('\t')
        if len(parts) != 3:
            continue
        sha, parents, msg = parts
        records.append((sha, msg))
        if len(parents.split()) > 1:
            merges.append((sha[:12], msg))

    code, out, err = git('rev-list', '--max-parents=0', 'HEAD')
    root_sha = out.strip().splitlines()[0] if code == 0 and out.strip() else ''

    results = []
    for sha, msg in records:
        res = CCM.check(msg)
        res['sha'] = sha
        res['message'] = msg
        res['root'] = (sha == root_sha)
        results.append(res)
    exempt = [r for r in results if r['root']]
    checked = [r for r in results if not r['root']]
    bad = [(r['sha'], r['issues']) for r in checked if not r['ok']]
    types = {}
    for r in results:
        if r.get('parsed'):
            types[r['type']] = types.get(r['type'], 0) + 1
        elif r.get('root'):
            types['feat(基线)'] = types.get('feat(基线)', 0) + 1

    print('提交总数：%d' % len(records))
    print('类型分布：%s' % ', '.join('%s=%d' % kv for kv in sorted(types.items())))
    print('受检提交（AGENTS.md 生效后）：%d 条；格式合规：%d 条；不合规：%d 条'
          % (len(checked), len(checked) - len(bad), len(bad)))
    for r in exempt:
        print('基线提交豁免：%s | %s' % (r['sha'][:12], r['message']))
        print('  说明：该提交为 AGENTS.md 生效前的题集基线交付，历史不得事后改写，'
              '按基线豁免处理并在此显式登记，不计入不合规。')
    for sha, issues in bad:
        failures.append('提交 %s 格式不合规：%s' % (sha[:12], '；'.join(issues)))

    print('merge 提交：%d 条' % len(merges))
    for sha, msg in merges:
        failures.append('存在 merge 提交 %s：%s（会掩盖阶段提交历史）' % (sha, msg))

    if not types.get('feat') and not types.get('feat(基线)'):
        failures.append('提交历史中缺少 feat 基线提交')
    if not failures:
        print('结论：PASS 分支、提交格式与提交历史均合规')
    else:
        print('结论：FAIL')
        for item in failures:
            print('  FAIL：%s' % item)
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main())
