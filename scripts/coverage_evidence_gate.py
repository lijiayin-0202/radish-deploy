#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""覆盖率证据一致性门禁（只读校验）。

依据 AGENTS.md Q-02 与 2.5「覆盖率：整体 ≥85%，各核心业务包分别 ≥85%」：
  1) evidence/coverage/ 下存在带版本标注的覆盖率原始文件、逐函数表、门禁判定与清单四件套；
  2) 清单登记的提交哈希在 git 历史中真实存在；
  3) 清单登记的整体与核心业务包覆盖率均达标；
  4) 用 scripts/coverage_gate.py 的同一口径重新解析快照，数字与清单一致（防篡改/防口径漂移）。

用法：python -X utf8 scripts/coverage_evidence_gate.py
"""
import importlib.util
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SNAP_DIR = ROOT / 'evidence/coverage'
SPEC = importlib.util.spec_from_file_location(
    'coverage_gate', str(ROOT / 'scripts/coverage_gate.py'))
CG = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CG)


def git_exists(sha):
    r = subprocess.run(['git', '-C', str(ROOT), 'cat-file', '-e', '%s^{commit}' % sha],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.returncode == 0


def main():
    print('===== 覆盖率证据一致性门禁 =====')
    print('快照目录：%s' % SNAP_DIR)
    failures = []
    if not SNAP_DIR.is_dir():
        print('FAIL：缺少版本化覆盖率快照目录')
        return 1
    manifests = sorted(SNAP_DIR.glob('*.manifest.json'))
    if not manifests:
        print('FAIL：未找到任何覆盖率清单（*.manifest.json）')
        return 1

    for manifest_path in manifests:
        prefix = manifest_path.name[:-len('.manifest.json')]
        print('-' * 96)
        print('快照前缀：%s' % prefix)
        profile = SNAP_DIR / (prefix + '.out')
        func = SNAP_DIR / (prefix + '.func.txt')
        gate = SNAP_DIR / (prefix + '.gate.txt')
        for path in (profile, func, gate):
            if not path.exists():
                failures.append('快照四件套不完整：缺少 %s' % path.name)
        data = json.loads(manifest_path.read_text(encoding='utf-8'))
        revision = data.get('revision') or '(未标注)'
        commit = data.get('commit') or '(未标注)'
        print('版本标注：%s；提交哈希：%s；生成时间：%s'
              % (revision, commit, data.get('generated_at')))
        print('采集命令：%s' % data.get('collect_command'))
        if revision == '(未标注)' or commit == '(未标注)':
            failures.append('%s：清单缺少版本号或提交哈希标注' % prefix)
        elif not git_exists(commit):
            failures.append('%s：清单登记的提交 %s 在 git 历史中不存在' % (prefix, commit))
        if not profile.exists():
            continue
        overall, packages, total, covered = CG.parse_profile(str(profile))
        print('重新解析快照：整体 %.2f%%（%d/%d）' % (overall, covered, total))
        if abs(overall - float(data.get('overall_coverage', 0))) > 0.01:
            failures.append('%s：清单登记整体覆盖率 %.2f%% 与重新解析的 %.2f%% 不一致'
                            % (prefix, float(data.get('overall_coverage', 0)), overall))
        if covered != data.get('covered_statements') or total != data.get('statements'):
            failures.append('%s：清单语句数（%s/%s）与重新解析（%d/%d）不一致'
                            % (prefix, data.get('covered_statements'), data.get('statements'),
                               covered, total))
        for name, (pct, stmts, cov) in sorted(packages.items()):
            print('  %-22s %6.2f%%  (%d/%d)' % (name, pct, cov, stmts))
        service = packages.get('server/service')
        if service is None:
            failures.append('%s：快照缺少核心业务包 server/service' % prefix)
        else:
            if service[0] < 85:
                failures.append('%s：核心业务包 server/service 覆盖率 %.2f%% 低于 85%%'
                                % (prefix, service[0]))
        if overall < 85:
            failures.append('%s：整体覆盖率 %.2f%% 低于 85%%' % (prefix, overall))
    print('-' * 96)
    print('快照组数：%d；不合格项：%d' % (len(manifests), len(failures)))
    for item in failures:
        print('  FAIL：%s' % item)
    print('结论：%s' % ('PASS 覆盖率证据齐备、可追溯且达标' if not failures else 'FAIL'))
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main())
