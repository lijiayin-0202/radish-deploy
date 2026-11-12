#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第四轮：由 audit-input.json + score.json 生成两份 UTF-8 BOM 明细 CSV。

继承第三轮全部历史过程行（S-01~S-30），只追加第四轮 S-31~S-40。
"""
import csv
import json
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
R3 = OUT.parent / '20261112-03'

data = json.loads((OUT / 'audit-input.json').read_text(encoding='utf-8-sig'))
score = json.loads((OUT / 'score.json').read_text(encoding='utf-8'))
norm = {row['id']: row for cat in score['categories'] for row in cat['checks']}

prior = {}
with (R3 / '要求与评分明细.csv').open('r', encoding='utf-8-sig', newline='') as f:
    for row in csv.DictReader(f):
        prior[row['要求编号']] = row

PROMOTED = {
    'R-A1-04', 'R-A1-10', 'R-A2-06', 'R-A3-01', 'R-A3-02',
    'R-A4-02', 'R-B2-03', 'R-B2-04', 'R-B3-02',
}


def dec4(text):
    return '%.4f' % float(Fraction(text))


def remedy(item):
    status = item['status']
    if status == 'pass':
        if item['id'] in PROMOTED:
            return ('本轮已由 partial 提升为 pass：逐用例证据/契约/边界单测/独立模拟渠道实例已补齐，保持回归',
                    '后续每轮复跑对应命令并绑定提交哈希；独立会话证据另行补证')
        return ('无需整改，保持回归', '每轮复跑对应命令并绑定提交哈希')
    if status == 'unknown':
        return ('环境补证（非代码缺陷）：在具备 CGO/gcc、真实 MySQL、meegle/远端权限的环境重跑并保存原始输出',
                '核对原始输出、退出码、race/覆盖率原件与最终提交哈希对应关系')
    if status == 'fail':
        return ('补齐缺失产物或独立会话证据；历史过程证据不可事后补造，见报告第 6 节',
                '在独立测试/验收会话逐项复查并保留原始输出；不可补项如实登记')
    return ('补齐 reason 中列明的环境/过程证据（见报告第 6 节）',
            '在具备条件的环境重跑对应场景或命令并核对原始输出')


fields = ['要求编号', '来源', '分类', '原子满分', '是否必做', '条件', '预期', '实际',
          '状态', '系数', '归一后得分', '失分', '证据', '整改', '复验']
with (OUT / '要求与评分明细.csv').open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for item in data['checks']:
        n = norm[item['id']]
        p = prior.get(item['id'], {})
        fix, check = remedy(item)
        w.writerow({
            '要求编号': item['id'],
            '来源': p.get('来源', ''),
            '分类': item['category'],
            '原子满分': item['max_points'],
            '是否必做': str(item['mandatory']).lower(),
            '条件': p.get('条件', ''),
            '预期': p.get('预期', ''),
            '实际': item['reason'],
            '状态': item['status'],
            '系数': n['factor'],
            '归一后得分': dec4(n['points_exact']),
            '失分': dec4(n['loss_exact']),
            '证据': ';'.join(item['evidence']),
            '整改': fix,
            '复验': check,
        })

with (R3 / '过程与提示词明细.csv').open('r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    proc_fields = list(reader.fieldnames)
    history = list(reader)


def step(**kw):
    base = {k: '' for k in proc_fields}
    base.update(kw)
    return base


R4 = '2026-11-12 第四轮证据闭环优化与门禁复核（同一开发/复核会话，非独立测试/验收会话）'
REV = 'HEAD 6083edd06…（dev/01 第 2 次提交）+ 第四轮工作区增量（证据/文档/测试，尚未提交）'
extra = [
    step(**{'步骤': 'S-31', '任务号': '第四轮证据采集-接口/页面/Skill', '前置': 'S-30 第三轮结论',
            '应做动作': '每个接口、每个 Skill、每个 HTML 页面各补一条独立冒烟证据，不合并汇总',
            '实际时间/会话/消息': R4,
            '提示及上下文': '用户「给每个接口、每个skill、每个html页面补充独立的单条冒烟证据，追加到evidence/，每个用例单独一条输出记录，不要合并汇总」',
            'AI行动与工具结果': 'scripts/r4-evidence-suite.ps1 因 PowerShell 5.1 中文编码解析失败后删除，改 Python 重写 scripts/r4_evidence_suite.py；go build + 4 个隔离进程真实执行，生成 evidence/smoke/ 38 个单用例文件（38 PASS / 0 FAIL），原始输出 evidence/r4-suite-output.txt',
            '学生判断': '用户明确禁止伪造、要求单用例单文件', '产物版本': REV,
            '验证/交接': 'E4-002/E4-004/E4-009/E4-013；r4-suite-output.txt',
            'Skill': '无', '状态/证据': '38 条单用例冒烟全部 PASS，SCOPE_NOTE 标注边界',
            '缺失步骤与正确补正思路': '文件级独立记录不等于独立测试 Agent 会话成果，不冒充',
            '失分归属': 'A1,A3,A4,B3', '是否历史问题': '否，第四轮实测'}),
    step(**{'步骤': 'S-32', '任务号': '第四轮文档契约与 Skill 闭环', '前置': 'S-31',
            '应做动作': '逐接口补前置/后置/异常/边界入参；逐 Skill 补真实调用/失败/边界样例',
            '实际时间/会话/消息': R4,
            '提示及上下文': '用户「完善skill-usage.md里每一个skill的【真实调用记录、失败样例、边界样例】」「补全docs/interface-list.md每个接口的前置条件、后置断言、异常case、边界入参示例」',
            'AI行动与工具结果': 'docs/interface-list.md 新增附录 A（API-01~23 逐接口契约 + A.1 证据索引，明确未标注已实测的边界样例尚未执行）；skill-usage.md 新增第 9 节（4 自编 Skill + 内置 student-project-audit 各三类样例，9.6 节声明文件级冒烟≠工具加载、独立验收复检未闭合）',
            '学生判断': '用户要求「不只是六类说明」，并禁止虚构', '产物版本': REV,
            '验证/交接': 'E4-009/E4-010/E4-013',
            'Skill': 'acceptance-check（口径）', '状态/证据': '契约与闭环文档齐备，真实失败样例（PowerShell 编码）如实登记',
            '缺失步骤与正确补正思路': '边界入参示例是契约样例，不等于全部已实测；独立验收会话复检仍缺',
            '失分归属': 'B2,B3', '是否历史问题': '否，第四轮产物'}),
    step(**{'步骤': 'S-33', '任务号': '第四轮异常手工记录与页面断言', '前置': 'S-32',
            '应做动作': '库存核查/调价/超时通知/退款/下单各一份异常手工记录；V01~V08 每页独立截图说明与访问断言',
            '实际时间/会话/消息': R4,
            '提示及上下文': '用户「给库存核查、调价、超时通知、退款、下单，分别增加异常场景的手工测试记录文档」「V01~V08每个页面增加独立的测试截图说明文档，每个页面单独写访问断言」',
            'AI行动与工具结果': 'evidence/manual/ 5 份 30 条真实记录（7/5/4/5/4 PASS，共 5 条 DIFF 如实登记、不弱化断言、不删失败用例、不改业务代码）；evidence/html-check/ 8 份 A1~A7 访问断言，明确本轮未生成浏览器截图文件、不冒充第 3 轮浏览器验收',
            '学生判断': '用户强调不改动稳定下单/退款核心业务代码', '产物版本': REV,
            '验证/交接': 'E4-003/E4-005/E4-013',
            'Skill': '无', '状态/证据': '30 条异常记录与 8 份页面断言齐备，DIFF 与未生成截图如实标注',
            '缺失步骤与正确补正思路': '截图文件与浏览器验收须由独立验收 Agent 会话补充',
            '失分归属': 'A1,A4', '是否历史问题': '否，第四轮实测'}),
    step(**{'步骤': 'S-34', '任务号': '第四轮提交规范对比与校验脚本', '前置': 'S-33',
            '应做动作': '补首次偏差提交与本次 opt 提交对比样例、可执行校验脚本',
            '实际时间/会话/消息': R4,
            '提示及上下文': '用户「完善git提交指引、commit convention，增加本次opt提交和首次偏差提交的对比样例、校验脚本」',
            'AI行动与工具结果': '新增 scripts/check_commit_message.py 并真实执行：6083edd06… PASS / 6cc6f134… FAIL，合计 PASS 1 / FAIL 1（evidence/commit-message-check-output.txt）；docs/commit-convention-校验说明.md 与 docs/git-提交指引.md 2.3 节补齐对比样例；commit-convention.md 原文一字未改',
            '学生判断': '用户授权；首次偏差按 P-08 不 amend', '产物版本': REV,
            '验证/交接': 'E4-011/E4-012/E4-016/E4-023',
            'Skill': '无', '状态/证据': '格式校验 PASS/FAIL 真实输出；不替代 meegle 编号核验',
            '缺失步骤与正确补正思路': 'meegle CLI 不可用，编号核验维持 unknown，不生成核验输出',
            '失分归属': 'B1,B4', '是否历史问题': '是，首次提交偏差不可补造'}),
    step(**{'步骤': 'S-35', '任务号': '第四轮覆盖率边界单测', '前置': 'S-34',
            '应做动作': '仅新增边界 case 单元测试，把 service 包覆盖率拉到 90% 以上',
            '实际时间/会话/消息': R4,
            '提示及上下文': '用户「补充边界case单元测试，把service包覆盖率拉到90%以上，整体覆盖率尽量抬高」「不改动已经稳定的下单、退款核心业务代码」',
            'AI行动与工具结果': '仅新增 server/service/r4_edge_test.go（r4ErrCreateRepo / r4InjectRepo 包装仓储注入事务内技术错误，WithTransaction 透传）；初次 89.8%→89.9%→补事务错误分支后 service 90.3%、整体 88.2%；gofmt/vet/test 全 exit=0',
            '学生判断': '用户明确不改生产代码、不新增业务状态机', '产物版本': REV,
            '验证/交接': 'E4-006/E4-007/E4-024',
            'Skill': 'unit-test-race（口径）', '状态/证据': 'service 88.9%→90.3%，整体 87.4%→88.2%，无生产代码改动',
            '缺失步骤与正确补正思路': 'go test -race 仍受 CGO/gcc 环境限制，不写成通过',
            '失分归属': 'A3', '是否历史问题': '否，第四轮实测'}),
    step(**{'步骤': 'S-36', '任务号': '第四轮独立模拟渠道服务实例', '前置': 'S-35',
            '应做动作': '补可控 HTTP 模拟支付渠道的独立服务实例与真实运行记录',
            '实际时间/会话/消息': R4,
            '提示及上下文': '用户第四轮要求遍历第三轮 partial 逐项补证；第二轮/第三轮报告登记「缺独立模拟渠道服务实例与运行记录」',
            'AI行动与工具结果': '新增 scripts/mock_channel_service.py（独立 Python 进程 :18085，只做 /notify/* 转发、不落库、不改订单状态）、scripts/r4_mock_channel_smoke.py；实测 MOCK-01~04（支付成功/超时状态不变/重复幂等/未知订单 M-30）4/4 PASS，evidence/mock-channel-run.txt 与 r4-mock-channel-output.txt',
            '学生判断': '用户要求题面外功能不得新增，模拟服务不得宣称为真实第三方', '产物版本': REV,
            '验证/交接': 'E4-008/E4-010/E4-023',
            'Skill': '无', '状态/证据': '独立进程真实启动与健康检查，4/4 PASS，订单状态后置核查仍待发货',
            '缺失步骤与正确补正思路': '真实第三方接入、真实 MySQL 唯一键冲突均不在授权范围，不冒充',
            '失分归属': 'A1,A2,A4', '是否历史问题': '否，第四轮真实运行'}),
    step(**{'步骤': 'S-37', '任务号': '第四轮证据清单与严格口径登记', '前置': 'S-36',
            '应做动作': '输出完整证据清单，逐项维持 race/MySQL/meegle/CI/会话/视频/events.jsonl 的 unknown/缺失',
            '实际时间/会话/消息': R4,
            '提示及上下文': '用户「race/CGO、真实MySQL、meegle、远端CI、独立测试会话、视频、早期会话events.json历史记录，维持unknown，不虚构、不补假证据」',
            'AI行动与工具结果': 'evidence/第四轮证据清单.md 7 节完整清单，第 6 节逐项登记不可补/待补证，第 7 节列出的完成声明边界禁止「门禁通过/已上线/三轮验证完成」；5 条 DIFF 与未生成截图如实登记',
            '学生判断': '用户明确禁止编造不存在的 CI、MySQL、race、视频、独立测试会话', '产物版本': REV,
            '验证/交接': 'E4-013/E4-014/E4-015/E4-017/E4-021',
            'Skill': 'acceptance-check（清单口径）', '状态/证据': '证据清单完成，环境/历史缺口未被补写成通过',
            '缺失步骤与正确补正思路': '历史过程证据不可事后补造；环境项须具备条件后重跑',
            '失分归属': 'A2,A3,A4,B1,B2,B4', '是否历史问题': '否，第四轮结论'}),
    step(**{'步骤': 'S-38', '任务号': '第四轮门禁复核', '前置': 'S-37',
            '应做动作': '按前三轮稳定 42 原子矩阵复核并输出 score.json 与报告',
            '实际时间/会话/消息': R4,
            '提示及上下文': '用户「优化完成后，输出完整证据清单，然后执行第四轮门禁复核，输出score.json和报告，统计pass数量提升情况」',
            'AI行动与工具结果': '真实加载 student-project-audit 并调用 score_audit.py；第四轮 audit-input.json 9 项 partial→pass；evidence/r4_verify.py 真实复跑 git/gofmt/vet/build/test/两种覆盖率/race 探针/环境/清点/提交格式校验/计分；score.json 输出 7.27/10 不合格，原始 7.27，成果 6.12 + 过程 1.15',
            '学生判断': '用户指定冲击 7.9 门禁合格线，但不得虚构证据', '产物版本': REV,
            '验证/交接': 'E4-001/E4-024；本目录 audit-input.json / score.json / 两份 CSV / 检查报告.md',
            'Skill': 'student-project-audit', '状态/证据': '第四轮复核完成，仍不合格；门禁未通过',
            '缺失步骤与正确补正思路': '19 项必做非 pass 触发门禁，原始分 7.27 < 7.90，封顶差额 0',
            '失分归属': '全部', '是否历史问题': '否，第四轮结论'}),
    step(**{'步骤': 'S-39', '任务号': 'pass 提升统计', '前置': 'S-38',
            '应做动作': '统计本轮相对第三轮的 pass 数量提升与分数变化',
            '实际时间/会话/消息': R4,
            '提示及上下文': '用户「统计pass数量提升情况」',
            'AI行动与工具结果': '读取两份 score.json：第三轮 14/20/6/2 → 第四轮 23/11/6/2，pass +9、partial -9、fail/unknown 不变；最终分 6.08→7.27（+1.19）；blockers 28→19；9 个提升项均列明证据，未通过改分或舍入跨线',
            '学生判断': '用户要求冲击 7.9，但结论须以脚本真实输出为准', '产物版本': REV,
            '验证/交接': 'E4-024 的 CMD-11；score.json',
            'Skill': 'student-project-audit', '状态/证据': 'pass 14→23（+9），仍未达 7.9/8 合格线',
            '缺失步骤与正确补正思路': '剩余 19 项多为环境/不可补历史证据，不能靠产物补齐跨线',
            '失分归属': '全部', '是否历史问题': '否，统计结果'}),
    step(**{'步骤': 'S-40', '任务号': '第四轮不可补项复核', '前置': 'S-39',
            '应做动作': '复核本轮未把任何环境/历史缺口补写成通过或合规',
            '实际时间/会话/消息': R4,
            '提示及上下文': '用户「不伪造、不虚构环境/过程证据」',
            'AI行动与工具结果': 'R-A3-03（race/CGO）与 R-B4-03（meegle）维持 unknown；真实 MySQL、远端 CI/PR/部署、独立测试/验收会话、视频/当日群提交、早期 events.jsonl 维持 partial/fail；第四轮工作区增量尚未提交，如实登记为未提交增量',
            '学生判断': '学生与教师须如实保留历史结论', '产物版本': REV,
            '验证/交接': 'E4-014/E4-015/E4-017/E4-018/E4-021/E4-024；报告第 6 节',
            'Skill': '无', '状态/证据': '未补造任何历史记录，未生成假 CI/MySQL/race/视频证据',
            '缺失步骤与正确补正思路': '后续项目从开始按阶段留存真实证据；本轮不得事后补写',
            '失分归属': 'A2,A3,A4,B1,B2,B4', '是否历史问题': '是，历史不可补造'}),
]

with (OUT / '过程与提示词明细.csv').open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=proc_fields)
    w.writeheader()
    for row in history + extra:
        w.writerow(row)

print('要求与评分明细.csv:', len(data['checks']), 'rows')
print('过程与提示词明细.csv:', len(history), 'history +', len(extra), 'round4 rows')
