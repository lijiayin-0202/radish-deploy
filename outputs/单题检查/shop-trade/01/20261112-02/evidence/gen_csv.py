#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第二轮：由 audit-input.json + score.json 生成两份 UTF-8 BOM 明细 CSV。

历史过程行完整保留第一轮结论，只追加第二轮整改/复核步骤，不改写历史。
"""
import csv
import json
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
R1 = OUT.parent / '20261112-01'

data = json.loads((OUT / 'audit-input.json').read_text(encoding='utf-8-sig'))
score = json.loads((OUT / 'score.json').read_text(encoding='utf-8'))
norm = {row['id']: row for cat in score['categories'] for row in cat['checks']}

prior = {}
with (R1 / '要求与评分明细.csv').open('r', encoding='utf-8-sig', newline='') as f:
    for row in csv.DictReader(f):
        prior[row['要求编号']] = row


def dec4(text):
    v = Fraction(text)
    return f'{float(v):.4f}'


def remedy(item):
    status = item['status']
    if status == 'pass':
        return ('无需整改，保持回归', '每轮复跑对应命令并绑定提交哈希')
    if status == 'unknown':
        return ('环境补证（非代码缺陷）：在具备 CGO/gcc、真实 MySQL、meegle/远端权限的环境重跑并保存原始输出',
                '核对原始输出、退出码、覆盖率/race 原件与最终提交哈希对应关系')
    if status == 'fail':
        return ('补齐缺失产物或独立会话证据（见报告第 6 节）',
                '在独立测试/验收会话逐项复查并保留原始输出')
    return ('补齐 reason 中列明的剩余范围（见报告第 6 节）',
            '重跑对应场景或命令并核对预期结果与持久化/版本对应')


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

with (R1 / '过程与提示词明细.csv').open('r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    proc_fields = list(reader.fieldnames)
    history = list(reader)


def step(**kw):
    base = {k: '' for k in proc_fields}
    base.update(kw)
    return base


R2 = '2026-11-12 第二轮门禁复核（同一复核会话，非独立测试/验收会话）'
REV = 'HEAD 6cc6f134…（dev/01 首次提交）'
extra = [
    step(**{'步骤': 'S-16', '任务号': '整改-缺陷1', '前置': 'S-15 第一轮检查报告',
            '应做动作': '补可运行入口、controller、路由，使五组场景有 HTTP 接口',
            '实际时间/会话/消息': '2026-11-12 开发会话（整改批次）',
            '提示及上下文': '用户「基于本次验收报告逐条修复」缺陷 1',
            'AI行动与工具结果': '新增 main.go、server/api/v1/order.go/views.go、server/router/order.go、server/initialize/router.go；第二轮实测 go run main.go 启动、/health=ok、五组场景 40 步全通过',
            '学生判断': '用户确认整改要求', '产物版本': REV,
            '验证/交接': 'E2-003/E2-004/E2-005；docs/完成声明边界.md 限定为开发草稿完成',
            'Skill': '无', '状态/证据': '整改完成，复验见 R-A1/A4 各项',
            '缺失步骤与正确补正思路': '缺 8 个 HTML 可操作页面与独立第 2 轮运行导出',
            '失分归属': 'A1,A4', '是否历史问题': '否，整改后复验结果'}),
    step(**{'步骤': 'S-17', '任务号': '整改-缺陷2', '前置': 'S-16',
            '应做动作': '补 CGO 开启后 race 命令、区分草稿与真实覆盖率',
            '实际时间/会话/消息': '2026-11-12 开发会话（整改批次）',
            '提示及上下文': '用户「补充 CGO 开启后执行 go test ./... -race 的命令」',
            'AI行动与工具结果': 'test-report.md 新增两类覆盖率定义与 $env:CGO_ENABLED=1 命令；测试文件加注释；第二轮复跑 race 仍为 -race requires cgo exit=2',
            '学生判断': '用户确认整改要求', '产物版本': REV,
            '验证/交接': 'E2-005/E2-009/E2-011；环境阻塞，不判代码缺陷',
            'Skill': 'unit-test-race', '状态/证据': '命令就绪，正式 race 证据待补证',
            '缺失步骤与正确补正思路': '需 CGO_ENABLED=1 + gcc/clang 环境重跑并保存 race-output-raw.txt',
            '失分归属': 'A3', '是否历史问题': '否，环境缺失项'}),
    step(**{'步骤': 'S-18', '任务号': '整改-缺陷3', '前置': 'S-17',
            '应做动作': '建立 dev/01 有效 HEAD，补 skill-usage 六类说明与 evidence 文档',
            '实际时间/会话/消息': '2026-11-12 开发会话（整改批次）',
            '提示及上下文': '用户指定提交说明 feat: 电商订单售前退款完整业务实现',
            'AI行动与工具结果': 'git commit 6cc6f134…，82 文件；skill-usage.md 六类说明齐备；evidence/ 12 份文档与原始输出；docs/git-提交指引.md 如实登记格式/编号核验偏差',
            '学生判断': '用户明确指定 message', '产物版本': REV,
            '验证/交接': 'E2-002/E2-006/E2-008/E2-014',
            'Skill': '无', '状态/证据': '有效 HEAD 已建立，提交格式未合规',
            '缺失步骤与正确补正思路': 'meegle 核验与 PR 需远端/权限；说明文档不替代会话导出与事件清单本体',
            '失分归属': 'B1,B2,B3,B4', '是否历史问题': '是，分阶段提交历史不可补造'}),
    step(**{'步骤': 'S-19', '任务号': '整改-AI行为', '前置': 'S-18',
            '应做动作': '接口清单定稿，Apipost 用例基于定稿重建，区分完成声明',
            '实际时间/会话/消息': '2026-11-12 开发会话（整改批次）',
            '提示及上下文': '用户「接口清单定稿，所有 Apipost 用例基于定稿接口清单重新生成」',
            'AI行动与工具结果': 'docs/interface-list.md v1.0 定稿 API-01~20；scripts/regen_apipost.py 重建 5 场景 48 用例；docs/完成声明边界.md 限定两类声明',
            '学生判断': '用户确认整改要求', '产物版本': REV,
            '验证/交接': 'E2-007/E2-010；apipost-collection.json 解析通过，状态仍为未运行',
            'Skill': 'apipost-case-gen', '状态/证据': '用例已重建，未运行',
            '缺失步骤与正确补正思路': '第 1 轮门禁通过后在独立测试会话运行 Apipost 并导出结果',
            '失分归属': 'A3,A4', '是否历史问题': '否'}),
    step(**{'步骤': 'S-20', '任务号': '第二轮复核', '前置': 'S-19',
            '应做动作': '复核启动/健康/五组场景、文档、Git 版本链并按稳定矩阵计分',
            '实际时间/会话/消息': R2,
            '提示及上下文': '用户「对 shop-trade dev/01 分支做第二轮门禁复核」',
            'AI行动与工具结果': '独立复跑 go run main.go + /health + /api/v1/me + 五组场景；复跑 gofmt/vet/build/test/两种覆盖率/race；git log/rev-parse/remote 核查；42 原子项重新判定；score_audit.py 输出 5.38/10',
            '学生判断': '用户指定 race 失败归类为环境限制', '产物版本': REV,
            '验证/交接': 'E2-002~E2-023；本目录全部产物',
            'Skill': 'student-project-audit', '状态/证据': '复核完成，仍不合格',
            '缺失步骤与正确补正思路': '独立测试/验收会话、PR/CI/部署/视频仍缺',
            '失分归属': '全部', '是否历史问题': '否，第二轮结论'}),
    step(**{'步骤': 'S-21', '任务号': '环境阻塞登记', '前置': 'S-20',
            '应做动作': '识别 CGO/gcc、真实 MySQL、meegle、CI 权限缺失并归类',
            '实际时间/会话/消息': R2,
            '提示及上下文': '用户第 4 项要求：不把环境限制判为代码缺陷',
            'AI行动与工具结果': 'CGO_ENABLED=0、gcc=NOT_FOUND、GVA_MYSQL_DSN_set=False、meegle=NOT_FOUND、workflows=False、Dockerfile=False；R-A3-03 与 R-B4-03 记 unknown',
            '学生判断': '用户明确授权归类', '产物版本': REV,
            '验证/交接': 'E2-012/E2-011/E2-020',
            'Skill': '无', '状态/证据': '环境缺失项，单列阻塞归属',
            '缺失步骤与正确补正思路': '具备条件环境重跑并保存原始输出；不修改代码',
            '失分归属': 'A2,A3,A4,B4', '是否历史问题': '否，待补证'}),
    step(**{'步骤': 'S-22', '任务号': '待补证清单', '前置': 'S-21',
            '应做动作': '列出仍缺的必交成果与复验条件',
            '实际时间/会话/消息': R2,
            '提示及上下文': 'rubric 第 41 行、report-template 第 6 节',
            'AI行动与工具结果': 'html_count=0、jsonl_count=0、video_count=0；无会话导出、无验收报告本体、无 apipost-run-export.json、无 PR/CI/部署记录',
            '学生判断': '须由学生与教师补交', '产物版本': REV,
            '验证/交接': 'E2-012/E2-021；报告第 6 节',
            'Skill': '无', '状态/证据': '成果/过程证据缺失，非环境权限阻塞',
            '缺失步骤与正确补正思路': '按报告第 6 节优先级补齐；历史过程不得事后补造',
            '失分归属': 'A3,A4,B1,B2,B4', '是否历史问题': '部分是，历史不可补造'}),
]

with (OUT / '过程与提示词明细.csv').open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=proc_fields)
    w.writeheader()
    for row in history + extra:
        w.writerow(row)

print('要求与评分明细.csv:', len(data['checks']), 'rows')
print('过程与提示词明细.csv:', len(history), 'history +', len(extra), 'round2 rows')
