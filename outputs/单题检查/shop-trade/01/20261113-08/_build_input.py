#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 V3 检查输入 audit-input.json（题目 01 / 学生 shop-trade / 批次 20261113-08）。

以第 7 轮输入为基线做定向修订。按学生本轮明确指示：放弃独立验收会话与验收相关
全部流程，不新增任何验收类产物；仅登记第 8 轮已真实提交、可复算的成果侧证据
（接入层分支覆盖、错误码穷举、版本化覆盖率快照、3 作业 23 步流水线与 10 项门禁），
未获得新证据的评分项逐字沿用，避免复核口径漂移。
"""
import hashlib
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(r'd:/Desktop/shop')
OUT = ROOT / 'outputs/单题检查/shop-trade/01/20261113-08'
R7 = ROOT / 'outputs/单题检查/shop-trade/01/20261113-07/_build_input.py'
PROFILE = pathlib.Path(r'C:/Users/10990/.codebuddy/skills/student-project-audit/references/profiles/01.json')

spec = importlib.util.spec_from_file_location('r7', str(R7))
r7 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r7)
m = r7.m
EV = m.EV

NEW_REV = '4e81942（dev/01，2026-11-13）'

# ---------------------------------------------------------------- 证据索引
EV['E-22'] = (
    '.github/workflows/ci.yml（生效路径，第 8 轮扩展为 3 作业 23 步：quality-gate 13 步、'
    'process-gate 6 步、deploy-gate 4 步）；scripts/pipeline_gates.py（与 CI 同源同序的 10 项门禁总控）；'
    'evidence/pipeline_gate_reports/（各门禁原始输出与门禁总表.md，2026-11-13 10:12:23 真实执行 10/10 PASS）；'
    'evidence/CI流水线说明.md；evidence/sessions/ 已被 .gitignore 排除、不作为交付物')
EV['E-23'] = (
    'server/api/v1/api_branch_coverage_test.go；evidence/coverage/README.md；'
    'evidence/coverage/coverage-v1.8.0-def0977.out / .func.txt / .gate.txt / .manifest.json；'
    'evidence/coverage-report.md（交付版本 v1.8.0：整体 97.63% 1563/1601、server/service 98.47%、'
    'server/api/v1 99.08%；清单绑定提交 def0977、生成时间 2026-11-13 09:05:16 与采集命令）')
EV['E-24'] = (
    'scripts/error_code_enumeration.py；evidence/error_code_enumeration.txt / .json / _runtime.log'
    '（真实启动 demo-memory 服务后 HTTP 逐条探测 M-01~M-30：52 条用例、断言未命中 0、'
    '27 个错误码作为业务错误码被真实触发，M-07/M-16/M-21 经源码核对仅为文案常量且无分支引用、'
    '未观测码 0）')
EV['E-25'] = (
    'scripts/coverage_evidence_gate.py、scripts/scenario_gate.py、scripts/git_process_gate.py、'
    'scripts/record_gate.py、scripts/secret_scan_gate.py 及 evidence/pipeline_gate_reports/ 下对应原始输出'
    '（覆盖率证据一致性、五组场景 38 条断言、Git 流程 22 条受检提交、AI 与 Skill 记录 13/13、'
    '敏感信息扫描 211 文件 0 命中）')
EV['E-26'] = (
    'scripts/coverage_gate.py 的 --revision/--commit/--manifest 版本标注能力；'
    'evidence/quality_gate.py 的 --revision/--commit；evidence/quality_gate_output.txt；'
    'evidence/coverage-gate-func.txt；evidence/coverage-gate.out；'
    'evidence/commit-message-check-output.txt（提交格式门禁真实输出）')

# ---------------------------------------------------------------- 产物修订
# 产物元组字段序：0 id / 1 presence / 2 validity / 3 owner / 4 reason / 5 location /
# 6 scenario / 7 usage / 8 quality_summary / 9 fix / 10 evidence
ART = {a[0]: list(a) for a in m.ARTIFACTS}

ART['pipeline'][4] = (
    '流水线定义位于生效路径 .github/workflows/ci.yml，第 8 轮由 2 作业 15 步扩展为 3 作业 23 步：'
    'quality-gate 13 步（格式、vet、构建、单测、race、覆盖率采集、整体与核心业务包双阈值判定、'
    '覆盖率证据一致性、五组场景、产物上传等）、process-gate 6 步（Git 流程、记录齐备、敏感信息扫描等）、'
    'deploy-gate 4 步且 depends on 前两个作业；逐项对应 AGENTS.md 2.5 的八项门禁。'
    'scripts/pipeline_gates.py 与 CI 同源同序在本地真实执行 10 项门禁，2026-11-13 10:12:23 '
    '输出 10/10 PASS、不通过 0，原始报告全部留档。仓库仍无远端（git remote -v 为空），'
    '流水线从未被真实触发，无任何 run 记录、run id 或步骤日志。')
ART['pipeline'][5] = (
    '.github/workflows/ci.yml;scripts/pipeline_gates.py;scripts/coverage_gate.py;'
    'scripts/deploy_gate.py;scripts/coverage_evidence_gate.py;scripts/scenario_gate.py;'
    'scripts/git_process_gate.py;scripts/record_gate.py;scripts/secret_scan_gate.py;'
    'evidence/pipeline_gate_reports/门禁总表.md;evidence/CI流水线说明.md')
ART['pipeline'][6] = (
    '检查者核对生效路径 YAML 含 on 与 3 个 jobs、共 23 个 name 步骤，核对覆盖率阈值判定参数 '
    '--overall 85 --pkg server/service:85，核对 deploy-gate 的 needs 依赖；'
    '并读取门禁总表与 10 份原始报告，确认本地真实执行结果为 10/10 PASS、退出码均为 0。'
    '同时核对 git remote -v 为空、全仓 run 记录为 0。')
ART['pipeline'][7] = (
    'PR 与 push 触发质量门禁，process-gate 核验过程记录，两者均通过后才进入 deploy-gate；'
    '本地可用 python -X utf8 scripts/pipeline_gates.py 一条命令原样复跑全部 10 项门禁。')
ART['pipeline'][8] = (
    '定义完整、阈值可判定、含部署前门禁依赖与健康/回退校验，10 项门禁经本地真实执行全部 PASS '
    '并有原始输出；缺口仅在从未于真实远端产生 run 记录。')
ART['pipeline'][9] = (
    '经 GitHub MCP 建仓并关联远端后，由真实 PR 触发该工作流，保存 run URL、run id、状态与各步骤日志。')
ART['pipeline'][10] = ['E-13', 'E-14', 'E-18', 'E-21', 'E-22', 'E-25']
m.ARTIFACT_IMPACT['pipeline'] = (
    '流水线产物是 A4-05 的唯一必要依赖：生效路径、双阈值判定、部署门禁、过程门禁与 10 项本地真实执行'
    '原始输出均已交付，配置侧已完整；剩余缺口是「未在真实远端运行」这一状态事实，'
    '故 A4-05 维持部分完成、质量维持满分档，不重复扣分。')

ART['coverage'][4] = (
    '覆盖率原件本轮收敛为版本化快照：evidence/coverage/coverage-v1.8.0-def0977.out、.func.txt、'
    '.gate.txt 与 .manifest.json，清单登记 revision、commit、generated_at、go_version、collect_command、'
    '整体与逐包覆盖率；scripts/coverage_evidence_gate.py 校验清单提交哈希存在、清单数字与重新解析 '
    'profile 一致、整体与 server/service 双阈值达标，实测 PASS。')
ART['coverage'][5] = (
    'evidence/coverage/coverage-v1.8.0-def0977.out;evidence/coverage/'
    'coverage-v1.8.0-def0977.func.txt;evidence/coverage/coverage-v1.8.0-def0977.gate.txt;'
    'evidence/coverage/coverage-v1.8.0-def0977.manifest.json;evidence/coverage/README.md;'
    'evidence/coverage-report.md;coverage.out;evidence/coverage-gate.out;evidence/coverage-gate-func.txt')
ART['coverage'][6] = (
    '检查者读取 manifest.json 与 .gate.txt/.func.txt，并与重新解析的 profile 数字对照：'
    '整体 97.63%（1563/1601）、server/service 98.47%（1161/1179）、server/api/v1 99.08%。')
ART['coverage'][8] = (
    '支撑 A3-02/03/04 三项判定；接入层覆盖不均与多份原件无版本标注两处缺口已于本轮闭环，'
    '三项均可由版本化快照与一致性门禁复算。')
ART['coverage'][9] = '后续每次重新采集覆盖率时同步生成新版本快照与清单，并刷新一致性门禁原始输出。'
ART['coverage'][10] = ['E-09', 'E-13', 'E-23', 'E-25']
m.ARTIFACT_IMPACT['coverage'] = (
    '覆盖率产物是 A3-02、A3-03、A3-04 的共同必要依赖；本轮接入层覆盖率提升至 99.08% 且原件完成'
    '版本化与一致性校验，使 A3-03、A3-04 的质量档由 good 升为 excellent。')

ART['unit_tests'][4] = (
    '单元测试源码除 server/service 下的 r4/r5 系列边界测试外，本轮新增 '
    'server/api/v1/api_branch_coverage_test.go 覆盖身份拒绝、请求体非法、未知订单、异常事件、'
    '越权与错误兜底等接入层分支；另新增 scripts/error_code_enumeration.py 对 M-01~M-30 做'
    '52 条真实 HTTP 穷举探测。')
ART['unit_tests'][5] = (
    'server/service/r4_edge_test.go;server/service/r5_edge_test.go;'
    'server/service/r5_edge2_test.go;server/api/v1/api_branch_coverage_test.go;'
    'scripts/error_code_enumeration.py;evidence/quality_gate_output.txt;'
    'evidence/error_code_enumeration.txt')
ART['unit_tests'][8] = (
    '支撑 A3-01 判定 pass/excellent 与 A3-08 的复测链部分；接入层分支覆盖与错误码穷举的加入'
    '使整体覆盖率由 94.19% 升至 97.63%。')
ART['unit_tests'][10] = ['E-09', 'E-13', 'E-23', 'E-24']

m.ARTIFACTS = [tuple(ART[a[0]]) for a in m.ARTIFACTS]

# ---------------------------------------------------------------- 评分项修订
CHECKS = {c[0]: list(c) for c in m.CHECKS}
POS = {'status': 1, 'quality': 2, 'owner': 3, 'reason': 4, 'fix': 5,
       'quality_basis': 6, 'evidence': 7, 'issue_ids': 8}


def patch(cid, **kw):
    for k, v in kw.items():
        CHECKS[cid][POS[k]] = v


patch('01-A2-02',
      quality='excellent',
      reason='检查者独立实测状态机：待支付→待发货→退款审核中→退款处理中→已退款、待发货→已发货、'
             '待支付→已取消/已关闭；终态保护生效（已发货不受理退款 M-11、已取消/已退款再申请被拒、'
             '重复取消 M-10、重复发货 M-19），源码对条件更新 rows!=1 有专门保护并有单测覆盖。'
             '第 8 轮新增 scripts/error_code_enumeration.py 与 evidence/error_code_enumeration.txt/.json/'
             '_runtime.log：真实启动 demo-memory 服务后以 HTTP 逐条探测 M-01~M-30，52 条用例、'
             '断言未命中 0；30 个错误码中 27 个作为业务错误码被真实触发，M-07/M-16/M-21 经源码核对'
             '仅为 server/service/types.go 中的文案常量、无任何分支引用（本就不作为错误码返回），'
             '未观测码为 0。此前「57 条巡检只触发 6 个业务错误码、映射不可逐一复算」的缺口已闭环。',
      fix='无需整改。',
      quality_basis='错误码清单与业务分支一一对应、逐条可复算，且对 3 个仅文案常量给出了源码级'
                    '排除依据而非跳过；状态机正反两侧断言齐备，质量满分。',
      evidence=['E-04', 'E-12', 'E-24'],
      issue_ids=[])

patch('01-A3-03',
      quality='excellent',
      reason='核心业务包 server/service 包级语句覆盖率 98.47%（1161/1179），整体 97.63%（1563/1601），'
             '均 ≥85%；第 8 轮新增 server/api/v1/api_branch_coverage_test.go 后，接入层由 82.21%'
             '（268/326）升至 99.08%（323/326），此前「逐函数最低 57.1%、接入层覆盖不均」的缺口已消除。'
             '版本化快照 evidence/coverage/coverage-v1.8.0-def0977.out/.func.txt/.gate.txt/'
             '.manifest.json 绑定提交哈希与采集命令，可原样复算。',
      fix='无需整改。',
      quality_basis='三个口径（整体、核心业务包、接入层）全部达标且均有原始 profile 与逐函数明细支撑，'
                    '覆盖率数字与清单由一致性门禁复算通过，质量满分。',
      evidence=['E-09', 'E-13', 'E-23', 'E-25'],
      issue_ids=[])

patch('01-A3-04',
      quality='excellent',
      reason='覆盖率原始文件与本轮门禁执行对应，报告可读且可复算；全量 coverpkg 表明无自编生产代码'
             '被排除，排除项为零。第 8 轮把此前并存的 coverage.out、coverage-all.out、coverage-r5.out '
             '与 evidence/coverage-gate.out 收敛为版本化快照四件套：manifest.json 登记 revision、'
             'commit、generated_at、go_version、collect_command、整体与逐包覆盖率；'
             'scripts/coverage_evidence_gate.py 校验清单提交哈希存在、清单数字与重新解析 profile 一致、'
             '整体与 server/service 双阈值达标，实测 PASS；scripts/coverage_gate.py 与 '
             'evidence/quality_gate.py 的原始输出亦自带版本/提交标注。',
      fix='无需整改。',
      quality_basis='版本、提交哈希、采集命令、生成时间与逐包数字全部可核验，且由独立脚本做一致性'
                    '复算并以非零退出码阻断不一致情形；多份原件无标注的问题闭环，质量满分。',
      evidence=['E-09', 'E-13', 'E-23', 'E-25', 'E-26'],
      issue_ids=[])

patch('01-A4-05',
      status='partial',
      quality='excellent',
      reason='流水线第 8 轮完成门禁体系补齐：生效路径 .github/workflows/ci.yml 由 2 作业 15 步扩展为 '
             '3 作业 23 步（quality-gate 13 步、process-gate 6 步、deploy-gate 4 步，且部署作业'
             '依赖前两者），逐项映射 AGENTS.md 2.5 的八项门禁；新增覆盖率证据一致性、五组必演示场景、'
             'Git 流程、AI 与 Skill 记录齐备、敏感信息扫描五项门禁脚本，并由 scripts/pipeline_gates.py '
             '与 CI 同源同序串成 10 项门禁总控，2026-11-13 10:12:23 本地真实执行 10/10 PASS、'
             '不通过 0、各门禁退出码均为 0，原始输出与门禁总表全部留档。'
             '未完成部分：仓库仍无远端，流水线从未被真实触发，无任何 run 记录、run id 与步骤日志，'
             '故「实际流水线执行」这一要求仍未满足。',
      fix='经 GitHub MCP 建仓并关联远端后，由真实 PR 触发该工作流，保存 run URL、run id、状态与各步骤'
          '日志，并按 AGENTS.md 2.1 把报告、覆盖率与结论附于 PR 描述。',
      quality_basis='交付物本身已达「可一键执行、结果可复现、失败可阻断、过程记录可核验」水平：'
                    '阈值判定、证据一致性、场景、Git、记录、敏感信息六类门禁均为独立脚本且本地真实'
                    '执行全通过；「未在真实远端运行」属状态维度，已由部分完成体现，按规则不再重复拉低质量。',
      evidence=['E-13', 'E-14', 'E-18', 'E-21', 'E-22', 'E-25'],
      issue_ids=['ISS-CI-NOT-EFFECTIVE'])

patch('01-A3-06',
      reason='适用并发与重复操作具备可重复验证：检查者独立重跑 20 并发下单恒为成功 5 + M-02 15、'
             '库存守恒；真实 InnoDB 下 20 并发成功 3、失败 17、available+occupied=5 恒等不超卖；'
             '重复支付/退款通知幂等已升级为表级断言（有效收款笔数恒为 1）；真实行锁下退款与发货'
             '互斥裁决 5 轮两种合法结果均出现且有外部事务持锁阻塞探针。竞态探针方面，学生在 WSL '
             'Ubuntu 的 gcc 15.2.0 + CGO_ENABLED=1 下执行 go test -race ./... -count=1，6 包 ok、'
             'exit=0、无 DATA RACE；该步骤已固化进生效路径流水线，第 8 轮又由 scripts/pipeline_gates.py '
             '把 10 项门禁串成可一键复跑总控。但检查者本机 CGO_ENABLED=0 且无 gcc/clang，'
             '竞态结论仍为第一方产出，且无远端即无第三方 run 记录，故质量维持 good。',
      quality_basis='并发守恒与重复操作已有数据库级证据，门禁总控提供了受影响检查的复跑条件；'
                    '但竞态探针为第一方产出、检查者未能在同环境复跑，质量降一档。',
      evidence=['E-09', 'E-12', 'E-13', 'E-15', 'E-17', 'E-18', 'E-22'])

patch('01-A3-08',
      reason='缺陷修复与复测链真实存在：第 1~7 轮检查结论逐条整改，evidence/acceptance-check-rerun.md '
             '对 G-01~G-24 逐项给结论并区分代码缺陷/环境缺失/过程证据缺失，检查者独立复跑七包全 ok。'
             '第 8 轮新增 scripts/pipeline_gates.py，使任一改动后可一键重跑 10 项门禁并留存带时间戳的'
             '原始报告（2026-11-13 10:12:23，10/10 PASS），受影响门禁的复跑能力已具备。'
             '但验收结论触发的回归范围仍缺失——本轮按学生指示放弃独立验收会话与验收相关全部流程，'
             '无独立验收结论，也就没有由验收结论界定的回归范围。',
      quality_basis='复测链与一键门禁复跑齐备，但缺独立验收结论界定回归范围，维持部分完成与 good。',
      evidence=['E-09', 'E-10', 'E-18', 'E-22', 'E-25'])

patch('01-B1-03',
      reason='阶段产物版本可追溯：22 次提交哈希、evidence/第五轮证据清单.md、第四轮证据清单.md、'
             '门禁自查汇总.md 与 .agent/06-workflow-devflow.md 均可定位到具体产物；第 8 轮新增'
             '带提交哈希与生成时间的版本化覆盖率快照（manifest.json）以及带执行时间戳的 10 份门禁'
             '原始报告，属「当时冻结」形态的部分补充。但原始事件（events.jsonl、会话导出）仍缺失，'
             '且业务开发阶段按七阶段冻结的交接检查点文件仍无，现有留证主体仍是事后整理的证据清单；'
             '本轮按学生指示放弃验收相关会话产物，未新增任何会话导出。',
      fix='若平台提供开发阶段会话导出能力，按七阶段补入当时冻结的交接检查点与原始事件；'
          '在此之前不得以推定补记。',
      quality_basis='版本化快照与时间戳报告提升了可核验性，但七阶段交接检查点与原始事件仍缺，'
                    '留证形态偏事后汇总，质量维持 basic。',
      evidence=['E-06', 'E-14', 'E-20', 'E-23', 'E-25'])

patch('01-B4-02',
      reason='全部变更仅在 dev/01 提交（git branch -a 仅本地 dev/01，无 main 分支）；第 8 轮新增 7 次'
             '按 test/opt/docs 分类型、带版本号的提交，scripts/git_process_gate.py 真实执行并输出'
             '22 条受检提交格式全部合规、merge 提交 0，基线提交 6cc6f134ee07 被显式登记为 '
             'AGENTS.md 生效前豁免而非改写历史。但阶段历史仍不完整：首次基线提交一次性纳入'
             '生产代码、测试、文档、Skill 与全部证据，后续提交均属证据补齐轮次而非真实开发阶段序列。',
      quality_basis='提交类型分离与格式门禁实测通过，但一次性基线与事后补齐轮次的时序事实未变，'
                    '维持部分完成与 good。',
      evidence=['E-06', 'E-14', 'E-25', 'E-26'])

patch('01-B4-03',
      reason='提交说明格式校验：第 8 轮 scripts/git_process_gate.py 实测 22 条受检提交格式全部合规；'
             '首条基线提交 6cc6f13 使用 feat: 电商订单售前退款完整业务实现，不符合原附件'
             '「[类型] [版本号] [编号] 描述」格式，已由门禁脚本显式登记为 AGENTS.md 生效前基线豁免'
             '（不改写历史）；本机 meegle CLI 不可用，仓库内仍无任何编号核验输出，'
             '本轮 7 次提交因此全部使用 test/opt/docs 类型，未使用需编号核验的 feat/fix。',
      quality_basis='格式门禁实测通过并如实登记基线豁免，但编号核验输出为零这一质量根因未消除，'
                    '维持部分完成与 good。',
      evidence=['E-06', 'E-14', 'E-25', 'E-26'])

m.CHECKS = [tuple(CHECKS[c[0]]) for c in m.CHECKS]

# ---------------------------------------------------------------- 问题修订
DROP = {'ISS-ERRCODE-ENUM', 'ISS-API-COVERAGE', 'ISS-COV-MULTI'}
ISSUES = {i[0]: list(i) for i in m.ISSUES}
for _k in DROP:
    ISSUES.pop(_k, None)


def setfield(iid, pos, value):
    ISSUES[iid][pos] = value


setfield('ISS-CI-NOT-EFFECTIVE', 2,
         '.github/workflows/ci.yml 位于生效路径且为可执行工作流：第 8 轮扩展为 3 作业 23 步，'
         'quality-gate 含整体与核心业务包双阈值判定，process-gate 覆盖 Git 流程、记录齐备与'
         '敏感信息扫描，deploy-gate 依赖前两者；scripts/pipeline_gates.py 本地真实执行 10 项门禁，'
         '2026-11-13 10:12:23 输出 10/10 PASS、不通过 0。剩余事实：git remote -v 为空，'
         '全仓无任何流水线 run 记录、run id、状态或步骤日志。')
setfield('ISS-CI-NOT-EFFECTIVE', 3,
         '检查者核对生效路径 YAML 含 on 与 3 个 jobs、23 个步骤及 deploy-gate 的 needs 依赖，'
         '读取 evidence/pipeline_gate_reports/门禁总表.md 与 10 份原始报告确认退出码全为 0；'
         '并核对 git remote -v 为空、全仓 run 记录为 0。')
setfield('ISS-CI-NOT-EFFECTIVE', 4,
         '题面共同要求「流水线实际执行质量、覆盖率、构建和部署门禁」，其中「实际执行」仍为零：'
         '配置、门禁能力与本地总控执行原始输出均已完整交付，但从未在真实流水线运行，'
         '失败路径也未在真实环境验证过。A4-05 判部分完成；因质量维度已达满分档，'
         '该项得分未因本缺口额外受损。')
setfield('ISS-CI-NOT-EFFECTIVE', 5,
         '经 GitHub MCP 建仓并关联远端后，由真实 PR 触发 .github/workflows/ci.yml，保存 run URL、'
         'run id、状态与各步骤日志原文；必要时先用一次故意失败的覆盖率样本验证阈值步骤在真实'
         '流水线中确实阻断。')
setfield('ISS-CI-NOT-EFFECTIVE', 7,
         '第 5 轮为 ISS-CI-PLACEHOLDER（纯注释模板，判失败）；第 6 轮升为部分完成但生效路径仍为'
         '占位；第 7 轮修正生效路径并补齐阈值判定与部署作业；第 8 轮补齐过程门禁作业、'
         '八项门禁映射与 10 项门禁总控的本地真实执行原始输出。本问题进一步收敛为'
         '「无远端故从未真实运行」这一单一事实，判定维持部分完成、质量维持 excellent。')
m.ISSUE_BASIS['ISS-CI-NOT-EFFECTIVE'] = (
    'A4-05 状态轴的独立根因是流水线从未在真实远端运行（零 run 记录）；'
    '同项原质量根因（缺覆盖率阈值判定与部署门禁作业）已于第 7 轮闭环，'
    '第 8 轮新增的过程门禁与总控输出属同一交付物的完善，不另立扣分事实、不重复计分。')
m.ISSUE_DEDUP['ISS-CI-NOT-EFFECTIVE'] = (
    '第 8 轮起本问题收敛为单一根因（无远端故流水线从未真实运行）；'
    '与已闭环并删除的 ISS-CI-NO-THRESHOLD、ISS-ERRCODE-ENUM、ISS-API-COVERAGE、ISS-COV-MULTI '
    '分属不同事实，不重复描述同一扣分事实。')

m.ISSUES = [tuple(ISSUES[i[0]]) for i in m.ISSUES if i[0] in ISSUES]

# ---------------------------------------------------------------- 元信息与输出
META = dict(r7.META)
META.update({
    'audit_id': 'AUDIT-SHOP-TRADE-01-20261113-08',
    'audit_date': '2026-11-13',
    'batch': '20261113-08',
    'calibration_id': '未校准：本批次为该 profile 在本班的第 8 次 V3.0 评分，前 7 批次可作纵向对照，'
                      '但无教师核准的同批其它样本可作评分校准',
    'environment': 'Windows 11 + PowerShell（禁止使用 WSL）；Go go1.26.0 windows/amd64；'
                   '本机 CGO_ENABLED=0、无 gcc/clang、无 MySQL 客户端、无远端仓库；'
                   '第 8 轮按学生明确指示强制中断全部子代理、放弃验收相关全部流程，'
                   'evidence/sessions/ 下的会话产物未纳入版本库并由 .gitignore 排除，'
                   '本批次不进入任何独立验收或逐项验收判定；'
                   '数据库层结论沿用 2026-11-12 22:44 的真实执行原始输出，不重跑、不伪造；'
                   '本批次新增证据全部来自仓库内已提交文件与本地门禁脚本的真实执行输出。',
    'previous_report': 'outputs/单题检查/shop-trade/01/20261113-07/检查报告.md',
    'previous_score': '6.47',
    'change_summary': '第 7 轮归档后新增 7 次提交，业务规则与状态机实现无改动：'
                      'def0977 [test] [v1.8.0] 补接入层分支覆盖测试与 M-01~M-30 错误码穷举脚本及真实执行输出 → '
                      '2462d52 [opt] [v1.8.1] 覆盖率门禁脚本补版本标注与清单输出 → '
                      'bb1ca7f [test] [v1.8.2] 刷新质量门禁与覆盖率原始输出并新增版本化覆盖率快照 → '
                      'ba1254e [test] [v1.8.3] 新增五项流水线门禁脚本与门禁总控并统一证据文件编码为 UTF-8 → '
                      '0705ef5 [opt] [v1.8.4] 流水线接入五项门禁作业并补齐 AGENTS.md 2.5 八项门禁映射 → '
                      '82981ae [docs] [v1.8.5] 更新流水线说明与覆盖率报告并登记版本化快照索引 → '
                      '4e81942 [test] [v1.8.6] 刷新门禁总控原始输出与门禁总表（HEAD，检查基准）。'
                      '新增证据：server/api/v1/api_branch_coverage_test.go 使接入层覆盖率 82.21%→99.08%、'
                      '整体 94.19%→97.63%；scripts/error_code_enumeration.py 与三份原始输出（52 用例、'
                      '27/30 错误码真实触发、3 个仅文案常量）；evidence/coverage/ 版本化快照四件套与'
                      '一致性门禁；.github/workflows/ci.yml 3 作业 23 步；五个过程门禁脚本与 '
                      'scripts/pipeline_gates.py 总控（2026-11-13 10:12:23 真实执行 10/10 PASS）；'
                      'evidence/pipeline_gate_reports/ 下 10 份原始输出与门禁总表。'
                      '本批次取证方式为读取已提交文件与本地门禁脚本真实输出，'
                      '未连接远端、未新建独立验收会话、未重跑已闭环的数据库与竞态校验。',
    'history_resolution': '第 7 轮判定分布 pass 37 / partial 6 / fail 14 / unknown 1，'
                          '已核验得分 6.47/10（成果 5.92/7、过程 0.55/1.5、Token 0.00/1.5 unknown）；'
                          '旧报告与旧分数保留不覆盖，本轮不沿用旧成绩。'
                          '第 7 轮登记的质量缺口逐项复核：(1) ISS-ERRCODE-ENUM —— 已由错误码穷举脚本'
                          '逐条复算闭环（52 用例、27/30 触发、3 个文案常量有源码排除依据），'
                          'A2-02 由 pass/good 升为 pass/excellent，问题删除。'
                          '(2) ISS-API-COVERAGE —— 接入层分支覆盖测试使 server/api/v1 达 99.08%，'
                          'A3-03 升为 pass/excellent，问题删除。'
                          '(3) ISS-COV-MULTI —— 版本化快照四件套与一致性门禁使覆盖率原件绑定提交哈希、'
                          '生成时间与采集命令，A3-04 升为 pass/excellent，问题删除。'
                          '(4) ISS-CI-NOT-EFFECTIVE —— 配置侧由 2 作业 15 步扩展为 3 作业 23 步，'
                          '新增五项过程门禁与 10 项总控的本地真实执行原始输出；'
                          '但无远端故仍零 run 记录，A4-05 维持 partial/excellent，扣分不变。'
                          '(5) ISS-RACE-FIRSTPARTY、ISS-AGENT-LOAD-BIND、ISS-ONE-SHOT-COMMIT、'
                          'ISS-STAGE-HISTORY、ISS-NO-MEEGLE、ISS-NO-CHECKPOINT、'
                          'ISS-CHECKPOINT-SNAPSHOT 本轮虽新增门禁输出与版本化快照，'
                          '但其各自独立根因（第一方竞态探针、开发阶段加载时点不可追溯、'
                          '一次性基线提交、无编号核验输出、无七阶段交接检查点）均未消除，判定维持。'
                          '仍维持 fail 的项：缺独立测试会话（A3-07）、缺独立验收会话（B1-04）、'
                          '五段前置链断裂（B1-02）、缺会话导出与原始提示（B2-03/04/05）、'
                          '部署与回退方案（A4-06、A4-07）、缺讲解视频（A4-08、A4-09）、'
                          '缺班级群凭据（A4-10）、无 MCP 建仓与 PR（B4-01、B4-04、B4-05）；'
                          '本轮学生已明确放弃验收相关流程，且暂不处理视频、远端 PR 与班级群凭据，'
                          '故上述 fail 项未产生新证据。'
                          'B1-01 因版本链仍无法证明阶段先后维持 unknown。'
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
