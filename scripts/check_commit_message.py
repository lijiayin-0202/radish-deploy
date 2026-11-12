#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按根目录 commit-convention.md 校验提交消息格式。

重要：本脚本只读取 commit-convention.md 原文，不改写题集随附的规范原文。
用法：
  python scripts/check_commit_message.py                 # 校验当前分支真实提交
  python scripts/check_commit_message.py --message "..."   # 校验单条消息
输出包含每条提交的类型、版本号、编号、结论与不符合项，可直接作为核查证据。
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONVENTION = ROOT / 'commit-convention.md'

# [类型] [版本号] [需求/Bug编号] 中文描述；docs/test 的版本号与编号可选
PATTERN = re.compile(
    r'^\[(?P<type>feat|fix|hotfix|opt|docs|test)\]'
    r'(?:\s+\[(?P<version>v\d+\.\d+\.\d+)\])?'
    r'(?:\s+\[(?P<item>#\d+)\])?'
    r'\s+(?P<desc>\S.*)$'
)
VERSION_REQUIRED = {'feat', 'fix', 'hotfix', 'opt'}
ITEM_REQUIRED = {'feat', 'fix'}


def check(message):
    issues = []
    m = PATTERN.match(message.strip())
    if not m:
        return {
            'message': message,
            'parsed': False,
            'ok': False,
            'issues': ['不符合 `[类型] [版本号] [需求/Bug编号] 中文描述` 格式'],
        }
    typ, version, item, desc = m.group('type'), m.group('version'), m.group('item'), m.group('desc')
    if typ in VERSION_REQUIRED and not version:
        issues.append(f'{typ} 类型版本号必填，实际缺失')
    if typ in ITEM_REQUIRED and not item:
        issues.append(f'{typ} 类型需求/Bug 编号必填，实际缺失')
    if not re.search(r'[\u4e00-\u9fff]', desc):
        issues.append('描述须使用中文')
    if version and not re.fullmatch(r'v\d+\.\d+\.\d+', version):
        issues.append('版本号格式须为 v{主版本}.{次版本}.{修订号}')
    return {
        'message': message,
        'parsed': True,
        'type': typ,
        'version': version or '(无)',
        'item': item or '(无)',
        'description': desc,
        'version_required': typ in VERSION_REQUIRED,
        'item_required': typ in ITEM_REQUIRED,
        'ok': not issues,
        'issues': issues,
    }


def git_messages():
    r = subprocess.run(['git', '-C', str(ROOT), 'log', '--pretty=format:%H%x09%s'],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        raise RuntimeError('git log 失败：' + r.stderr.strip())
    out = []
    for line in r.stdout.splitlines():
        if '\t' not in line:
            continue
        sha, msg = line.split('\t', 1)
        out.append((sha, msg))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--message', help='校验单条提交消息，不读取 git log')
    ap.add_argument('--json', action='store_true', help='额外输出 JSON')
    args = ap.parse_args()

    if not CONVENTION.exists():
        print('ERROR: 缺少 commit-convention.md 原文')
        return 2
    records = [('MANUAL', args.message)] if args.message else git_messages()
    print('规范原文：commit-convention.md（题集随附副本，本脚本不改写）')
    print('校验命令：python scripts/check_commit_message.py')
    print('-' * 78)
    results = []
    for idx, (sha, msg) in enumerate(records, 1):
        res = check(msg)
        res['sha'] = sha
        results.append(res)
        print(f'[{idx}] {sha[:12]} | {msg}')
        if res['parsed']:
            print(f"     类型={res['type']} 版本号={res['version'] or '(无)'} "
                  f"编号={res['item'] or '(无)'} 描述={res['description']}")
            print(f"     必填规则：版本号={res['version_required']} 编号={res['item_required']}")
        print(f"     结论：{'PASS 符合规范' if res['ok'] else 'FAIL 不符合规范'}")
        for issue in res['issues']:
            print(f'       - {issue}')
    print('-' * 78)
    print(f'合计 {len(results)} 条，PASS {sum(r["ok"] for r in results)} 条，'
          f'FAIL {sum(not r["ok"] for r in results)} 条')
    print('说明：格式合规不等于 meegle 编号核验通过；本机 meegle CLI 不可用，'
          'feat/fix 编号核验属环境/过程证据缺失，不得伪造。')
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
