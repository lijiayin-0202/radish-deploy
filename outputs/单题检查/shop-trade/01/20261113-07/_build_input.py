#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 V3 检查输入 audit-input.json（题目 01 / 学生 shop-trade / 批次 20261113-07）。

以第 6 轮输入为基线做定向修订：仅改动本轮有新证据支撑的评分项与问题，
未变动的评分项逐字沿用，避免复核时的口径漂移。判读全部基于本轮检查者独立实测。
"""
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(r'd:/Desktop/shop')
OUT = ROOT / 'outputs/单题检查/shop-trade/01/20261113-07'
R6 = ROOT / 'outputs/单题检查/shop-trade/01/20261112-06/_build_input.py'
PROFILE = pathlib.Path(r'C:/Users/10990/.codebuddy/skills/student-project-audit/references/profiles/01.json')

spec = importlib.util.spec_from_file_location('r6', str(R6))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

NEW_REV = 'ed675f7（dev/01，2026-11-13）'

# ---------------------------------------------------------------- 证据索引
m.EV['E-18'] = ('.github/workflows/ci.yml（生效路径，本轮由 evidence/ci.yml 迁入并重写）；'
                'scripts/coverage_gate.py；scripts/deploy_gate.py；evidence/CI流水线说明.md')
m.EV['E-19'] = ('evidence/db/inno_ship_refund_race.py；evidence/db/inno_ship_refund_race_raw.txt；'
                'evidence/db/inno_ship_refund_race_raw.json；evidence/db/inno_ship_refund_race.app.log；'
                'evidence/db/inno_ship_refund_race.md（真实 InnoDB 行锁下退款与发货互斥裁决复现，'
                '含外部事务持锁阻塞探针）')
m.EV['E-20'] = 'README.md（根目录统一运行入口）；evidence/agent-rules-load-log.md（AGENTS 约束加载登记）'
m.EV['E-21'] = ('outputs/单题检查/shop-trade/01/20261113-07/evidence/gate_scripts_verify.txt'
                '（新增两个门禁脚本的本地实测：真实覆盖率 PASS、低覆盖样本 FAIL、核心包缺失 FAIL、'
                '部署门禁全流程 PASS，4/4 符合预期）')

# ---------------------------------------------------------------- 产物修订
# 产物元组字段序：0 id / 1 presence / 2 validity / 3 owner / 4 reason / 5 location /
# 6 scenario / 7 usage / 8 quality_summary / 9 fix / 10 evidence
ART = {a[0]: list(a) for a in m.ARTIFACTS}

ART['pipeline'][4] = (
    '流水线定义已从 evidence/ci.yml 迁至生效路径 .github/workflows/ci.yml：质量门禁 11 步'
    '（checkout、setup-go、gofmt、go vet、go build、单元测试、竞态检测、覆盖率采集、'
    '覆盖率阈值判定、覆盖率明细、产物上传）与部署门禁 4 步（checkout、setup-go、基础部署门禁、'
    '产物上传）；阈值判定由 scripts/coverage_gate.py 执行（原定义只统计不判定），'
    '部署门禁由 scripts/deploy_gate.py 执行（构建制品、版本登记、启动、健康检查、业务冒烟、'
    '回退准备校验）。仓库仍无远端，流水线从未被真实触发，无任何 run 记录。')
ART['pipeline'][5] = ('.github/workflows/ci.yml;scripts/coverage_gate.py;scripts/deploy_gate.py;'
                      'evidence/CI流水线说明.md')
ART['pipeline'][6] = (
    '检查者核对生效路径文件为可执行工作流而非注释模板（YAML 解析通过，含 on 与 jobs，'
    '质量门禁 11 步、部署门禁 4 步），核对 git remote -v 为空、全仓 run 记录为 0；'
    '并对两个门禁脚本执行四个用例的本地实测（真实覆盖率样本 PASS、低覆盖样本 FAIL、'
    '核心包缺失 FAIL、部署门禁全流程 PASS）。')
ART['pipeline'][7] = ('PR 与 push 触发质量门禁，通过后进入部署门禁；两个门禁脚本与本地命令一一对应，'
                      '可原样复跑。')
ART['pipeline'][8] = ('定义完整、阈值可判定、含健康检查与回退校验，且两个门禁脚本经检查者四用例'
                      '本地实测全部符合预期，不是空壳；缺口仅在未于真实远端运行。')
ART['pipeline'][9] = ('经 GitHub MCP 建仓并关联远端后，由真实 PR 触发该工作流，保存 run URL、run id、'
                      '状态与各步骤日志。')
ART['pipeline'][10] = ['E-13', 'E-14', 'E-18', 'E-21']
m.ARTIFACT_IMPACT['pipeline'] = (
    '流水线产物是 A4-05 的唯一必要依赖：生效路径、覆盖率阈值判定与部署门禁作业均已完整交付，'
    '使该项由失败升为部分完成；剩余缺口仅在从未于真实远端运行。')

ART['runtime'][4] = (
    '运行交付含 schema.sql 与 evidence/schema.sql（引擎 InnoDB、字符集 utf8mb4、唯一键 '
    'uk_payment_dedup_key / uk_order_order_no / uk_goods_goods_no 等）、可控 HTTP 模拟支付渠道'
    '服务、运行说明、真实 MySQL 建库与启动步骤，以及本轮新增的根目录 README.md 统一入口。')
ART['runtime'][5] = ('schema.sql;evidence/schema.sql;scripts/mock_channel_service.py;'
                     'scripts/r4_mock_channel_smoke.py;docs/代码产物补齐说明.md;'
                     'evidence/mysql核查记录.md;README.md')
ART['runtime'][6] = (
    '检查者独立读取建表语句摘录 ENGINE/CHARSET/唯一索引，独立拉起模拟渠道服务，'
    '并按根目录 README.md 从干净构建到启动成功复核统一入口与五组场景接口清单。')
ART['runtime'][7] = ('README.md 汇总环境前置、构建、启动、演示账号、模拟渠道、MySQL 模式建库与核对命令、'
                     '五组场景接口入口、质量门禁脚本与验证脚本清单，形成统一复现入口。')
ART['runtime'][8] = ('schema.sql、模拟渠道与运行说明三项齐备，第三方全部为可控 HTTP 模拟服务；'
                     '运行说明本轮已收敛到根目录 README.md 单一入口，复现成本问题消除。')
ART['runtime'][9] = '无需整改；后续新增启动方式时同步更新 README.md 即可。'
ART['runtime'][10] = ['E-05', 'E-15', 'E-20']
m.ARTIFACT_IMPACT['runtime'] = (
    '运行交付支撑 A4-01 与 A4-04；本轮补齐根目录 README.md 统一入口后，A4-01 的质量达满分档。')

m.ARTIFACTS = [tuple(ART[a[0]]) for a in m.ARTIFACTS]

# ---------------------------------------------------------------- 评分项修订
CHECKS = {c[0]: list(c) for c in m.CHECKS}
POS = {'status': 1, 'quality': 2, 'owner': 3, 'reason': 4, 'fix': 5,
       'quality_basis': 6, 'evidence': 7, 'issue_ids': 8}


def patch(cid, **kw):
    for k, v in kw.items():
        CHECKS[cid][POS[k]] = v


patch('01-A1-13',
      quality='excellent',
      reason='检查者独立实测场景 S5：退款申请与发货并发 3 轮，内存模式下结果恒为 refund=0 且 ship=M-22'
             '（订单落在「退款审核中」）；重复支付与退款通知幂等；越权查单、取消、审核、调价、核查、汇总'
             '均被 M-20 拒绝。第 7 轮新增真实 InnoDB 行锁复现脚本 evidence/db/inno_ship_refund_race.py 并'
             '真实执行：5 轮并发裁决中 3 轮由退款胜出（ship=M-22）、2 轮由发货胜出（refund=M-11），'
             '两种合法结果均真实出现；每轮订单行终态唯一、goods 表 available_stock+occupied_stock 恒定、'
             'payment 终态类审计事件不重复；行锁阻塞探针证明请求确实阻塞在外部事务 T0 持有的 InnoDB 行锁上'
             '（持锁 4 秒未返回，T0 回滚后立即成功），共 37 条断言全部 PASS。',
      fix='无需整改。',
      quality_basis='并发裁决结论在进程内互斥锁与真实 InnoDB 行锁两种环境下均成立，且有外部事务持锁阻塞'
                    '探针这一决定性证据；幂等与越权两侧断言齐备，质量满分。',
      evidence=['E-04', 'E-12', 'E-15', 'E-19'],
      issue_ids=[])

patch('01-A4-01',
      quality='excellent',
      reason='检查者按根目录 README.md 从干净构建到启动成功，/health 返回 200，schema.sql 提供建表与'
             '演示数据；README 汇总了环境前置、构建、演示账号、模拟渠道、MySQL 模式建库与核对命令、'
             '五组场景接口入口，并列出全部质量门禁与验证脚本位置。此前分散在 docs/interface-list.md、'
             'docs/代码产物补齐说明.md、docs/git-提交指引.md 与 evidence/mysql核查记录.md 四处的运行说明，'
             '本轮已收敛到单一入口。',
      fix='无需整改。',
      quality_basis='第三方只读 README.md 即可完整复现两种运行模式与全部验证路径，统一入口成立，'
                    '复现成本问题消除，质量满分。',
      evidence=['E-05', 'E-12', 'E-15', 'E-20'],
      issue_ids=[])

patch('01-A4-05',
      status='partial',
      quality='excellent',
      reason='流水线本轮完成实质改造：定义已从 evidence/ci.yml 迁至生效路径 .github/workflows/ci.yml'
             '（质量门禁 11 步 + 部署门禁 4 步），新增 scripts/coverage_gate.py 实现「整体 ≥85% 且核心业务包'
             'server/service ≥85%」的阈值判定（原定义只统计覆盖率、不做阈值判断），新增 scripts/deploy_gate.py '
             '实现构建制品、版本登记、启动、健康检查、业务冒烟与回退准备校验，并作为独立部署门禁作业接入。'
             '两个脚本由检查者本地实测四个用例（真实覆盖率文件 PASS、低覆盖样本 FAIL、核心包缺失 FAIL、'
             '部署门禁全流程 PASS）全部符合预期。未完成部分：仓库仍无远端，流水线从未被真实触发，'
             '无任何 run 记录与步骤日志，故「实际流水线执行」这一要求仍未满足。',
      fix='经 GitHub MCP 建仓并关联远端后，由真实 PR 触发该工作流，保存 run URL、run id、状态与各步骤'
          '日志；再按 AGENTS.md 2.1 发起 PR 并把报告、覆盖率与验收结论附于 PR 描述。',
      quality_basis='交付物本身已达「可一键执行、结果可复现、含健康与回滚」水平：阈值判定与部署门禁均为'
                    '独立脚本，本地正反双向实测通过、失败时以非零码真实阻断，不是空壳；「未在真实远端运行」'
                    '属状态维度，已由部分完成体现，按规则不再重复拉低质量。',
      evidence=['E-13', 'E-14', 'E-18', 'E-21'],
      issue_ids=['ISS-CI-NOT-EFFECTIVE'])

patch('01-B2-02',
      status='pass',
      reason='本轮新增 evidence/agent-rules-load-log.md：说明根目录 AGENTS.md 由 IDE 按工作区规则自动注入'
             '会话上下文的加载机制，并按 AGENTS.md 第 0 章要求逐次登记加载时间、采用版本、对应任务与对应'
             '提交哈希，同时保留 v1.0/v1.1 版本对照与本轮条款对照。加载记录文件缺失这一状态缺口已闭环，'
             '该项由部分完成升为通过。仍有一处不可追溯：业务开发阶段（PRE-01 至 DB-01/BE-01）的加载时点'
             '因平台无会话录制能力无法还原，记录中已显式标注「无法追溯」而非按推定补记。',
      fix='若平台后续提供开发阶段的会话导出能力，按实际时点把该阶段加载记录补入本表；在此之前不得以推定填补。',
      quality_basis='加载机制、逐次登记与版本对照齐备，版本演进与任务绑定可核验；开发阶段的历史时点不可追溯'
                    '属客观限制而非遗漏，质量保留一档。',
      evidence=['E-06', 'E-14', 'E-20'],
      issue_ids=['ISS-AGENT-LOAD-BIND'])

patch('01-A3-06',
      reason='适用并发与重复操作具备可重复验证：检查者独立重跑 20 并发下单，恒为成功 5 + M-02 15、库存守恒；'
             '学生补充真实 InnoDB 下 20 并发成功 3、失败 17、available+occupied=5 恒等不超卖；重复支付/退款通知'
             '幂等已升级为表级断言（有效收款笔数恒为 1）。竞态探针方面，学生在 WSL Ubuntu 的真实 gcc 15.2.0 + '
             'CGO_ENABLED=1 工具链下执行 go test -race ./... -count=1，6 个测试包全部 ok、exit=0、无 DATA RACE；'
             '该竞态步骤本轮已固化进生效路径 .github/workflows/ci.yml 的质量门禁作业，具备由第三方在真实流水线'
             '复核的条件。但检查者本机 CGO_ENABLED=0 且无 gcc/clang，竞态结论仍为第一方产出。',
      quality_basis='并发守恒与重复操作已有数据库级证据，竞态探针有真实工具链输出且步骤已固化进生效路径的'
                    '流水线；但探针为第一方产出、检查者未能在同环境复跑，质量降一档。',
      evidence=['E-09', 'E-12', 'E-13', 'E-15', 'E-17', 'E-18'],
      issue_ids=['ISS-RACE-FIRSTPARTY'])

m.CHECKS = [tuple(CHECKS[c[0]]) for c in m.CHECKS]

# ---------------------------------------------------------------- 问题修订
DROP = {'ISS-A1-13-SHIP-RACE', 'ISS-RUN-DOC-SCATTER', 'ISS-CI-NO-THRESHOLD',
        'ISS-NO-AGENT-LOAD'}
ISSUES = {i[0]: list(i) for i in m.ISSUES}
for _k in DROP:
    ISSUES.pop(_k, None)


def setfield(iid, pos, value):
    ISSUES[iid][pos] = value


setfield('ISS-CI-NOT-EFFECTIVE', 2,
         '.github/workflows/ci.yml 已成为生效路径且是可执行工作流（质量门禁 11 步含覆盖率阈值判定，'
         '部署门禁 4 步含制品构建、健康检查、业务冒烟与回退准备校验）；原 evidence/ci.yml 已迁移删除，'
         '旧占位模板已被替换。剩余事实：git remote -v 为空，无远端即无法由 PR 或 push 触发该工作流；'
         '全仓无任何流水线 run 记录、run id、状态或步骤日志。')
setfield('ISS-CI-NOT-EFFECTIVE', 3,
         '检查者核对生效路径文件为可执行定义而非注释模板（YAML 解析通过，含 on 与 jobs，质量门禁 11 步、'
         '部署门禁 4 步），并核对 git remote -v 为空、全仓 run 记录为 0；'
         '两个门禁脚本另经四用例本地实测，正反双向均符合预期。')
setfield('ISS-CI-NOT-EFFECTIVE', 4,
         '题面共同要求「流水线实际执行质量、覆盖率、构建和部署门禁」，其中「实际执行」仍为零：'
         '配置与门禁能力已完整交付，但从未在真实流水线运行，失败路径也未在真实环境验证过。'
         'A4-05 判部分完成；因质量维度已达满分档，该项得分未因本缺口额外受损。')
setfield('ISS-CI-NOT-EFFECTIVE', 5,
         '经 GitHub MCP 建仓并关联远端后，由真实 PR 触发 .github/workflows/ci.yml，保存 run URL、run id、'
         '状态与各步骤日志原文；必要时先用一次故意失败的覆盖率样本验证阈值步骤在真实流水线中确实阻断。')
setfield('ISS-CI-NOT-EFFECTIVE', 7,
         '第 5 轮该项为 ISS-CI-PLACEHOLDER（配置为纯注释模板，判失败）；第 6 轮升为部分完成但生效路径仍为'
         '占位、且缺阈值判定与部署作业；第 7 轮生效路径已修正、阈值判定与部署门禁作业已补齐并本地实测通过，'
         '本问题收敛为「无远端故从未真实运行」这一单一事实，判定维持部分完成、质量由 poor 升为 excellent。')
setfield('ISS-CI-NOT-EFFECTIVE', 8,
         'A4-05 状态轴的独立根因是流水线从未在真实远端运行；同项原质量根因（缺覆盖率阈值判定与部署作业）'
         '已闭环，不再重复计分。')

setfield('ISS-RACE-FIRSTPARTY', 2,
         'evidence/race_raw_output.txt 显示 Go 1.26.8 linux/amd64、gcc (Ubuntu 15.2.0)、CGO_ENABLED=1、'
         '6 包 ok、race_exit=0，输出无 WARNING: DATA RACE，执行方式为 WSL 内的 evidence/wsl_race_run.sh。'
         '检查者本机为 Windows，CGO_ENABLED=0，where gcc 与 where clang 均无结果，无法在检查者环境复现同一探针。'
         '本轮变化：该竞态步骤已固化进生效路径 .github/workflows/ci.yml 的质量门禁作业，'
         '具备在真实流水线中由第三方复核的条件，但因无远端仍未产生 run 记录。')
setfield('ISS-RACE-FIRSTPARTY', 5,
         '关联远端后触发一次真实流水线并上传 race 原始输出与竞态步骤日志，使结论可由第三方复核。')
setfield('ISS-RACE-FIRSTPARTY', 7,
         '第 6 轮首次登记该证据来源的可核验性问题；第 7 轮竞态步骤已固化进生效路径的流水线作业，'
         '第一方性在真实流水线运行前仍未消除，故保留。')

setfield('ISS-DB-SCREENSHOT-UNTRACKED', 2,
         'evidence/db/screenshots/ 下有 7 张 PNG：order_insert_success、order_select_check、'
         'order_select_result、order_unique_dup_error、ticket_create_table_ok、ticket_python_conn_refuse、'
         'ticket_python_traceback；git log --all -- evidence/db/screenshots 跟踪提交数为 0；'
         '全仓文档对 screenshots 的引用数为 0。内容为 Navicat Premium 执行 INSERT INTO `order` 返回 '
         '1062 - Duplicate entry 的原始界面，以及 WSL 中 python ticket_verify.py 抛出 pymysql 1698 '
         'Access denied 的排查过程。第 7 轮学生已明确决定该 7 张截图保留在 evidence/db/screenshots '
         '不纳入版本库。')
setfield('ISS-DB-SCREENSHOT-UNTRACKED', 4,
         '两项作用：其一，截图可佐证 E-16 的唯一索引 1062 冲突确为真实执行，且 ticket_python_traceback 记录了'
         '学生用 root@localhost 触发 1698 权限失败后改用 mysql_prepare_user.sh 建应用账号的真实排查过程，'
         '与 mysql_raw_00_env.txt 的账号准备叙述一致，属诚实的过程留痕；其二，截图未入库使克隆仓库的复核者'
         '无法看到，证据可及性受限。因属佐证性补充、无文档引用且不影响业务判定，不扣分。')
setfield('ISS-DB-SCREENSHOT-UNTRACKED', 5,
         '维持现状即可（按学生决定不纳入版本库）；若后续愿意入库，再在 docs/db/order_table_verify.md 与 '
         'docs/db/ticket_table_verify.md 中按步骤引用。')
setfield('ISS-DB-SCREENSHOT-UNTRACKED', 7,
         '第 7 轮首次登记；同轮学生已明确该 7 张截图保留在工作区不提交，事实已更新，扣分口径不变（仍为建议项）。')

# 13 长元组的 deduction_basis / deduplication 由 ISSUE_BASIS / ISSUE_DEDUP 在构建时注入，
# 直接改这两个字典，避免与元组下标错位（13 长的 certainty/owner/evidence/deductions
# 分别位于 9/10/11/12，14 长的位于 10/11/12/13）。
m.ISSUE_BASIS['ISS-CI-NOT-EFFECTIVE'] = (
    'A4-05 状态轴的独立根因是流水线从未在真实环境生效与运行（无远端、零 run 记录）；'
    '同项原质量根因（缺覆盖率阈值判定与部署门禁作业）已于本轮闭环并单列 ISS-CI-NO-THRESHOLD 后删除，'
    '两者不重复计分。')
m.ISSUE_DEDUP['ISS-CI-NOT-EFFECTIVE'] = (
    '第 7 轮起本问题收敛为单一根因（无远端故流水线从未真实运行）；'
    '与已闭环并删除的 ISS-CI-NO-THRESHOLD 分属不同事实，不重复描述同一扣分事实。')

setfield('ISS-AGENT-LOAD-BIND', 1,
         '业务开发阶段（PRE-01 至 DB-01/BE-01）的约束加载时点因平台无会话录制能力而不可追溯，'
         '仅第 7 轮及之后的加载记录可核验')
setfield('ISS-AGENT-LOAD-BIND', 2,
         'evidence/agent-rules-load-log.md 已按 AGENTS.md 第 0 章登记加载机制、逐次加载时间、采用版本、'
         '对应任务与提交哈希，并保留 v1.0/v1.1 版本对照；但业务开发阶段的加载时点无法还原，'
         '记录中显式标注「无法追溯」而非按推定补记。')
setfield('ISS-AGENT-LOAD-BIND', 3,
         '检查者读取 evidence/agent-rules-load-log.md 全文并与 AGENTS.md 第 7 章变更表逐条比对，'
         '确认版本演进与任务绑定可核验，同时确认开发阶段时点为显式标注的不可追溯项。')
setfield('ISS-AGENT-LOAD-BIND', 4,
         '加载记录已使约束实际生效可证，B2-02 状态由部分完成升为通过；但开发阶段加载时点不可追溯，'
         '绑定证据在该阶段仍不完整，B2-02 的质量保留一档。')
setfield('ISS-AGENT-LOAD-BIND', 5,
         '若平台后续提供开发阶段的会话导出能力，按实际时点把该阶段加载记录补入本表；'
         '在此之前不得以推定填补。')
setfield('ISS-AGENT-LOAD-BIND', 6,
         '复评时抽查两条第 7 轮之后的加载记录，确认其时间、版本、任务与提交哈希自洽，'
         '并核对开发阶段条目是否仍为显式标注的不可追溯。')
setfield('ISS-AGENT-LOAD-BIND', 7,
         '第 5 轮首次单独登记该质量根因；第 6 轮维持；第 7 轮 evidence/agent-rules-load-log.md 交付后，'
         '加载记录缺失的状态根因闭环，本质量根因收窄为开发阶段时点不可追溯这一项。')
setfield('ISS-AGENT-LOAD-BIND', 11, ['E-06', 'E-14', 'E-20'])
setfield('ISS-AGENT-LOAD-BIND', 12,
         [('01-B2-02', 'quality', '开发阶段加载时点不可追溯，质量保留一档。')])
m.ISSUE_BASIS['ISS-AGENT-LOAD-BIND'] = (
    'B2-02 质量轴的独立根因是开发阶段加载时点不可追溯；'
    '与已闭环的 ISS-NO-AGENT-LOAD（加载记录文件缺失）分属不同事实，不重复计分。')
m.ISSUE_DEDUP['ISS-AGENT-LOAD-BIND'] = (
    '与 ISS-NO-AGENT-LOAD 区分：后者为加载记录缺失（状态，已于第 7 轮闭环并删除），'
    '本项为开发阶段加载时点不可追溯（质量，保留），两者不重复描述同一事实。')

m.ISSUES = [tuple(ISSUES[i[0]]) for i in m.ISSUES if i[0] in ISSUES]

# ---------------------------------------------------------------- 元信息与输出
META = dict(m.META)
META.update({
    'audit_id': 'AUDIT-SHOP-TRADE-01-20261113-07',
    'auditor': 'CodeBuddy 检查会话（student-project-audit V3.0）；该会话与本题第 1~7 轮开发会话同源，'
               '存在利益相关风险，已在 limitations 与 score.json 的 audit_meta 中显式声明，复评应改由'
               '不同检查者执行',
    'audit_date': '2026-11-13',
    'batch': '20261113-07',
    'calibration_id': '未校准：本批次为该 profile 在本班的第 7 次 V3.0 评分，前 6 批次可作纵向对照，'
                      '但无教师核准的同批其它样本可作评分校准',
    'environment': 'Windows 11 + PowerShell（本轮明确禁止使用 WSL）；Go 官方工具链 go1.26.0 windows/amd64；'
                   '本机 CGO_ENABLED=0、无 gcc/clang、无 MySQL 客户端、无远端仓库；'
                   '2026-11-13 复核时 127.0.0.1:3306 拒绝连接、3306 无监听、Windows 无 MySQL 服务、'
                   'WSL 网段扫描无 MySQL 实例（WSL 内 MySQL 已停止且禁止以 WSL 启动），'
                   '故本轮数据库层结论一律以 2026-11-12 22:44 的真实执行原始输出为凭据，不重跑、不伪造；'
                   '检查者以独立二进制与独立端口运行服务，与学生脚本完全分离',
    'previous_report': 'outputs/单题检查/shop-trade/01/20261112-06/检查报告.md',
    'previous_score': '6.38',
    'change_summary': '第 6 轮后新增 4 次提交，业务代码与数据库脚本无任何改动：'
                      'd37e8f6 [opt] 流水线定义落地生效路径并补齐覆盖率阈值判定与部署门禁作业 → '
                      'cd823f5 [test] 新增 InnoDB 行锁下退款与发货互斥裁决复现脚本与真实执行原始输出 → '
                      'c452555 [docs] 补根目录 README 统一运行入口与 AGENTS 约束加载记录 → '
                      'ed675f7 [opt] 修正覆盖率阈值口径为整体与核心业务包 server/service 双阈值（HEAD，检查基准）。'
                      '新增证据：.github/workflows/ci.yml（生效路径，质量门禁 11 步含覆盖率阈值判定、'
                      '部署门禁 4 步含制品构建与健康检查）、scripts/coverage_gate.py、scripts/deploy_gate.py、'
                      'evidence/db/inno_ship_refund_race.py 与同名 _raw.txt/_raw.json/.app.log/.md'
                      '（真实 InnoDB 行锁下 37 条断言全部 PASS，执行于 2026-11-12 22:44）、README.md、'
                      'evidence/agent-rules-load-log.md，以及本批次 '
                      'outputs/单题检查/shop-trade/01/20261113-07/evidence/gate_scripts_verify.txt'
                      '（两个门禁脚本四用例本地实测 4/4 符合预期）。'
                      '检查者本批次独立取证：ci.yml 生效路径与 YAML 结构核对、git remote 与全仓 run 记录清点、'
                      '门禁脚本四用例正反双向实测、MySQL 可达性探测（探测结果为不可达，已如实登记，'
                      '未以任何方式伪造数据库层复核）。',
    'history_resolution': '第 6 轮报告按 V3.0 固定清单 58 个原子项给出判定分布 pass 37 / partial 6 / '
                          'fail 14 / unknown 1，当前已核验得分 6.38/10（成果 5.88/7、过程 0.50/1.5、'
                          'Token 0.00/1.5 unknown），状态待核定；旧报告与旧分数保留不覆盖，本轮不沿用旧成绩。'
                          '第 6 轮登记的 5 项本轮问题逐项复核：(1) ISS-CI-NOT-EFFECTIVE 与 '
                          'ISS-CI-NO-THRESHOLD —— 流水线定义已从 evidence/ci.yml 迁至生效路径 '
                          '.github/workflows/ci.yml，并补齐覆盖率阈值判定（scripts/coverage_gate.py，'
                          '整体与核心业务包 server/service 双阈值，不达标非零退出即阻断）与部署门禁作业'
                          '（scripts/deploy_gate.py，构建制品、版本登记、启动、健康检查、业务冒烟、回退准备），'
                          '两个脚本经检查者四用例本地实测全部符合预期，质量根因闭环；剩余单一事实为'
                          '无远端故流水线从未真实运行，A4-05 由 pass/poor 升为 partial/excellent。'
                          '(2) ISS-A1-13-SHIP-RACE —— 已由 evidence/db/inno_ship_refund_race.py 在真实 '
                          'InnoDB 行锁下复现：5 轮并发裁决中 3 轮退款胜出（ship=M-22）、2 轮发货胜出'
                          '（refund=M-11），每轮订单行终态唯一且 available_stock+occupied_stock 恒定，'
                          '另有外部事务 T0 持锁 4 秒使请求确实阻塞、回滚释放后立即成功的阻塞探针，'
                          '37 条断言全部 PASS；A1-13 由 pass/good 升为 pass/excellent。'
                          '(3) ISS-RUN-DOC-SCATTER —— 已由根目录 README.md 把分散在四份文档的运行说明收敛为'
                          '单一入口（环境前置、构建、启动、演示账号、模拟渠道、MySQL 模式建库与核对、'
                          '五组场景接口、质量门禁与验证脚本清单），A4-01 由 pass/good 升为 pass/excellent。'
                          '(4) ISS-NO-AGENT-LOAD —— 已由 evidence/agent-rules-load-log.md 闭环（加载机制、'
                          '逐次登记、版本与任务绑定、v1.0/v1.1 对照），B2-02 由 partial/good 升为 pass/good；'
                          'ISS-AGENT-LOAD-BIND 收窄为开发阶段加载时点不可追溯这一质量项并保留，'
                          '业务开发阶段的时点因平台无会话录制能力不可追溯，已显式标注而非按推定补记。'
                          '(5) ISS-RACE-FIRSTPARTY —— 竞态步骤已固化进生效路径流水线质量门禁作业，'
                          '但无远端即无 run 记录，第一方性未消除，故维持不变。'
                          '仍维持 fail 的项：缺独立测试会话（A3-07）、缺独立验收会话（B1-04）、'
                          '五段前置链断裂（B1-02）、缺会话导出与原始提示（B2-03/04/05）、'
                          '部署与回退方案（A4-06、A4-07）、缺讲解视频（A4-08、A4-09）、'
                          '缺班级群凭据（A4-10）、无 MCP 建仓与 PR（B4-01、B4-04、B4-05）。'
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
        'profile_sha256': __import__('hashlib').sha256(PROFILE.read_bytes()).hexdigest(),
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

