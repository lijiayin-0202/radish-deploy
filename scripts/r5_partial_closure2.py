#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第五轮（续）：R-B1-01 / R-B1-05 / R-B1-06 / R-B2-01 / R-B2-02 五条 partial 闭环文档。"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from r5_closure_lib import (  # noqa: E402
    ROOT, block, build, call, case_lines, code_of, data_of, git, now,
    partial_doc, run, save, start_demo, stop_demo,
)

AUDIT = json.loads((ROOT / 'outputs/单题检查/shop-trade/01/20261112-04/audit-input.json')
                   .read_text(encoding='utf-8'))
REASON = {c['id']: c.get('reason', '') for c in AUDIT['checks']}

build()
print('go build ok')

# ============================ R-B1-01 会话导出 / events.jsonl ============================
sections = []
sessions_dir = ROOT / 'evidence/sessions'
events = list(ROOT.rglob('events.jsonl'))
sections.append('### 1.1 会话导出产物是否存在（真实文件系统核查）')
sections.append(block(
    f'$ ls evidence/sessions\n'
    f'exists={sessions_dir.exists()}\n'
    f'$ Get-ChildItem -Recurse -Filter events.jsonl\n'
    f'命中数={len(events)}'
    + ('\n' + '\n'.join(str(p) for p in events) if events else '')))
sections.append('### 1.2 `evidence/会话导出说明.md` 第 3 节原文摘录')
txt = (ROOT / 'evidence/会话导出说明.md').read_text(encoding='utf-8')
lines = txt.splitlines()
s3 = lines.index('## 3. 当前真实状态（如实登记）')
e3 = next(i for i in range(s3 + 1, len(lines)) if lines[i].startswith('## 4.'))
sections.append(block('\n'.join(lines[s3:e3]).strip()))
sections.append('### 1.3 AGENTS.md 1.1 会话隔离强制要求（原文摘录）')
ag = (ROOT / 'AGENTS.md').read_text(encoding='utf-8').splitlines()
s11 = next(i for i, l in enumerate(ag) if l.startswith('### 1.1'))
e11 = next(i for i in range(s11 + 1, len(ag)) if ag[i].startswith('### 1.2'))
sections.append(block('\n'.join(ag[s11:e11]).strip()))
sections.append('### 1.4 四轮真实提交序列（可追溯的真实提交只有 2 次）')
rc, out = git('log', '--format=%H|%ad|%s', '--date=iso')
sections.append(block('$ git log --format=%H|%ad|%s --date=iso\n' + out))

partial_doc(
    'R-B1-01', '会话导出与 events.jsonl（阶段前置关系可核实性）',
    REASON.get('R-B1-01', ''),
    '仍为 `partial`（过程证据项，属不可补造范围）',
    sections,
    gap=[
        '`evidence/sessions/` 目录**不存在**，全仓 `events.jsonl` 命中数 = 0；'
        '开发 / 测试 / 验收三方的会话导出均未建立（`evidence/会话导出说明.md` 第 3 节已如实登记）。',
        '因此**无法核实** AGENTS.md 1.1 要求的「开发前加载 AGENTS.md」「独立测试 → 独立验收 → 部署」'
        '阶段前置关系。',
        '首次提交一次性包含全部文件，需求 / 原型 / 计划 / 开发 / 测试 / 验收的**分阶段历史不可重建**，'
        '按 AGENTS.md P-08 与「不得完工后补造过程记录」，本条历史缺口不可事后补造。',
    ],
    release=[
        '由学生新建**独立**测试 Agent 会话与**独立**验收 Agent 会话，各自导出为 '
        '`evidence/sessions/test-01.md`、`evidence/sessions/accept-01.md`；'
        '开发会话按平台导出功能另存为 `evidence/sessions/dev-01.md`，不可获取字段标注「不可获取」。',
        '每份导出需包含：阶段、任务编号、模型、关联提交哈希、输入与输出位置（S-05）。',
        '**不得**由本开发会话代写三方导出；导出内容须与本仓库真实提交哈希一一对应。',
    ],
    boundary='',
)

# ============================ R-B1-05 提交序列分阶段 ============================
sections = []
rc, out = git('log', '--format=%H|%s')
sections.append('### 1.1 真实提交序列')
sections.append(block('$ git log --format=%H|%s\n' + out))
sections.append('### 1.2 真实执行 `scripts/check_commit_message.py`（原始输出）')
rc, out = run(['python', 'scripts/check_commit_message.py'])
sections.append(block(f'$ python scripts/check_commit_message.py\nexit={rc}\n' + out))
sections.append('### 1.3 格式规范原文（`commit-convention.md`）')
conv = (ROOT / 'commit-convention.md').read_text(encoding='utf-8')
sections.append(block(conv[:1200] + ('\n…（截断，完整文件见仓库根目录）' if len(conv) > 1200 else '')))
sections.append('### 1.4 分阶段提交历史核查（是否存在按阶段的独立提交）')
rc, out = git('log', '--format=%s')
kinds = {}
for s in out.splitlines():
    key = s.split(':')[0].split(']')[0].strip('[') if s else '(empty)'
    kinds[key] = kinds.get(key, 0) + 1
sections.append(block('提交类型分布：\n' + json.dumps(kinds, ensure_ascii=False, indent=2)))

partial_doc(
    'R-B1-05', '按需求 / 原型 / 计划 / 开发 / 测试 / 验收分阶段的提交历史',
    REASON.get('R-B1-05', ''),
    '仍为 `partial`（格式校验工具已落地并真实执行，分阶段历史不可重建）',
    sections,
    gap=[
        '`scripts/check_commit_message.py` 已在本轮**真实执行**（原始输出见上），'
        '两条提交中 PASS 1 条、FAIL 1 条，格式判定可复核。',
        '但首次提交是一次性基线提交（含生产代码、测试、文档、Skill 与证据），'
        '按 P-08 **不改写历史**；因此「按需求 / 原型 / 计划 / 开发 / 测试 / 验收分阶段的真实提交序列」'
        '**在本仓库不可重建**。',
        '第四轮工作区增量在本轮之前未提交，同样造成版本链与产物不对应。',
    ],
    release=[
        '本轮第五轮增量按 `docs/git-提交指引.md` 第 2.4 节分批提交（`test` 与 `docs` 严格分开），'
        '形成新的、可追溯的提交序列；提交后回补 `R-A4-04` 的最终 HEAD。',
        '分阶段历史的既有缺口**不追溯补造**：由验收 Agent 在独立会话中据实判定'
        '「首次基线提交偏差已登记、后续提交合规」，并在验收报告中如实记录该历史限制。',
    ],
    boundary='',
)

# ============================ R-B1-06 缺陷登记 → fix → 复测 → 复核 ============================
sections = []
sections.append('### 1.1 缺陷登记单文件核查（真实文件系统）')
cands = sorted(str(p.relative_to(ROOT)) for p in ROOT.rglob('*')
               if p.is_file() and ('缺陷' in p.name or 'defect' in p.name.lower()
                                    or 'bug' in p.name.lower()))
sections.append(block('命中文件：\n' + ('\n'.join(cands) if cands else '(无)')))
sections.append('### 1.2 提交历史中是否存在 `fix` 类型提交')
rc, out = git('log', '--format=%H|%s', '--grep=fix')
sections.append(block('$ git log --grep=fix\n' + (out or '(无 fix 类型提交)')))
rc, out = git('log', '--format=%H|%s')
sections.append(block('全部提交类型：\n' + out))
sections.append('### 1.3 四轮检查中登记的边界差异条目（第四轮报告摘录）')
rep = (ROOT / 'outputs/单题检查/shop-trade/01/20261112-04/检查报告.md').read_text(encoding='utf-8')
hit = [ln for ln in rep.splitlines() if ('DIFF' in ln or '差异' in ln or '缺陷' in ln)]
sections.append(block('命中行（最多 40 行）：\n' + '\n'.join(hit[:40])))
sections.append('### 1.4 复测记录载体核查')
rec = [str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and '复测' in p.name]
sections.append(block('含「复测」的证据文件：\n' + ('\n'.join(sorted(rec)) if rec else '(无)')))

partial_doc(
    'R-B1-06', '缺陷登记 → 开发 Agent fix → 测试 Agent 复测 → 验收 Agent 复核的正式交接链',
    REASON.get('R-B1-06', ''),
    '仍为 `partial`（四轮整改链真实，但正式交接单据缺失）',
    sections,
    gap=[
        '本仓库**没有飞书 Bug 登记单**，也没有 `fix` 类型提交；`fix` 提交在 AGENTS.md 2.4 下'
        '必须引用经 meegle 核验的真实 Bug 编号，而本机 `meegle` CLI 不可用（R-B4-03 `unknown`）。',
        '第 1~5 轮「发现问题 → 用户整改指令 → 补齐 → 复核」链真实存在且可核查，'
        '但复测与复核**仍在同一开发会话内完成**，不是「测试 Agent 复测 + 验收 Agent 复核」的独立交接。',
        '因此形式上的交接单据（缺陷登记单 / fix 提交 / 复测记录 / 复核结论）仍缺。',
    ],
    release=[
        '由学生在 meegle 登记**真实缺陷工作项**，取得工作项 ID；'
        '本机具备 meegle CLI 后执行 `meegle workitem get --work-item-id <编号> --project-key r17te9` 并保存原始输出。',
        '开发 Agent 在 `dev/01` 以 `[fix] [版本号] [#<真实编号>] 中文描述` 提交修复（不改写历史）。',
        '测试 Agent 在**独立会话**执行复测并保存原始输出，验收 Agent 在**独立会话**复核并出具结论；'
        '三者记录分别导出到 `evidence/sessions/`。',
        '以上四步产物齐备后本条方可升为 `pass`；任一缺失继续如实登记。',
    ],
    boundary='',
)

# ============================ R-B2-01 AGENTS.md 开发前加载记录 ============================
sections = []
sections.append('### 1.1 AGENTS.md 版本文件核查')
v1 = ROOT / 'AGENTS-v1.0.md'
sections.append(block(f'AGENTS.md exists={(ROOT / "AGENTS.md").exists()}\n'
                      f'AGENTS-v1.0.md exists={v1.exists()} size={v1.stat().st_size if v1.exists() else 0}'))
sections.append('### 1.2 AGENTS.md 第 7 章版本与变更记录（原文摘录）')
ag = (ROOT / 'AGENTS.md').read_text(encoding='utf-8').splitlines()
s7 = next(i for i, l in enumerate(ag) if l.startswith('## 7.'))
sections.append(block('\n'.join(ag[s7:]).strip()))
sections.append('### 1.3 AGENTS.md 进入版本库的提交（真实 git 追踪）')
rc, out = git('log', '--format=%H|%ad|%s', '--date=iso', '--', 'AGENTS.md', 'AGENTS-v1.0.md')
sections.append(block('$ git log -- AGENTS.md AGENTS-v1.0.md\n' + (out or '(无提交记录)')))
sections.append('### 1.4 第 0 章生效证据要求（原文摘录）')
s0 = next(i for i, l in enumerate(ag) if l.startswith('## 0.'))
e0 = next(i for i in range(s0 + 1, len(ag)) if ag[i].startswith('## 1.'))
sections.append(block('\n'.join(ag[s0:e0]).strip()))

partial_doc(
    'R-B2-01', 'AGENTS.md 在业务开发前的实际加载记录',
    REASON.get('R-B2-01', ''),
    '仍为 `partial`（文件与版本齐备、复核时确实读取，但无开发前加载记录文件）',
    sections,
    gap=[
        '`AGENTS.md`（v1.1）与 `AGENTS-v1.0.md`（v1.0）**两个版本文件都真实存在**，历史版本被保留，'
        '符合 AGENTS.md 第 7 章「不得只留最终版本」。',
        '第 0 章要求的「开发前实际加载或读取本文件的记录 + 对应任务编号 + 提交版本哈希」**没有独立记录文件**，'
        '也没有学生逐项确认记录。',
        '`git log -- AGENTS.md` 显示该文件随基线提交一次性进入版本库，'
        '**无法证明它是在业务开发开始之前加载生效的**（首次提交即包含全部文件）。',
    ],
    release=[
        '由学生在开发开始前补一份「AGENTS.md 加载生效记录」：记录加载时间、'
        '读到的版本（v1.0）与提交哈希、覆盖的开发任务编号清单，以及学生的逐项确认。',
        '后续迭代中如修改 AGENTS.md，须按第 7 章**新增版本行**并保留旧版本（当前 v1.0 / v1.1 已符合）。',
        '本条为过程证据项，历史不可补造；只能对**后续迭代**建立真实加载记录，'
        '既有迭代的缺口由验收 Agent 如实判定。',
    ],
    boundary='',
)

# ============================ R-B2-02 events.jsonl ============================
sections = []
sections.append('### 1.1 全仓 `events.jsonl` 真实查找')
hits = [str(p.relative_to(ROOT)) for p in ROOT.rglob('events.jsonl')]
sections.append(block('命中文件：\n' + ('\n'.join(hits) if hits else '(0 命中：仓库中不存在 events.jsonl)')))
sections.append('### 1.2 `evidence/事件清单说明.md` 原文')
ev_text = (ROOT / 'evidence/事件清单说明.md').read_text(encoding='utf-8')
sections.append(block(ev_text))
sections.append('### 1.3 会话导出说明中对 events.jsonl 的声明（摘录）')
sess = (ROOT / 'evidence/会话导出说明.md').read_text(encoding='utf-8').splitlines()
hit = [ln for ln in sess if 'events.jsonl' in ln]
sections.append(block('\n'.join(hit) if hit else '(无相关行)'))

partial_doc(
    'R-B2-02', 'events.jsonl 事件清单交付物',
    REASON.get('R-B2-02', ''),
    '仍为 `partial`（交付物不存在，按用户口径维持，不补造）',
    sections,
    gap=[
        '仓库中**不存在 `events.jsonl`**（全仓查找 0 命中）；'
        '`evidence/事件清单说明.md` 与 `evidence/会话导出说明.md` 均**自述不是交付物本体**。',
        '早期会话上下文多次被压缩为结构化总结，**精确时间戳已不可还原**；'
        '按用户口径与 AGENTS.md P-05，**不生成任何伪 events.jsonl 数据**。',
        '该条与 `R-B1-01` 同源：三方独立会话尚未建立，事件清单自然无法产出。',
    ],
    release=[
        '建立独立测试 / 验收会话后，从平台导出的会话记录中按真实时间戳生成 `events.jsonl`'
        '（建议字段：`timestamp` / `agent_role` / `task_id` / `commit` / `action` / `evidence_path`）。',
        '生成脚本须落在 `scripts/` 并**真实可重跑**；生成结果须与 `evidence/sessions/` 的导出内容一致。',
        '在此之前，本条维持 `partial` 并如实登记，**不得**以手工编造的时间戳充数。',
    ],
    boundary='',
)

print('partial docs (part 2) done')
