#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 V3 检查输入 audit-input.json（题目 01 / 学生 shop-trade / 批次 20261113-09）。

以第 8 轮输入为基线做定向修订。学生本轮撤销「放弃验收相关全部流程」约束，
真实重建两个相互隔离的独立会话（测试 / 验收）并落盘会话导出与原始提示存档。
本轮只修订这些新证据直接支撑的评分项与问题；远端 CI run、部署、视频、群凭据等
保留约束下的缺口一律不改动、不虚增。
"""
import hashlib
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(r'd:/Desktop/shop')
OUT = ROOT / 'outputs/单题检查/shop-trade/01/20261113-09'
R8 = ROOT / 'outputs/单题检查/shop-trade/01/20261113-08/_build_input.py'
PROFILE = pathlib.Path(r'C:/Users/10990/.codebuddy/skills/student-project-audit/references/profiles/01.json')

spec = importlib.util.spec_from_file_location('r8', str(R8))
r8 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r8)
m = r8.m
EV = m.EV

NEW_REV = '2c76fa3（dev/01，2026-11-13）'

# ---------------------------------------------------------------- 证据索引
EV['E-27'] = (
    'evidence/sessions/test-agent/round9/会话导出.md（第 1 节任务指令全文、第 2 节会话标识与'
    '独立性声明、第 3 节真实执行轨迹、第 4 节产出清单与诚实边界）；'
    'evidence/sessions/test-agent/round9/测试计划与用例清单.md；'
    'evidence/sessions/test-agent/round9/测试报告.md；'
    'evidence/sessions/test-agent/round9/执行原始输出.txt。'
    '独立测试 Agent 第 9 轮重建会话，自行核实基线 8fe01bed…，第一手读取三份上游文档与 '
    'AGENTS.md 及对应版本源码，独立执行 gofmt/vet/build/test 与 6 个门禁脚本，'
    '登记 7 项缺陷（Critical 0 / Important 3 / Suggestion 4），只登记不修复')
EV['E-28'] = (
    'evidence/sessions/acceptance-agent/round9/会话导出.md；验收报告.md；逐项验收结论.md；'
    '验收核验原始输出.txt；Skill 发现问题到修正到复检闭环记录.md。'
    '独立验收 Agent 第 9 轮重建会话，自行核实基线 8fe01bed…，第一手读取题面 AC-01~AC-25 / '
    'S-01~S-05 / E-01~E-16、原型 M-01~M-30 与对应版本代码，路径 A 源码判读 + 路径 B 自主执行；'
    '明确不出具「验收通过」：AC 11 项通过、14 项待补证，登记 3 项不通过产物缺陷（D-01~D-03）、'
    '2 项约定偏差与 12 项待补证（P-01~P-12），并给出验收后变更的受影响回归范围；'
    '结束时 git diff --stat 为空')
EV['E-29'] = (
    'evidence/sessions/原始提示存档.md：第 1 节学生本轮指令原文（含撤销约束、目标、保留约束、'
    '执行顺序）；第 2/3 节两份独立会话任务指令全文的位置与 SHA-256 摘要；'
    '第 4 节提示到实现验证的步骤链；第 5 节诚实边界（平台无完整录制、开发阶段全量提示'
    '不可追溯且不按推定补记）')
EV['E-30'] = (
    'evidence/sessions/会话导出索引.md：三方会话隔离对照、两个独立会话的产出清单、'
    '交接记录、证据编号映射、36 份历史与本轮会话证据的保留清单；'
    '.gitignore 解除 /evidence/sessions/ 目录级排除；'
    '提交 0367acd [opt] [v1.9.0] 与 2c76fa3 [test] [v1.9.1]（36 份会话证据入库）')

# ---------------------------------------------------------------- 产物修订
# 产物元组字段序：0 id / 1 presence / 2 validity / 3 owner / 4 reason / 5 location /
# 6 scenario / 7 usage / 8 quality_summary / 9 fix / 10 evidence
ART = {a[0]: list(a) for a in m.ARTIFACTS}

ART['test_agent'][1], ART['test_agent'][2] = 'present', 'valid'
ART['test_agent'][4] = (
    '第 9 轮真实重建独立测试 Agent 会话，产出位于 evidence/sessions/test-agent/round9/：'
    '会话导出（含任务指令全文、会话标识、真实执行轨迹与诚实边界）、测试计划与用例清单、'
    '测试报告、执行原始输出。会话自行核实基线提交 8fe01bed…（dev/01），第一手全文阅读'
    '三份上游文档与 AGENTS.md、通读对应版本源码，明确不采信任何既有「已通过」声明；'
    '独立执行 gofmt / go vet / go build / go test -count=1 与 6 个门禁脚本，全部 exit=0；'
    '登记 7 项缺陷且只登记不修复。会话对生产代码、测试代码与既有证据只读，未删除任何文件。')
ART['test_agent'][5] = ('evidence/sessions/test-agent/round9/会话导出.md;'
                        'evidence/sessions/test-agent/round9/测试计划与用例清单.md;'
                        'evidence/sessions/test-agent/round9/测试报告.md;'
                        'evidence/sessions/test-agent/round9/执行原始输出.txt;'
                        'evidence/sessions/会话导出索引.md')
ART['test_agent'][6] = (
    '检查者读取两份会话导出的第 1/2/3 节，核对任务指令原文、会话标识与基线提交哈希、'
    '命令清单与退出码，并抽查执行原始输出与测试报告中的缺陷登记，确认结论由该会话'
    '自主执行而非转述开发侧声明。')
ART['test_agent'][7] = (
    'TST-01~08 与 TST-S1~S5 由独立测试会话按题面与对应版本代码制定并执行，'
    '测试报告逐项给出「执行了什么、看到什么、判定是什么、证据在哪」。')
ART['test_agent'][8] = (
    '会话隔离、第一手读取、自主执行与缺陷登记齐备，支撑 A3-07 判通过；'
    '测试会话自己登记数据库层/竞态/五组场景正式运行未当日复跑、覆盖率快照绑 def0977 '
    '而非 HEAD，故 A3-07 质量保留 good 一档。')
ART['test_agent'][9] = ('后续交付版本变更时，以新 HEAD 重新执行一次独立测试会话并另存 round 目录；'
                        '既有 round 产物保留不删。')
ART['test_agent'][10] = ['E-04', 'E-09', 'E-12', 'E-27', 'E-30']
m.ARTIFACT_IMPACT['test_agent'] = (
    '独立测试会话产物是 A3-07 的唯一必要依赖；本轮由 missing/empty 升为 present/valid，'
    '使 A3-07 由 fail 升为 pass/good，并解除该必交产物的强制失败门禁。')

ART['accept_agent'][1], ART['accept_agent'][2] = 'present', 'valid'
ART['accept_agent'][4] = (
    '第 9 轮真实重建独立验收 Agent 会话，产出位于 evidence/sessions/acceptance-agent/round9/：'
    '会话导出、验收报告、逐项验收结论、验收核验原始输出、Skill 发现问题到修正到复检闭环记录。'
    '会话自行核实基线 8fe01bed…，第一手读取题面 AC-01~AC-25 / S-01~S-05 / E-01~E-16、'
    '原型 M-01~M-30 与状态机、任务规划、AGENTS.md 及对应版本代码；'
    '明确不读取测试会话产物、不凭完成声明判通过；采用源码判读 + 自主执行两条独立路径；'
    '结论为不出具「验收通过」（AC 11 通过 / 14 待补证，3 项不通过产物缺陷、'
    '12 项待补证），并给出验收后变更的受影响回归范围；结束时 git diff --stat 为空。')
ART['accept_agent'][5] = ('evidence/sessions/acceptance-agent/round9/会话导出.md;'
                          'evidence/sessions/acceptance-agent/round9/验收报告.md;'
                          'evidence/sessions/acceptance-agent/round9/逐项验收结论.md;'
                          'evidence/sessions/acceptance-agent/round9/验收核验原始输出.txt;'
                          'evidence/sessions/acceptance-agent/round9/'
                          'Skill 发现问题到修正到复检闭环记录.md;'
                          'evidence/sessions/会话导出索引.md')
ART['accept_agent'][6] = (
    '检查者核对会话导出的独立性声明、基线哈希与命令轨迹，读取逐项验收结论与待补证清单，'
    '并确认该会话明确不出具「验收通过」，未把开发侧或测试侧结论当作验收依据。')
ART['accept_agent'][7] = (
    'ACC-01~ACC-05 由独立验收会话按 AGENTS.md 1.4 逐项给「通过 / 不通过 / 待补证」与证据位置，'
    '并附 PR 前八项门禁核验清单、交付清单完整性核查与受影响回归范围。')
ART['accept_agent'][8] = (
    '验收会话独立性与逐项结论齐备，支撑 B1-04 判通过、A3-08 由部分完成升为通过、'
    'B3-02 由部分完成升为通过；因验收结论为不通过且 12 项待补证，三项质量均保留 good 一档。')
ART['accept_agent'][9] = ('按 12 项待补证与 3 项产物缺陷整改后，由新的独立验收会话复检并另存 '
                          'round 目录；既有 round 产物保留不删。')
ART['accept_agent'][10] = ['E-09', 'E-10', 'E-28', 'E-30']
m.ARTIFACT_IMPACT['accept_agent'] = (
    '独立验收会话产物是 B1-04 的唯一必要依赖，并同时支撑 A3-08 与 B3-02；'
    '本轮由 missing/empty 升为 present/valid，解除 B1-04 的强制失败门禁，'
    '并使验收结论触发的受影响回归范围成立。')

ART['prompts'][1], ART['prompts'][2] = 'present', 'valid'
ART['prompts'][4] = (
    '第 9 轮交付原始提示与会话导出证据：evidence/sessions/原始提示存档.md 第 1 节为学生本轮'
    '指令原文，第 2/3 节指向两份独立会话导出第 1 节的任务指令全文（含 SHA-256 摘要），'
    '第 4 节给出提示到实现验证的步骤链与提示四要素对照；两份会话导出第 3 节为真实工具结果、'
    '第 4 节为失败登记与诚实边界；会话导出索引.md 给出三方隔离对照与交接记录。'
    '36 份会话证据已由提交 2c76fa3 纳入版本库。诚实边界：平台无完整会话录制能力，'
    '仓库仍无 events.jsonl，开发阶段全量提示与模型回复不可追溯，未按推定补记。')
ART['prompts'][5] = ('evidence/sessions/原始提示存档.md;'
                     'evidence/sessions/会话导出索引.md;'
                     'evidence/sessions/test-agent/round9/会话导出.md;'
                     'evidence/sessions/acceptance-agent/round9/会话导出.md;'
                     'evidence/sessions/test-agent/round9/执行原始输出.txt;'
                     'evidence/sessions/acceptance-agent/round9/验收核验原始输出.txt')
ART['prompts'][6] = (
    '检查者读取原始提示存档第 1/4 节与两份会话导出第 1/3/4 节，核对指令原文、SHA-256 摘要、'
    '工具结果与失败登记，并核对 36 份会话证据确已入库（git ls-files evidence/sessions = 36）。')
ART['prompts'][7] = (
    '本轮真实发生的提示链（学生指令 → 两份独立会话任务指令 → 执行轨迹 → 产出 → 验证与失败登记）'
    '可完整追溯，直接支撑 B2-03、B2-04、B2-05 三项由强制失败升为部分完成。')
ART['prompts'][8] = (
    '第 9 轮交付物本身的完整性与四要素齐备度达满分档：指令原文、上下文、目标、边界、完成条件、'
    '工具结果、失败登记与交接索引均可核验；状态缺口仅在开发阶段全量会话不可追溯，'
    '按状态与质量分离原则不重复拉低质量。')
ART['prompts'][9] = ('若平台后续提供全阶段会话录制能力，按实际时点导出开发阶段 events.jsonl 与'
                     '逐条提示原文；在此之前不得以推定补记。')
ART['prompts'][10] = ['E-14', 'E-27', 'E-28', 'E-29', 'E-30']
m.ARTIFACT_IMPACT['prompts'] = (
    '提示与事件产物是 B2-03、B2-04、B2-05 三项的共同必要依赖；本轮由 missing/empty 升为 '
    'present/valid，解除三项强制失败门禁，但开发阶段全量不可追溯使三项仍判部分完成。')

ART['checkpoints'][4] = (
    '阶段留证含 evidence/第五轮证据清单.md、第四轮证据清单.md、门禁自查汇总.md、'
    'evidence/acceptance-check-rerun.md 与 .agent/06-workflow-devflow.md、docs/git-提交指引.md；'
    '第 9 轮新增 36 份会话证据入库、带提交哈希与时间点的版本化覆盖率快照、带执行时间戳的'
    '10 份门禁原始报告，以及 evidence/sessions/会话导出索引.md 的三方隔离与交接记录，'
    '使原始事件与会话导出形态得到部分补齐。业务开发阶段按七阶段冻结的交接检查点目录仍无。')
ART['checkpoints'][5] = ('evidence/sessions/会话导出索引.md;evidence/sessions/原始提示存档.md;'
                         'evidence/coverage/coverage-v1.8.0-def0977.manifest.json;'
                         'evidence/pipeline_gate_reports/门禁总表.md;'
                         'evidence/第五轮证据清单.md;evidence/第四轮证据清单.md;'
                         'evidence/门禁自查汇总.md;.agent/06-workflow-devflow.md')
ART['checkpoints'][6] = (
    '检查者核对 git ls-files evidence/sessions = 36、两份会话导出的时间与基线哈希、'
    '以及版本化快照与门禁报告的时间戳；仍未见 evidence/checkpoints/ 七阶段冻结目录。')
ART['checkpoints'][7] = '产物版本、会话导出与交接记录可定位到提交哈希；七阶段交接检查点仍缺。'
ART['checkpoints'][8] = (
    '支撑 B1-01 维持 unknown、B1-02 由 fail 升为 partial/excellent、'
    'B1-03 由 partial/basic 升为 partial/good。')
ART['checkpoints'][9] = '建立 evidence/checkpoints/，每阶段冻结产物哈希、时间、交接双方与会话导出位置。'
ART['checkpoints'][10] = ['E-10', 'E-11', 'E-14', 'E-27', 'E-28', 'E-29', 'E-30']

ART['acceptance_skill'][4] = (
    '自编验收 Skill acceptance-check 具备完整 SKILL.md（5 步流程 + 必过门禁 + 证据位置要求）；'
    '第 9 轮已由独立验收 Agent 会话按该 Skill 实际执行一次，产出 '
    'evidence/sessions/acceptance-agent/round9/Skill 发现问题到修正到复检闭环记录.md、'
    '逐项验收结论.md 与验收报告.md 中的 PR 前八项门禁核验清单。')
ART['acceptance_skill'][5] = ('.codebuddy/skills/acceptance-check/SKILL.md;'
                              'evidence/sessions/acceptance-agent/round9/'
                              'Skill 发现问题到修正到复检闭环记录.md;'
                              'evidence/sessions/acceptance-agent/round9/逐项验收结论.md;'
                              'evidence/sessions/acceptance-agent/round9/验收报告.md')
ART['acceptance_skill'][6] = (
    '检查者核对闭环记录的方法论与 SKILL.md 五步流程一致，并核对门禁核验清单八项'
    '与 AGENTS.md 2.5 的对应关系及逐项结论的证据位置。')
ART['acceptance_skill'][7] = (
    '验收 Skill 由独立会话依据原题执行，逐项给通过/不通过/待补证结论与证据位置，'
    '并登记发现问题到修正要求到复检的闭环；本轮未触发代码修正，记录中如实写明。')
ART['acceptance_skill'][8] = (
    '支撑 B3-02 由 partial 升为 pass；因独立验收结论为不出具通过且 12 项待补证，'
    '门禁清单未全部闭环，质量保留 good 一档。')
ART['acceptance_skill'][9] = '按 12 项待补证整改后由独立验收会话按同一 Skill 复检。'
ART['acceptance_skill'][10] = ['E-07', 'E-18', 'E-28', 'E-30']
m.ARTIFACT_IMPACT['acceptance_skill'] = (
    '验收 Skill 是 B3-02 的唯一直接依赖；本轮 Skill 首次由独立验收会话执行并产出闭环记录，'
    '使 B3-02 由部分完成升为通过。')

m.ARTIFACTS = [tuple(ART[a[0]]) for a in m.ARTIFACTS]

# ---------------------------------------------------------------- 评分项修订
CHECKS = {c[0]: list(c) for c in m.CHECKS}
POS = {'status': 1, 'quality': 2, 'owner': 3, 'reason': 4, 'fix': 5,
       'quality_basis': 6, 'evidence': 7, 'issue_ids': 8}


def patch(cid, **kw):
    for k, v in kw.items():
        CHECKS[cid][POS[k]] = v


patch('01-A3-07',
      status='pass', quality='good',
      reason='第 9 轮真实重建独立测试 Agent 会话（E-27）：会话自行核实基线 '
             '8fe01bed5e092e8e9a401657a12433736830df91（dev/01），第一手全文阅读三份上游文档与 '
             'AGENTS.md、通读对应版本源码，明确声明不采信任何既有「已通过」结论；'
             '独立执行 git 版本核对、gofmt、go vet、go build、go test -count=1 与 6 个门禁脚本，'
             '全部 exit=0；对覆盖率双阈值、错误码穷举 52 用例 / 27 触发 / 3 个仅文案常量做'
             '三方静态复算并确认一致；产出会话导出、测试计划与用例清单、测试报告与执行原始输出，'
             '登记 7 项缺陷（Critical 0 / Important 3 / Suggestion 4）且只登记不修复。'
             '会话与开发、验收会话隔离，对生产代码与既有证据只读，未删除任何文件。',
      fix='后续交付版本变更时以新 HEAD 重新执行一次独立测试会话；既有 round 产物保留不删。',
      quality_basis='会话隔离、第一手读取、自主执行轨迹与缺陷登记均可核验，满足「独立上下文、'
                    '读取原题及对应代码」；但测试会话自己登记数据库层、竞态探针与五组场景正式运行'
                    '未当日复跑，且覆盖率快照标注 def0977 而非 HEAD，故质量降一档为 good。',
      evidence=['E-04', 'E-09', 'E-12', 'E-27', 'E-30'],
      issue_ids=['ISS-NO-TEST-AGENT'])

patch('01-B1-04',
      status='pass', quality='good',
      reason='第 9 轮真实重建独立验收 Agent 会话（E-28）：会话自行核实基线 8fe01bed…（dev/01），'
             '第一手阅读题面 AC-01~AC-25 / S-01~S-05 / E-01~E-16、原型 3.1 显隐矩阵与 '
             '3.3 M-01~M-30、任务规划、AGENTS.md 及对应版本代码；明确不读取测试会话产物、'
             '不凭开发或测试声明判通过；以源码判读 + 自主执行两条独立路径核验，'
             '产出会话导出、验收报告、逐项验收结论、验收核验原始输出与 Skill 闭环记录；'
             '给出验收后变更的受影响回归范围，结束时 git diff --stat 为空，未修改或删除任何既有文件。'
             '返工链在 outputs/单题检查/ 第 03~08 批次与 evidence/ 整改记录中可追溯，无伪造痕迹；'
             '本轮「变更后重测验收」由独立会话完成。',
      fix='按独立验收会话登记的 12 项待补证与 3 项产物缺陷整改后，由新的独立验收会话复检。',
      quality_basis='独立验收会话及其逐项结论真实存在，返工与重测验收环节成立；'
                    '但验收结论明确为「不出具验收通过」（AC 11 通过 / 14 待补证、12 项待补证、'
                    '3 项不通过产物缺陷），复检闭环尚未完成，质量降一档为 good。',
      evidence=['E-09', 'E-10', 'E-28', 'E-30'],
      issue_ids=['ISS-NO-INDEP-ACCEPT'])

patch('01-A3-08',
      status='pass', quality='good',
      reason='缺陷修复与复测链真实存在：第 1~8 轮检查结论逐条整改，'
             'evidence/acceptance-check-rerun.md 对 G-01~G-24 逐项给结论并区分代码缺陷/环境缺失/'
             '过程证据缺失；第 8 轮 scripts/pipeline_gates.py 使任一改动后一键重跑 10 项门禁并留存'
             '带时间戳的原始报告（10/10 PASS）；第 9 轮独立验收会话（E-28）给出「验收后若修改业务'
             '代码须重新验证」的受影响回归范围，独立测试会话（E-27）提供与开发上下文隔离的复测，'
             '使「验收后变更有受影响回归」这一后半段要求成立。',
      fix='按独立验收会话的受影响回归范围，在后续任何业务代码变更后由独立测试会话执行复测并留档。',
      quality_basis='受影响回归范围已由独立验收结论界定，隔离复测已具备；但验收结论为不通过、'
                    '12 项待补证，回归范围内项目尚未全部执行完毕，质量降一档为 good。',
      evidence=['E-09', 'E-10', 'E-18', 'E-22', 'E-25', 'E-27', 'E-28'],
      issue_ids=['ISS-NO-INDEP-ACCEPT', 'ISS-RETEST-ISOLATION'])

for _cid, _title in (('01-B2-03', '全量会话、回复、工具结果、失败及附件可追溯'),
                     ('01-B2-04', '每项任务及全部分支有提示到实现验证的完整步骤'),
                     ('01-B2-05', '提示有必要上下文、目标、边界和完成条件')):
    patch(_cid, status='partial', quality='excellent',
          reason='第 9 轮交付真实会话导出与原始提示存档（E-27~E-30）并已由提交 2c76fa3 纳入版本库：'
                 'evidence/sessions/原始提示存档.md 第 1 节为学生本轮指令原文，第 2/3 节指向两份'
                 '独立会话导出第 1 节的任务指令全文并给出文件字节数与 SHA-256 摘要，'
                 '第 4 节给出「提示 → 独立会话指令 → 工具调用与结果 → 实现/产出 → 验证与失败登记 → '
                 '交接索引」的完整步骤链与提示四要素（上下文、目标、边界、完成条件）对照；'
                 '两份会话导出第 3 节为真实命令与退出码，第 4 节为失败登记与诚实边界；'
                 '会话导出索引.md 给出三方隔离对照、交接记录与 36 份证据清单。'
                 '本轮真实发生的提示链与工具结果完整可核验（对应要求：' + _title + '）。'
                 '未完成部分：平台无完整会话录制能力，仓库仍无 events.jsonl，'
                 '题目 01 业务开发阶段（PRE-01 至 DB-01~UI-05）的原始提示、模型回复与工具结果'
                 '无法还原；原始提示存档第 5 节显式标注不可追溯，未按推定补记。',
          fix='若平台后续提供全阶段会话录制能力，按实际时点导出开发阶段 events.jsonl 与逐条'
              '提示原文；在此之前不得推定补记。',
          quality_basis='第 9 轮交付物本身达满分档：指令原文、会话标识与基线哈希、命令与退出码、'
                        '工具结果、失败登记、交接索引与四要素对照齐备且相互印证；'
                        '剩余缺口是开发阶段全量不可追溯这一状态维度，已由部分完成体现，'
                        '按状态与质量分离原则不再重复拉低质量。',
          evidence=['E-14', 'E-27', 'E-28', 'E-29', 'E-30'],
          issue_ids=['ISS-NO-EVENTS'])

patch('01-B1-02',
      status='partial', quality='excellent',
      reason='题面要求「开发、独立测试、独立验收、PR 及部署」五段前置成立。第 9 轮后，'
             '开发环节有 26 次 dev/01 提交与全部源码；独立测试环节有 E-27 的独立测试会话、'
             '用例清单、测试报告与原始输出；独立验收环节有 E-28 的独立验收会话、逐项结论与'
             '验收报告；三段前置链均有真实会话导出与交接记录（E-30）。'
             '未完成部分：PR 与部署两段仍缺，且 git remote -v 为空、无 main 分支、无制品与'
             '上线地址——这是学生本轮明确保留的约束（不主动连接远端 GitHub、不做真实 CI run、'
             '不处理部署/回退/建仓/合并发布），不是既有证据被否定。',
      fix='待学生放开远端与部署约束后，补 PR 记录、状态检查、合并与部署上线证据，'
          '使五段前置链完整；在此之前不得伪造远端或部署产物。',
      quality_basis='已成立的三段前置链证据齐备、会话隔离可核验、交接记录明确；'
                    '剩余缺口纯粹是保留约束下的状态维度，按状态与质量分离原则不重复拉低质量。',
      evidence=['E-06', 'E-14', 'E-27', 'E-28', 'E-29', 'E-30'],
      issue_ids=['ISS-NO-PRECONDITIONS'])

patch('01-B1-03',
      quality='good',
      reason='阶段产物版本可追溯：26 次提交哈希、evidence/第五轮证据清单.md、第四轮证据清单.md、'
             '门禁自查汇总.md 与 .agent/06-workflow-devflow.md 均可定位到具体产物；'
             '第 9 轮新增 36 份会话证据入库、带提交哈希与生成时间的版本化覆盖率快照、'
             '带执行时间戳的 10 份门禁原始报告，以及 evidence/sessions/会话导出索引.md 的'
             '三方隔离对照与交接记录，使原始事件与会话导出形态得到实质补齐。'
             '但业务开发阶段按七阶段冻结的交接检查点目录（evidence/checkpoints/）仍无，'
             '开发阶段原始事件仍不可追溯，留证主体仍偏事后整理。',
      fix='建立 evidence/checkpoints/，每阶段冻结产物哈希、时间、交接双方与会话导出位置；'
          '开发阶段原始事件不可追溯项维持显式标注。',
      quality_basis='会话导出与带版本/时间的冻结快照使留证形态从「纯事后汇总」提升为'
                    '「部分当时冻结」，质量由 basic 升为 good；七阶段交接检查点仍缺，'
                    '状态维持部分完成。',
      evidence=['E-06', 'E-14', 'E-20', 'E-23', 'E-25', 'E-27', 'E-28', 'E-29', 'E-30'],
      issue_ids=['ISS-NO-CHECKPOINT', 'ISS-CHECKPOINT-SNAPSHOT'])

patch('01-B3-02',
      status='pass', quality='good',
      reason='自编验收 Skill acceptance-check 的 SKILL.md 结构完整（5 步流程、必过门禁清单、'
             '证据位置要求），方法论与题面 PR 门禁表一致。第 9 轮该 Skill 首次由独立验收 Agent '
             '会话按流程实际执行（E-28）：产出 Skill 发现问题到修正到复检闭环记录.md、'
             '逐项验收结论.md，并在验收报告.md 中给出 PR 前八项门禁核验清单与交付清单完整性核查，'
             '逐项标注通过/不通过/待补证与证据位置；本轮未触发代码修正，闭环记录中如实写明。'
             '方法论、独立核验与复检承诺已兑现。',
      fix='按 12 项待补证整改后由独立验收会话按同一 Skill 复检，形成完整复检闭环。',
      quality_basis='Skill 已由独立会话依据原题执行并产出闭环记录；但独立验收结论为'
                    '不出具通过、12 项待补证、3 项不通过产物缺陷，门禁清单未全部闭环，'
                    '质量降一档为 good。',
      evidence=['E-07', 'E-18', 'E-28', 'E-30'],
      issue_ids=['ISS-ACCEPT-SKILL-NORECORD'])

m.CHECKS = [tuple(CHECKS[c[0]]) for c in m.CHECKS]

# ---------------------------------------------------------------- 问题修订
DROP = {'ISS-ACCEPT-SKILL-UNUSED'}
ISSUES = {i[0]: list(i) for i in m.ISSUES}
for _k in DROP:
    ISSUES.pop(_k, None)


def setfield(iid, pos, value):
    ISSUES[iid][pos] = value


# 14 长元组（索引 8=deduction_basis / 9=deduplication / -2=evidence / -1=deductions）
setfield('ISS-NO-TEST-AGENT', 1,
         '独立测试会话已建立，但数据库层、竞态探针与五组场景正式运行未当日复跑，'
         '覆盖率快照标注提交 def0977 而非交付基线 HEAD')
setfield('ISS-NO-TEST-AGENT', 2,
         'evidence/sessions/test-agent/round9/ 四份文件证明独立测试会话真实存在且自主执行；'
         '该会话在测试报告与执行原始输出中自行登记：数据库层、竞态探针、五组场景正式运行'
         '仅能依据既有原始输出复核，未当日复跑；覆盖率版本化快照 manifest.json 的 commit 为 '
         'def0977，与本轮交付基线 8fe01bed… 不一致。')
setfield('ISS-NO-TEST-AGENT', 3,
         '检查者读取 round9/会话导出.md 第 3 节命令轨迹、测试报告.md 的诚实登记，'
         '并核对 evidence/coverage/coverage-v1.8.0-def0977.manifest.json 的 commit 字段。')
setfield('ISS-NO-TEST-AGENT', 4,
         '独立测试会话的状态根因已闭环，A3-07 由 fail 升为 pass；'
         '本质量根因使其保留 good 一档，不再归零。')
setfield('ISS-NO-TEST-AGENT', 5,
         '在具备 MySQL 实例与 C 工具链的环境重跑数据库层与竞态探针；'
         '每次交付版本变更后重新采集覆盖率并生成绑定新 HEAD 的版本化快照。')
setfield('ISS-NO-TEST-AGENT', 7,
         '第 4~8 轮为「无独立测试会话」状态根因；第 9 轮学生撤销放弃验收约束后真实重建'
         '独立测试会话，状态根因闭环，本问题收窄为复跑环境与快照版本标注这一质量项。')
setfield('ISS-NO-TEST-AGENT', 8,
         'A3-07 质量轴的独立根因是复跑限制与覆盖率快照版本标注；'
         '与已闭环的「无独立会话」状态根因分属不同事实，不重复计分。')
setfield('ISS-NO-TEST-AGENT', 9,
         '与其它问题的区分：本项只描述独立测试会话自身登记的复跑与版本标注限制，'
         '不与 ISS-RACE-FIRSTPARTY（第一方竞态探针）或 ISS-CI-NOT-EFFECTIVE（无远端 run）重复。')
setfield('ISS-NO-TEST-AGENT', -2, ['E-09', 'E-12', 'E-23', 'E-27', 'E-30'])
setfield('ISS-NO-TEST-AGENT', -1,
         [('01-A3-07', 'quality', '数据库/竞态/五组场景未当日复跑且覆盖率快照绑旧提交，质量降一档。')])

setfield('ISS-NO-INDEP-ACCEPT', 1,
         '独立验收会话已建立但明确不出具「验收通过」，12 项待补证与 3 项不通过产物缺陷使复检闭环未完成')
setfield('ISS-NO-INDEP-ACCEPT', 2,
         'evidence/sessions/acceptance-agent/round9/ 五份文件证明独立验收会话真实存在；'
         '其验收报告明确「不出具验收通过」：AC-01~AC-25 中 11 项通过、14 项待补证，'
         '登记 3 项不通过产物缺陷（D-01~D-03）、2 项约定偏差与 12 项待补证（P-01~P-12）。')
setfield('ISS-NO-INDEP-ACCEPT', 3,
         '检查者读取 round9/验收报告.md 的总体结论、逐项验收结论.md 与 '
         'Skill 发现问题到修正到复检闭环记录.md，并核对会话结束时 git diff --stat 为空的自检。')
setfield('ISS-NO-INDEP-ACCEPT', 4,
         '独立验收会话的状态根因已闭环，B1-04 由 fail 升为 pass、A3-08 由 partial 升为 pass；'
         '验收结论不通过与待补证使两项质量保留 good 一档。')
setfield('ISS-NO-INDEP-ACCEPT', 5,
         '按 12 项待补证与 3 项产物缺陷整改后，由新的独立验收会话复检并出具闭环结论。')
setfield('ISS-NO-INDEP-ACCEPT', 7,
         '第 4~8 轮为「无独立验收会话」状态根因；第 9 轮真实重建后状态根因闭环，'
         '本问题收窄为验收结论未通过、待补证未闭环这一质量项。')
setfield('ISS-NO-INDEP-ACCEPT', 8,
         'B1-04 与 A3-08 质量轴的共同独立根因是独立验收结论未通过且复检未闭环；'
         '与已闭环的「无独立会话」状态根因分属不同事实，不重复计分。')
setfield('ISS-NO-INDEP-ACCEPT', 9,
         '与 ISS-RETEST-ISOLATION 区分：后者描述复测隔离性，本项描述独立验收结论本身'
         '不通过与待补证，两者独立。')
setfield('ISS-NO-INDEP-ACCEPT', -2, ['E-09', 'E-10', 'E-28', 'E-30'])
setfield('ISS-NO-INDEP-ACCEPT', -1,
         [('01-B1-04', 'quality', '独立验收结论为不通过且 12 项待补证，质量降一档。'),
          ('01-A3-08', 'quality', '受影响回归范围已界定但尚未执行完毕，质量降一档。')])

# 13 长元组：文本字段 1/2/3/4/5/7，-2=evidence，-1=deductions，
# deduction_basis / deduplication 由 ISSUE_BASIS / ISSUE_DEDUP 注入
setfield('ISS-NO-PRECONDITIONS', 1,
         '五段前置链中 PR 与部署两段因学生本轮保留约束仍缺')
setfield('ISS-NO-PRECONDITIONS', 2,
         '开发、独立测试、独立验收三段已有真实会话导出与交接记录（E-27~E-30）；'
         '但 git remote -v 为空、无 main 分支、无 PR 记录、无制品与上线地址，'
         'PR 与部署两段无产物。学生本轮指令明确保留「不主动连接远端 GitHub、不做真实 CI run、'
         '不处理部署/回退/建仓/合并发布」。')
setfield('ISS-NO-PRECONDITIONS', 4,
         '五段前置链由「只完成一段」升为「完成三段」，B1-02 由 fail 升为部分完成；'
         'PR 与部署两段仍缺，状态不能判通过。')
setfield('ISS-NO-PRECONDITIONS', 5,
         '待学生放开远端与部署约束后补 PR、状态检查、合并与部署上线证据。')
setfield('ISS-NO-PRECONDITIONS', 7,
         '第 4~8 轮为五段只完成一段；第 9 轮三段前置链闭环，本问题收窄为 PR 与部署两段'
         '在保留约束下仍缺这一单一状态事实。')
setfield('ISS-NO-PRECONDITIONS', -2, ['E-06', 'E-14', 'E-27', 'E-28', 'E-30'])
setfield('ISS-NO-PRECONDITIONS', -1,
         [('01-B1-02', 'status', 'PR 与部署两段在保留约束下仍缺，五段前置链判部分完成。')])
m.ISSUE_BASIS['ISS-NO-PRECONDITIONS'] = (
    'B1-02 状态轴的独立根因是 PR 与部署两段前置缺失；'
    '开发、独立测试、独立验收三段已于第 9 轮闭环，按状态与质量分离原则不重复扣分。')
m.ISSUE_DEDUP['ISS-NO-PRECONDITIONS'] = (
    '与 A4-06/07、B4-01/04/05 分属阶段顺序与具体交付物两类评分要求；'
    '缺测试与验收两段的历史根因已闭环，本项只描述 PR 与部署两段。')

setfield('ISS-NO-EVENTS', 1,
         '开发阶段全量会话与 events.jsonl 因平台无录制能力不可追溯')
setfield('ISS-NO-EVENTS', 2,
         '第 9 轮 evidence/sessions/ 已交付 36 份会话证据并由 2c76fa3 入库：'
         '原始提示存档.md 含学生指令原文、两份独立会话任务指令全文位置与 SHA-256 摘要、'
         '提示到实现验证步骤链与四要素对照；两份 round9/会话导出.md 含指令全文、真实工具结果、'
         '失败登记与诚实边界。但全仓检索 events.jsonl 命中仍为 0，平台无完整会话录制能力，'
         '题目 01 业务开发阶段（PRE-01 至 DB-01~UI-05）的原始提示、模型回复与工具结果'
         '无法还原；原始提示存档第 5 节显式标注不可追溯，未按推定补记。')
setfield('ISS-NO-EVENTS', 3,
         '检查者读取原始提示存档.md 全文、两份 round9/会话导出.md 第 1/3/4 节，'
         '核对 SHA-256 摘要与 git ls-files evidence/sessions = 36，并复核全仓 events.jsonl 检索结果。')
setfield('ISS-NO-EVENTS', 4,
         '第 9 轮真实发生的提示链与工具结果使 B2-03、B2-04、B2-05 由强制失败升为部分完成；'
         '开发阶段全量不可追溯这一状态缺口仍在，三项不能判通过。')
setfield('ISS-NO-EVENTS', 5,
         '若平台提供全阶段会话录制能力，按实际时点导出开发阶段 events.jsonl 与逐条提示原文。')
setfield('ISS-NO-EVENTS', 7,
         '第 4~8 轮为「无任何会话导出」状态根因；第 9 轮会话导出与原始提示存档交付后，'
         '本问题收窄为开发阶段全量不可追溯这一单一状态事实。')
setfield('ISS-NO-EVENTS', -2, ['E-14', 'E-27', 'E-28', 'E-29', 'E-30'])
m.ISSUE_BASIS['ISS-NO-EVENTS'] = (
    'B2-03、B2-04、B2-05 三项状态轴的共同独立根因是开发阶段全量会话不可追溯；'
    '第 9 轮已交付的会话导出与提示存档属同一交付物，按三项要求分别计状态分，不按文件数重复拆分。')
m.ISSUE_DEDUP['ISS-NO-EVENTS'] = (
    '三项要求共享同一缺失产物，合并为一个问题登记；'
    '与 ISS-NO-STUDENT-SIGN、ISS-AGENT-LOAD-BIND 分属不同事实，不重复描述。')

setfield('ISS-RETEST-ISOLATION', 1,
         '隔离复测已建立，但受影响回归范围内项目尚未全部执行')
setfield('ISS-RETEST-ISOLATION', 2,
         '第 9 轮独立测试会话（E-27）提供了与开发上下文隔离的复测，独立验收会话（E-28）'
         '界定了验收后变更的受影响回归范围；但验收结论为不出具通过、12 项待补证，'
         '回归范围内项目尚未全部执行完毕。')
setfield('ISS-RETEST-ISOLATION', 4,
         '复测隔离性缺口已闭环，A3-08 由 partial 升为 pass；'
         '回归未执行完毕使其质量保留 good 一档。')
setfield('ISS-RETEST-ISOLATION', 7,
         '第 4~8 轮登记复测由开发会话自行执行；第 9 轮独立测试会话建立后隔离性闭环，'
         '本问题收窄为回归范围未全部执行。')
setfield('ISS-RETEST-ISOLATION', -2, ['E-09', 'E-27', 'E-28'])
m.ISSUE_BASIS['ISS-RETEST-ISOLATION'] = (
    'A3-08 质量轴的独立根因是受影响回归尚未执行完毕；'
    '与已闭环的「复测未隔离」分属不同事实，不重复计分。')

setfield('ISS-NO-CHECKPOINT', 1,
         '业务开发阶段按七阶段冻结的交接检查点目录仍缺')
setfield('ISS-NO-CHECKPOINT', 2,
         '第 9 轮新增 36 份会话证据、三方隔离对照与交接记录（E-30），'
         '版本化快照与门禁报告均带提交哈希与时间戳；但 evidence/checkpoints/ 七阶段'
         '冻结目录仍不存在，开发阶段原始事件不可追溯。')
setfield('ISS-NO-CHECKPOINT', 4,
         '会话导出与交接记录使 B1-03 质量由 basic 升为 good；'
         '七阶段交接检查点仍缺，状态维持部分完成。')
setfield('ISS-NO-CHECKPOINT', 7,
         '第 4~8 轮为交接检查点完全缺失；第 9 轮交接记录部分补齐，'
         '本问题收窄为七阶段冻结目录仍无。')
setfield('ISS-NO-CHECKPOINT', -2, ['E-10', 'E-11', 'E-14', 'E-27', 'E-28', 'E-29', 'E-30'])

setfield('ISS-CHECKPOINT-SNAPSHOT', 2,
         '第 9 轮会话导出索引、两份独立会话导出与带提交哈希/时间戳的快照使留证形态'
         '从「纯事后汇总」提升为「部分当时冻结」；但整轮结束后的证据清单式汇总仍占主体。')
setfield('ISS-CHECKPOINT-SNAPSHOT', 4,
         '留证形态改善使 B1-03 质量由 basic 升为 good；仍非逐阶段当时冻结，保留一档。')
setfield('ISS-CHECKPOINT-SNAPSHOT', 7,
         '第 4~8 轮为留证全为事后汇总；第 9 轮出现带时间点与哈希的当时冻结材料，'
         '本质量根因收窄为逐阶段冻结仍不完整。')
setfield('ISS-CHECKPOINT-SNAPSHOT', -2, ['E-10', 'E-23', 'E-25', 'E-27', 'E-28', 'E-30'])

setfield('ISS-ACCEPT-SKILL-NORECORD', 1,
         '独立验收会话已产出门禁核验清单，但结论为不通过且 12 项待补证，复检闭环未完成')
setfield('ISS-ACCEPT-SKILL-NORECORD', 2,
         '第 9 轮独立验收会话按 acceptance-check 的 5 步流程执行，产出 '
         'Skill 发现问题到修正到复检闭环记录.md、逐项验收结论.md 与验收报告中的 PR 前'
         '八项门禁核验清单；但结论明确不出具验收通过，竞态检测、五组场景正式证据、'
         '独立验收闭环三项门禁未以真实证据闭环，12 项待补证（P-01~P-12）仍开放。')
setfield('ISS-ACCEPT-SKILL-NORECORD', 3,
         '检查者读取闭环记录与逐项验收结论，并对照 AGENTS.md 2.5 八项门禁逐条核对。')
setfield('ISS-ACCEPT-SKILL-NORECORD', 4,
         'Skill 由独立会话执行使 B3-02 由 partial 升为 pass；'
         '门禁清单未全部闭环使其质量保留 good 一档。')
setfield('ISS-ACCEPT-SKILL-NORECORD', 5,
         '按 12 项待补证整改后由独立验收会话按同一 Skill 复检，形成完整闭环。')
setfield('ISS-ACCEPT-SKILL-NORECORD', 7,
         '第 4~8 轮为门禁清单只由开发侧自检；第 9 轮独立核验成立，'
         '本问题收窄为独立核验结论未通过、复检未闭环这一质量项。')
setfield('ISS-ACCEPT-SKILL-NORECORD', -2, ['E-07', 'E-18', 'E-28', 'E-30'])
m.ISSUE_BASIS['ISS-ACCEPT-SKILL-NORECORD'] = (
    'B3-02 质量轴的独立根因是独立验收结论不通过、12 项待补证未闭环；'
    '与已删除的 ISS-ACCEPT-SKILL-UNUSED（Skill 未被独立会话执行）分属不同事实。')
m.ISSUE_DEDUP['ISS-ACCEPT-SKILL-NORECORD'] = (
    'ISS-ACCEPT-SKILL-UNUSED 的状态根因已于第 9 轮闭环并删除；'
    '本项只描述独立核验的结论与复检缺口，不重复描述同一事实。')

m.ISSUES = [tuple(ISSUES[i[0]]) for i in m.ISSUES if i[0] in ISSUES]

# ---------------------------------------------------------------- 元信息与输出
META = dict(r8.META)
META.update({
    'audit_id': 'AUDIT-SHOP-TRADE-01-20261113-09',
    'audit_date': '2026-11-13',
    'batch': '20261113-09',
    'calibration_id': '未校准：本批次为该 profile 在本班的第 9 次 V3.0 评分，前 8 批次可作纵向对照，'
                      '但无教师核准的同批其它样本可作评分校准',
    'environment': 'Windows 11 + PowerShell（禁止使用 WSL）；Go go1.26.0 windows/amd64；'
                   '本机 CGO_ENABLED=0、无 gcc/clang、无 MySQL 客户端、无远端仓库。'
                   '学生本轮撤销「放弃验收相关全部流程」约束，真实重建两个相互隔离的独立子代理会话'
                   '（独立测试 Agent、独立验收 Agent），各自第一手读取题面与对应版本代码、'
                   '自主执行命令并自行撰写会话导出与报告；36 份会话证据已入库。'
                   '保留约束：不主动连接远端 GitHub、不做真实 CI run、不处理部署/回退/建仓/合并发布、'
                   '不做讲解视频与班级群凭据、不删除 evidence/sessions/ 目录及任何既有证据文件。'
                   '数据库层与竞态探针结论沿用既有真实原始输出，不重跑、不伪造。',
    'previous_report': 'outputs/单题检查/shop-trade/01/20261113-08/检查报告.md',
    'previous_score': '6.54',
    'change_summary': '第 8 轮归档后新增 2 次提交：'
                      '0367acd [opt] [v1.9.0] 解除会话证据目录的忽略规则并保留全部历史产物 → '
                      '2c76fa3 [test] [v1.9.1] 重建独立测试与验收会话并归档会话导出、报告与'
                      '原始提示存档（HEAD，检查基准）。'
                      '本轮真实启动两个相互隔离的独立子代理会话，基线均为 8fe01bed…（dev/01）：'
                      '独立测试 Agent 产出 evidence/sessions/test-agent/round9/ 四份文件'
                      '（会话导出含任务指令全文、会话标识、执行轨迹与诚实边界；测试计划与用例清单；'
                      '测试报告；执行原始输出），自主执行 gofmt/vet/build/test 与 6 个门禁脚本全部 '
                      'exit=0，登记 7 项缺陷只登记不修复；'
                      '独立验收 Agent 产出 evidence/sessions/acceptance-agent/round9/ 五份文件'
                      '（会话导出、验收报告、逐项验收结论、验收核验原始输出、Skill 闭环记录），'
                      '明确不出具验收通过（AC 11 通过 / 14 待补证、3 项不通过产物缺陷、'
                      '12 项待补证），结束时 git diff --stat 为空。'
                      '开发侧另编制 evidence/sessions/原始提示存档.md 与 会话导出索引.md，'
                      '记录学生本轮指令原文、两份会话指令全文位置与 SHA-256、提示四要素对照、'
                      '三方隔离对照与交接记录；round9/ 之前的历史会话产物全部保留未删。'
                      '本批次取证方式为读取已入库文件与两份会话导出的真实执行轨迹，'
                      '未连接远端、未做真实 CI run、未重跑已闭环的数据库与竞态校验。',
    'history_resolution': '第 8 轮判定分布 pass 37 / partial 6 / fail 14 / unknown 1，'
                          '已核验得分 6.54/10（成果 5.98/7、过程 0.55/1.5、Token 0.00/1.5 unknown）；'
                          '旧报告与旧分数保留不覆盖，本轮不沿用旧成绩。'
                          '第 8 轮登记的问题按新证据逐项复核：'
                          '(1) ISS-NO-TEST-AGENT —— 独立测试会话真实重建，状态根因闭环，'
                          'A3-07 由 fail 升为 pass/good；问题收窄为复跑限制与覆盖率快照绑旧提交的'
                          '质量根因并保留。'
                          '(2) ISS-NO-INDEP-ACCEPT —— 独立验收会话真实重建，B1-04 由 fail 升为 '
                          'pass/good、A3-08 由 partial 升为 pass/good；问题收窄为验收结论不通过与'
                          '12 项待补证的质量根因并保留。'
                          '(3) ISS-ACCEPT-SKILL-UNUSED —— 验收 Skill 首次由独立会话执行，'
                          '状态根因闭环并删除；ISS-ACCEPT-SKILL-NORECORD 收窄为复检未闭环的'
                          '质量根因，B3-02 由 partial 升为 pass/good。'
                          '(4) ISS-NO-EVENTS —— 会话导出与原始提示存档交付并入库，'
                          'B2-03/04/05 由强制失败升为 partial/excellent；'
                          '开发阶段全量会话不可追溯这一状态根因保留，故不判通过。'
                          '(5) ISS-NO-PRECONDITIONS —— 五段前置链由完成一段升为三段，'
                          'B1-02 由 fail 升为 partial/excellent；PR 与部署两段因学生保留约束仍缺。'
                          '(6) ISS-NO-CHECKPOINT / ISS-CHECKPOINT-SNAPSHOT —— 会话导出与交接记录'
                          '使 B1-03 质量由 basic 升为 good，状态维持 partial；'
                          '七阶段冻结检查点仍缺。'
                          '(7) ISS-RETEST-ISOLATION —— 独立测试会话使复测隔离性闭环，'
                          '问题收窄为受影响回归未执行完毕。'
                          '维持不变的缺口：ISS-CI-NOT-EFFECTIVE（A4-05 仍 partial/excellent，'
                          '无远端 run 记录）、ISS-NO-DEPLOY / ISS-NO-ROLLBACK（A4-06/07 fail）、'
                          'ISS-NO-VIDEO（A4-08/09 fail）、ISS-NO-GROUP（A4-10 fail）、'
                          'ISS-NO-MCP-REPO / ISS-NO-PR（B4-01/04/05 fail）、'
                          'ISS-NO-STUDENT-SIGN、ISS-AGENT-LOAD-BIND、ISS-RACE-FIRSTPARTY、'
                          'ISS-BASE-COMMIT-FMT、ISS-NO-MEEGLE、ISS-ONE-SHOT-COMMIT、'
                          'ISS-STAGE-HISTORY、ISS-APIPOST-NOT-RUN、ISS-PROTO-BROWSER、'
                          'ISS-TICKET-SCOPE、ISS-DB-SCREENSHOT-UNTRACKED。'
                          '上述 fail 项均属学生本轮明确保留的约束或尚无新证据的事实，未虚增。'
                          'B1-01 因版本链仍无法证明阶段先后维持 unknown；'
                          'Token 因教师基准未发布维持 unknown 与 0 分，归责 teacher。',
})


def main():
    profile = json.loads(PROFILE.read_text(encoding='utf-8'))
    data = {
        'schema_version': '3.0',
        'student': 'shop-trade',
        'question': profile['question'],
        'revision': NEW_REV,
        'profile_sha256': hashlib.sha256(PROFILE.read_bytes()).hexdigest(),
        'audit_meta': META,
        'artifacts': m.build_artifacts(),
        'checks': m.build_checks(profile),
        'issues': m.build_issues(),
        'token_usage': m.TOKEN,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'audit-input.json').write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('audit-input.json written: artifacts=%d checks=%d issues=%d'
          % (len(data['artifacts']), len(data['checks']), len(data['issues'])))


if __name__ == '__main__':
    main()
