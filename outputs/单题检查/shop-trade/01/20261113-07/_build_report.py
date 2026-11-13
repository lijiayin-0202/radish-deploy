#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 report-data.json（13 节报告叙述数据，批次 20261113-07）。

以第 6 轮报告数据为基线做定向修订：只改本轮有新证据支撑的表格行与叙述，
其余逐字沿用，避免复核口径漂移。
"""
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(r'd:/Desktop/shop')
OUT = ROOT / 'outputs/单题检查/shop-trade/01/20261113-07'
R6 = ROOT / 'outputs/单题检查/shop-trade/01/20261112-06/_build_report.py'
REV = 'ed675f7（dev/01，2026-11-13）'
OLD_REV = '82c4847（dev/01，2026-11-12）'

spec = importlib.util.spec_from_file_location('r6r', str(R6))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

TABLES = m.TABLES
EV = m.EV

# ---------------------------------------------------------------- 证据索引
EV['E-18'] = (
    'artifact', '.github/workflows/ci.yml；scripts/coverage_gate.py；scripts/deploy_gate.py；evidence/CI流水线说明.md',
    '生效路径上的可执行流水线定义：质量门禁 11 步（checkout、setup-go、gofmt、go vet、go build、单元测试、'
    '竞态检测、覆盖率采集、覆盖率阈值判定、覆盖率明细、产物上传）与部署门禁 4 步；'
    '阈值判定由 scripts/coverage_gate.py 执行（原定义只统计不判定），部署门禁由 scripts/deploy_gate.py 执行'
    '（构建制品、版本登记、启动、健康检查、业务冒烟、回退准备校验）',
    '2026-11-13（HEAD ed675f7）', '流水线门禁配置、覆盖率阈值判定与部署门禁作业的完整性',
    '学生提交；检查者逐行审读生效路径 YAML 并对两个门禁脚本执行四用例本地实测')
EV['E-19'] = (
    'raw_tool', 'evidence/db/inno_ship_refund_race.py；evidence/db/inno_ship_refund_race_raw.txt；'
    'evidence/db/inno_ship_refund_race_raw.json；evidence/db/inno_ship_refund_race.app.log；'
    'evidence/db/inno_ship_refund_race.md',
    '真实 MySQL 8.4.11 InnoDB 下退款与发货互斥裁决复现：5 轮并发中 3 轮由退款胜出（ship=M-22）、'
    '2 轮由发货胜出（refund=M-11），每轮订单行终态唯一且 available_stock+occupied_stock 恒定；'
    '另有外部事务 T0 持锁 4 秒使应用请求确实阻塞、T0 回滚后立即成功的行锁阻塞探针；共 37 条断言全部 PASS，'
    '执行于 2026-11-12 22:44',
    '2026-11-12（HEAD cd823f5）', '退款与发货互斥裁决在真实行锁下的合法结果唯一性与库存守恒',
    '学生执行原始输出；检查者于 2026-11-13 复核时 MySQL 已不可达，未重跑，据 2026-11-12 原始输出判定')
EV['E-20'] = (
    'artifact', 'README.md；evidence/agent-rules-load-log.md',
    '根目录 README.md 统一运行入口（环境前置、构建、启动、演示账号、模拟渠道、MySQL 模式建库与核对、'
    '五组场景接口、质量门禁与验证脚本清单）；evidence/agent-rules-load-log.md 登记 AGENTS.md 加载机制、'
    '逐次加载时间、采用版本、对应任务与提交哈希，并保留 v1.0/v1.1 对照，开发阶段时点显式标注「无法追溯」',
    '2026-11-13（HEAD c452555）', '运行复现入口的单一化与 Agent 约束加载留痕',
    '学生提交；检查者按 README 从干净构建到启动复核，并逐条比对加载登记与 AGENTS.md 第 7 章')
EV['E-21'] = (
    'raw_tool', 'outputs/单题检查/shop-trade/01/20261113-07/evidence/gate_scripts_verify.txt；同目录 gate_scripts_verify.py',
    '两个门禁脚本的四用例本地实测：真实覆盖率样本 PASS、低覆盖样本 FAIL、核心业务包缺失 FAIL、'
    '部署门禁全流程 PASS，4/4 全部符合预期；失败路径以非零退出码真实阻断',
    '2026-11-13（检查者本批次）', '覆盖率阈值判定与部署门禁脚本的可执行性与阻断行为',
    '检查者独立执行，与学生脚本分离留档')

# ---------------------------------------------------------------- 修订基线版本号
for _name, _rows in TABLES.items():
    for _row in _rows:
        if isinstance(_row, dict) and _row.get('revision') == OLD_REV:
            _row['revision'] = REV

# ---------------------------------------------------------------- 业务表
for _row in TABLES['completion']:
    if _row['requirement_id'] == '01-A1-13':
        _row['operations'] = ('3 轮并发同时发起退款申请与发货，重复支付与退款通知各两次，越权访问 6 类接口；'
                              '真实 MySQL 侧另做 20 并发下单与重复通知表级核对；'
                              '第 7 轮另在真实 InnoDB 行锁下复现退款/发货互斥裁决 5 轮，'
                              '并以外部事务持锁探针验证请求确实阻塞在行锁上')
        _row['actual'] = ('内存模式 3 轮并发结果恒为 refund=0 且 ship=M-22、订单落「退款审核中」；'
                          '重复通知幂等且真实库中有效收款笔数恒为 1；6 类越权全部返回 M-20。'
                          '真实 InnoDB 行锁复现 5 轮：3 轮退款胜出（ship=M-22）、2 轮发货胜出（refund=M-11），'
                          '两种合法结果均真实出现且每轮订单行终态唯一、available_stock+occupied_stock 恒定；'
                          '外部事务持锁 4 秒期间请求阻塞、回滚释放后立即成功，37 条断言全部 PASS')
        _row['evidence'] = ['E-04', 'E-12', 'E-15', 'E-19']

# ---------------------------------------------------------------- 运行指标
for _row in TABLES['code_runtime']:
    if _row['metric'] == 'normal_business':
        _row['actual'] = ('120 条断言 119 PASS，唯一 1 条 DIFF 为 demo-memory 无持久化的环境限制，非业务失败；'
                          '第 7 轮真实 InnoDB 行锁下的退款/发货互斥裁决 5 轮共 37 条断言全部 PASS')
        _row['evidence'] = ['E-12', 'E-19']
    elif _row['metric'] == 'abnormal_business':
        _row['command'] = ('越权、幂等、重复、并发、非法参数与未知订单共 38 类负向断言；'
                           '另加真实 InnoDB 行锁下的退款/发货互斥裁决 5 轮与外部事务持锁阻塞探针')
        _row['actual'] = ('全部返回预期错误码；重复支付/退款通知不重复记款与退款；20 并发守恒；6 类越权全部 M-20；'
                          '真实行锁下 5 轮互斥裁决每次只产生一种合法结果，订单行终态唯一、库存两列守恒，'
                          '外部事务持锁期间请求确实阻塞、回滚释放后立即成功')
        _row['evidence'] = ['E-12', 'E-19']
    elif _row['metric'] == 'deployed_smoke':
        _row['command'] = ('（无）无远端仓库、无 main 分支、无部署流水线，无法执行上线冒烟；'
                           '本地已具备可原样复跑的部署门禁脚本 scripts/deploy_gate.py')
        _row['actual'] = ('未执行：git remote -v 为空、无部署产物与上线地址，缺证按 unknown 登记而非判失败；'
                          '部署门禁脚本经检查者本地全流程实测 PASS，可由真实流水线直接调用')
        _row['evidence'] = ['E-13', 'E-14', 'E-18', 'E-21']

# ---------------------------------------------------------------- 阶段检查点
for _row in TABLES['workflow']:
    if _row['stage'] == 'development':
        _row['time'] = '2026-11-12 至 2026-11-13（6cc6f13 及后续 17 次提交）'
        _row['snapshot'] = ('Go 源码、schema.sql、模拟渠道服务、8 个业务视图、AGENTS.md v1.1、'
                            '根目录 README.md 与 evidence/agent-rules-load-log.md')
        _row['evidence'] = ['E-04', 'E-05', 'E-06', 'E-20']
    elif _row['stage'] == 'testing':
        _row['snapshot'] = '12 个 *_test.go、170 份集成证据、5 个采集脚本与第 7 轮新增的 InnoDB 行锁并发复现脚本'
        _row['evidence'] = ['E-09', 'E-10', 'E-14', 'E-19']
    elif _row['stage'] == 'deployment':
        _row['snapshot'] = ('无远端仓库、无 main 分支、无制品、无部署流水线与上线地址；'
                            '但仓库已有生效路径的流水线定义与两个可原样复跑的门禁脚本')
        _row['evidence'] = ['E-13', 'E-14', 'E-18', 'E-21']

# ---------------------------------------------------------------- Agent 与 Skill
for _row in TABLES['agents_skills']:
    if _row['id'] == 'SKILL-AGENT-RULES':
        _row['loaded_at'] = 'evidence/agent-rules-load-log.md 逐次登记加载时间、采用版本、对应任务与提交哈希'
        _row['usage_location'] = ('开发阶段约束开发、测试与验收三类会话的范围与提交门禁；'
                                  '第 7 轮加载记录已按 AGENTS.md 第 0 章要求登记')
        _row['limitations'] = ('加载记录已交付并可核验版本、任务与提交哈希的绑定；'
                                '业务开发阶段（PRE-01 至 DB-01/BE-01）的加载时点因平台无会话录制能力不可追溯，'
                                '记录中显式标注「无法追溯」而非按推定补记')
        _row['evidence'] = ['E-06', 'E-20']

# ---------------------------------------------------------------- 限制项
LIM = {r['id']: r for r in TABLES['limitations']}

LIM['LIM-02']['reason'] = ('仓库内未找到教师对 references/profiles/01.json 的核准记录；'
                            '本班前 6 批次可作纵向对照，但无教师核准的同批其它样本可作评分校准。')
LIM['LIM-02']['score_effect'] = '计分口径未经教师核准与校准，6.47 为当前已核验得分，不是最终成绩。'

LIM['LIM-03']['reason'] = (
    'evidence/race_raw_output.txt 与 mysql_raw_05_app_persistence.txt 均为第一方原始输出。'
    '检查者本机 CGO_ENABLED=0、无 gcc/clang、无 MySQL 客户端，且受本批次 PowerShell-only 约束未使用 WSL，'
    '无法在同环境复跑竞态探针与应用级重启复核。第 7 轮竞态步骤已固化进生效路径 .github/workflows/ci.yml '
    '的质量门禁作业，具备由第三方在真实流水线复核的条件，但因无远端仍未产生 run 记录。'
    '检查者可独立复核的部分为：120 条业务断言、gofmt/vet/build/test、覆盖率独立 profile、'
    '两个门禁脚本的四用例本地实测，以及对同一 MySQL 实例的引擎、字符集、唯一约束、1062 冲突与'
    '数据库重启后数据留存的直接查询。')
LIM['LIM-03']['score_effect'] = ('A3-06 因竞态结论为第一方产出且不可同环境复跑而质量降一档'
                                  '（ISS-RACE-FIRSTPARTY）；A2-04、A3-05、A4-04 的数据库层已由检查者独立复核，'
                                  '不受此限制影响。')
LIM['LIM-03']['next_action'] = ('关联远端后触发一次真实流水线并上传 race 原始输出与竞态步骤日志，'
                                 '使结论可由第三方复核。')

LIM['LIM-05']['reason'] = ('git remote -v 为空；.github/workflows/ci.yml 已于第 7 轮由占位模板替换为'
                            '可执行工作流（质量门禁 11 步含覆盖率阈值判定、部署门禁 4 步）；'
                            '但无 main 分支、制品与上线地址，流水线从未被触发，run 记录为 0。')
LIM['LIM-05']['score_effect'] = ('A4-05 判部分完成（配置、阈值判定与部署门禁作业均已交付，'
                                  '实际执行与远端运行缺失），A4-06、A4-07、B4-01、B4-04、B4-05 判失败。')
LIM['LIM-05']['next_action'] = ('经 GitHub MCP 建仓并关联远端，由真实 PR 触发 .github/workflows/ci.yml，'
                                 '走 PR 合并 main 后部署并留存冒烟与回退方案。')

LIM['LIM-09']['score_effect'] = ('B2-03、B2-04、B2-05 三项判失败；B2-02 因加载记录已交付由部分完成升为通过，'
                                  '仅保留开发阶段加载时点不可追溯这一质量项。')

TABLES['limitations'].append({
    'id': 'LIM-10', 'scope': '真实 InnoDB 行锁复现证据的当日复跑', 'owner': 'student',
    'reason': ('第 7 轮复核时 127.0.0.1:3306 拒绝连接、3306 无监听、Windows 无 MySQL 服务、'
               'WSL 网段扫描无 MySQL 实例，而本批次明确禁止使用 WSL，故无法重启同一 MySQL 实例复跑'
               'evidence/db/inno_ship_refund_race.py。该脚本的真实执行原始输出（含应用启动标识 '
               'mode=mysql-innodb）保留于 2026-11-12 22:44，未删除、未改写、未以任何方式重造。'),
    'score_effect': ('A1-13 依据 2026-11-12 的真实 InnoDB 原始输出判定为通过；'
                     '因当日无法独立复跑，检查者在 A1-13 的理由中显式标注执行时点与复跑限制。'),
    'next_action': ('恢复 MySQL 实例后按 evidence/db/inno_ship_refund_race.md 的复现步骤原样重跑一次，'
                    '并在产物中并列两次输出以便对照。'),
    'evidence': ['E-19']})

# ---------------------------------------------------------------- 理解与日表
UND = {r['id']: r for r in TABLES['understanding']}
UND['UND-03']['result'] = ('7 项必交产物缺失；流水线生效路径已修正为可执行工作流（质量门禁 11 步 + 部署门禁 4 步）；'
                            '就绪状态两项未就绪')
UND['UND-06']['method'] = ('逐行审读生效路径 .github/workflows/ci.yml，并对 on/jobs/steps、阈值判定与部署作业做关键字检索')
UND['UND-06']['result'] = ('定义含 on 与 jobs、质量门禁 11 步与部署门禁 4 步，含覆盖率 ≥85% 阈值判定步骤'
                            '（整体与核心业务包 server/service 双阈值，不达标非零退出即阻断）与部署门禁作业'
                            '（制品构建、版本登记、启动、健康检查、业务冒烟、回退准备）；'
                            '两个门禁脚本经四用例本地实测正反双向符合预期；'
                            '仍未在任何真实远端运行，全仓 run 记录为 0')
TABLES['understanding'].append({
    'id': 'UND-08', 'method': '对 scripts/coverage_gate.py 与 scripts/deploy_gate.py 执行四用例本地实测（正反双向）',
    'scope': '覆盖率阈值判定的阻断行为、核心业务包缺失的处理、部署门禁全流程',
    'result': ('真实覆盖率样本 PASS、低覆盖样本 FAIL、核心业务包缺失 FAIL、部署门禁全流程 PASS，4/4 符合预期；'
               '失败路径以非零退出码真实阻断，可由第三方原样复跑'),
    'evidence': ['E-21']})

TABLES['daily'][0]['date'] = '2026-11-13'
TABLES['daily'][0]['scope'] = '第 7 轮整改后交付版本（HEAD ed675f7）的成果与过程复核'
TABLES['daily'][0]['result'] = ('成果 5.92/7、过程 0.55/1.5、Token 0.00/1.5，扣后原始分 6.47，状态待核定；'
                                 '判定分布 pass 37 / partial 6 / fail 14 / unknown 1；'
                                 '较第 6 轮 6.38 提升 0.09，全部来自成果侧四项质量提升')
TABLES['daily'][0]['evidence'] = ['E-12', 'E-13', 'E-14', 'E-19', 'E-21']
TABLES['daily'].append({
    'id': 'DAY-04', 'date': '2026-11-13', 'scope': '流水线生效路径核对、两个门禁脚本四用例实测与 MySQL 可达性探测',
    'result': ('ci.yml 已位于 .github/workflows/ 生效路径且为可执行工作流（质量门禁 11 步 + 部署门禁 4 步）；'
               '门禁脚本四用例 4/4 符合预期；MySQL 探测结果为不可达，数据库层结论以 2026-11-12 原始输出为凭据'),
    'evidence': ['E-19', 'E-21']})

# ---------------------------------------------------------------- 元信息
META = dict(m.META)
META.update({
    'delivery_date': '2026-11-13',
    'deployment': ('未部署。本地无远端仓库（git remote -v 为空）、无 main 分支、无制品与已触发的流水线、'
                   '无上线地址，部署与上线冒烟按缺证登记为 unknown/fail'
                   '（见 LIM-05、表格 code_runtime.deployed_smoke）。第 7 轮已把流水线定义落到生效路径 '
                   '.github/workflows/ci.yml 并补齐部署门禁作业（scripts/deploy_gate.py：构建制品、版本登记、'
                   '启动、健康检查、业务冒烟、回退准备校验，经检查者本地全流程实测 PASS），'
                   '但因无远端，其 pull_request 触发条件从未生效，run 记录为 0。'),
    'version_chain': (
        'dev/01 共 19 次提交：6cc6f13（基线 feat：需求/原型/计划文档 + 全部业务源码）→ '
        '6083edd [opt] 补齐验收检查 Skill 与商品调价等交付产物 → '
        '018551c [opt] 补齐模拟支付渠道服务与第四轮冒烟产物 → '
        '00520bd [test] 补充第五轮边界单测与证据采集产物 → '
        '537453c [docs] 补齐接口边界矩阵与第五轮证据闭环文档 → '
        '68801cb [docs] 回补版本链核查与第五轮提交记录 → '
        '58719fb [test] 追加提交后门禁复核原始输出 → '
        '25aa8f1 [opt] 补全订单服务与 GORM 仓储层导出方法文档注释并修正 go.mod 直接依赖声明 → '
        '9c32eff [test] 补充真实 MySQL 环境建表脚本与 InnoDB 核查、竞态检测、覆盖率及接口入参巡检证据 → '
        '501136c [docs] 补充 MySQL 核查记录、会话导出与 CI 流水线说明、竞态检测说明及门禁自查汇总 → '
        'e142649 [docs] 归档第五轮单题检查报告、评分明细与两份输入 → '
        '85c4ae6 [test] 修正 mysql_raw_01_schema.txt 编码为 UTF-8 → '
        '03c4238 [docs] 新增订单表 order_no 唯一索引与持久化验证文档及真实执行原始输出 → '
        '82c4847 [docs] 新增工单表 ticket_no 唯一索引与持久化验证文档及真实执行原始输出 → '
        'a31384b [docs] 归档第六轮单题检查报告、评分明细与两份输入 → '
        'd37e8f6 [opt] 流水线定义落地生效路径并补齐覆盖率阈值判定与部署门禁作业 → '
        'cd823f5 [test] 新增 InnoDB 行锁下退款与发货互斥裁决复现脚本与真实执行原始输出 → '
        'c452555 [docs] 补根目录 README 统一运行入口与 AGENTS 约束加载记录 → '
        'ed675f7 [opt] 修正覆盖率阈值口径为整体与核心业务包 server/service 双阈值（HEAD，检查基准）。'
        '第 6 轮之后的 4 次提交不含任何业务代码与数据库脚本改动：流水线定义与两个门禁脚本、'
        '并发复现脚本与原始输出、README 与加载登记文档，以及一处覆盖率阈值口径修正。'
        '全程仅 dev/01 一个分支，无 main、无远端、无 PR 记录。'),
    'scope': ('题面「题目 01 + 一、所有题目共同适用的要求」全量条目，叠加固定清单 references/profiles/01.json '
              '的 58 个原子评分项：A1 八条业务规则与五组演示场景（13 项）、A2 数据与持久化、A3 代码与并发、'
              'A4 流程与交付物、B1 阶段与顺序、B2 测试与验收独立性、B3 Agent 与 Skill、'
              'B4 Git/流水线/部署/讲解。核查手段为：全仓产物清点与缺证登记、Go 工具链独立复跑'
              '（gofmt/go vet/go build/go test/go test -coverpkg）、独立二进制 + 独立端口 18097 的 120 条'
              '反例探测、对同一 MySQL 8.4.11 实例的直接查询复核（引擎、字符集、四类唯一索引、1062 冲突、'
              '数据库重启后数据留存）、事务回滚与唯一索引原始输出审读、真实 InnoDB 行锁下退款与发货互斥裁决'
              '5 轮复现与外部事务持锁阻塞探针、流水线生效路径 YAML 逐行审读、两个门禁脚本四用例正反双向实测、'
              'MySQL 可达性探测、源码通读与版本链核查。'),
    'token_note': ('Token 计分暂记 0.00/1.5、状态 unknown，理由：教师未发布本题 Token 基准'
                   '（references/profiles/01.json 的 token_baselines 为空），学生亦未提交分阶段原始 usage 与'
                   '去重台账，无可比总量，无法计算消耗比与可避免 Token，因此不计分、不推定学生浪费。'
                   '该缺口已按教师责任登记为限制项 LIM-01 与门禁项 TOKEN；教师发布基准并由学生补交官方 usage '
                   '原件后，须重新运行 token_score 并重算总分，故本批次 6.47 为当前已核验得分而非最终成绩。'
                   '与第 6 轮相比，本轮过程类评分（B1~B4 共 1.5 分）仅 B2-02 由部分完成升为通过（+0.045），'
                   '其余全部提升集中在成果侧的 A1-13、A4-01、A4-05 三项（+0.041），即学生以真实环境证据与'
                   '真实门禁脚本关闭的缺口。'),
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


