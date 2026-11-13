#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成第 9 轮 report-data.json（13 节报告叙述数据，批次 20261113-09）。

以第 8 轮报告数据为基线做定向修订：仅改本轮两个真实独立会话、会话导出与
原始提示存档所支撑的叙述；保留约束下的远端/部署/视频/群凭据缺口一律不改写。
"""
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(r'd:/Desktop/shop')
OUT = ROOT / 'outputs/单题检查/shop-trade/01/20261113-09'
R8 = ROOT / 'outputs/单题检查/shop-trade/01/20261113-08/_build_report.py'
REV = '2c76fa3（dev/01，2026-11-13）'
OLD_REV = '4e81942（dev/01，2026-11-13）'

spec = importlib.util.spec_from_file_location('r8r', str(R8))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

TABLES = m.TABLES
EV = m.EV

# ---------------------------------------------------------------- 证据索引
EV['E-27'] = (
    'recording',
    'evidence/sessions/test-agent/round9/会话导出.md；测试计划与用例清单.md；测试报告.md；'
    '执行原始输出.txt',
    '第 9 轮重建的独立测试 Agent 会话：自行核实基线 8fe01bed…（dev/01），第一手全文阅读'
    '三份上游文档与 AGENTS.md 及对应版本源码，声明不采信任何既有「已通过」结论；'
    '会话导出含任务指令全文、会话标识与独立性声明、真实命令轨迹、产出清单与诚实边界；'
    '自主执行 gofmt/vet/build/test 与 6 个门禁脚本全部 exit=0；'
    '登记 7 项缺陷（Critical 0 / Important 3 / Suggestion 4），只登记不修复',
    '2026-11-13（HEAD 8fe01be → 归档 2c76fa3）', 'A3-07 独立测试会话与隔离复测',
    '独立测试 Agent 会话自行撰写；检查者核对会话导出、执行原始输出与缺陷登记')
EV['E-28'] = (
    'recording',
    'evidence/sessions/acceptance-agent/round9/会话导出.md；验收报告.md；逐项验收结论.md；'
    '验收核验原始输出.txt；Skill 发现问题到修正到复检闭环记录.md',
    '第 9 轮重建的独立验收 Agent 会话：自行核实基线 8fe01bed…，第一手阅读题面 '
    'AC-01~AC-25 / S-01~S-05 / E-01~E-16、原型 3.1 与 3.3 M-01~M-30、任务规划、AGENTS.md '
    '及对应版本代码；明确不读取测试会话产物、不凭完成声明判通过；源码判读 + 自主执行两条路径；'
    '结论为不出具「验收通过」（AC 11 通过 / 14 待补证，3 项不通过产物缺陷 D-01~D-03、'
    '2 项约定偏差、12 项待补证 P-01~P-12），给出验收后变更的受影响回归范围；'
    '结束时 git diff --stat 为空',
    '2026-11-13（HEAD 8fe01be → 归档 2c76fa3）', 'B1-04 独立验收会话、A3-08 受影响回归、B3-02 验收 Skill 独立执行',
    '独立验收 Agent 会话自行撰写；检查者核对会话导出、逐项结论与待补证清单')
EV['E-29'] = (
    'artifact',
    'evidence/sessions/原始提示存档.md',
    '第 1 节学生本轮指令原文（撤销约束、目标、保留约束、执行顺序）；第 2/3 节两份独立会话'
    '任务指令全文的位置、字节数与 SHA-256 摘要；第 4 节提示到实现验证的步骤链与提示四要素'
    '（上下文、目标、边界、完成条件）对照；第 5 节诚实边界（平台无完整录制、开发阶段全量'
    '提示不可追溯且不按推定补记）',
    '2026-11-13（归档 2c76fa3）', 'B2-03/04/05 原始提示与会话事件链',
    '开发侧汇编，只抄录真实指令原文并指向会话本体导出，不代写结论、不补记历史提示')
EV['E-30'] = (
    'artifact',
    'evidence/sessions/会话导出索引.md；.gitignore；git 提交 0367acd / 2c76fa3',
    '三方会话隔离对照（开发 / 独立测试 / 独立验收）、两个独立会话的产出清单与交接记录、'
    '证据编号映射、36 份会话证据的保留清单；/evidence/sessions/ 目录级忽略已解除，'
    '36 份会话证据由 2c76fa3 纳入版本库；round9/ 之前历史产物全部保留未删',
    '2026-11-13（归档 2c76fa3）', 'A3-07、B1-02、B1-03、B1-04、B2 系列的交接与可及性',
    '开发侧编制；检查者核对 git ls-files evidence/sessions = 36 与两份会话导出的基线哈希')

# ---------------------------------------------------------------- 修订基线版本号
for _name, _rows in TABLES.items():
    for _row in _rows:
        if isinstance(_row, dict) and _row.get('revision') == OLD_REV:
            _row['revision'] = REV

# ---------------------------------------------------------------- 运行指标
for _row in TABLES['code_runtime']:
    if _row['metric'] in ('format_vet', 'build'):
        _row['actual'] += ('；第 9 轮两个相互隔离的独立会话又各自复跑一次该项，'
                           '退出码均为 0、结论一致（E-27、E-28）')
        _row['evidence'] = list(dict.fromkeys(_row['evidence'] + ['E-27', 'E-28']))
    elif _row['metric'] == 'deployed_smoke':
        _row['actual'] += ('；第 9 轮独立验收会话亦明确不把任何本地门禁输出当作上线冒烟证据，'
                           'PR 与部署两段仍属学生保留约束下的缺证')
        _row['evidence'] = list(dict.fromkeys(_row['evidence'] + ['E-28']))

# ---------------------------------------------------------------- 阶段检查点
for _row in TABLES['workflow']:
    if _row['stage'] == 'development':
        _row['time'] = '2026-11-12 至 2026-11-13（6cc6f13 及后续提交链）'
    elif _row['stage'] == 'testing':
        _row['time'] = '2026-11-12（开发侧脚本）＋ 2026-11-13（独立测试 Agent 会话，基线 8fe01bed…）'
        _row['snapshot'] = ('12 个 *_test.go、170 份集成证据、5 个采集脚本、InnoDB 行锁并发复现脚本、'
                            '接入层分支覆盖测试与错误码穷举脚本、版本化覆盖率快照四件套，'
                            '以及第 9 轮 evidence/sessions/test-agent/round9/ 四份独立测试会话产物')
        _row['handoff'] = ('独立测试 Agent 会话导出、测试计划与用例清单、测试报告、执行原始输出与 '
                           '7 项缺陷登记；由会话导出索引.md 登记交接，未采信开发侧结论')
        _row['status'] = 'pass'
        _row['gate'] = ('独立测试 Agent 已读取原题与对应版本代码后自主执行并导出会话，'
                        '会话隔离与只读边界成立')
        _row['evidence'] = ['E-09', 'E-10', 'E-14', 'E-19', 'E-23', 'E-24', 'E-27', 'E-30']
    elif _row['stage'] == 'acceptance':
        _row['time'] = '2026-11-13（独立验收 Agent 会话，基线 8fe01bed…）'
        _row['snapshot'] = ('evidence/sessions/acceptance-agent/round9/ 五份文件：会话导出、验收报告、'
                            '逐项验收结论、验收核验原始输出、Skill 发现问题到修正到复检闭环记录')
        _row['handoff'] = ('独立验收会话逐项给出通过/不通过/待补证与证据位置，附 PR 前八项门禁'
                           '核验清单、交付清单完整性核查与验收后变更的受影响回归范围；'
                           '结论明确为不出具「验收通过」')
        _row['status'] = 'partial'
        _row['gate'] = ('独立验收会话已成立且自主核验，但结论不通过、12 项待补证、'
                        '3 项不通过产物缺陷，PR 前门禁未全部闭环')
        _row['evidence'] = ['E-14', 'E-18', 'E-28', 'E-30']
    elif _row['stage'] == 'deployment':
        _row['snapshot'] += ('；第 9 轮学生明确保留不连远端、不做真实 CI run、不处理部署/回退/'
                             '建仓/合并发布，本阶段无新证据')
        _row['evidence'] = list(dict.fromkeys(_row['evidence'] + ['E-30']))

# ---------------------------------------------------------------- Agent 与 Skill
for _row in TABLES['agents_skills']:
    if _row['id'] == 'SKILL-ACCEPT-CHECK':
        _row['loaded_at'] = ('2026-11-12（第 3~6 轮检查期）＋ 2026-11-13 由独立验收 Agent 会话实际执行')
        _row['usage_location'] = ('第 9 轮由 evidence/sessions/acceptance-agent/round9/ 的独立验收会话'
                                  '按 5 步流程执行，产出 Skill 发现问题到修正到复检闭环记录.md、'
                                  '逐项验收结论.md 与验收报告中的 PR 前八项门禁核验清单')
        _row['input_output'] = ('输入为题面验收条件、交付物清单与对应版本代码；输出为独立逐项结论、'
                                '证据位置、门禁核验清单与受影响回归范围；本轮未触发代码修正，'
                                '闭环记录中如实写明')
        _row['limitations'] = ('独立核验结论为不出具验收通过，12 项待补证与 3 项不通过产物缺陷仍开放，'
                              '复检闭环未完成')
        _row['status'] = 'pass'
        _row['evidence'] = ['E-07', 'E-18', 'E-28', 'E-30']

# ---------------------------------------------------------------- 提示链
for _row in TABLES['prompts']:
    _loc = _row.get('prompt_location', '')
    if '（缺失）' in _loc or 'events.jsonl' in _loc:
        _row['prompt_location'] = (
            '第 9 轮 evidence/sessions/原始提示存档.md 第 1/4 节（本轮指令与步骤链）与 '
            '两份 round9/会话导出.md 第 1 节（会话指令全文）；该任务在开发阶段的原始提示仍不可追溯')
    _gap = _row.get('gap', '')
    if _gap:
        _row['gap'] = ('开发阶段原始提示与模型回复因平台无完整录制能力不可追溯，'
                       '已由 evidence/sessions/原始提示存档.md 第 5 节显式标注、不按推定补记；'
                       '第 9 轮本任务提示链与工具结果已由两份 round9/会话导出.md 补齐。')
    if _row.get('status') == 'unknown':
        _row['status'] = 'partial'
    _row['evidence'] = list(dict.fromkeys(_row['evidence'] + ['E-29', 'E-30']))

# ---------------------------------------------------------------- 限制项
LIM = {r['id']: r for r in TABLES['limitations']}

LIM['LIM-02']['score_effect'] = '计分口径未经教师核准与校准，7.11 为当前已核验得分，不是最终成绩。'

LIM['LIM-09']['reason'] = (
    '第 9 轮已交付 evidence/sessions/原始提示存档.md 与 36 份会话证据（含两份独立会话导出、'
    '测试与验收报告、原始输出），并由 2c76fa3 入库；本轮真实发生的提示链、工具结果与失败登记'
    '可核验。但平台无完整会话录制能力，仓库仍无 events.jsonl，题目 01 业务开发阶段'
    '（PRE-01 至 DB-01~UI-05）的原始提示、模型回复与工具结果无法还原。')
LIM['LIM-09']['score_effect'] = (
    'B2-03、B2-04、B2-05 由强制失败升为 partial/excellent（交付物质量满分，'
    '状态缺口为开发阶段全量不可追溯）；B2-02 维持 pass/good。')
LIM['LIM-09']['next_action'] = (
    '若平台后续提供全阶段会话录制能力，按实际时点导出开发阶段 events.jsonl 与逐条提示原文；'
    '在此之前不得以推定补记。')
LIM['LIM-09']['evidence'] = ['E-14', 'E-27', 'E-28', 'E-29', 'E-30']

LIM['LIM-11']['reason'] = (
    '第 8 轮的「放弃验收相关全部流程」指令已由第 9 轮学生指令明确撤销；'
    '独立测试会话与独立验收会话已真实重建，会话导出、报告、逐项结论与原始提示存档'
    '全部落盘并入库。但独立验收会话明确不出具「验收通过」：AC 11 项通过 / 14 项待补证，'
    '3 项不通过产物缺陷、2 项约定偏差与 12 项待补证（P-01~P-12）仍开放。')
LIM['LIM-11']['score_effect'] = (
    'A3-07 由 fail 升为 pass/good、B1-04 由 fail 升为 pass/good、'
    'A3-08 由 partial 升为 pass/good、B3-02 由 partial 升为 pass/good；'
    '四项质量均因验收结论不通过、复检未闭环而保留 good 一档。')
LIM['LIM-11']['next_action'] = (
    '按 12 项待补证与 3 项产物缺陷整改后，由新的独立验收会话按同一 Skill 复检，'
    '形成完整闭环结论。')
LIM['LIM-11']['evidence'] = ['E-27', 'E-28', 'E-30']

TABLES['limitations'].append({
    'id': 'LIM-12', 'scope': '平台会话录制能力与开发阶段全量提示', 'owner': 'platform',
    'reason': ('两份 round9/会话导出.md 是「任务指令原文 + 真实执行轨迹 + 产出清单」的可核验记录，'
               '不含隐藏推理，也不是平台级全量录制；仓库仍无 events.jsonl。'
               '开发阶段全量会话因平台无录制能力不可追溯，原始提示存档.md 第 5 节显式标注，'
               '未按推定补记、未伪造。'),
    'score_effect': ('B2-03/04/05 维持 partial（状态缺口），但交付物质量判 excellent；'
                     'B1-01 因版本链仍无法证明阶段先后维持 unknown。'),
    'next_action': ('平台提供录制能力后按实际时点导出开发阶段全量会话；'
                    '在此之前保留显式标注，不得以说明文档冒充会话本体。'),
    'evidence': ['E-29', 'E-30']})

TABLES['limitations'].append({
    'id': 'LIM-13', 'scope': '保留约束下的 PR、部署与远端 CI 证据', 'owner': 'student',
    'reason': ('学生本轮明确保留：不主动连接远端 GitHub、不做真实 CI run、'
               '不处理部署/回退/建仓/合并发布、不做讲解视频与班级群凭据。'
               'git remote -v 为空、无 main 分支、无 PR 记录、无制品与上线地址，'
               '流水线 run 记录仍为 0。'),
    'score_effect': ('B1-02 判 partial/excellent（五段前置链完成三段）；'
                     'A4-05 维持 partial/excellent，A4-06/07/08/09/10 与 '
                     'B4-01/04/05 维持 fail，均未虚增。'),
    'next_action': ('待学生放开远端与部署约束后，补 PR、状态检查、合并、部署上线与回滚证据，'
                    '并对发布提交重新执行门禁。'),
    'evidence': ['E-13', 'E-14', 'E-22', 'E-30']})

# ---------------------------------------------------------------- 理解与日表
TABLES['understanding'].append({
    'id': 'UND-10',
    'method': ('读取 evidence/sessions/ 下 36 份会话证据，重点核对两份 round9/会话导出.md 的'
               '任务指令全文、会话标识与基线哈希、命令轨迹与诚实边界，'
               '并核对原始提示存档.md 与会话导出索引.md 的隔离对照和交接记录'),
    'scope': '三方会话隔离、独立测试与验收会话的真实性、原始提示链与工具结果可追溯性',
    'result': ('开发 / 独立测试 / 独立验收三方会话相互隔离且各有真实导出；'
               '两个独立会话均自行核实基线 8fe01bed…、第一手读取题面与对应版本代码、'
               '自主执行命令并自行撰写结论；验收会话明确不出具验收通过（12 项待补证）；'
               '提示四要素与步骤链可核验，但开发阶段全量会话不可追溯'),
    'evidence': ['E-27', 'E-28', 'E-29', 'E-30']})

TABLES['daily'].append({
    'id': 'DAY-06', 'date': '2026-11-13',
    'scope': '第 9 轮重建独立测试与验收会话后的成果与过程复核（HEAD 2c76fa3）',
    'result': ('成果 6.21/7、过程 0.89/1.5、Token 0.00/1.5，扣后原始分 7.11，状态待核定；'
               '判定分布 pass 41 / partial 8 / fail 8 / unknown 1；'
               '较第 8 轮 6.54 提升 0.57，全部来自独立测试/验收会话、会话导出与原始提示存档'
               '所支撑的 A3-07、A3-08、B1-02、B1-03、B1-04、B2-03/04/05、B3-02 九项'),
    'evidence': ['E-27', 'E-28', 'E-29', 'E-30']})

# ---------------------------------------------------------------- 元信息
META = dict(m.META)
META.update({
    'delivery_date': '2026-11-13',
    'deployment': (
        '未部署。学生本轮明确保留不主动连接远端 GitHub、不做真实 CI run、'
        '不处理部署/回退/建仓/合并发布，故 git remote -v 为空、无 main 分支、'
        '无制品与上线地址，部署与上线冒烟按缺证登记（见 LIM-05、LIM-13 与 '
        'code_runtime.deployed_smoke）。第 9 轮独立验收会话亦未把任何本地门禁输出'
        '当作上线冒烟证据。'),
    'version_chain': (
        'dev/01 共 28 次提交。第 9 轮新增 2 次：'
        '0367acd [opt] [v1.9.0] 解除会话证据目录的忽略规则并保留全部历史产物 → '
        '2c76fa3 [test] [v1.9.1] 重建独立测试与验收会话并归档会话导出、报告与原始提示存档'
        '（HEAD，检查基准）。这 2 次提交不含任何业务规则、状态机、生产代码或测试断言改动，'
        '仅新增 36 份会话证据与一份忽略规则调整；round9/ 之前的历史会话产物全部保留、'
        '未删除、未改写。两个独立子代理会话自身以 8fe01bed… 为核验基线，'
        '该提交即会话证据归档前的最后交付版本。'
        '全程仅 dev/01 一个分支，无 main、无远端、无 PR 记录。'),
    'scope': (
        '题面「题目 01 + 一、所有题目共同适用的要求」全量条目，叠加固定清单 '
        'references/profiles/01.json 的 58 个原子评分项：A1 八条业务规则与五组演示场景、'
        'A2 数据与持久化、A3 代码与并发、A4 流程与交付物、B1 阶段与顺序、B2 测试与验收独立性、'
        'B3 Agent 与 Skill、B4 Git/流水线/部署/讲解。'
        '第 9 轮取证方式为：读取已入库的 36 份会话证据，核对两份 round9/会话导出.md 的'
        '任务指令全文、会话标识、基线提交哈希、命令轨迹与诚实边界，'
        '核对原始提示存档.md 的四要素对照与 SHA-256 摘要、会话导出索引.md 的三方隔离与'
        '交接记录，核对 git ls-files evidence/sessions = 36；'
        '未连接远端、未做真实 CI run、未重跑已闭环的 MySQL 落库/事务回滚/竞态探针/幂等校验、'
        '未制作讲解视频与班级群凭据、未删除任何证据文件。'),
    'token_note': (
        'Token 计分暂记 0.00/1.5、状态 unknown，理由：教师未发布本题 Token 基准'
        '（references/profiles/01.json 的 token_baselines 为空），学生亦未提交分阶段原始 usage 与'
        '去重台账，无可比总量，无法计算消耗比与可避免 Token，因此不计分、不推定学生浪费。'
        '该缺口已按教师责任登记为限制项 LIM-01 与门禁项 TOKEN；教师发布基准并由学生补交官方 usage '
        '原件后，须重新运行 token_score 并重算总分，故本批次 7.11 为当前已核验得分而非最终成绩。'
        '与第 8 轮相比，成果侧由 5.98 升至 6.21（+0.23，来自 A3-07 与 A3-08）、'
        '过程侧由 0.55 升至 0.89（+0.34，来自 B1-02/03/04、B2-03/04/05、B3-02），'
        '合计 +0.57，全部由第 9 轮两个真实独立会话及其会话导出、原始提示存档支撑。'),
})

# ---------------------------------------------------------------- 输出
EVIDENCE = []
for _eid, (_level, _loc, _sum, _rev, _scope, _prov) in EV.items():
    EVIDENCE.append({'id': _eid, 'level': _level, 'location': _loc, 'summary': _sum,
                     'revision_time': _rev, 'scope': _scope, 'provenance': _prov})

USED_SKILL_IDS = [r['id'] for r in TABLES['agents_skills']
                  if r['kind'] != 'agent_rules' and r['status'] in ('pass', 'partial')]

REPORT_DATA = {
    'schema_version': '3.0',
    'meta': META,
    'tables': TABLES,
    'evidence': EVIDENCE,
    'used_skill_ids': USED_SKILL_IDS,
}


def main():
    assert set(REPORT_DATA['tables']) == {
        'completion', 'code_runtime', 'workflow', 'prompts', 'agents_skills',
        'limitations', 'understanding', 'daily'}, '结构表不齐全'
    assert len(REPORT_DATA['tables']['completion']) == 13, '业务表行数须为 13'
    assert len(REPORT_DATA['tables']['workflow']) == 7, '七阶段须完整'
    assert len(REPORT_DATA['tables']['code_runtime']) == 8, '运行指标须完整'
    assert len(USED_SKILL_IDS) == 4 and len(set(USED_SKILL_IDS)) == 4, 'Skill 清单须唯一且为 4 项'
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / 'report-data.json'
    path.write_text(json.dumps(REPORT_DATA, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(path)
    print('tables:', sorted(REPORT_DATA['tables']))
    print('used_skill_ids:', USED_SKILL_IDS)
    print('evidence:', len(EVIDENCE))


if __name__ == '__main__':
    main()
