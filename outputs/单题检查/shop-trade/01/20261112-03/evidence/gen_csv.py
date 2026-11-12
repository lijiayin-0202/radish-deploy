#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第三轮：由 audit-input.json + score.json 生成两份 UTF-8 BOM 明细 CSV。

保留第一、第二轮全部历史过程行，只追加第三批整改与第三轮复核步骤。
"""
import csv
import json
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
R2 = OUT.parent / '20261112-02'

data = json.loads((OUT / 'audit-input.json').read_text(encoding='utf-8-sig'))
score = json.loads((OUT / 'score.json').read_text(encoding='utf-8'))
norm = {row['id']: row for cat in score['categories'] for row in cat['checks']}

prior = {}
with (R2 / '要求与评分明细.csv').open('r', encoding='utf-8-sig', newline='') as f:
    for row in csv.DictReader(f):
        prior[row['要求编号']] = row


def dec4(text):
    return f'{float(Fraction(text)):.4f}'


def remedy(item):
    status = item['status']
    if status == 'pass':
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

with (R2 / '过程与提示词明细.csv').open('r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    proc_fields = list(reader.fieldnames)
    history = list(reader)


def step(**kw):
    base = {k: '' for k in proc_fields}
    base.update(kw)
    return base


R3 = '2026-11-12 第三轮门禁复核（同一复核会话，非独立测试/验收会话）'
REV = 'HEAD 6083edd06…（dev/01 第 2 次提交，[opt] [v1.1.0]）'
extra = [
    step(**{'步骤': 'S-23', '任务号': '整改-验收Skill', '前置': 'S-22 第二轮待补证清单',
            '应做动作': '新增验收检查 Skill 并补齐 skill-usage.md 六类说明',
            '实际时间/会话/消息': '2026-11-12 开发会话（第三批整改）',
            '提示及上下文': '用户「新增【验收检查Skill】，放到skills目录，在skill-usage.md补充这个Skill的6类说明」',
            'AI行动与工具结果': '新增 .codebuddy/skills/acceptance-check/SKILL.md；skill-usage.md 第 3.1 节补齐①用途②触发③输入④输出⑤验收检查点⑥禁用场景，第 5/6/7 节登记调用与缺口；第三轮复核读取确认',
            '学生判断': '用户明确授权（C-08）', '产物版本': REV,
            '验证/交接': 'E3-008/E3-009/E3-020；未由验收 Agent 独立会话真实触发',
            'Skill': 'acceptance-check', '状态/证据': '代码产物补齐，独立会话复检仍缺',
            '缺失步骤与正确补正思路': 'Skill 文件不等于验收会话成果；须验收 Agent 独立会话执行并导出',
            '失分归属': 'B3,B1', '是否历史问题': '否，产物已补齐'}),
    step(**{'步骤': 'S-24', '任务号': '整改-业务分支', '前置': 'S-23',
            '应做动作': '补商品调价入口、渠道超时通知分支、库存恢复逐单核查，不改动主业务',
            '实际时间/会话/消息': '2026-11-12 开发会话（第三批整改）',
            '提示及上下文': '用户「补齐业务分支：商品调价入口接口、渠道超时通知分支逻辑、缓存恢复逐单核查逻辑」',
            'AI行动与工具结果': '新增 server/service/extension.go、api/v1/extension.go、router/extension.go；API-21/22/23 注册；interface-list.md 增量 v1.1；第三轮实测调价 M-12、越权 M-20、超时通知状态不变与幂等、逐单核查 consistent=true',
            '学生判断': '用户明确要求不改已跑通的下单/退款主业务', '产物版本': REV,
            '验证/交接': 'E3-010/E3-011/E3-013/E3-019',
            'Skill': '无', '状态/证据': '三个接口实测可访问，原 API-01~20 未回归',
            '缺失步骤与正确补正思路': '真实 MySQL 下唯一键冲突与持久化复核属环境证据',
            '失分归属': 'A1,A2,A4', '是否历史问题': '否，第三批实测结果'}),
    step(**{'步骤': 'S-25', '任务号': '整改-静态页面', '前置': 'S-24',
            '应做动作': '补 V-01~V-08 简易 HTML 页面与静态资源路由',
            '实际时间/会话/消息': '2026-11-12 开发会话（第三批整改）',
            '提示及上下文': '用户「补齐前端简易HTML页面（V-01~V-08要求，GVA静态页面，放resource/static）」',
            'AI行动与工具结果': 'resource/static 新增 index.html + v01~v08 共 9 个 HTML 与 app.css/app.js；initialize/router.go 增加 engine.Static 与 GET /；第三轮逐个 HTTP 200',
            '学生判断': '用户确认不要复杂 Vue', '产物版本': REV,
            '验证/交接': 'E3-012/E3-013/E3-019',
            'Skill': '无', '状态/证据': 'html_count=9，静态路由正常',
            '缺失步骤与正确补正思路': '第 3 轮浏览器页面验收须由独立验收会话执行，不能由 HTTP 200 替代',
            '失分归属': 'A4', '是否历史问题': '否，产物已补齐'}),
    step(**{'步骤': 'S-26', '任务号': '整改-CI与声明边界', '前置': 'S-25',
            '应做动作': '新增 CI 注释模板、更新 git 提交指引、区分代码产物与环境/过程证据',
            '实际时间/会话/消息': '2026-11-12 开发会话（第三批整改）',
            '提示及上下文': '用户「新增CI模板文件只放模板注释，写明依赖环境（CGO、MySQL、meegle），不伪造可运行CI」「文档区分【代码产物补齐】」',
            'AI行动与工具结果': '.github/workflows/ci.yml 纯注释非注释行 0；docs/git-提交指引.md 新增 2.2 修正记录；新增 docs/代码产物补齐说明.md；docs/完成声明边界.md 新增 3.1 边界',
            '学生判断': '用户明确禁止伪造 CI/部署/门禁通过', '产物版本': REV,
            '验证/交接': 'E3-014/E3-015/E3-016/E3-024',
            'Skill': '无', '状态/证据': '模板与文档齐备，未触发流水线',
            '缺失步骤与正确补正思路': '远端 CI 运行、PR 状态检查、部署与回滚须平台权限',
            '失分归属': 'A4,B4', '是否历史问题': '否，模板为产物不是运行证据'}),
    step(**{'步骤': 'S-27', '任务号': '第二次合规提交', '前置': 'S-26',
            '应做动作': '修正首次 commit 格式偏差并建立 2 次提交版本链',
            '实际时间/会话/消息': '2026-11-12 开发会话（第三批整改）',
            '提示及上下文': '用户「修正首次commit格式偏差，在docs/git-提交指引.md更新说明，标记本次整改commit符合规范」',
            'AI行动与工具结果': '首次提交 6cc6f134… 不 amend、不改写；新增提交 6083edd06… message 为 [opt] [v1.1.0] 补齐验收检查Skill与商品调价等交付产物；第三轮核查 rev-list --count HEAD=2、分支 dev/01、工作区仅复核产物未跟踪',
            '学生判断': '用户授权修正方式；meegle 不可用不伪造编号', '产物版本': REV,
            '验证/交接': 'E3-002/E3-015/E3-020',
            'Skill': '无', '状态/证据': 'HEAD 有效，本次提交格式合规；首次偏差按 P-08 保留',
            '缺失步骤与正确补正思路': 'feat/fix 的 meegle 编号核验与 PR 门禁仍须远端与权限',
            '失分归属': 'B1,B4', '是否历史问题': '是，首次提交偏差与分阶段提交历史不可补造'}),
    step(**{'步骤': 'S-28', '任务号': '第三轮复核', '前置': 'S-27',
            '应做动作': '按稳定矩阵复核原有基线与全部新增产物并计分',
            '实际时间/会话/消息': R3,
            '提示及上下文': '用户「第三轮门禁复核，读取本次全部补齐产物」6 项要求',
            'AI行动与工具结果': '锁定前两轮 42 原子项与 score_audit.py；独立复跑 gofmt/vet/build/test、覆盖率 87.4%/88.9%、race 探针、环境核查；round3-verify.ps1 在 go run main.go 实例跑五组场景 40 步，在编译实例跑 12 个静态资源 + API-21/22/23 全 PASS；score_audit.py 输出 6.08/10',
            '学生判断': '用户指定环境/过程证据不得判为代码缺陷', '产物版本': REV,
            '验证/交接': 'E3-001~E3-025；本目录全部产物',
            'Skill': 'student-project-audit', '状态/证据': '复核完成，代码产物项全部补齐，仍不合格',
            '缺失步骤与正确补正思路': '独立测试/验收会话、CI/部署/视频仍缺；不冒充门禁通过',
            '失分归属': '全部', '是否历史问题': '否，第三轮结论'}),
    step(**{'步骤': 'S-29', '任务号': '环境/过程证据归类', '前置': 'S-28',
            '应做动作': '把 race/CGO、MySQL、meegle、远端 CI、独立会话、视频、Apipost 导出归为环境/过程证据缺失',
            '实际时间/会话/消息': R3,
            '提示及上下文': '用户「严格沿用约束口径…归类为【环境/过程证据缺失】，不判定为代码缺陷」',
            'AI行动与工具结果': 'CGO_ENABLED=0、gcc/clang=NOT_FOUND、GVA_MYSQL_DSN=NOT_SET、meegle=NOT_FOUND、remote 为空、video=0、apipost-run-export=False；R-A3-03 与 R-B4-03 记 unknown，其余相关原子项 reason 统一标注【环境/过程证据缺失】',
            '学生判断': '用户明确授权归类口径', '产物版本': REV,
            '验证/交接': 'E3-007/E3-014/E3-020/E3-022/E3-024',
            'Skill': 'acceptance-check（检查清单口径）', '状态/证据': '环境缺失项单列阻塞归属，不判代码缺陷',
            '缺失步骤与正确补正思路': '具备条件环境重跑并保存原始输出；不得据此宣称门禁通过',
            '失分归属': 'A2,A3,A4,B4', '是否历史问题': '否，待补证'}),
    step(**{'步骤': 'S-30', '任务号': '不可补过程证据登记', '前置': 'S-29',
            '应做动作': '单独标注历史不可补的过程证据项，不伪造',
            '实际时间/会话/消息': R3,
            '提示及上下文': '用户「仅环境权限、历史过程证据无法补齐，不伪造证据」「单独标注不可补的过程证据项」',
            'AI行动与工具结果': '登记 7 类不可补项：三方会话导出与开发前加载记录、events.jsonl 真实时间戳、分阶段真实提交序列、首次提交格式偏差、独立测试/验收交接与复检链、GitHub MCP 建仓请求结果时间、当日群提交与讲解时间点；报告第 6 节单列',
            '学生判断': '学生与教师须如实保留历史结论', '产物版本': REV,
            '验证/交接': 'E3-020/E3-021/E3-023；报告第 6 节',
            'Skill': '无', '状态/证据': '不可补项已单列，未补造任何历史记录',
            '缺失步骤与正确补正思路': '历史事实不改写；后续项目从开始即按阶段留存真实证据',
            '失分归属': 'A3,A4,B1,B2,B4', '是否历史问题': '是，历史不可补造'}),
]

with (OUT / '过程与提示词明细.csv').open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=proc_fields)
    w.writeheader()
    for row in history + extra:
        w.writerow(row)

print('要求与评分明细.csv:', len(data['checks']), 'rows')
print('过程与提示词明细.csv:', len(history), 'history +', len(extra), 'round3 rows')
