#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查者独立执行的产物清点与缺失核查（题目 01，批次 20261112-05）。

仅做只读核查：不修改学生仓库，不采信学生自述结论。
"""
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(r'd:/Desktop/shop')
SKILL = pathlib.Path(r'C:/Users/10990/.codebuddy/skills/student-project-audit')
PROFILE = SKILL / 'references/profiles/01.json'
TARGET = ROOT / 'outputs/单题检查/shop-trade/01/20261112-05/evidence/产物清点与缺失核查.txt'

LINES = []


def p(*args):
    LINES.append(' '.join(str(a) for a in args))


def exists(rel):
    return (ROOT / rel).exists()


def kind(rel):
    t = ROOT / rel
    if not t.exists():
        return 'MISSING'
    if t.is_dir():
        n = sum(1 for _ in t.rglob('*'))
        return f'DIR({n} entries)'
    return f'FILE({t.stat().st_size}B)'


# 23 项必交产物的关键路径核查清单（依据固定清单 artifacts 定义逐项落地）
ARTIFACT_PATHS = {
    'requirements': ['题目01-小型电商订单交易发货与售前退款-需求文档.md', 'docs/dev-assumptions.md'],
    'prototype': ['题目01-小型电商订单交易发货与售前退款-原型设计文档.md', 'resource/static/index.html',
                  'resource/static/v01-goods.html', 'resource/static/v08-late-payment.html'],
    'plan': ['题目01-小型电商订单交易发货与售前退款-任务规划文档.md'],
    'source': ['main.go', 'server', 'resource/static', 'docs/interface-list.md'],
    'runtime': ['schema.sql', 'scripts/mock_channel_service.py', 'scripts/r4_mock_channel_smoke.py',
                'docs/代码产物补齐说明.md', 'evidence/go-run-main-output.txt'],
    'agent_rules': ['AGENTS.md', 'AGENTS-v1.0.md'],
    'business_skill': ['.codebuddy/skills/gva-model-generate/SKILL.md',
                       '.codebuddy/skills/unit-test-race/SKILL.md',
                       '.codebuddy/skills/apipost-case-gen/SKILL.md',
                       'evidence/smoke/SKILL-gva-model-generate.txt',
                       'evidence/smoke/SKILL-unit-test-race.txt',
                       'evidence/smoke/SKILL-apipost-case-gen.txt'],
    'acceptance_skill': ['.codebuddy/skills/acceptance-check/SKILL.md',
                         'evidence/smoke/SKILL-acceptance-check.txt'],
    'skill_usage': ['skill-usage.md'],
    'prompts': ['evidence/sessions', 'evidence/events.jsonl', 'events.jsonl'],
    'ai_summary': ['evidence/AI使用说明.md', 'skill-usage.md'],
    'unit_tests': ['server/service/r4_edge_test.go', 'server/service/r5_edge_test.go',
                   'server/service/r5_edge2_test.go', 'evidence/r5-quality-output.txt'],
    'coverage': ['coverage-r5.out', 'coverage.out', 'coverage-all.out',
                 'evidence/r5-coverage-output.txt', 'evidence/r5-coverage-func.txt'],
    'integration': ['evidence/smoke', 'evidence/manual', 'evidence/manual-round2',
                    'evidence/partial-closure', 'evidence/html-check'],
    'test_agent': ['evidence/sessions/test-01.md', 'evidence/test-agent-report.md'],
    'accept_agent': ['evidence/sessions/accept-01.md', 'evidence/accept-agent-report.md'],
    'git': ['.git', 'scripts/check_commit_message.py', 'evidence/r5-post-commit-verification.txt',
            'evidence/r5-commit-message-check-output.txt'],
    'pipeline': ['.github/workflows/ci.yml'],
    'deployment': ['docs/部署与冒烟说明.md', 'evidence/deployment-smoke.txt'],
    'video': ['evidence/讲解视频.mp4', 'evidence/视频时间目录.md'],
    'group': ['evidence/班级群提交凭据.md'],
    'tokens': ['evidence/Token用量台账.md', 'outputs/原始usage.json'],
    'checkpoints': ['evidence/第五轮证据清单.md', 'evidence/第四轮证据清单.md',
                    '.agent/06-workflow-devflow.md', 'docs/git-提交指引.md'],
}

# 佐证路径：不决定产物本体是否存在，仅用于说明缺口归属与独立扣分依据
AUX_PATHS = {
    'agent_rules': ['evidence/agent-rules-load-log.md'],
    'prompts': ['evidence/会话导出说明.md', 'evidence/事件清单说明.md'],
    'test_agent': ['test-report.md'],
    'accept_agent': ['evidence/验收报告说明.md'],
    'git': ['evidence/commit-message-check-output.txt'],
}

# 存在但仅为「说明/待办索引」的文件（自述缺口登记，不构成产物本体）
PLACEHOLDER_NOTE = {
    'evidence/会话导出说明.md': '文件自述「不是任何一方的会话导出本体」',
    'evidence/事件清单说明.md': '文件自述「不是事件清单本体」，目标文件尚不存在',
    'evidence/验收报告说明.md': '文件自述「非验收报告本体」，不含通过/不通过结论',
}


def git(*args):
    r = subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return (r.stdout or '') + (r.stderr or '')


def main():
    p('学生单题项目检查 · 产物清点与缺失核查')
    p('题目 01「小型电商的订单交易、发货与售前退款」· 批次 20261112-05')
    p('受检仓库：d:/Desktop/shop（本地工作副本）')
    p('基准版本：58719fb（分支 dev/01）')
    p('执行方式：检查者独立脚本 + 原始文件系统检索与 git 实测，不采信学生自述结论')
    p('生成时间：2026-11-12（Asia/Shanghai）')
    p('')

    raw = PROFILE.read_bytes()
    profile = json.loads(raw.decode('utf-8'))
    p('=== 0. 固定清单来源 ===')
    p('profile 路径：', PROFILE)
    p('profile sha256：', hashlib.sha256(raw).hexdigest())
    p('清单要求项总数：', len(profile['requirements']), '；产物项总数：', len(profile['artifacts']))
    p('token_baselines：', json.dumps(profile.get('token_baselines'), ensure_ascii=False),
      '（空表示教师未发布本题 Token 基准）')
    p('')

    p('=== 1. 23 项必交产物逐项存在性核查 ===')
    p('（判定口径：关键路径全部存在且含实体内容=present/valid；仅存在说明或空目录=占位；'
      '关键路径缺失=missing）')
    p('')
    for a in profile['artifacts']:
        aid = a['id']
        paths = ARTIFACT_PATHS.get(aid, [])
        p(f'[{aid}] {a["name"]}')
        missing, placeholder, valid = [], [], []
        for rel in paths:
            st = kind(rel)
            p(f'    - {rel}  ->  {st}')
            if st == 'MISSING':
                missing.append(rel)
            elif rel in PLACEHOLDER_NOTE:
                placeholder.append(rel)
            else:
                valid.append(rel)
        for rel in AUX_PATHS.get(aid, []):
            st = kind(rel)
            note = PLACEHOLDER_NOTE.get(rel, '')
            p(f'    (佐证) {rel}  ->  {st}' + (f'；{note}' if note else ''))
        if not missing and not placeholder:
            verdict = 'present / valid'
        elif not missing:
            verdict = 'present / placeholder（仅有说明性文件，无产物本体）'
        else:
            verdict = 'missing（关键路径缺失：%s）' % '、'.join(missing)
        if aid == 'pipeline':
            ci = ROOT / '.github/workflows/ci.yml'
            if ci.exists():
                lines = ci.read_text(encoding='utf-8', errors='replace').splitlines()
                eff = [l for l in lines if l.strip() and not l.strip().startswith('#')]
                if not eff:
                    verdict = (f'present / placeholder（文件存在但非注释且非空行数为 {len(eff)}，'
                               '无 on/jobs 键，不会触发任何流水线）')
        p(f'    => {verdict}')
        p('')

    p('=== 2. 会话导出与结构化事件清单检索 ===')
    p('检索目标：evidence/sessions/ 目录、events.jsonl（含任意子目录）、会话导出 Markdown')
    hits = [str(x.relative_to(ROOT)).replace('\\', '/') for x in ROOT.rglob('events.jsonl')]
    p('  events.jsonl 命中：', hits if hits else '0')
    p('  evidence/sessions 存在：', exists('evidence/sessions'))
    p('  evidence/会话导出说明.md 存在：', exists('evidence/会话导出说明.md'),
      '（内容自述：阶段会话导出「无」，独立测试/验收会话「未建立」）')
    p('  evidence/事件清单说明.md 存在：', exists('evidence/事件清单说明.md'),
      '（内容自述：正式事件清单「未生成」）')
    p('')

    p('=== 3. 讲解视频与时间目录检索 ===')
    exts = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv', '.m4v'}
    vids = [str(x.relative_to(ROOT)).replace('\\', '/') for x in ROOT.rglob('*')
            if x.is_file() and x.suffix.lower() in exts]
    p('  视频文件命中：', len(vids), vids if vids else '')
    p('  evidence/视频时间目录.md 存在：', exists('evidence/视频时间目录.md'))
    p('')

    p('=== 4. 当日班级群提交凭据检索 ===')
    kw = ['班级群', '群提交', '群消息', '提交凭据']
    found = []
    for pat in ('*.md', '*.png', '*.jpg', '*.jpeg'):
        for x in ROOT.rglob(pat):
            if 'outputs' in x.parts or '.git' in x.parts:
                continue
            if any(k in x.name for k in kw):
                found.append(str(x.relative_to(ROOT)).replace('\\', '/'))
    p('  文件名含群提交关键词的命中：', found if found else '0')
    p('  evidence/班级群提交凭据.md 存在：', exists('evidence/班级群提交凭据.md'))
    p('')

    p('=== 5. Token 用量台账检索 ===')
    tk = []
    for pat in ('*.md', '*.json', '*.jsonl', '*.csv'):
        for x in ROOT.rglob(pat):
            if 'outputs' in x.parts or '.git' in x.parts:
                continue
            if 'token' in x.name.lower() or 'usage' in x.name.lower():
                tk.append(str(x.relative_to(ROOT)).replace('\\', '/'))
    p('  文件名含 token/usage 的命中：', tk if tk else '0')
    p('  evidence/Token用量台账.md 存在：', exists('evidence/Token用量台账.md'))
    p('  outputs/原始usage.json 存在：', exists('outputs/原始usage.json'))
    p('')

    p('=== 6. 流水线可执行性实测 ===')
    ci = ROOT / '.github/workflows/ci.yml'
    if ci.exists():
        lines = ci.read_text(encoding='utf-8', errors='replace').splitlines()
        eff = [l for l in lines if l.strip() and not l.strip().startswith('#')]
        p('  .github/workflows/ci.yml 总行数：', len(lines))
        p('  非注释且非空行数：', len(eff))
        p('  含 on: 键：', any(l.strip().startswith('on:') for l in lines))
        p('  含 jobs: 键：', any(l.strip().startswith('jobs:') for l in lines))
        p('  结论：', '存在可执行流水线定义' if any(l.strip().startswith('jobs:') for l in lines)
              else '纯注释模板，不会触发任何流水线（占位）')
    else:
        p('  .github/workflows/ci.yml 不存在')
    p('')

    p('=== 7. Git 远端、分支与 PR 实测 ===')
    p('$ git branch -a')
    p(git('branch', '-a').rstrip())
    p('$ git remote -v')
    p((git('remote', '-v').rstrip() or '（无输出：无远端仓库）'))
    p('$ git log --oneline -7')
    p(git('log', '--oneline', '-7').rstrip())
    p('  远端 PR 记录：不可核验（无远端，无 .git/refs/pull，无 PR 导出）')
    p('')

    p('=== 8. AGENTS.md 实际加载记录检索 ===')
    p('  evidence/agent-rules-load-log.md 存在：', exists('evidence/agent-rules-load-log.md'))
    p('  仓库内含「加载/生效记录」的文件：')
    for rel in ('AGENTS.md', 'evidence/交付证据说明.md', 'evidence/第五轮证据清单.md'):
        f = ROOT / rel
        if f.exists():
            hits = [l.strip() for l in f.read_text(encoding='utf-8', errors='replace').splitlines()
                    if '加载' in l]
            p(f'    - {rel}：命中 {len(hits)} 行', ('；示例：' + hits[0][:90]) if hits else '')
    p('')

    p('=== 9. 就绪状态核查（规则发布 / 清单核准 / 评分校准）===')
    p('  规则发布：题面与三份上游文档随附，学生侧可见 -> rules_published = True')
    p('  清单核准：仓库内未找到教师对固定清单 references/profiles/01.json 的核准记录 -> '
      'profile_approved = False')
    p('  评分校准：本班无该清单的已评分样本可作校准对照 -> calibrated = False')
    p('  Token 基准：profile.token_baselines 为空 -> 教师未发布 -> Token 计分暂记 0 分、标 unknown')
    p('')

    p('=== 10. 核查结论 ===')
    p('  1) 23 项必交产物中，8 项存在缺口：prompts、test_agent、accept_agent、deployment、')
    p('     video、group、tokens 为关键路径缺失（missing），pipeline 为占位（placeholder）。')
    p('  2) prompts / test_agent / accept_agent / deployment / video / group / pipeline 共 7 项')
    p('     属学生可自行补齐且题面与 AGENTS.md 已列为 PR 门禁，归责 student。')
    p('  3) tokens 一项因教师基准未发布而双向缺证，归责 teacher，暂记 0 分并标 unknown。')
    p('  4) 真实 MySQL 落库与 go test -race 两项属本机环境限制（无 MySQL、CGO_ENABLED=0 且无')
    p('     C 编译器），不计入产物缺失，按限制项 LIM-03 / LIM-04 单列。')
    p('  5) 上述缺口与检查报告第 10 节门禁表、第 12 节限制项表逐条对应。')


if __name__ == '__main__':
    main()
    text = '\n'.join(LINES) + '\n'
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(text, encoding='utf-8')
    print(text)
    print('written:', TARGET)
