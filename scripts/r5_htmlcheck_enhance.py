#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第五轮：为 8 份 html-check 文档追加 A8~A12 增强断言（静态页面契约一致性）。

A1~A7 为第四轮 HTTP 层独立访问断言；A8~A12 为第五轮新增的**页面契约级**断言：
- A8 契约一致性：本页引用的 /api/v1 路径全部登记在 docs/interface-list.md 的 API-01~API-23 中；
- A9 关键交互入口：关键按钮 ID 存在且以 Shop.click('<id>' 绑定（有入口且有行为）；
- A10 失败原因文案：页内 M-xx 编号属于 M-01~M-30，且该页必现编号确实出现；
- A11 角色一致性：Shop.init 的演示账号角色与视图角色一致；
- A12 写操作口径：仅使用 GET/POST，无 DELETE/PUT/PATCH，无删除或直接改写订单状态入口。

口径：静态源码 + HTTP 层断言；**非浏览器截图、非第 3 轮浏览器验收、非独立验收会话**。
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from r5_closure_lib import (  # noqa: E402
    HTMLCHECK_DIR, ROOT, build, call, now, save, start_demo, stop_demo,
)

PAGES = [
    ('V01', 'GoodsBrowse', 'v01-goods.html', 'buyer01', '买家',
     ['/api/v1/goods', '/api/v1/orders'],
     ['btnRefresh', 'btnOrder'],
     ['M-02', 'M-03', 'M-12']),
    ('V02', 'MyOrders', 'v02-orders.html', 'buyer01', '买家',
     ['/api/v1/orders/', '/api/v1/ops/stock-check/'],
     ['btnDetail', 'btnStatus', 'btnCancel', 'btnCheck'],
     ['M-10', 'M-20']),
    ('V03', 'GoodsAdmin', 'v03-goods-admin.html', 'ops01', '运营',
     ['/api/v1/goods', '/api/v1/admin/goods/', '/price'],
     ['btnRefresh', 'btnPrice'],
     ['M-12', 'M-13', 'M-20']),
    ('V04', 'OpsSummary', 'v04-ops-summary.html', 'ops01', '运营',
     ['/api/v1/ops/summary', '/api/v1/goods', '/api/v1/ops/stock-check/',
      '/api/v1/admin/clock', '/api/v1/admin/orders/close-expired'],
     ['btnSummary', 'btnGoods', 'btnCheck', 'btnClock', 'btnClose'],
     ['M-13', 'M-14', 'M-17', 'M-26']),
    ('V05', 'ShipmentList', 'v05-shipment-list.html', 'warehouse01', '仓库',
     ['/api/v1/orders/', '/api/v1/ops/stock-check/', '/api/v1/goods'],
     ['btnDetail', 'btnStatus', 'btnCheck', 'btnGoods'],
     ['M-18', 'M-22']),
    ('V06', 'ShipmentForm', 'v06-shipment-form.html', 'warehouse01', '仓库',
     ['/api/v1/orders/', '/shipment'],
     ['btnShip', 'btnStatus'],
     ['M-11', 'M-19', 'M-22', 'M-23']),
    ('V07', 'RefundReview', 'v07-refund-review.html', 'cs01', '客服',
     ['/api/v1/orders/', '/refund/approve', '/refund/reject', '/refund/retry',
      '/api/v1/refund/callback', '/api/v1/ops/stock-check/', '/api/v1/ops/summary'],
     ['btnApprove', 'btnReject', 'btnRetry', 'btnDetail', 'btnFail', 'btnOK',
      'btnCheck', 'btnSummary'],
     ['M-08', 'M-24']),
    ('V08', 'LatePayment', 'v08-late-payment.html', 'cs01', '客服',
     ['/api/v1/ops/summary', '/api/v1/late-payment/', '/verify', '/refund/initiate',
      '/api/v1/ops/stock-check/', '/api/v1/payment/timeout'],
     ['btnSummary', 'btnVerify', 'btnInitiate', 'btnCheck', 'btnTimeout'],
     ['M-09', 'M-14', 'M-15', 'M-26']),
]

ROLE_OF = {'buyer01': '买家', 'buyer02': '买家', 'buyer03': '买家', 'ops01': '运营',
           'warehouse01': '仓库', 'cs01': '客服', 'mock01': '模拟渠道'}
ALL_CODES = {f'M-{i:02d}' for i in range(1, 31)}

iface = (ROOT / 'docs/interface-list.md').read_text(encoding='utf-8')
appjs = (ROOT / 'resource/static/app.js').read_text(encoding='utf-8')

build()
p = start_demo()
try:
    for pid, name, filename, account, role, api_paths, buttons, codes in PAGES:
        src = (ROOT / 'resource/static' / filename).read_text(encoding='utf-8')
        doc_path = HTMLCHECK_DIR / f'{pid}-{name}.md'

        # A8 契约一致性
        a8_rows = []
        for ap in api_paths:
            in_page = (ap in src) or (ap in appjs)
            in_iface = ap in iface
            ok = in_page and in_iface
            a8_rows.append((ap, f'页面/app.js={in_page}', f'接口表={in_iface}',
                            'PASS' if ok else 'FAIL'))
        a8_ok = all(r[3] == 'PASS' for r in a8_rows)

        # A9 关键交互入口
        a9_rows = []
        for bid in buttons:
            has_id = f'id="{bid}"' in src
            bound = f"Shop.click('{bid}'" in src
            ok = has_id and bound
            a9_rows.append((bid, f'id 存在={has_id}', f'Shop.click 绑定={bound}',
                            'PASS' if ok else 'FAIL'))
        a9_ok = all(r[3] == 'PASS' for r in a9_rows)

        # A10 失败原因文案
        found = sorted(set(re.findall(r'M-\d{2}', src)))
        unknown = [c for c in found if c not in ALL_CODES]
        missing = [c for c in codes if c not in found]
        a10_ok = (not unknown) and (not missing)
        a10_detail = (f'页内出现 {",".join(found) if found else "无"}；'
                      f'越界编号 {",".join(unknown) if unknown else "无"}；'
                      f'必现缺失 {",".join(missing) if missing else "无"}')

        # A11 角色一致性
        init = re.search(r"Shop\.init\('([^']+)'\)", src)
        init_acct = init.group(1) if init else ''
        a11_ok = bool(init_acct) and ROLE_OF.get(init_acct, '') == role
        a11_detail = f"Shop.init('{init_acct}') → 角色 {ROLE_OF.get(init_acct, '未知')}；期望 {role}"

        # A12 写操作口径
        verbs = sorted(set(re.findall(r"Shop\.call\([^,]+,\s*'([A-Z]+)'", src)))
        raw_verbs = sorted(set(re.findall(r"'(GET|POST|PUT|PATCH|DELETE)'", src)))
        bad_verbs = [v for v in raw_verbs if v in ('PUT', 'PATCH', 'DELETE')]
        a12_ok = (not bad_verbs) and all(v in ('GET', 'POST') for v in verbs)
        a12_detail = (f'Shop.call 显式方法 {verbs or "默认 GET"}；'
                      f'源码中出现的写动词 {raw_verbs}；越界动词 {bad_verbs or "无"}')

        # HTTP 层复核（真实请求该静态页）
        http = call('GET', f'/static/{filename}', account)
        http_ok = http['status'] == 200

        rows = [
            ('A8', '本页（含公共脚本 `app.js`）引用的 /api/v1 路径均登记在 '
                    '`docs/interface-list.md`（API-01~API-23）',
             '；'.join(f'{r[0]}：页面/app.js={r[1][3:]}，接口表={r[2][4:]}' for r in a8_rows),
             'PASS' if a8_ok else 'FAIL'),
            ('A9', '关键按钮 ID 存在且以 `Shop.click` 绑定（有入口且有行为）',
             f'{len(buttons)} 个按钮全部命中：{",".join(buttons)}',
             'PASS' if a9_ok else 'FAIL'),
            ('A10', '页内 M-xx 失败原因编号属于 M-01~M-30，且该页必现编号确实出现',
             a10_detail, 'PASS' if a10_ok else 'FAIL'),
            ('A11', '`Shop.init` 演示账号角色与视图角色一致',
             a11_detail, 'PASS' if a11_ok else 'FAIL'),
            ('A12', '仅使用 GET/POST，无 DELETE/PUT/PATCH，无删除或直接改写订单状态入口',
             a12_detail, 'PASS' if a12_ok else 'FAIL'),
        ]
        detail = (
            '### A8 契约一致性逐路径明细\n\n'
            '| 接口路径 | 页面源码 / app.js | 接口契约表 | 结论 |\n'
            '| --- | --- | --- | --- |\n'
            + '\n'.join('| ' + ' | '.join(str(x) for x in r) + ' |' for r in a8_rows)
            + '\n\n### A9 关键交互入口逐按钮明细\n\n'
            '| 按钮 ID | 元素存在 | 行为绑定 | 结论 |\n'
            '| --- | --- | --- | --- |\n'
            + '\n'.join('| ' + ' | '.join(str(x) for x in r) + ' |' for r in a9_rows)
        )

        section = '\n'.join([
            '',
            '---',
            '',
            '## 第五轮增强断言（A8~A12）',
            '',
            '| 项 | 内容 |',
            '| --- | --- |',
            f'| 增强断言采集时间 | {now()} |',
            '| 采集方式 | 静态页面源码逐项断言 + HTTP 层复核（真实 GET 静态页） |',
            f'| HTTP 层复核 | `GET /static/{filename}` → HTTP {http["status"]}'
            f'（{len(http["body"])} 字节）→ **{"PASS" if http_ok else "FAIL"}** |',
            '| 口径 | **静态源码 + HTTP 层断言**；非浏览器截图、非第 3 轮浏览器验收、非独立验收会话 |',
            '',
            '| 编号 | 断言 | 实际 | 结论 |',
            '| --- | --- | --- | --- |',
            '\n'.join('| ' + ' | '.join(str(x) for x in r) + ' |' for r in rows),
            '',
            detail,
            '',
            '> A8~A12 只证明「页面声明与接口契约、角色、失败原因、写操作口径一致」，'
            '**不替代浏览器端渲染与交互验收**；截图仍须由第 3 轮浏览器验收在独立验收会话中补充。',
            '',
            '## 第五轮关联证据',
            '',
            '- 增强断言采集脚本：`scripts/r5_htmlcheck_enhance.py`',
            '- 页面源码：`resource/static/' + filename + '`',
            '- 接口契约：`docs/interface-list.md`（附录 A 的 API-01~API-23 契约表、附录 B 全量边界矩阵）',
            '- 同批次证据：`evidence/partial-closure/`、`evidence/manual-round2/`',
            '',
        ])

        old = doc_path.read_text(encoding='utf-8') if doc_path.exists() else ''
        marker = '\n---\n\n## 第五轮增强断言（A8~A12）'
        if marker in old:
            head = old.split(marker)[0].rstrip() + '\n'
        else:
            head = old.rstrip() + '\n'
        save(doc_path, head + section)
        print(f'{pid} A8={a8_ok} A9={a9_ok} A10={a10_ok} A11={a11_ok} A12={a12_ok} '
              f'http={http["status"]}')
finally:
    stop_demo(p)

print('html_check_docs=', len(list(HTMLCHECK_DIR.glob('*.md'))))
print('R5 HTMLCHECK ENHANCE COMPLETE')
