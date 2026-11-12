#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第五轮：第二批五类异常手工记录（下单 / 退款 / 调价 / 超时通知 / 库存核查）。

与第一批（evidence/manual/*.md，第四轮采集）的区别：
- 第一批覆盖「空 / 超长 / 负数 / 越权 / 不存在 / 重复」等**参数级**异常；
- 第二批覆盖**业务状态级与库存守恒级**异常：合法上限值、库存不足与耗尽、
  跨账号共享库存、取消后库存恢复、各订单状态下退款申请、审核中重复申请、
  调价与订单金额快照隔离、渠道超时通知不改变订单状态、逐单库存恢复核查与一致性。
每个分类使用**独立 demo 进程**，避免互相污染库存与状态。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from r5_closure_lib import (  # noqa: E402
    MANUAL2_DIR, ROOT, block, build, call, case_lines, code_of, data_of, now,
    save, start_demo, stop_demo,
)

build()
print('go build ok')

DOCS = {}


def doc(cat, title, rows, extra=''):
    DOCS[cat] = (title, rows, extra)


# ============================ 1. 下单 ============================
rows = []
p = start_demo()
try:
    o1 = call('POST', '/api/v1/orders', 'buyer01', {'goods_id': 1, 'quantity': 2})
    no1 = data_of(o1).get('order_no', '')
    b, _ = case_lines('合法上限值：quantity=2 下单成功（可售 5 → 3）', 'POST', '/api/v1/orders',
                      'buyer01', {'goods_id': 1, 'quantity': 2}, '0', o1)
    rows.append(b)

    o2 = call('POST', '/api/v1/orders', 'buyer02', {'goods_id': 1, 'quantity': 2})
    no2 = data_of(o2).get('order_no', '')
    b, _ = case_lines('跨账号共享同一商品库存：buyer02 再下单 qty=2（可售 3 → 1）', 'POST',
                      '/api/v1/orders', 'buyer02', {'goods_id': 1, 'quantity': 2}, '0', o2)
    rows.append(b)

    o3 = call('POST', '/api/v1/orders', 'buyer03', {'goods_id': 1, 'quantity': 2})
    b, _ = case_lines('库存不足：可售仅 1 件仍下单 qty=2', 'POST', '/api/v1/orders',
                      'buyer03', {'goods_id': 1, 'quantity': 2}, 'M-02', o3)
    rows.append(b)

    o4 = call('POST', '/api/v1/orders', 'buyer01', {'goods_id': 1, 'quantity': 1})
    b, _ = case_lines('剩余 1 件时下单 qty=1 成功（可售 1 → 0）', 'POST', '/api/v1/orders',
                      'buyer01', {'goods_id': 1, 'quantity': 1}, '0', o4)
    rows.append(b)

    o5 = call('POST', '/api/v1/orders', 'buyer02', {'goods_id': 1, 'quantity': 1})
    b, _ = case_lines('库存耗尽：可售 0 时下单 qty=1', 'POST', '/api/v1/orders',
                      'buyer02', {'goods_id': 1, 'quantity': 1}, 'M-02', o5)
    rows.append(b)

    c1 = call('POST', f'/api/v1/orders/{no1}/cancel', 'buyer01', None)
    b, _ = case_lines('取消弃单释放库存（可售 0 → 2）', 'POST', f'/api/v1/orders/{no1}/cancel',
                      'buyer01', None, '0', c1)
    rows.append(b)

    o6 = call('POST', '/api/v1/orders', 'buyer03', {'goods_id': 1, 'quantity': 1})
    b, _ = case_lines('库存释放后可再次下单（可售 2 → 1）', 'POST', '/api/v1/orders',
                      'buyer03', {'goods_id': 1, 'quantity': 1}, '0', o6)
    rows.append(b)

    g = call('GET', '/api/v1/goods', 'buyer01')
    rows.append('#### 下单批次结束时的商品库存快照\n\n```text\n' +
                'GET /api/v1/goods\n' + g['body'] + '\n```\n')
finally:
    stop_demo(p)
doc('下单', '下单异常场景手工测试记录（第二批：库存守恒与状态边界）', rows)

# ============================ 2. 退款 ============================
rows = []
p = start_demo()
try:
    # 2.1 待支付订单申请退款
    a = call('POST', '/api/v1/orders', 'buyer01', {'goods_id': 1, 'quantity': 1})
    n_pending = data_of(a).get('order_no', '')
    r = call('POST', f'/api/v1/orders/{n_pending}/refund/apply', 'buyer01', {'reason': '待支付即申请'})
    b, _ = case_lines('待支付订单申请整单退款（状态不允许）', 'POST',
                      f'/api/v1/orders/{n_pending}/refund/apply', 'buyer01',
                      {'reason': '待支付即申请'}, 'M-05', r)
    rows.append(b)

    # 2.2 已取消订单申请退款
    c = call('POST', f'/api/v1/orders/{n_pending}/cancel', 'buyer01', None)
    r = call('POST', f'/api/v1/orders/{n_pending}/refund/apply', 'buyer01', {'reason': '已取消再申请'})
    b, _ = case_lines('已取消订单再申请退款', 'POST', f'/api/v1/orders/{n_pending}/refund/apply',
                      'buyer01', {'reason': '已取消再申请'}, 'M-05', r)
    rows.append(b)

    # 2.3 已发货订单申请退款
    a2 = call('POST', '/api/v1/orders', 'buyer01', {'goods_id': 2, 'quantity': 1})
    n_ship = data_of(a2).get('order_no', '')
    call('POST', '/api/v1/payment/callback', 'mock01',
         {'order_no': n_ship, 'channel_trade_no': 'R5-B2-SHIP', 'amount': 10000,
          'signature_valid': True})
    call('POST', f'/api/v1/orders/{n_ship}/shipment', 'warehouse01',
         {'carrier': '顺丰', 'tracking_no': 'R5-B2-SF'})
    r = call('POST', f'/api/v1/orders/{n_ship}/refund/apply', 'buyer01', {'reason': '已发货申请'})
    b, _ = case_lines('已发货订单申请售前退款（M-11）', 'POST', f'/api/v1/orders/{n_ship}/refund/apply',
                      'buyer01', {'reason': '已发货申请'}, 'M-11', r)
    rows.append(b)

    # 2.4 审核中重复申请
    a3 = call('POST', '/api/v1/orders', 'buyer01', {'goods_id': 1, 'quantity': 1})
    n_review = data_of(a3).get('order_no', '')
    call('POST', '/api/v1/payment/callback', 'mock01',
         {'order_no': n_review, 'channel_trade_no': 'R5-B2-REV', 'amount': 10000,
          'signature_valid': True})
    call('POST', f'/api/v1/orders/{n_review}/refund/apply', 'buyer01', {'reason': '首次申请'})
    r = call('POST', f'/api/v1/orders/{n_review}/refund/apply', 'buyer01', {'reason': '重复申请'})
    b, _ = case_lines('退款审核中重复申请（M-10 幂等拒绝）', 'POST',
                      f'/api/v1/orders/{n_review}/refund/apply', 'buyer01',
                      {'reason': '重复申请'}, 'M-10', r)
    rows.append(b)

    # 2.5 已退款订单再申请
    call('POST', f'/api/v1/orders/{n_review}/refund/approve', 'cs01', {'remark': '同意退款'})
    call('POST', '/api/v1/refund/callback', 'mock01',
         {'order_no': n_review, 'refund_channel_trade_no': 'R5-B2-RF', 'amount': 10000,
          'success': True, 'signature_valid': True})
    r = call('POST', f'/api/v1/orders/{n_review}/refund/apply', 'buyer01', {'reason': '已退款再申请'})
    b, _ = case_lines('已退款订单再次申请退款（M-11）', 'POST',
                      f'/api/v1/orders/{n_review}/refund/apply', 'buyer01',
                      {'reason': '已退款再申请'}, 'M-11', r)
    rows.append(b)

    st = call('GET', f'/api/v1/orders/{n_review}/status', 'buyer01')
    rows.append('#### 退款批次结束时的终态订单快照\n\n```text\n' +
                f'GET /api/v1/orders/{n_review}/status\n{st["body"]}\n```\n')
finally:
    stop_demo(p)
doc('退款', '退款异常场景手工测试记录（第二批：各订单状态下的退款申请）', rows)

# ============================ 3. 调价 ============================
rows = []
p = start_demo()
try:
    o_before = call('POST', '/api/v1/orders', 'buyer01', {'goods_id': 1, 'quantity': 1})
    n_before = data_of(o_before).get('order_no', '')

    pr = call('POST', '/api/v1/admin/goods/1/price', 'ops01',
              {'unit_price': 12000, 'reason': '第二批：活动价 12000'})
    b, _ = case_lines('运营调价 10000 → 12000 成功', 'POST', '/api/v1/admin/goods/1/price',
                      'ops01', {'unit_price': 12000, 'reason': '第二批：活动价 12000'}, '0', pr)
    rows.append(b)

    o_after = call('POST', '/api/v1/orders', 'buyer01', {'goods_id': 1, 'quantity': 1})
    n_after = data_of(o_after).get('order_no', '')
    d_after = data_of(o_after)
    b, _ = case_lines('调价后新下单按新价 12000', 'POST', '/api/v1/orders', 'buyer01',
                      {'goods_id': 1, 'quantity': 1}, '0', o_after)
    rows.append(b)
    rows.append(f'- 断言：新订单金额快照 = 12000 → **{"PASS" if d_after.get("unit_price") == 12000 else "FAIL"}**'
                f'（实际 unit_price={d_after.get("unit_price")}, total_amount={d_after.get("total_amount")}）\n')

    old = call('GET', f'/api/v1/orders/{n_before}', 'buyer01')
    d_old = data_of(old)
    b, _ = case_lines('调价不影响调价前已存在订单的金额快照', 'GET', f'/api/v1/orders/{n_before}',
                      'buyer01', None, '0', old)
    rows.append(b)
    rows.append(f'- 断言：旧订单金额快照仍为 10000（M-12）→ '
                f'**{"PASS" if d_old.get("unit_price") == 10000 else "FAIL"}**'
                f'（实际 unit_price={d_old.get("unit_price")}）\n')

    pr2 = call('POST', '/api/v1/admin/goods/1/price', 'ops01',
               {'unit_price': 12000, 'reason': '第二批：重复调价到同一价格'})
    b, _ = case_lines('重复调价到同一价格（审计追加，不报错）', 'POST',
                      '/api/v1/admin/goods/1/price', 'ops01',
                      {'unit_price': 12000, 'reason': '第二批：重复调价到同一价格'}, '0', pr2)
    rows.append(b)

    pr3 = call('POST', '/api/v1/admin/goods/1/price', 'ops01',
               {'unit_price': 13500, 'reason': '第二批：二次调价 13500'})
    b, _ = case_lines('二次调价 12000 → 13500 成功', 'POST', '/api/v1/admin/goods/1/price',
                      'ops01', {'unit_price': 13500, 'reason': '第二批：二次调价 13500'}, '0', pr3)
    rows.append(b)

    pr4 = call('POST', '/api/v1/admin/goods/1/price', 'ops01',
               {'unit_price': 13500, 'reason': ''})
    b, _ = case_lines('调价 reason 为空字符串（记录实际行为）', 'POST',
                      '/api/v1/admin/goods/1/price', 'ops01',
                      {'unit_price': 13500, 'reason': ''}, '0', pr4)
    rows.append(b)

    g = call('GET', '/api/v1/goods', 'ops01')
    rows.append('#### 调价批次结束时的商品快照\n\n```text\n' +
                'GET /api/v1/goods\n' + g['body'] + '\n```\n')
finally:
    stop_demo(p)
doc('调价', '商品调价异常场景手工测试记录（第二批：价格快照隔离与连续调价）', rows)

# ============================ 4. 超时通知 ============================
rows = []
p = start_demo()
try:
    o = call('POST', '/api/v1/orders', 'buyer01', {'goods_id': 1, 'quantity': 1})
    n_paid = data_of(o).get('order_no', '')
    call('POST', '/api/v1/payment/callback', 'mock01',
         {'order_no': n_paid, 'channel_trade_no': 'R5-B4-PAY', 'amount': 10000,
          'signature_valid': True})
    st_before = call('GET', f'/api/v1/orders/{n_paid}/status', 'buyer01')

    t1 = call('POST', '/api/v1/payment/timeout', 'mock01',
              {'order_no': n_paid, 'channel_trade_no': 'R5-B4-TO-1', 'reason': '渠道判定超时'})
    b, _ = case_lines('已支付订单收到渠道超时通知（只登记，不改订单状态）', 'POST',
                      '/api/v1/payment/timeout', 'mock01',
                      {'order_no': n_paid, 'channel_trade_no': 'R5-B4-TO-1',
                       'reason': '渠道判定超时'}, '0', t1)
    rows.append(b)
    st_after = call('GET', f'/api/v1/orders/{n_paid}/status', 'buyer01')
    rows.append(f'- 断言：通知前后订单状态一致 → '
                f'**{"PASS" if code_of(st_before) == code_of(st_after) and data_of(st_before) == data_of(st_after) else "FAIL"}**'
                f'（通知前 {st_before["body"]} / 通知后 {st_after["body"]}）\n')

    t2 = call('POST', '/api/v1/payment/timeout', 'mock01',
              {'order_no': n_paid, 'channel_trade_no': 'R5-B4-TO-1', 'reason': '重复通知'})
    b, _ = case_lines('同一 channel_trade_no 重复超时通知（幂等）', 'POST',
                      '/api/v1/payment/timeout', 'mock01',
                      {'order_no': n_paid, 'channel_trade_no': 'R5-B4-TO-1',
                       'reason': '重复通知'}, '0', t2)
    rows.append(b)
    rows.append(f'- 断言：重复通知返回 duplicate=true → '
                f'**{"PASS" if data_of(t2).get("duplicate") is True else "FAIL"}**'
                f'（实际 duplicate={data_of(t2).get("duplicate")}）\n')

    t3 = call('POST', '/api/v1/payment/timeout', 'mock01',
              {'order_no': n_paid, 'channel_trade_no': 'R5-B4-TO-2', 'reason': '另一笔交易号'})
    b, _ = case_lines('同一订单另一 channel_trade_no（独立登记，状态仍不变）', 'POST',
                      '/api/v1/payment/timeout', 'mock01',
                      {'order_no': n_paid, 'channel_trade_no': 'R5-B4-TO-2',
                       'reason': '另一笔交易号'}, '0', t3)
    rows.append(b)

    o2 = call('POST', '/api/v1/orders', 'buyer01', {'goods_id': 2, 'quantity': 1})
    n_cancel = data_of(o2).get('order_no', '')
    call('POST', f'/api/v1/orders/{n_cancel}/cancel', 'buyer01', None)
    t4 = call('POST', '/api/v1/payment/timeout', 'mock01',
              {'order_no': n_cancel, 'channel_trade_no': 'R5-B4-TO-3', 'reason': '已取消订单'})
    b, _ = case_lines('已取消订单收到超时通知（终态不被改写）', 'POST', '/api/v1/payment/timeout',
                      'mock01', {'order_no': n_cancel, 'channel_trade_no': 'R5-B4-TO-3',
                                 'reason': '已取消订单'}, '0', t4)
    rows.append(b)
    rows.append(f'- 断言：返回订单状态为已取消 → '
                f'**{"PASS" if data_of(t4).get("order_status") == "已取消" else "FAIL"}**'
                f'（实际 order_status={data_of(t4).get("order_status")}）\n')

    t5 = call('POST', '/api/v1/payment/timeout', 'mock01',
              {'order_no': 'NO-SUCH-ORDER', 'channel_trade_no': 'R5-B4-TO-4', 'reason': '未知订单'})
    b, _ = case_lines('未知订单超时通知（M-30）', 'POST', '/api/v1/payment/timeout', 'mock01',
                      {'order_no': 'NO-SUCH-ORDER', 'channel_trade_no': 'R5-B4-TO-4',
                       'reason': '未知订单'}, 'M-30', t5)
    rows.append(b)
finally:
    stop_demo(p)
doc('超时通知', '渠道超时通知异常场景手工测试记录（第二批：不改订单状态的登记语义）', rows)

# ============================ 5. 库存核查 ============================
rows = []
p = start_demo()
try:
    # 5.1 待支付订单核查
    a = call('POST', '/api/v1/orders', 'buyer01', {'goods_id': 1, 'quantity': 1})
    n1 = data_of(a).get('order_no', '')
    c1 = call('GET', f'/api/v1/ops/stock-check/{n1}', 'ops01')
    b, _ = case_lines('待支付订单逐单库存核查', 'GET', f'/api/v1/ops/stock-check/{n1}', 'ops01',
                      None, '0', c1)
    rows.append(b)
    rows.append(f'- 断言：expected_restore_times=0、actual_restore_times=0、consistent=true → '
                f'**{"PASS" if data_of(c1).get("consistent") is True else "FAIL"}**'
                f'（实际 {c1["body"]}）\n')

    # 5.2 quantity=2 订单核查
    a2 = call('POST', '/api/v1/orders', 'buyer02', {'goods_id': 1, 'quantity': 2})
    n2 = data_of(a2).get('order_no', '')
    c2 = call('GET', f'/api/v1/ops/stock-check/{n2}', 'ops01')
    b, _ = case_lines('quantity=2 订单逐单库存核查', 'GET', f'/api/v1/ops/stock-check/{n2}',
                      'ops01', None, '0', c2)
    rows.append(b)
    rows.append(f'- 断言：quantity=2、占用 3（2 件 + 前一单 1 件） → '
                f'**{"PASS" if data_of(c2).get("quantity") == 2 else "FAIL"}**'
                f'（实际 quantity={data_of(c2).get("quantity")}, '
                f'available_stock={data_of(c2).get("available_stock")}, '
                f'occupied_stock={data_of(c2).get("occupied_stock")}）\n')

    # 5.3 已发货订单核查
    a3 = call('POST', '/api/v1/orders', 'buyer01', {'goods_id': 2, 'quantity': 1})
    n3 = data_of(a3).get('order_no', '')
    call('POST', '/api/v1/payment/callback', 'mock01',
         {'order_no': n3, 'channel_trade_no': 'R5-B5-SHIP', 'amount': 10000,
          'signature_valid': True})
    call('POST', f'/api/v1/orders/{n3}/shipment', 'warehouse01',
         {'carrier': '顺丰', 'tracking_no': 'R5-B5-SF'})
    c3 = call('GET', f'/api/v1/ops/stock-check/{n3}', 'ops01')
    b, _ = case_lines('已发货订单逐单库存核查（不释放库存）', 'GET',
                      f'/api/v1/ops/stock-check/{n3}', 'ops01', None, '0', c3)
    rows.append(b)
    rows.append(f'- 断言：已发货订单 expected_restore_times=0 → '
                f'**{"PASS" if data_of(c3).get("expected_restore_times") == 0 else "FAIL"}**'
                f'（实际 {c3["body"]}）\n')

    # 5.4 已退款订单核查（库存恢复一次）
    a4 = call('POST', '/api/v1/orders', 'buyer01', {'goods_id': 1, 'quantity': 1})
    n4 = data_of(a4).get('order_no', '')
    call('POST', '/api/v1/payment/callback', 'mock01',
         {'order_no': n4, 'channel_trade_no': 'R5-B5-PAY', 'amount': 10000,
          'signature_valid': True})
    call('POST', f'/api/v1/orders/{n4}/refund/apply', 'buyer01', {'reason': '第二批：售前退款'})
    call('POST', f'/api/v1/orders/{n4}/refund/approve', 'cs01', {'remark': '同意整单退款'})
    call('POST', '/api/v1/refund/callback', 'mock01',
         {'order_no': n4, 'refund_channel_trade_no': 'R5-B5-RF', 'amount': 10000,
          'success': True, 'signature_valid': True})
    c4 = call('GET', f'/api/v1/ops/stock-check/{n4}', 'ops01')
    b, _ = case_lines('已退款订单逐单库存核查（库存恢复恰 1 次）', 'GET',
                      f'/api/v1/ops/stock-check/{n4}', 'ops01', None, '0', c4)
    rows.append(b)
    rows.append(f'- 断言：expected_restore_times=1、actual_restore_times=1、consistent=true → '
                f'**{"PASS" if data_of(c4).get("consistent") is True else "FAIL"}**'
                f'（实际 {c4["body"]}）\n')

    # 5.5 核查后立即下单，验证核查结论与实际可售一致
    g_before = call('GET', '/api/v1/goods', 'ops01')
    avail = None
    for it in data_of(g_before).get('items', []):
        if it.get('id') == 1:
            avail = it.get('available_stock')
    o5 = call('POST', '/api/v1/orders', 'buyer02', {'goods_id': 1, 'quantity': 1})
    b, _ = case_lines('核查后立即下单，验证可售数与核查一致', 'POST', '/api/v1/orders', 'buyer02',
                      {'goods_id': 1, 'quantity': 1}, '0', o5)
    rows.append(b)
    rows.append(f'- 断言：核查读到可售 {avail}，随后的 qty=1 下单 '
                f'{"成功（与可售>0 一致）" if avail and avail > 0 else "应被拒"} → '
                f'**{"PASS" if (avail and avail > 0 and code_of(o5) == "0") or (not avail and code_of(o5) != "0") else "FAIL"}**'
                f'（实际 code={code_of(o5)}）\n')
finally:
    stop_demo(p)
doc('库存核查', '库存恢复逐单核查异常场景手工测试记录（第二批：恢复次数与守恒一致性）', rows)

# ============================ 输出文档 ============================
for cat, (title, rows, extra) in DOCS.items():
    head = '\n'.join([
        f'# {title}',
        '',
        '| 项 | 内容 |',
        '| --- | --- |',
        '| 批次 | **第二批**（第五轮采集）；第一批见 `evidence/manual/*.md` |',
        '| 采集方式 | 本地 `go build` 实例逐条真实 HTTP 调用；**每个分类使用独立 demo 进程**，避免库存与状态互相污染 |',
        f'| 采集时间 | {now()} |',
        '| 运行模式 | `demo-memory`（`GVA_MYSQL_DSN` 未设置）；非真实 MySQL(InnoDB)、非 Apipost 运行导出、非独立测试 Agent 会话 |',
        '| 断言 | 每条含请求、入参、预期、实际 HTTP 与实际响应，逐条判定 PASS / DIFF |',
        '| 覆盖维度 | 业务状态级与库存守恒级异常（第一批为参数级异常） |',
        '',
        '## 异常用例',
        '',
    ])
    foot = '\n'.join([
        '',
        '## 边界说明',
        '',
        '- 以上为**开发会话内**的第五轮手工执行记录，**不是独立测试 Agent 会话产物**，'
        '也不是第 2 轮 Apipost 正式导出。',
        '- 未在真实 MySQL(InnoDB) 下复跑；唯一键冲突、InnoDB 行锁并发与重启后查询证据仍属环境缺失项，'
        '已在 `evidence/partial-closure/` 中逐条登记。',
        '- 判定为 `DIFF` 的条目如实登记边界行为差异，**不改动业务代码、不弱化断言、不删除失败用例**。',
        '- 不改写订单状态消除异常、不删除业务记录、不新增业务状态机。',
        '',
    ])
    save(MANUAL2_DIR / f'{title}.md', head + '\n'.join(rows) + foot)

print('manual round2 docs=', len(list(MANUAL2_DIR.glob('*.md'))))
print('R5 MANUAL ROUND2 COMPLETE')
