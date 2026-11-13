#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成第 8 轮 report-data.json（13 节报告叙述数据，批次 20261113-08）。

以第 7 轮报告数据为基线做定向修订：仅改本轮有已提交证据支撑的叙述与表格行，
其余逐字沿用；按学生指示不新增任何验收类结论或会话产物。
"""
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(r'd:/Desktop/shop')
OUT = ROOT / 'outputs/单题检查/shop-trade/01/20261113-08'
R7 = ROOT / 'outputs/单题检查/shop-trade/01/20261113-07/_build_report.py'
REV = '4e81942（dev/01，2026-11-13）'
OLD_REV = 'ed675f7（dev/01，2026-11-13）'

spec = importlib.util.spec_from_file_location('r7r', str(R7))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

TABLES = m.TABLES
EV = m.EV

# ---------------------------------------------------------------- 证据索引
EV['E-22'] = (
    'artifact',
    '.github/workflows/ci.yml；scripts/pipeline_gates.py；evidence/pipeline_gate_reports/门禁总表.md；'
    'evidence/pipeline_gate_reports/*.txt；evidence/CI流水线说明.md',
    '生效路径流水线扩展为 3 作业 23 步（quality-gate 13 / process-gate 6 / deploy-gate 4），'
    '逐项映射 AGENTS.md 2.5 八项门禁；与 CI 同源同序的 10 项门禁总控于 2026-11-13 10:12:23 '
    '本地真实执行 10/10 PASS、不通过 0、各门禁退出码均为 0，原始输出与门禁总表全部留档',
    '2026-11-13（HEAD 4e81942）', '流水线门禁配置的完整性、可复跑性与真实执行输出',
    '学生提交；检查者读取生效路径 YAML、门禁总表与 10 份原始报告核对作业数、步骤数与退出码')
EV['E-23'] = (
    'raw_tool',
    'server/api/v1/api_branch_coverage_test.go；evidence/coverage/README.md；'
    'evidence/coverage/coverage-v1.8.0-def0977.out / .func.txt / .gate.txt / .manifest.json；'
    'evidence/coverage-report.md',
    '接入层分支覆盖测试使 server/api/v1 由 82.21%（268/326）升至 99.08%（323/326），'
    '整体由 94.19% 升至 97.63%（1563/1601），server/service 98.47%（1161/1179）；'
    '版本化快照绑定 revision v1.8.0、提交 def0977、生成时间 2026-11-13 09:05:16、'
    'Go 版本与采集命令，清单与重新解析 profile 数字一致',
    '2026-11-13（HEAD bb1ca7f）', '覆盖率三口径达标、接入层均衡性与原件版本可核验性',
    '学生提交；检查者读取 manifest 与 .gate/.func 明细，并由一致性门禁复算')
EV['E-24'] = (
    'raw_tool',
    'scripts/error_code_enumeration.py；evidence/error_code_enumeration.txt / .json / _runtime.log',
    '真实启动 demo-memory 服务后以 HTTP 逐条探测 M-01~M-30：52 条用例、断言未命中 0；'
    '30 个错误码中 27 个作为业务错误码被真实触发，M-07/M-16/M-21 经源码核对仅为 '
    'server/service/types.go 的文案常量且无任何分支引用，未观测码 0',
    '2026-11-13（HEAD def0977）', '错误码清单与业务分支映射的逐条可复算性',
    '学生执行原始输出；检查者核对脚本、JSON 结果与运行日志的一致性')
EV['E-25'] = (
    'raw_tool',
    'scripts/coverage_evidence_gate.py；scripts/scenario_gate.py；scripts/git_process_gate.py；'
    'scripts/record_gate.py；scripts/secret_scan_gate.py；evidence/pipeline_gate_reports/*.txt',
    '五项过程门禁真实执行：覆盖率证据一致性 PASS（清单提交哈希存在、数字一致、双阈值达标）、'
    '五组必演示场景 PASS（5 组 38 条断言、关键失败码全命中）、Git 流程 PASS（dev/01、22 条受检'
    '提交格式全合规、0 merge、基线提交显式豁免）、AI 与 Skill 记录齐备 13/13、'
    '敏感信息扫描 211 文件 0 命中',
    '2026-11-13（HEAD 4e81942）', '过程类门禁的可执行性与原始输出完整性',
    '学生脚本执行；检查者读取门禁总表与对应原始报告核对退出码与判定')
EV['E-26'] = (
    'artifact',
    'scripts/coverage_gate.py；evidence/quality_gate.py；evidence/quality_gate_output.txt；'
    'evidence/coverage-gate-func.txt；evidence/coverage-gate.out；'
    'evidence/commit-message-check-output.txt',
    '覆盖率门禁脚本新增 --revision/--commit/--manifest 版本标注与清单输出；'
    '质量门禁原始输出自带版本/提交标注并调用双阈值判定；提交格式门禁原始输出留档',
    '2026-11-13（HEAD bb1ca7f）', '门禁原始输出与交付版本、提交哈希的绑定',
    '学生提交；检查者读取脚本参数与原始输出核对标注字段')

# ---------------------------------------------------------------- 修订基线版本号
for _name, _rows in TABLES.items():
    for _row in _rows:
        if isinstance(_row, dict) and _row.get('revision') == OLD_REV:
            _row['revision'] = REV

# ---------------------------------------------------------------- 运行指标
for _row in TABLES['code_runtime']:
    if _row['metric'] == 'format_vet':
        _row['command'] = ('gofmt -l . ； go vet ./... ； python -X utf8 scripts/pipeline_gates.py'
                           '（10 项门禁总控，其中格式检查与静态检查为前两项）')
        _row['actual'] = ('gofmt -l . 无输出；go vet 无输出，exit=0；'
                          '第 8 轮 10 项门禁总控中格式检查 gofmt 与静态检查 go vet 两项均 PASS、退出码 0')
        _row['evidence'] = ['E-13', 'E-22', 'E-25']
    elif _row['metric'] == 'abnormal_business':
        _row['command'] = ('越权、幂等、重复、并发、非法参数与未知订单共 38 类负向断言；'
                           '真实 InnoDB 行锁下退款/发货互斥裁决 5 轮与外部事务持锁阻塞探针；'
                           '第 8 轮新增 M-01~M-30 错误码逐条 HTTP 穷举 52 条用例')
        _row['actual'] = ('全部返回预期错误码；重复支付/退款通知不重复记款与退款；20 并发守恒；'
                          '6 类越权全部 M-20；真实行锁下 5 轮互斥裁决每次只产生一种合法结果；'
                          '错误码穷举 52 条用例断言未命中 0，27 个错误码被真实触发，'
                          'M-07/M-16/M-21 为仅文案常量且经源码核对无分支引用，未观测码 0')
        _row['evidence'] = ['E-12', 'E-19', 'E-24']
    elif _row['metric'] == 'deployed_smoke':
        _row['command'] = ('（无）无远端仓库、无 main 分支、无部署流水线，无法执行上线冒烟；'
                           '本地已具备可原样复跑的部署门禁 scripts/deploy_gate.py 与 '
                           '3 作业 23 步的 .github/workflows/ci.yml')
        _row['actual'] = ('未执行：git remote -v 为空、无部署产物与上线地址，缺证按 unknown 登记而非判失败；'
                          '第 8 轮部署作业已依赖质量门禁与过程门禁，10 项门禁总控本地真实执行 10/10 PASS，'
                          '但从未在真实远端触发，run 记录仍为 0')
        _row['evidence'] = ['E-13', 'E-14', 'E-18', 'E-21', 'E-22']

# ---------------------------------------------------------------- 阶段检查点
for _row in TABLES['workflow']:
    if _row['stage'] == 'development':
        _row['time'] = '2026-11-12 至 2026-11-13（6cc6f13 及后续 24 次提交）'
        _row['evidence'] = ['E-04', 'E-05', 'E-06', 'E-20']
    elif _row['stage'] == 'testing':
        _row['snapshot'] = ('12 个 *_test.go、170 份集成证据、5 个采集脚本、InnoDB 行锁并发复现脚本，'
                            '以及第 8 轮新增的接入层分支覆盖测试、错误码穷举脚本与 '
                            'evidence/coverage/ 版本化覆盖率快照四件套')
        _row['evidence'] = ['E-09', 'E-10', 'E-14', 'E-19', 'E-23', 'E-24']
    elif _row['stage'] == 'deployment':
        _row['snapshot'] = ('无远端仓库、无 main 分支、无制品、无部署流水线与上线地址；'
                            '仓库已有生效路径的 3 作业 23 步流水线定义、10 项可原样复跑的门禁脚本'
                            '与本地真实执行原始输出，但零 run 记录')
        _row['evidence'] = ['E-13', 'E-14', 'E-18', 'E-22', 'E-25']

# ---------------------------------------------------------------- 限制项
LIM = {r['id']: r for r in TABLES['limitations']}

LIM['LIM-02']['score_effect'] = '计分口径未经教师核准与校准，6.54 为当前已核验得分，不是最终成绩。'

LIM['LIM-05']['reason'] = (
    'git remote -v 为空；.github/workflows/ci.yml 第 8 轮已扩展为 3 作业 23 步'
    '（quality-gate、process-gate、deploy-gate，含双阈值覆盖率判定与八项门禁映射），'
    'scripts/pipeline_gates.py 本地真实执行 10 项门禁 10/10 PASS；'
    '但无 main 分支、无制品与上线地址，流水线从未被触发，run 记录仍为 0。')
LIM['LIM-05']['score_effect'] = (
    'A4-05 判部分完成（配置、门禁能力与本地总控执行输出均已交付，实际远端运行缺失），'
    'A4-06、A4-07、B4-01、B4-04、B4-05 判失败。')
LIM['LIM-05']['next_action'] = (
    '经 GitHub MCP 建仓并关联远端，由真实 PR 触发 .github/workflows/ci.yml，'
    '走 PR 合并 main 后部署并留存冒烟与回退方案。')

TABLES['limitations'].append({
    'id': 'LIM-11', 'scope': '独立验收会话与验收流程证据', 'owner': 'student',
    'reason': ('第 8 轮学生明确指示强制中断全部子代理执行、停止 code-reviewer、'
               '放弃验收相关全部流程，且不进入任何验收或逐项核验判定；'
               'evidence/sessions/ 下的子代理产物未纳入版本库并由 .gitignore 排除。'
               '因此本批次没有独立测试会话、独立验收会话、验收结论触发的回归范围或会话导出，'
               'A3-07、B1-04、B2-03/04/05、A3-08 的既有判定无新证据可改。'),
    'score_effect': ('A3-07 与 B1-04 维持 fail、B2-03/04/05 维持 fail、A3-08 维持 partial；'
                     '本批次既不新增验收结论，也不以门禁脚本输出替代独立会话证据。'),
    'next_action': ('若复评要提升过程侧得分，须由学生重新授权建立相互独立的测试与验收会话，'
                    '分别导出会话与结论，并按 AGENTS.md 1.1 保持会话隔离。'),
    'evidence': ['E-22', 'E-25']})

# ---------------------------------------------------------------- 理解与日表
UND = {r['id']: r for r in TABLES['understanding']}
UND['UND-06']['method'] = ('逐行审读生效路径 .github/workflows/ci.yml 的 on/jobs/steps 与 needs，'
                           '并读取门禁总表与 10 份原始报告核对退出码')
UND['UND-06']['result'] = (
    '定义含 on 与 3 个 jobs、共 23 个步骤，deploy-gate 依赖 quality-gate 与 process-gate；'
    '含覆盖率 ≥85% 的整体与核心业务包双阈值判定、覆盖率证据一致性、五组必演示场景、'
    'Git 流程、AI 与 Skill 记录齐备、敏感信息扫描等门禁；'
    'scripts/pipeline_gates.py 本地真实执行 10/10 PASS；'
    '仍未在任何真实远端运行，全仓 run 记录为 0')
TABLES['understanding'].append({
    'id': 'UND-09',
    'method': ('读取版本化覆盖率快照四件套与一致性门禁输出，并读取错误码穷举脚本、JSON 结果与运行日志'),
    'scope': '覆盖率原件的版本绑定与复算一致性、M-01~M-30 错误码与业务分支的映射',
    'result': ('整体 97.63%（1563/1601）、server/service 98.47%、server/api/v1 99.08%，'
               '清单绑定提交 def0977 与采集命令且复算一致；'
               '错误码穷举 52 条用例断言未命中 0、27/30 错误码被真实触发、'
               '3 个仅文案常量有源码级排除依据、未观测码 0'),
    'evidence': ['E-23', 'E-24', 'E-25']})

TABLES['daily'].append({
    'id': 'DAY-05', 'date': '2026-11-13',
    'scope': '第 8 轮整改后交付版本（HEAD 4e81942）的成果与过程复核',
    'result': ('成果 5.98/7、过程 0.55/1.5、Token 0.00/1.5，扣后原始分 6.54，状态待核定；'
               '判定分布 pass 37 / partial 6 / fail 14 / unknown 1；'
               '较第 7 轮 6.47 提升 0.07，全部来自 A2-02、A3-03、A3-04 三项质量档由 good 升为 excellent'),
    'evidence': ['E-22', 'E-23', 'E-24', 'E-25']})

# ---------------------------------------------------------------- 元信息
META = dict(m.META)
META.update({
    'delivery_date': '2026-11-13',
    'deployment': (
        '未部署。本地无远端仓库（git remote -v 为空）、无 main 分支、无制品与已触发的流水线、'
        '无上线地址，部署与上线冒烟按缺证登记为 unknown/fail（见 LIM-05 与 code_runtime.deployed_smoke）。'
        '第 8 轮 .github/workflows/ci.yml 已扩展为 3 作业 23 步，部署作业依赖质量门禁与过程门禁，'
        'scripts/pipeline_gates.py 本地真实执行 10 项门禁 10/10 PASS 并留下带时间戳的原始报告；'
        '但因无远端，其 pull_request 触发条件从未生效，run 记录为 0。'),
    'version_chain': (
        'dev/01 共 26 次提交。第 7 轮归档（f784e00）之后的 8 次提交为：'
        'ed675f7 [opt] [v1.6.1] 修正覆盖率阈值口径为整体与核心业务包双阈值 → '
        'def0977 [test] [v1.8.0] 补接入层分支覆盖测试与 M-01~M-30 错误码穷举脚本及真实执行输出 → '
        '2462d52 [opt] [v1.8.1] 覆盖率门禁脚本补版本标注与清单输出 → '
        'bb1ca7f [test] [v1.8.2] 刷新质量门禁与覆盖率原始输出并新增版本化覆盖率快照 → '
        'ba1254e [test] [v1.8.3] 新增五项流水线门禁脚本与门禁总控并统一证据文件编码为 UTF-8 → '
        '0705ef5 [opt] [v1.8.4] 流水线接入五项门禁作业并补齐 AGENTS.md 2.5 八项门禁映射 → '
        '82981ae [docs] [v1.8.5] 更新流水线说明与覆盖率报告并登记版本化快照索引 → '
        '4e81942 [test] [v1.8.6] 刷新门禁总控原始输出与门禁总表（HEAD，检查基准）。'
        '这 8 次提交不含任何业务规则或状态机改动，均为测试、门禁、覆盖率证据与文档；'
        '全程仅 dev/01 一个分支，无 main、无远端、无 PR 记录。'
        '第 8 轮学生明确放弃验收相关全部流程，未新增独立验收会话产物。'),
    'scope': (
        '题面「题目 01 + 一、所有题目共同适用的要求」全量条目，叠加固定清单 '
        'references/profiles/01.json 的 58 个原子评分项：A1 八条业务规则与五组演示场景、'
        'A2 数据与持久化、A3 代码与并发、A4 流程与交付物、B1 阶段与顺序、B2 测试与验收独立性、'
        'B3 Agent 与 Skill、B4 Git/流水线/部署/讲解。'
        '第 8 轮按学生指示不进入验收或逐项验收判定，取证方式为：读取仓库内已提交文件、'
        '核对生效路径流水线 YAML 的作业与步骤、读取版本化覆盖率快照与一致性门禁输出、'
        '读取错误码穷举原始输出、读取 10 项门禁总控及各门禁原始报告，'
        '以及核对提交链与 git remote 状态。'
        '未连接远端、未重跑已闭环的 MySQL 落库/事务回滚/竞态探针/幂等等校验、'
        '未新建独立会话、未使用被 .gitignore 排除的 evidence/sessions/ 产物。'),
    'token_note': (
        'Token 计分暂记 0.00/1.5、状态 unknown，理由：教师未发布本题 Token 基准'
        '（references/profiles/01.json 的 token_baselines 为空），学生亦未提交分阶段原始 usage 与'
        '去重台账，无可比总量，无法计算消耗比与可避免 Token，因此不计分、不推定学生浪费。'
        '该缺口已按教师责任登记为限制项 LIM-01 与门禁项 TOKEN；教师发布基准并由学生补交官方 usage '
        '原件后，须重新运行 token_score 并重算总分，故本批次 6.54 为当前已核验得分而非最终成绩。'
        '与第 7 轮相比，过程类评分（B1~B4 共 1.5 分）维持 0.55 不变，'
        '本轮 0.07 分提升全部来自成果侧 A2-02、A3-03、A3-04 三项质量档提升。'),
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
