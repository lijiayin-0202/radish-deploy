#!/usr/bin/env python3
"""基于 docs/interface-list.md v1.0（定稿）重新生成 Apipost 用例集合。

只重建身份头、触发说明、集合元信息与运行前置，保留 5 组场景 / 48 个用例的断言内容。
生成结果仍为「未运行」草案，不产生任何伪造的运行结果。
"""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
INTERFACE_LIST = BASE / 'docs' / 'interface-list.md'
COLLECTION = BASE / 'apipost-collection.json'
DRAFT = BASE / 'docs' / 'interface-list-draft.md'

list_text = INTERFACE_LIST.read_text(encoding='utf-8')
assert '已定稿' in list_text, '缺少定稿接口清单，禁止重新生成 Apipost 用例'
assert 'API-20' in list_text and 'X-Demo-Account' in list_text, '定稿清单字段不完整'

data = json.loads(COLLECTION.read_text(encoding='utf-8'))

TRIGGER_NOTE = ('可控 HTTP 模拟渠道通知入口即定稿清单 API-04 / API-10 / API-14；'
                '通过 signature_valid、success、amount、channel_trade_no 触发'
                '成功/失败/验签失败/金额不符/未知订单/重复通知，无独立真实第三方服务')


def account_for(case):
    api = str(case.get('api', ''))
    cid = str(case.get('case_id', ''))
    if '+' in api:
        return 'buyer01'
    if '/' in api:
        api = api.split('/')[0]
    if api == '无':
        return 'ops01'
    if api.startswith('API-04') or api.startswith('API-10') or api.startswith('API-14'):
        return 'mock01'
    if api.startswith('API-05') or api.startswith('API-16') or api.startswith('API-20'):
        return 'ops01'
    if api.startswith('API-11'):
        return 'warehouse01'
    if any(api.startswith(x) for x in ('API-07', 'API-08', 'API-09', 'API-12', 'API-13', 'API-15')):
        return 'cs01'
    if cid.startswith('S4'):
        return 'buyer03'
    if cid.startswith('S2-08'):
        return 'buyer02'
    return 'buyer01'


for scenario in data['scenarios']:
    for case in scenario['cases']:
        account = account_for(case)
        case['headers'] = {'X-Demo-Account': account}
        if str(case.get('method', '')).upper() == 'POST':
            case['headers']['Content-Type'] = 'application/json'
        if 'trigger' in case:
            case['trigger'] = TRIGGER_NOTE
        if '+' in str(case.get('api', '')):
            case['concurrent_accounts'] = ['buyer01', 'warehouse01']

data['collection_name'] = 'shop-trade 题目01 第2轮 Apipost 用例（基于接口清单 v1.0 定稿重新生成）'
data['source_interface_list'] = 'docs/interface-list.md v1.0（定稿）；docs/interface-list-draft.md 仅保留为历史版本，不再作为用例依据'
data['regenerated_at'] = '2026-11-12'
data['format_note'] = ('用例草案结构，不是 Apipost 官方导出格式；接口路径、方法、请求/响应字段与身份头'
                       '已与定稿清单及 server/router/order.go 一致；导入前须按实际 Apipost 导出格式转换')
data['status'] = '未运行；不得作为第 2 轮接口自动化证据'
data['base_url'] = '{{base_url}}'
data.pop('mock_channel_base_url', None)
data['mock_channel_note'] = TRIGGER_NOTE
data['variables']['base_url'] = 'http://127.0.0.1:8080'
for key in ('buyer01_account', 'buyer02_account', 'buyer03_account', 'ops_account',
            'warehouse_account', 'cs_account', 'mock_channel_account', 'mock_channel_base_url'):
    data['variables'].pop(key, None)
data['variables'].update({
    'buyer01_account': 'buyer01',
    'buyer02_account': 'buyer02',
    'buyer03_account': 'buyer03',
    'ops_account': 'ops01',
    'warehouse_account': 'warehouse01',
    'cs_account': 'cs01',
    'mock_channel_account': 'mock01',
})
data['role_headers_note'] = ('身份只由 X-Demo-Account 解析为服务端预置账号（user_id + role）；'
                             'X-Role / X-User-Id 一律忽略，改请求中的用户编号不能越权')
data['run_prerequisites'] = [
    '服务可启动：go run main.go（demo-memory）或配置 GVA_MYSQL_DSN 走 MySQL(InnoDB)',
    '第 1 轮单元测试、覆盖率 ≥85%、go test -race（CGO_ENABLED=1）全部通过后才可执行本用例集',
    '接口清单 docs/interface-list.md v1.0 已定稿，api/v1 与 router 已实现',
    '真实 MySQL(InnoDB) 测试库、演示数据基线与服务端时间推进规则就绪',
    'Apipost 环境变量与身份头确认，密钥/口令一律脱敏',
    '本集合未运行，不得冒充第 2 轮运行导出结果',
]

COLLECTION.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'regenerated {COLLECTION} scenarios={len(data["scenarios"])} '
      f'cases={sum(len(s["cases"]) for s in data["scenarios"])}')

DOC_UPDATES = {
    'apipost-case-list.md': [
        ('# Apipost 用例清单（第 2 轮草案，未运行）',
         '# Apipost 用例清单（基于接口清单 v1.0 定稿重新生成，第 2 轮未运行）'),
        ('> 来源：`docs/interface-list-draft.md`（`API-01~API-16` 为新增假设，待学生确认）。\n'
         '> 集合文件：`apipost-collection.json`。本清单不是运行导出结果，不得作为第 2 轮证据。',
         '> 来源：`docs/interface-list.md` v1.0（定稿），与 `main.go`、`server/router/order.go`、`server/api/v1/order.go` 一致；'
         '`docs/interface-list-draft.md` 仅保留为历史版本，不再作为用例依据。\n'
         '> 身份头统一为 `X-Demo-Account`（服务端预置账号映射），`X-Role` / `X-User-Id` 一律忽略。\n'
         '> 集合文件：`apipost-collection.json`（由 `scripts/regen_apipost.py` 基于定稿重建）。'
         '本清单不是运行导出结果，不得作为第 2 轮证据。'),
        ('`{{mock_channel_base_url}}/trigger` 需支持 8 类可控通知：正常支付成功、重复支付通知、迟到支付成功、退款成功、退款失败、验签失败、金额不符、未知订单。全部为可控 HTTP 模拟服务，不得宣称为真实第三方接入成果。',
         '可控 HTTP 模拟渠道通知入口即定稿清单 `API-04` / `API-10` / `API-14`，通过 `signature_valid`、`success`、`amount`、`channel_trade_no` 触发 8 类通知：'
         '正常支付成功、重复支付通知、迟到支付成功、退款成功、退款失败、验签失败、金额不符、未知订单。'
         '不再引用未定稿的 `/trigger` 变量；不得宣称为真实第三方接入成果。'),
        ('2. 接口清单经学生确认，并定稿 `api/v1` 与路由实现。',
         '2. 接口清单已定稿为 `docs/interface-list.md` v1.0，`api/v1` 与路由已实现；正式运行前仍需学生复核。'),
    ],
    'apipost-assertion-matrix.md': [
        ('# Apipost 断言矩阵（第 2 轮草案，未运行）',
         '# Apipost 断言矩阵（基于接口清单 v1.0 定稿重新生成，第 2 轮未运行）'),
        ('> 不得写死成功、不得返回空结果。失败原因一律引用 `M-01~M-30` 中文文案。',
         '> 不得写死成功、不得返回空结果。失败原因一律引用 `M-01~M-30` 中文文案。\n'
         '> 来源：`docs/interface-list.md` v1.0（定稿）；身份头为 `X-Demo-Account`。'),
    ],
    'apipost-run-summary.md': [
        ('# Apipost 第 2 轮运行摘要（草案状态说明，非运行结果）',
         '# Apipost 第 2 轮运行摘要（基于接口清单 v1.0 定稿重建，非运行结果）'),
        ('| 对应提交版本 | 未提交；当前为 `dev/01` 工作区草案 |',
         '| 对应提交版本 | 整改批次本地首次提交，见 `docs/git-提交指引.md`；本批用例仍未运行 |'),
        ('2. 接口清单 `docs/interface-list-draft.md` 是「按 service 推导」的新增假设，路径、方法、请求/响应字段、鉴权头尚未经学生确认，`api/v1` 与路由实现未定稿。',
         '2. 接口清单已定稿为 `docs/interface-list.md` v1.0，`api/v1` 与路由已实现，Apipost 集合已基于定稿重建；但集合本身仍未在 Apipost 中运行。'),
        ('3. 真实 MySQL(InnoDB) 测试库、可控 HTTP 模拟支付渠道服务实例与演示数据基线尚未就绪。',
         '3. 可控模拟通知入口已由 `API-04` / `API-10` / `API-14` 实现；真实 MySQL(InnoDB) 测试库与演示数据基线尚未就绪，正式第 2 轮仍须在持久化模式执行。'),
        ('| `apipost-collection.json` | 用例集合草案（非 Apipost 官方导出格式，导入前需转换并经学生确认） |',
         '| `apipost-collection.json` | 基于定稿接口清单重建的用例集合（非 Apipost 官方导出格式，导入前需按实际导出格式转换） |'),
        ('2. 学生确认接口清单后，把草案集合转换为实际 Apipost 导出格式，配置环境变量与前置/后置脚本，接入模拟渠道 `/trigger`。',
         '2. 复核定稿接口清单后，把集合转换为实际 Apipost 导出格式，配置环境变量与前置/后置脚本，接入 `API-04` / `API-10` / `API-14` 模拟通知入口。'),
    ],
}

for name, pairs in DOC_UPDATES.items():
    path = BASE / name
    text = path.read_text(encoding='utf-8')
    for old, new in pairs:
        if old in text:
            text = text.replace(old, new)
        elif new not in text:
            raise SystemExit(f'{name}: 未找到待替换文本 {old[:50]!r}')
    path.write_text(text, encoding='utf-8')
    print(f'updated {name}')

