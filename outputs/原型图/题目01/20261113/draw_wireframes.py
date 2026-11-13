#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""题目 01「小型电商订单交易发货与售前退款」线框原型图生成器。

基于 d:/Desktop/shop 的业务语义（8 视图 / 4 类角色 / 8 状态机 / M-01~M-30 文案），
用 Pillow 绘制 8 张独立 PNG。风格：黑白 + 蓝灰点缀的产品线框稿，非真实 UI。
运行：python -X utf8 draw_wireframes.py
"""
from PIL import Image, ImageDraw, ImageFont
import pathlib

OUT = pathlib.Path(r'd:/Desktop/shop/outputs/原型图/题目01/20261113')
OUT.mkdir(parents=True, exist_ok=True)

W, H, S = 1440, 1000, 2
FONT = 'C:/Windows/Fonts/msyh.ttc'
BOLD = 'C:/Windows/Fonts/msyhbd.ttc'

WHITE = '#FFFFFF'
INK = '#2C3945'
MUTED = '#6B7887'
LINE = '#A8B3BF'
LINE_L = '#CDD5DD'
FILL = '#F5F7F9'
HEAD = '#EAEFF4'
BLUE = '#47698A'
BLUE_L = '#E3EAF1'

_fc = {}
CANVAS = None
D = None


def FN(sz, bold=False):
    key = (sz, bold)
    if key not in _fc:
        _fc[key] = ImageFont.truetype(BOLD if bold else FONT, sz * S)
    return _fc[key]


def TW(s, sz=13, bold=False):
    return FN(sz, bold).getlength(s) / S


def R(x, y, w, h, fill=None, outline=LINE, width=1, radius=0):
    box = [round(x * S), round(y * S), round((x + w) * S), round((y + h) * S)]
    kw = {}
    if fill is not None:
        kw['fill'] = fill
    if outline is not None:
        kw['outline'] = outline
        kw['width'] = max(1, round(width * S))
    if radius:
        D.rounded_rectangle(box, radius=round(radius * S), **kw)
    else:
        D.rectangle(box, **kw)


def T(x, y, s, sz=13, color=INK, bold=False, anchor='lt'):
    D.text((round(x * S), round(y * S)), str(s), font=FN(sz, bold),
           fill=color, anchor=anchor)


def L(x1, y1, x2, y2, color=LINE, width=1):
    D.line([round(x1 * S), round(y1 * S), round(x2 * S), round(y2 * S)],
           fill=color, width=max(1, round(width * S)))


def DASH_H(x1, x2, y, color=LINE, seg=8, gap=5):
    x = x1
    while x < x2:
        L(x, y, min(x + seg, x2), y, color)
        x += seg + gap


def DASH_V(x, y1, y2, color=LINE, seg=8, gap=5):
    y = y1
    while y < y2:
        L(x, y, x, min(y + seg, y2), color)
        y += seg + gap


def DASH_RECT(x, y, w, h, color=LINE):
    DASH_H(x, x + w, y, color)
    DASH_H(x, x + w, y + h, color)
    DASH_V(x, y, y + h, color)
    DASH_V(x + w, y, y + h, color)


def TAG(x, y, label, w=None, h=24, tone='blue', sz=12):
    if w is None:
        w = TW(label, sz, True) + 20
    fill = BLUE_L if tone == 'blue' else (FILL if tone == 'gray' else WHITE)
    fg = BLUE if tone == 'blue' else (MUTED if tone == 'gray' else INK)
    ol = BLUE if tone == 'blue' else LINE
    R(x, y, w, h, fill=fill, outline=ol, radius=3)
    T(x + w / 2, y + h / 2, label, sz, fg, True, 'mm')
    return w


def BTN(x, y, w, h, label, primary=False, disabled=False, sz=13):
    fill = BLUE if primary else WHITE
    fg = WHITE if primary else (MUTED if disabled else INK)
    ol = BLUE if primary else (LINE_L if disabled else LINE)
    R(x, y, w, h, fill=fill, outline=ol, radius=2)
    T(x + w / 2, y + h / 2, label, sz, fg, primary, 'mm')


def INPUT(x, y, w, h, ph, drop=False, value=False, sz=13):
    R(x, y, w, h, fill=WHITE, outline=LINE)
    T(x + 10, y + h / 2, ph, sz, INK if value else MUTED, False, 'lm')
    if drop:
        px, py = x + w - 18, y + h / 2
        D.polygon([(round((px - 5) * S), round((py - 3) * S)),
                   (round((px + 5) * S), round((py - 3) * S)),
                   (round(px * S), round((py + 4) * S))], fill=LINE)


def RADIO(x, y, label, checked=False, sz=13):
    D.ellipse([round(x * S), round(y * S), round((x + 14) * S), round((y + 14) * S)],
              outline=LINE, width=S)
    if checked:
        D.ellipse([round((x + 4) * S), round((y + 4) * S),
                   round((x + 10) * S), round((y + 10) * S)], fill=BLUE)
    T(x + 20, y + 7, label, sz, INK, False, 'lm')


def PANEL(x, y, w, h, title=None):
    R(x, y, w, h, fill=WHITE, outline=LINE)
    if title:
        R(x, y, w, 34, fill=HEAD, outline=LINE)
        T(x + 12, y + 17, title, 14, INK, True, 'lm')


def TABLE(x, y, cols, head, rows, rowh=38, headh=36, tags=None, sz=12):
    total = sum(cols)
    R(x, y, total, headh, fill=HEAD, outline=LINE)
    cx = x
    for i, c in enumerate(cols):
        if i:
            L(cx, y, cx, y + headh, LINE_L)
        T(cx + 10, y + headh / 2, head[i], 12, INK, True, 'lm')
        cx += c
    for r, row in enumerate(rows):
        ry = y + headh + r * rowh
        R(x, ry, total, rowh, fill=WHITE, outline=LINE_L)
        cx = x
        for i, c in enumerate(cols):
            if i:
                L(cx, ry, cx, ry + rowh, LINE_L)
            if tags and (r, i) in tags:
                lab, tone = tags[(r, i)]
                TAG(cx + 8, ry + (rowh - 22) / 2, lab, h=22, tone=tone, sz=11)
            else:
                T(cx + 10, ry + rowh / 2, row[i], sz, INK, False, 'lm')
            cx += c
    return y + headh + len(rows) * rowh


def NOTE(x, y, w, h, title, lines, sz=12):
    R(x, y, w, h, fill=FILL, outline=None)
    DASH_RECT(x, y, w, h, LINE)
    T(x + 14, y + 12, title, 13, BLUE, True, 'lm')
    for i, s in enumerate(lines):
        T(x + 14, y + 36 + i * 20, s, sz, MUTED, False, 'lm')


def FIELD(x, y, label, value, lw=110, vw=300, h=34, ro=True):
    T(x, y + h / 2, label, 13, MUTED, False, 'lm')
    INPUT(x + lw, y, vw, h, value, value=True)
    if ro:
        R(x + lw, y, vw, h, fill=None, outline=LINE_L)


def NAV(active, account, role, navs):
    R(0, 0, W, 62, fill=WHITE, outline=None)
    L(0, 62, W, 62, LINE)
    T(28, 31, 'shop-trade · 题目01 线框原型', 16, INK, True, 'lm')
    x = 340
    for item in navs:
        w = TW(item, 14) + 30
        is_act = (item == active)
        T(x + w / 2, 31, item, 14, BLUE if is_act else MUTED, is_act, 'mm')
        if is_act:
            L(x + 10, 53, x + w - 10, 53, BLUE, 2)
        x += w
    T(W - 28, 31, f'当前账号 {account}（{role}）', 13, MUTED, False, 'rm')


def HEADER(title, sub):
    T(40, 100, title, 26, INK, True, 'lm')
    T(40, 132, sub, 13, MUTED, False, 'lm')
    T(W - 40, 100, 'WIREFRAME / 线框稿', 12, MUTED, False, 'rm')
    L(40, 150, W - 40, 150, LINE_L)


def FOOTER(no, name, role, view, scene):
    L(40, 944, W - 40, 944, LINE_L)
    T(40, 968, f'图 {no:02d}/08 · {name}', 13, INK, True, 'lm')
    T(40, 988, '黑白 / 蓝灰线框原型 · 非真实 UI · 金额单位：分 · 服务端时间', 11, MUTED, False, 'lm')
    T(W - 40, 968, f'业务角色：{role} · 对应视图：{view} · 场景：{scene}', 12, MUTED, False, 'rm')
    T(W - 40, 988, 'shop-trade / 题目01 / dev-01', 11, MUTED, False, 'rm')


def NEW(no, name, active, navs, account, role, sub, view, scene):
    global CANVAS, D
    CANVAS = Image.new('RGB', (W * S, H * S), WHITE)
    D = ImageDraw.Draw(CANVAS)
    NAV(active, account, role, navs)
    HEADER(name, sub)
    FOOTER(no, name, role, view, scene)


def MASK():
    global CANVAS, D
    layer = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    ImageDraw.Draw(layer).rectangle(
        [0, round(62 * S), W * S, round(944 * S)], fill=(233, 237, 241, 170))
    CANVAS = Image.alpha_composite(CANVAS.convert('RGBA'), layer).convert('RGB')
    D = ImageDraw.Draw(CANVAS)


def SAVE(filename):
    CANVAS.resize((W, H), Image.LANCZOS).save(OUT / filename, 'PNG', optimize=True)
    print('written:', filename)


BUYER_NAV = ['商品列表', '我的订单', '订单详情', '帮助']
OPS_NAV = ['支付控制台', '通知记录', '帮助']
WH_NAV = ['待发货订单', '发货处理', '帮助']
CS_NAV = ['退款审核', '异常支付', '帮助']


# ---------------------------------------------------------------- 01 商品列表页
def p01():
    NEW(1, '商品列表页', '商品列表', BUYER_NAV, 'buyer01', '买家',
        'V-01 商品浏览 · 仅展示在售商品与本买家可操作入口 · 金额一律整数「分」', 'V-01', 'S1 / S2')
    PANEL(40, 170, 1360, 66, None)
    T(58, 203, '在售状态', 13, MUTED, False, 'lm')
    INPUT(140, 186, 130, 34, '在售', drop=True, value=True)
    T(292, 203, '商品名称 / 编号', 13, MUTED, False, 'lm')
    INPUT(410, 186, 230, 34, '输入关键字（占位）')
    BTN(654, 186, 82, 34, '查询', primary=True)
    BTN(746, 186, 82, 34, '重置')
    T(1400, 203, '仅买家可见，本页不展示任何他人订单数据', 12, MUTED, False, 'rm')

    TABLE(40, 252, [150, 230, 140, 130, 120, 150, 160],
          ['商品编号', '商品名称', '单价(分)', '可售数量', '已占用', '在售状态', '操作'],
          [['SP-001', '活动商品 A', '10000', '5', '0', '', '[立即下单]'],
           ['SP-002', '备用商品 B', '12000', '2', '0', '', '[不可购买]'],
           ['SP-003', '赠品（非售）', '0', '0', '0', '', '—']],
          rowh=44, headh=38,
          tags={(0, 5): ('在售', 'blue'), (1, 5): ('下架', 'gray'), (2, 5): ('未上架', 'gray')})

    PANEL(1140, 252, 260, 250, '下单规则（题面既定）')
    for i, s in enumerate(['① 一单仅一种商品', '② 数量只能 1 或 2 件', '③ 单价 10000 分，可售 5 件',
                           '④ 应付 = 单价 × 数量', '⑤ 无运费 / 无优惠', '⑥ 下单保存价格快照',
                           '⑦ 待支付保留 10 分钟']):
        T(1154, 306 + i * 27, s, 12, INK, False, 'lm')

    NOTE(40, 560, 660, 170, '操作结果区 C-02 · 失败原因（M-xx）',
         ['M-01  商品未上架，不能购买', 'M-02  可售数量不足，下单失败（20 并发抢 5 件不超卖）',
          'M-03  每单数量只能是 1 或 2 件', 'M-04  一单只能购买一种商品',
          'M-20  越权：不能查看或处理他人订单'])
    NOTE(720, 560, 680, 170, '业务标注 · 结构与边界',
         ['导航栏 / 筛选区 / 列表区 / 操作列 / 结果区 / 页脚 六段式结构',
          '上下架与调价属运营 V-03，买家页只显示「在售 / 未上架」',
          '调价或下架不改变已有订单金额（M-12 价格快照）',
          'S1 正常成交入口；S2 缺货与弃单（超时/取消释放后可再购）'])

    T(40, 772, '页面流程入口', 14, INK, True, 'lm')
    boxes = [('商品列表', 40), ('下单页', 360), ('支付页', 680), ('订单列表', 1000)]
    for i, (lab, x) in enumerate(boxes):
        R(x, 800, 260, 62, fill=WHITE, outline=BLUE if i == 0 else LINE)
        T(x + 130, 831, lab, 15, BLUE if i == 0 else INK, True, 'mm')
        if i < 3:
            L(x + 260, 831, x + 320, 831, BLUE, 2)
            D.polygon([(round((x + 320) * S), round(831 * S)),
                       (round((x + 310) * S), round(826 * S)),
                       (round((x + 310) * S), round(836 * S))], fill=BLUE)
    SAVE('01-商品列表页.png')


# ---------------------------------------------------------------- 02 下单页
def p02():
    NEW(2, '下单页', '商品列表', BUYER_NAV, 'buyer01', '买家',
        '确认商品与数量后提交 · 提交字段仅 goods_id + quantity · 不做购物车 / 收货地址', 'V-01（提交区）', 'S1 / S2')
    PANEL(40, 170, 600, 250, '商品信息（只读）')
    for i, (k, v) in enumerate([('商品编号', 'SP-001'), ('商品名称', '活动商品 A'),
                                ('单价', '10000 分'), ('在售状态', '在售'),
                                ('当前可售', '5 件'), ('已占用', '0 件')]):
        FIELD(58, 218 + i * 33, k, v, lw=100, vw=420, h=30)

    PANEL(40, 440, 600, 250, '下单表单')
    FIELD(58, 490, '商品编号', 'SP-001（只读）', lw=100, vw=420, h=34)
    T(58, 551, '购买数量', 13, MUTED, False, 'lm')
    INPUT(158, 534, 420, 34, '1  （下拉：1 / 2）', drop=True, value=True)
    FIELD(58, 582, '演示账号', 'buyer01（由 X-Demo-Account 解析，只读）', lw=100, vw=420, h=34)
    BTN(58, 634, 130, 36, '提交订单', primary=True)
    BTN(198, 634, 130, 36, '返回商品列表')

    PANEL(670, 170, 730, 210, '金额计算（整数分）')
    T(690, 232, '单价 10000 分  ×  数量 1  =  应付金额 10000 分', 17, INK, True, 'lm')
    for i, s in enumerate(['· 金额一律整数「分」，不使用浮点数', '· 不含运费、优惠、促销',
                           '· 下单时保存商品与单价快照，后续调价/下架不改本单金额（M-12）']):
        T(690, 276 + i * 27, s, 12, MUTED, False, 'lm')

    PANEL(670, 400, 730, 290, '提交结果（成功时展示）')
    for i, s in enumerate(['订单编号：ORD-20261113-0001', '订单状态：待支付',
                           '应付金额：10000 分', '库存动作：预扣 1 件（可售 4 / 占用 1）',
                           '过期时间：expires_at = 下单时间 + 10 分钟（服务端时间）',
                           '后续：发起付款 → 待发货；超时 → 已关闭（终态），占用释放']):
        T(690, 452 + i * 34, s, 13, INK, False, 'lm')

    NOTE(40, 720, 660, 190, '操作结果区 C-02 · 失败原因（M-xx）',
         ['M-01  商品未上架，不能购买', 'M-02  缺货，下单失败（并发抢单按可售判定）',
          'M-03  数量仅限 1~2 件', 'M-04  一单只能购买一种商品',
          'M-12  已有订单的下单时价格不受调价影响'])
    NOTE(720, 720, 680, 190, '业务标注 · 禁止扩大范围',
         ['不做购物车、多商品一单、部分退款、真实物流与收货地址',
          '身份只由 X-Demo-Account 解析；X-Role / X-User-Id 一律忽略',
          '下单与支付分离：本页只创建待支付订单，不记款',
          'S1 正常成交起点；S2 缺货时返回 M-02 且不预扣库存'])
    SAVE('02-下单页.png')


# ---------------------------------------------------------------- 03 支付页
def p03():
    NEW(3, '支付页', '支付控制台', OPS_NAV, 'mock01', '模拟支付渠道',
        'S-01 可控 HTTP 模拟支付渠道控制台 · 非真实第三方支付 · 通知需鉴权且幂等', 'V-08 / S-01 控制台', 'S1 / S4 / S5')
    PANEL(40, 170, 560, 230, '订单摘要（只读）')
    for i, (k, v) in enumerate([('订单编号', 'ORD-20261113-0001'), ('应付金额', '10000 分'),
                                ('订单状态', '待支付'), ('待支付剩余', '09:42（服务端时间）'),
                                ('库存占用', '1 件（超时关闭后释放）')]):
        FIELD(58, 216 + i * 36, k, v, lw=110, vw=390, h=30)

    PANEL(40, 420, 560, 290, '模拟通知参数')
    FIELD(58, 466, '订单编号', 'ORD-20261113-0001', lw=110, vw=390, h=32)
    FIELD(58, 508, '渠道交易号', 'CH-20261113-0001', lw=110, vw=390, h=32)
    FIELD(58, 550, '通知金额', '10000 分', lw=110, vw=390, h=32)
    T(58, 601, '验签结果', 13, MUTED, False, 'lm')
    INPUT(168, 584, 280, 32, '通过（signature_valid）', drop=True, value=True)
    T(58, 643, '通知类型', 13, MUTED, False, 'lm')
    INPUT(168, 626, 280, 32, '支付成功', drop=True, value=True)
    T(58, 678, '身份：mock01（模拟渠道）· 通知需鉴权', 12, MUTED, False, 'lm')

    PANEL(630, 170, 770, 230, '模拟通知入口（8 类）')
    labels = ['正常支付成功', '重复支付通知', '迟到支付成功', '退款成功',
              '退款失败', '验签失败', '金额不符', '未知订单']
    for i, lab in enumerate(labels):
        x = 650 + (i % 4) * 185
        y = 222 + (i // 4) * 78
        BTN(x, y, 170, 56, lab, primary=(i == 0))
    T(650, 378, '成功后：待支付 → 待发货，记款一次；渠道交易号唯一，不得归属两单',
      12, MUTED, False, 'lm')

    PANEL(630, 420, 770, 290, '操作结果区 C-02 · 通知处理结果')
    for i, s in enumerate(['M-25  重复支付通知已幂等处理，未重复记款',
                           'M-27  同一渠道交易号已归属其他订单，关联被拒',
                           'M-28  支付通知验签失败，订单状态不变',
                           'M-29  支付通知金额与订单不符，订单状态不变',
                           'M-30  支付通知指向未知订单，订单状态不变',
                           'M-09  迟到支付：订单已关闭，不恢复订单 / 不重新占用库存，',
                           '         仅生成异常支付待处理记录并返回 event_id']):
        T(650, 468 + i * 33, s, 12, INK, False, 'lm')

    NOTE(40, 730, 1360, 180, '业务标注 · 迟到支付与幂等（S4 / S5）',
         ['① 本页是可控 HTTP 模拟服务，不得宣称为真实第三方支付接入成果。',
          '② 支付成功通知到来时若订单已过 10 分钟关闭，状态保持「已关闭（终态）」，只转异常支付待处理（M-09 / M-15）。',
          '③ 重复通知不产生第二笔收款；退款通知重复也不产生第二笔退款（M-10 / M-25）。',
          '④ 迟到支付后续链路：客服异常列表核实并写明原因 → 发起退款 → 运营确认无重复释放、无重复退款（M-17 / M-26）。'])
    SAVE('03-支付页.png')


# ---------------------------------------------------------------- 04 订单列表页
def p04():
    NEW(4, '订单列表页', '我的订单', BUYER_NAV, 'buyer01', '买家',
        '按状态筛选 · 8 个订单状态与 4 个终态 · C-03 状态标签统一口径', 'V-02', 'S1 / S2 / S3 / S4')
    PANEL(40, 170, 1360, 62, None)
    T(58, 201, '订单状态', 13, MUTED, False, 'lm')
    INPUT(140, 184, 220, 34, '全部 / 8 个状态', drop=True, value=True)
    T(382, 201, '订单编号', 13, MUTED, False, 'lm')
    INPUT(464, 184, 250, 34, '按订单号逐单查看（占位）')
    BTN(728, 184, 82, 34, '查询', primary=True)
    BTN(820, 184, 82, 34, '重置')
    T(1400, 201, '实现版不提供订单全表列表接口；本图按原型设计文档 2.2 绘制', 12, MUTED, False, 'rm')

    rows = [
        ['ORD-0001', '活动商品 A', '10000', '1', '10000', '', '11-13 09:00', '09:42', '[查看详情]'],
        ['ORD-0002', '活动商品 A', '10000', '2', '20000', '', '11-13 09:02', '—', '[申请退款]'],
        ['ORD-0003', '活动商品 A', '10000', '1', '10000', '', '11-13 09:05', '—', '[查看详情]'],
        ['ORD-0004', '活动商品 A', '10000', '1', '10000', '', '11-13 09:07', '—', '[查看退款结果]'],
        ['ORD-0005', '活动商品 A', '10000', '1', '10000', '', '11-13 09:09', '—', '[查看详情]'],
        ['ORD-0006', '活动商品 A', '10000', '1', '10000', '', '11-13 09:11', '—', '[查看详情]'],
        ['ORD-0007', '活动商品 A', '10000', '1', '10000', '', '11-13 09:13', '—', '[查看详情]'],
        ['ORD-0008', '活动商品 A', '10000', '1', '10000', '', '11-13 09:15', '—', '[查看运单]'],
    ]
    states = ['待支付', '待发货', '退款审核中', '退款处理中',
              '已关闭（终态）', '已取消（终态）', '已退款（终态）', '已发货（终态）']
    tags = {(r, 5): (states[r], 'blue' if r < 4 else 'gray') for r in range(8)}
    TABLE(40, 248, [140, 150, 105, 70, 125, 175, 145, 100, 350],
          ['订单编号', '商品名称', '单价(分)', '数量', '应付金额(分)', '订单状态', '下单时间', '剩余时间', '操作'],
          rows, rowh=44, headh=38, tags=tags)

    PANEL(40, 664, 1360, 96, '订单状态标签图例 C-03（8 状态 / 4 终态）')
    for i, s in enumerate(states):
        x = 58 + (i % 4) * 335
        y = 706 + (i // 4) * 30
        TAG(x, y, s, w=150, h=24, tone='blue' if i < 4 else 'gray', sz=11)
    T(1400, 681, '终态以灰底标签显示', 12, MUTED, False, 'rm')

    NOTE(40, 780, 660, 140, '操作结果区 C-02 · 失败原因（M-xx）',
         ['M-20  越权：不能查看或处理他人订单', 'M-06  订单已超时关闭（满 10 分钟），占用已释放',
          'M-10  重复取消被拒，不产生第二笔业务结果'])
    NOTE(720, 780, 680, 140, '业务标注 · 状态机与显隐',
         ['允许流转：创建→待支付→待发货→已发货 / 退款审核中→退款处理中→已退款',
          '终态不可再跳转；待发货及之后不可取消 / 关闭（F-01~F-10）',
          '按钮按 3.1 显隐矩阵随状态变化：付款/取消仅待支付，申请退款仅待发货'])
    SAVE('04-订单列表页.png')


# ---------------------------------------------------------------- 05 订单详情页
def p05():
    NEW(5, '订单详情页', '订单详情', BUYER_NAV, 'buyer01', '买家',
        '按订单号查看 · 状态标签 + 四类子区 + 按状态显隐的操作按钮', 'V-02（详情区）', 'S1 / S3 / S4')
    PANEL(40, 170, 1360, 66, None)
    T(58, 203, '订单编号  ORD-20261113-0002', 15, INK, True, 'lm')
    TAG(360, 190, '待发货', w=100, h=26)
    T(480, 203, '状态说明：已付款、未发货；可申请整单售前退款', 13, MUTED, False, 'lm')
    T(1400, 203, 'C-03 状态标签：8 状态之一，终态标注「终态」', 12, MUTED, False, 'rm')

    PANEL(40, 252, 660, 300, '订单基本信息（只读）')
    left = [('订单编号', 'ORD-0002'), ('买家', 'buyer01（1001）'), ('商品名称', '活动商品 A'),
            ('下单时单价', '10000 分'), ('数量', '2 件'), ('应付金额', '20000 分'),
            ('下单时间', '2026-11-13 09:02'), ('支付时间', '2026-11-13 09:04'),
            ('渠道交易号', 'CH-20261113-0002'), ('待支付剩余', '—（已支付）')]
    for i, (k, v) in enumerate(left):
        y = 298 + i * 25
        T(58, y, k, 12, MUTED, False, 'lm')
        T(210, y, v, 12, INK, False, 'lm')
        if i < len(left) - 1:
            L(58, y + 13, 682, y + 13, LINE_L)

    PANEL(720, 252, 680, 300, '四类子区（随状态出现）')
    subs = [('收款信息', '支付结果 / 渠道交易号 / 收款时间', 40, 296),
            ('退款信息', '退款状态 / 渠道退款结果（失败 M-08）', 350, 296),
            ('发货信息', '承运方 / 运单号 / 发货时间', 40, 410),
            ('异常支付信息', '通知到达 / 关闭时间 / 处理结果', 350, 410)]
    for name, desc, dx, dy in subs:
        R(720 + dx, dy, 300, 100, fill=WHITE, outline=LINE_L)
        T(720 + dx + 12, dy + 26, name, 13, BLUE, True, 'lm')
        T(720 + dx + 12, dy + 60, desc, 11, MUTED, False, 'lm')

    PANEL(40, 570, 1360, 170, '操作按钮区 · 按 3.1 显隐矩阵（8 状态 × 11 按钮）')
    btns = [('发起付款', '仅待支付'), ('取消订单', '仅待支付'), ('申请整单退款', '仅待发货'),
            ('查看退款结果', '退款处理中 / 已退款'), ('查看运单', '已发货')]
    for i, (lab, cond) in enumerate(btns):
        x = 58 + i * 268
        BTN(x, 620, 200, 42, lab, primary=(i == 2))
        T(x + 100, 682, cond, 11, MUTED, False, 'mm')
    T(58, 716, '其余按钮随状态隐藏或只读；V-04 运营核查页全状态只读；越权点击已发货订单申请退款返回 M-11',
      12, MUTED, False, 'lm')

    NOTE(40, 760, 660, 160, '操作结果区 C-02 · 失败原因（M-xx）',
         ['M-06  已超时关闭（服务端时间满 10 分钟），占用已释放',
          'M-10  重复取消 / 重复操作被拒，不产生第二笔业务结果',
          'M-11  已发货订单不受理本题售前退款',
          'M-20  越权：不能查看或处理他人订单'])
    NOTE(720, 760, 680, 160, '业务标注 · 各状态展示要点',
         ['待支付：应付金额、剩余时间、库存已占用｜待发货：支付结果与收款时间',
          '退款审核中：发货已暂停（M-07）｜退款处理中：渠道失败显示 M-08 供客服重试',
          '已取消/已关闭：占用已释放；迟到支付显示 M-09｜已退款：退款金额与恢复数量',
          '已发货：承运方、运单号、发货时间（终态）'])
    SAVE('05-订单详情页.png')


# ---------------------------------------------------------------- 06 退款弹窗
def p06():
    NEW(6, '退款弹窗', '订单详情', BUYER_NAV, 'buyer01', '买家',
        'V-02 订单详情上弹出的申请整单退款弹窗 · 与发货互斥 · 不做部分退款', 'V-02（弹窗）/ V-07', 'S3 / S5')
    # 背景页（简化）
    PANEL(40, 170, 1360, 700, None)
    T(58, 210, '订单详情（背景页）', 18, INK, True, 'lm')
    TAG(240, 196, '待发货', w=100, h=26)
    T(58, 260, '订单编号  ORD-0002    |    应付金额  20000 分    |    数量  2 件', 14, MUTED, False, 'lm')
    BTN(58, 300, 160, 42, '申请整单退款', primary=True)
    BTN(230, 300, 160, 42, '查看运单')
    R(58, 370, 1320, 460, fill=None, outline=LINE_L)
    T(74, 400, '订单基本信息 / 收款信息 / 发货信息 / 异常支付信息（背景内容，弹窗打开时不可操作）',
      13, MUTED, False, 'lm')

    MASK()

    # 弹窗
    mx, my, mw, mh = 380, 230, 680, 540
    R(mx + 6, my + 8, mw, mh, fill='#D7DEE5', outline=None)
    R(mx, my, mw, mh, fill=WHITE, outline=BLUE, width=2)
    R(mx, my, mw, 48, fill=HEAD, outline=BLUE)
    T(mx + 20, my + 24, '申请整单退款', 18, INK, True, 'lm')
    T(mx + mw - 24, my + 24, '×', 20, MUTED, True, 'mm')
    L(mx, my + 48, mx + mw, my + 48, BLUE, 1)

    T(mx + 24, my + 72, '订单摘要（只读）', 14, BLUE, True, 'lm')
    for i, (k, v) in enumerate([('订单编号', 'ORD-20261113-0002'),
                                ('商品 / 数量', '活动商品 A / 2 件'),
                                ('订单实收金额', '20000 分'),
                                ('当前状态', '待发货')]):
        y = my + 106 + i * 34
        T(mx + 28, y, k, 13, MUTED, False, 'lm')
        T(mx + 180, y, v, 13, INK, False, 'lm')
        L(mx + 24, y + 20, mx + mw - 24, y + 20, LINE_L)

    T(mx + 24, my + 258, '退款金额', 13, MUTED, False, 'lm')
    INPUT(mx + 130, my + 242, 300, 34, '20000 分（整单，只读）', value=True)
    TAG(mx + 446, my + 248, '不做部分退款', w=150, h=24, tone='gray', sz=11)

    T(mx + 24, my + 306, '退款原因（必填）', 13, MUTED, False, 'lm')
    R(mx + 24, my + 328, mw - 48, 76, fill=WHITE, outline=LINE)
    T(mx + 36, my + 348, '请填写退款原因（占位文字）', 12, MUTED, False, 'lm')

    R(mx + 24, my + 420, mw - 48, 52, fill=FILL, outline=None)
    DASH_RECT(mx + 24, my + 420, mw - 48, 52, LINE)
    T(mx + 38, my + 438, '提交后订单转为「退款审核中」，发货暂停（M-07）；仅「待发货」可申请。',
      12, INK, False, 'lm')
    T(mx + 38, my + 458, '与发货并发时只形成一种合法结果（M-22）。', 12, MUTED, False, 'lm')

    BTN(mx + 24, my + 488, 150, 40, '提交申请', primary=True)
    BTN(mx + 186, my + 488, 120, 40, '取消')

    NOTE(40, 800, 660, 110, '操作结果区 C-02 · 失败原因（M-xx）',
         ['M-11  已发货，不受理售前退款｜M-22  退款/发货并发，仅一种结果生效',
          'M-07  退款申请审核中，发货已暂停｜M-24  原因必填'])
    NOTE(720, 800, 680, 110, '业务标注 · 与发货互斥',
         ['整单退款金额恒等于订单实收金额；不做部分退款、不做售后退货',
          'S3 售前退款链起点；S5 并发竞争时客服审核与仓库发货互斥裁决'])
    SAVE('06-退款弹窗.png')


# ---------------------------------------------------------------- 07 仓库发货页
def p07():
    NEW(7, '仓库发货页', '发货处理', WH_NAV, 'warehouse01', '仓库',
        'V-05 待发货列表 + V-06 发货录入 · 发货登记只一次 · 与退款流程互斥', 'V-05 / V-06', 'S1 / S3 / S5')
    PANEL(40, 170, 800, 62, None)
    T(58, 201, '发货筛选', 13, MUTED, False, 'lm')
    INPUT(140, 184, 190, 34, '可发货 / 暂停 / 已发货 / 全部', drop=True, value=True)
    T(348, 201, '订单编号', 13, MUTED, False, 'lm')
    INPUT(430, 184, 190, 34, '输入订单号（占位）')
    BTN(632, 184, 82, 34, '查询', primary=True)

    TABLE(40, 248, [160, 130, 60, 110, 150, 190],
          ['订单编号', '商品名称', '数量', '金额(分)', '订单状态', '操作'],
          [['ORD-0002', '活动商品 A', '2', '20000', '', '[登记发货]'],
           ['ORD-0003', '活动商品 A', '1', '10000', '', '[暂停发货·只读]'],
           ['ORD-0008', '活动商品 A', '1', '10000', '', '[已登记·只读]'],
           ['ORD-0009', '活动商品 A', '1', '10000', '', '[登记发货]']],
          rowh=50, headh=38,
          tags={(0, 4): ('待发货', 'blue'), (1, 4): ('退款审核中', 'gray'),
                (2, 4): ('已发货（终态）', 'gray'), (3, 4): ('待发货', 'blue')})

    PANEL(860, 170, 540, 470, '发货录入表单（登记一次）')
    T(878, 222, '订单摘要（只读）', 13, BLUE, True, 'lm')
    for i, (k, v) in enumerate([('订单编号', 'ORD-0002'), ('商品 / 数量', '活动商品 A / 2 件'),
                                ('金额', '20000 分'), ('当前状态', '待发货'),
                                ('付款时间', '2026-11-13 09:04')]):
        y = 254 + i * 30
        T(878, y, k, 12, MUTED, False, 'lm')
        T(1010, y, v, 12, INK, False, 'lm')
    L(878, 410, 1382, 410, LINE_L)
    T(878, 438, '承运方（必填）', 13, MUTED, False, 'lm')
    INPUT(1010, 421, 370, 34, '如：演示承运方')
    T(878, 484, '运单号（必填）', 13, MUTED, False, 'lm')
    INPUT(1010, 467, 370, 34, '如：YD20261113001')
    BTN(878, 528, 150, 40, '登记发货', primary=True)
    BTN(1040, 528, 130, 40, '取消')
    T(878, 596, '成功后状态转「已发货（终态）」，本表单整体只读；不提供改写订单状态入口',
      12, MUTED, False, 'lm')

    NOTE(40, 680, 800, 230, '操作结果区 C-02 · 失败原因（M-xx）',
         ['M-23  承运方或运单号未填写，不能登记发货',
          'M-19  该订单已登记发货，不能重复登记',
          'M-18  只有合法待发货订单可登记发货',
          'M-07  退款申请审核中 / 处理中，发货已暂停',
          'M-22  退款与发货并发：本单已进入退款流程，发货未登记；',
          '         仅形成一种合法业务结果，表单锁定只读、提交隐藏'])
    NOTE(860, 680, 540, 230, '业务标注 · 互斥与并发',
         ['发货登记一次：重复登记被拒，不产生第二笔业务结果（M-10）',
          '待发货且 refund_state = 未申请 时才可登记',
          'S1 正常成交：运营上架 → 买家付款 → 仓库发货 → 买家查运单',
          'S3 申请退款后发货暂停；S5 退款与发货并发只形成一种合法结果',
          '仓库不可审核退款；账号权限由 X-Demo-Account 服务端判定'])
    SAVE('07-仓库发货页.png')


# ---------------------------------------------------------------- 08 客服退款处理页
def p08():
    NEW(8, '客服退款处理页', '退款审核', CS_NAV, 'cs01', '客服',
        'V-07 退款审核与渠道失败重试 + V-08 迟到支付异常待处理核实 · 原因必填', 'V-07 / V-08', 'S3 / S4 / S5')
    PANEL(40, 170, 820, 62, None)
    T(58, 201, '退款筛选', 13, MUTED, False, 'lm')
    INPUT(140, 184, 230, 34, '待审核 / 处理中 / 失败待重试 / 已完成', drop=True, value=True)
    BTN(382, 184, 82, 34, '查询', primary=True)
    T(840, 201, '客服：同意 / 拒绝 / 重试 / 核实，不登记发货', 12, MUTED, False, 'rm')

    TABLE(40, 248, [150, 110, 160, 130, 130, 140],
          ['订单编号', '退款金额(分)', '退款状态', '渠道结果', '申请时间', '操作'],
          [['ORD-0003', '10000', '', '—', '09:05', '[同意] [拒绝]'],
           ['ORD-0004', '10000', '', '首次失败', '09:07', '[发起退款] [重试]'],
           ['ORD-0007', '10000', '', '成功', '09:13', '[已完成·只读]'],
           ['ORD-0010', '10000', '', '—', '09:20', '[同意] [拒绝]']],
          rowh=48, headh=36,
          tags={(0, 2): ('退款审核中', 'blue'), (1, 2): ('渠道失败待重试', 'gray'),
                (2, 2): ('已退款（终态）', 'gray'), (3, 2): ('退款审核中', 'blue')})

    PANEL(880, 170, 520, 300, '审核 / 重试表单')
    T(898, 222, '审核结论', 13, MUTED, False, 'lm')
    RADIO(1000, 208, '同意', True)
    RADIO(1100, 208, '拒绝', False)
    T(898, 262, '审核原因 / 备注（必填）', 13, MUTED, False, 'lm')
    R(898, 280, 484, 66, fill=WHITE, outline=LINE)
    T(910, 298, '请写明审核或核实原因（占位文字）', 12, MUTED, False, 'lm')
    BTN(898, 366, 120, 38, '提交审核', primary=True)
    BTN(1028, 366, 120, 38, '发起退款')
    BTN(1158, 366, 120, 38, '重试退款')
    T(898, 432, '渠道首次失败保留待处理记录（M-08），订单停留「退款处理中」供重试',
      12, MUTED, False, 'lm')

    PANEL(40, 500, 1360, 240, '迟到支付异常待处理列表（V-08）')
    T(58, 540, '筛选：待处理 / 已核实 / 已发起退款 / 退款成功 / 退款失败    身份：cs01（客服）',
      12, MUTED, False, 'lm')
    TABLE(58, 562, [140, 160, 150, 150, 150, 170, 170, 170],
          ['异常编号 event_id', '渠道交易号', '订单编号', '通知到达', '异常状态',
           '订单当前状态', '处理原因（必填）', '操作'],
          [['EV-0001', 'CH-0009', 'ORD-0005', '09:19', '', '', '[填写原因]', '[核实] [发起退款]'],
           ['EV-0002', 'CH-0010', 'ORD-0006', '09:21', '', '', '[已写原因]', '[已核实·只读]'],
           ['EV-0003', 'CH-0011', 'ORD-0001', '09:25', '', '', '[填写原因]', '[核实] [发起退款]']],
          rowh=44, headh=34,
          tags={(0, 4): ('待处理', 'blue'), (1, 4): ('已核实', 'gray'),
                (2, 4): ('待处理', 'blue'),
                (0, 5): ('已关闭（终态）', 'gray'), (1, 5): ('已关闭（终态）', 'gray'),
                (2, 5): ('已关闭（终态）', 'gray')})

    NOTE(40, 760, 660, 160, '操作结果区 C-02 · 失败原因（M-xx）',
         ['M-08  渠道退款失败，已保留待处理记录，请客服重试',
          'M-09  迟到支付：订单不恢复，转异常支付待处理',
          'M-24  审核退款 / 核实异常必须写明原因',
          'M-10  重复审核 / 重复退款被拒，不产生第二笔业务结果'])
    NOTE(720, 760, 680, 160, '业务标注 · 迟到支付与库存',
         ['M-15  迟到支付订单保持「已关闭（终态）」，V-08 列表状态恒显终态',
          'M-26  迟到支付对应的退款不得再次恢复此前已释放数量',
          'M-17  运营核查结论：无重复释放、无重复退款',
          'S3 退款首次失败再成功；S4 迟到支付核实退款；S5 重复通知幂等'])
    SAVE('08-客服退款处理页.png')


def main():
    for fn in (p01, p02, p03, p04, p05, p06, p07, p08):
        fn()
    print('all 8 wireframes written to', OUT)


if __name__ == '__main__':
    main()
