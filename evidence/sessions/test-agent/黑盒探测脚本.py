# -*- coding: utf-8 -*-
"""
独立测试 Agent 自写黑盒探测脚本（题目 01：订单交易、发货与售前退款）

设计原则：
1. 纯黑盒：只通过 HTTP 接口调用服务，不 import 任何被测包，不读数据库，不改生产代码。
2. 自带服务生命周期：脚本自行 build 并以 demo-memory 模式启动服务（GVA_ADDR=:18099），
   不连接 MySQL（本机无实例，且禁止使用 WSL）。
3. 每个用例都带编号、前置条件、断言依据；断言失败即记 FAIL，不做任何“美化”或弱化。
4. 只做检测与登记，不修改被测代码。

库存预算（demo-memory 预置：goods 1 = 活动商品 可售 5；goods 2 = 演示商品 可售 2）：
    goods1 用于 S2 / S2b / S1 / S3 / S4 / E / S5-1 / S5-2
    goods2 用于 S5-3 / R
    预置库存不可补充（服务端未提供可售数量维护接口），故按「峰值同时占用 ≤ 7」编排。

用法：
    python evidence/sessions/test-agent/黑盒探测脚本.py
    python evidence/sessions/test-agent/黑盒探测脚本.py --base-url http://127.0.0.1:18099 --no-start
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

# ----------------------------------------------------------------------------------
# 基础常量
# ----------------------------------------------------------------------------------

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

# 原型设计文档 3.3「异常提示文案总表（M-xx）」原文，用于错误码与文案映射校验
M_TABLE = {
    "M-01": "商品未上架，不能购买",
    "M-02": "可售数量不足，下单失败",
    "M-03": "每单数量只能是 1 或 2 件",
    "M-04": "一单只能购买一种商品",
    "M-05": "该订单状态不允许此操作",
    "M-06": "订单已超时关闭（服务端时间满 10 分钟），占用已释放",
    "M-07": "退款申请审核中 / 处理中，发货已暂停",
    "M-08": "渠道退款失败，已保留待处理记录，请客服重试",
    "M-09": "迟到支付：订单已关闭，支付成功通知不能恢复订单或重新占用库存，已转异常支付待处理",
    "M-10": "重复操作被拒绝，不产生第二笔业务结果",
    "M-11": "已发货订单不受理本题售前退款",
    "M-12": "已有订单的下单时商品与价格不受本次调价 / 上下架影响",
    "M-13": "不得通过商品维护或改写订单状态消除异常记录",
    "M-14": "异常记录不能通过直接修改订单状态消失",
    "M-15": "迟到支付订单保持已关闭终态",
    "M-16": "退款失败待处理，请客服跟进重试",
    "M-17": "核查结果：无重复释放、无重复退款",
    "M-18": "只有合法待发货订单可登记发货",
    "M-19": "该订单已登记发货，不能重复登记",
    "M-20": "无权限 / 越权：不能查看或处理他人订单",
    "M-21": "当前为演示教学时钟，10 分钟超时已缩短为 X，测试与线上演示规则一致",
    "M-22": "退款与发货并发：本单已进入退款流程，发货未登记；仅形成一种合法业务结果",
    "M-23": "承运方或运单号未填写，不能登记发货",
    "M-24": "审核退款 / 核实异常必须写明原因",
    "M-25": "重复支付通知已幂等处理，未重复记款",
    "M-26": "迟到支付对应的退款不得再次恢复此前已释放数量",
    "M-27": "同一渠道交易号已归属其他订单，本次关联被拒",
    "M-28": "支付通知验签失败，订单状态不变",
    "M-29": "支付通知金额与订单不符，订单状态不变",
    "M-30": "支付通知指向未知订单，订单状态不变",
}

OBSERVED_M = {}       # 顶层业务拒绝码 -> 返回 message
OBSERVED_EVENT_M = {}  # 事件记录中的 failure_code -> failure_reason
SEEN_CODES = set()

RESULTS = []
LOCK = threading.Lock()
_counter = {"n": 0}


def record(case_id, verdict, title, detail=""):
    with LOCK:
        RESULTS.append((case_id, verdict, title, detail))
        _counter["n"] += 1
        print("[%s] %-4s | %s | %s" % (case_id, verdict, title, detail), flush=True)


def check(case_id, title, condition, detail=""):
    record(case_id, "PASS" if condition else "FAIL", title, detail)
    return bool(condition)


def blocked(case_id, title, detail=""):
    record(case_id, "BLOCK", title, detail)


def info(case_id, title, detail=""):
    record(case_id, "INFO", title, detail)


# ----------------------------------------------------------------------------------
# HTTP 客户端
# ----------------------------------------------------------------------------------

BASE_URL = "http://127.0.0.1:18099"


def http(method, path, account=None, body=None, extra_headers=None, timeout=30, retries=1):
    """HTTP 调用；对连接层瞬时异常做有限次重试（客户端稳健性措施，断言本身不放宽）。"""
    url = BASE_URL + path
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if account:
        headers["X-Demo-Account"] = account
    if extra_headers:
        headers.update(extra_headers)
    last_err = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                status = resp.status
            break
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            status = e.code
            break
        except Exception as e:                               # noqa: BLE001
            last_err = e
            if attempt < retries:
                time.sleep(0.3)
                continue
            return -1, {"_transport_error": repr(e)}
    try:
        payload = json.loads(raw) if raw else {}
    except Exception:                                        # noqa: BLE001
        payload = {"_raw": raw}
    if isinstance(payload, dict):
        code = payload.get("code")
        if isinstance(code, str) and code.startswith("M-"):
            OBSERVED_M[code] = payload.get("message", "")
            SEEN_CODES.add(code)
        # 事件记录把 M-xx 编号放在 data.failure_code 中（如幂等重复通知、迟到支付退款），
        # 与顶层业务拒绝码分开统计，用于核对「编号 → 文案」映射。
        d = payload.get("data")
        if isinstance(d, dict):
            fcode = d.get("failure_code")
            if isinstance(fcode, str) and fcode.startswith("M-"):
                OBSERVED_EVENT_M.setdefault(fcode, d.get("failure_reason", "") or "")
                SEEN_CODES.add(fcode)
    return status, payload


def api(method, path, account=None, body=None, extra_headers=None):
    """返回 (http_status, code, message, data)"""
    status, payload = http(method, path, account, body, extra_headers)
    if not isinstance(payload, dict):
        return status, "_BAD_JSON", str(payload), {}
    if "_transport_error" in payload:
        return status, None, "TRANSPORT_ERROR: %s" % payload["_transport_error"], {}
    return status, payload.get("code"), payload.get("message"), payload.get("data")


def goods(goods_id=1, account="ops01"):
    _, _, _, data = api("GET", "/api/v1/goods", account)
    for g in (data or {}).get("items", []):
        if g["id"] == goods_id:
            return g
    return None


def stock(goods_id=1):
    g = goods(goods_id)
    if g is None:
        return None
    return g["available_stock"], g["occupied_stock"]


EMPTY_ORDER = {k: None for k in (
    "id", "order_no", "buyer_id", "goods_id", "goods_no", "goods_name", "quantity",
    "unit_price", "total_amount", "status", "expires_at", "paid_at", "closed_at",
    "cancelled_at", "refund_kind", "refund_reason", "refund_state", "refund_retry_count",
    "refund_channel_trade_no", "refunded_at", "stock_restored", "late_payment_refunded",
    "shipment_carrier", "shipment_tracking_no", "shipped_at")}


def order_of(order_no, account="ops01"):
    """查不到订单时返回字段齐全的空对象，避免脚本因一次查询失败而中断。"""
    _, code, _, data = api("GET", "/api/v1/orders/%s" % order_no, account)
    return data if code == "0" else dict(EMPTY_ORDER)


def summary(account="ops01"):
    _, code, _, data = api("GET", "/api/v1/ops/summary", account)
    return data if code == "0" else None


# ----------------------------------------------------------------------------------
# 服务生命周期（demo-memory 模式，不连接 MySQL）
# ----------------------------------------------------------------------------------

class Service(object):
    """自行编译并以 demo-memory 模式启动被测服务；结束后终止并清理临时产物。"""

    def __init__(self, port=18099):
        self.port = port
        self.proc = None
        self.binpath = None

    def build(self):
        self.binpath = os.path.join(tempfile.mkdtemp(prefix="shop-ta-"), "shop-trade-ta.exe")
        print(">>> 编译被测程序: go build -o %s ." % self.binpath, flush=True)
        p = subprocess.run(["go", "build", "-o", self.binpath, "."],
                           cwd=REPO_ROOT, capture_output=True, text=True)
        if p.returncode != 0:
            print(p.stdout, file=sys.stderr)
            print(p.stderr, file=sys.stderr)
            raise SystemExit("go build 失败，终止黑盒探测")
        print(">>> go build 成功", flush=True)

    def start(self):
        env = dict(os.environ)
        env["GVA_ADDR"] = ":%d" % self.port
        env["GIN_MODE"] = "release"
        env.pop("GVA_MYSQL_DSN", None)          # 明确不连接 MySQL
        env.pop("DEMO_CLOCK_OFFSET_MINUTES", None)
        print(">>> 启动服务: GVA_ADDR=:%d （demo-memory 模式，未设置 GVA_MYSQL_DSN）" % self.port, flush=True)
        # 运行日志直接落盘，避免 Windows 管道缓冲区写满导致服务阻塞
        self.logpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_server_runtime.log")
        self.logfile = open(self.logpath, "w", encoding="utf-8")
        self.proc = subprocess.Popen([self.binpath], cwd=REPO_ROOT, env=env,
                                     stdout=self.logfile, stderr=subprocess.STDOUT, text=True)
        for _ in range(120):
            try:
                status, payload = http("GET", "/health", timeout=3)
                if status == 200 and payload.get("status") == "ok":
                    print(">>> 健康检查通过: %s" % json.dumps(payload, ensure_ascii=False), flush=True)
                    print(">>> 服务运行日志: %s" % self.logpath, flush=True)
                    return payload
            except Exception:                    # noqa: BLE001
                pass
            time.sleep(0.5)
        raise SystemExit("服务启动超时（健康检查未通过）")

    def stop(self):
        if self.proc is not None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except Exception:                    # noqa: BLE001
                self.proc.kill()
            print(">>> 服务已停止", flush=True)
        if getattr(self, "logfile", None):
            try:
                self.logfile.close()
            except Exception:                    # noqa: BLE001
                pass
        if self.binpath and os.path.isdir(os.path.dirname(self.binpath)):
            shutil.rmtree(os.path.dirname(self.binpath), ignore_errors=True)


# ----------------------------------------------------------------------------------
# 业务辅助
# ----------------------------------------------------------------------------------

def make_order(account, goods_id, qty):
    """返回 (code, message, order_no)"""
    _, code, msg, data = api("POST", "/api/v1/orders", account, {"goods_id": goods_id, "quantity": qty})
    order_no = (data or {}).get("order_no") if isinstance(data, dict) else None
    return code, msg, order_no


def pay(account, order_no, trade_no, amount, signature_valid=True):
    return api("POST", "/api/v1/payment/callback", account, {
        "order_no": order_no, "channel_trade_no": trade_no,
        "amount": amount, "signature_valid": signature_valid})


def refund_cb(account, order_no, refund_no, amount, success, signature_valid=True):
    return api("POST", "/api/v1/refund/callback", account, {
        "order_no": order_no, "refund_channel_trade_no": refund_no,
        "amount": amount, "success": success, "signature_valid": signature_valid})


def set_clock(offset_minutes, account="ops01"):
    return api("POST", "/api/v1/admin/clock", account, {"offset_minutes": offset_minutes})


def close_expired(account="ops01"):
    return api("POST", "/api/v1/admin/orders/close-expired", account, {})


def cancel(order_no, account):
    return api("POST", "/api/v1/orders/%s/cancel" % order_no, account, {})


def apply_refund(order_no, account, reason="申请整单售前退款"):
    return api("POST", "/api/v1/orders/%s/refund/apply" % order_no, account, {"reason": reason})


def approve_refund(order_no, account="cs01", remark="同意整单退款"):
    return api("POST", "/api/v1/orders/%s/refund/approve" % order_no, account, {"remark": remark})


def refund_success_flow(order_no, refund_no, amount, account="cs01"):
    """客服同意 → 渠道成功退款（用于释放库存的收尾动作）"""
    approve_refund(order_no, account)
    return refund_cb("mock01", order_no, refund_no, amount, True)


# ==================================================================================
# 场景 S1：活动正常成交
# ==================================================================================

def scenario_s1():
    print("\n================ 场景 S1 活动正常成交 ================", flush=True)
    g = goods(1)
    check("TC-S1-01", "活动商品在售、单价 10000 分、初始可售 5 件（AC-01）",
          g is not None and g["status"] == "在售" and g["unit_price"] == 10000 and g["available_stock"] == 5,
          "goods=%s" % json.dumps(g, ensure_ascii=False))

    code, msg, ono = make_order("buyer01", 1, 2)
    check("TC-S1-02", "buyer01 下单 2 件成功，订单待支付",
          code == "0" and ono is not None, "code=%s msg=%s order_no=%s" % (code, msg, ono))
    o = order_of(ono)
    check("TC-S1-03", "订单金额 = 单价 10000 × 数量 2 = 20000 分（整数分，C-01/C-06）",
          o and o["total_amount"] == 20000 and o["unit_price"] == 10000 and o["quantity"] == 2
          and isinstance(o["total_amount"], int),
          "order=%s" % json.dumps({k: o[k] for k in ("order_no", "unit_price", "quantity", "total_amount", "status")}, ensure_ascii=False) if o else "order=None")
    check("TC-S1-04", "下单后库存预扣：可售 3 件、占用 2 件（R-03/R-06）",
          stock(1) == (3, 2), "stock=%s" % (stock(1),))

    st, code, msg, data = pay("mock01", ono, "CH-S1-001", 20000)
    check("TC-S1-05", "模拟渠道支付成功通知 → 订单转待发货，记款一次（R-14/R-15）",
          code == "0" and order_of(ono)["status"] == "待发货",
          "code=%s msg=%s status=%s" % (code, msg, order_of(ono)["status"]))
    check("TC-S1-06", "支付通知后库存占用不重复变化（可售 3 / 占用 2，R-12）",
          stock(1) == (3, 2), "stock=%s" % (stock(1),))

    st, code, msg, data = api("POST", "/api/v1/orders/%s/shipment" % ono, "warehouse01",
                               {"carrier": "SF", "tracking_no": "SF0001"})
    check("TC-S1-07", "仓库登记发货一次 → 订单转已发货（T-06/R-31）",
          code == "0" and order_of(ono)["status"] == "已发货",
          "code=%s msg=%s status=%s" % (code, msg, order_of(ono)["status"]))

    st, code, msg, data = api("GET", "/api/v1/orders/%s" % ono, "buyer01")
    check("TC-S1-08", "买家可查本人订单的承运方与运单号（AC-02）",
          code == "0" and data["shipment_carrier"] == "SF" and data["shipment_tracking_no"] == "SF0001",
          "carrier=%s tracking=%s" % (data.get("shipment_carrier"), data.get("shipment_tracking_no")))

    s = summary()
    check("TC-S1-09", "运营汇总：已收款 ≥ 20000 分、已发货订单数 ≥ 1",
          s and s["effective_payment_amount"] >= 20000 and s["shipped_orders"] >= 1,
          "summary=%s" % json.dumps(s, ensure_ascii=False))

    st, code, msg, data = api("POST", "/api/v1/admin/goods/1/price", "ops01",
                               {"unit_price": 12000, "reason": "活动调价（测试用）"})
    check("TC-S1-10", "运营调价成功并回带 M-12 / M-13 约束提示文案",
          code == "0" and data.get("hint") == M_TABLE["M-12"]
          and data.get("constraint") == M_TABLE["M-13"],
          "code=%s hint=%s constraint=%s" % (code, data.get("hint"), data.get("constraint")))
    o2 = order_of(ono)
    check("TC-S1-11", "调价后既有订单商品与金额快照保持下单时值不变（R-02 / AC-03）",
          o2["unit_price"] == 10000 and o2["total_amount"] == 20000,
          "unit_price=%s total=%s" % (o2["unit_price"], o2["total_amount"]))
    api("POST", "/api/v1/admin/goods/1/price", "ops01", {"unit_price": 10000, "reason": "恢复演示价"})
    check("TC-S1-12", "恢复商品单价为 10000 分",
          goods(1)["unit_price"] == 10000, "unit_price=%s" % goods(1)["unit_price"])
    return ono


# ==================================================================================
# 场景 S2：缺货与弃单
# ==================================================================================

def scenario_s2():
    print("\n================ 场景 S2 缺货与弃单（20 并发抢单不超卖） ================", flush=True)
    results = [None] * 20
    quantities = [1 if i % 2 == 0 else 2 for i in range(20)]
    buyers = ["buyer01", "buyer02", "buyer03"]

    def worker(idx):
        results[idx] = make_order(buyers[idx % 3], 1, quantities[idx])

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    ok_orders = [(quantities[i], results[i][2], buyers[i % 3]) for i in range(20) if results[i][0] == "0"]
    rejected = [(quantities[i], results[i][0], results[i][1]) for i in range(20) if results[i][0] != "0"]
    occupied = sum(q for q, _, _ in ok_orders)
    avail, occ = stock(1)
    check("TC-S2-01", "20 并发下单（每单数量取 1 或 2）不超卖：预扣合计 ≤ 5 件（R-05 / AC-05）",
          occupied <= 5, "成功订单数=%d 预扣合计=%d 可售=%d 占用=%d" % (len(ok_orders), occupied, avail, occ))
    check("TC-S2-02", "库存守恒：已占用 + 可售 = 初始 5 件",
          avail + occ == 5 and occ == occupied,
          "可售=%d 占用=%d 初始=5" % (avail, occ))
    check("TC-S2-03", "被拒请求全部返回 M-02「可售数量不足，下单失败」",
          len(rejected) == 20 - len(ok_orders) and all(c == "M-02" for _, c, _ in rejected),
          "被拒数=%d 错误码集合=%s" % (len(rejected), sorted({c for _, c, _ in rejected})))
    check("TC-S2-04", "成功订单数 + 被拒数 = 20，被拒请求不产生订单",
          len(ok_orders) + len(rejected) == 20,
          "成功=%d 被拒=%d" % (len(ok_orders), len(rejected)))
    check("TC-S2-05", "每个成功订单都有对应库存预扣（占用数 = 成功订单数量之和）",
          occ == occupied, "占用=%d 成功订单数量之和=%d" % (occ, occupied))

    # --- 可售不足被拒：在并发抢单把可售压到 0 之后立即验证 ---
    avail_before = stock(1)[0]
    c1, m1, _ = make_order("buyer02", 1, 1)
    c2, m2, _ = make_order("buyer03", 1, 2)
    check("TC-S2-09", "可售为 0 时下单 1 件被拒（M-02）",
          c1 == "M-02", "可售=%d code=%s msg=%s" % (avail_before, c1, m1))
    check("TC-S2-10", "可售为 0 时下单 2 件被拒（E-03），库存不变",
          c2 == "M-02" and stock(1)[0] == avail_before,
          "code=%s msg=%s stock=%s 期望可售=%d" % (c2, m2, stock(1), avail_before))

    before = stock(1)[0]
    released_total = 0
    release_ok = True
    for q, ono, who in ok_orders:
        _, c, m, _ = cancel(ono, who)
        if c != "0":
            release_ok = False
        released_total += q
    check("TC-S2-06", "取消全部成功订单：每单释放一次，预扣合计全部释放（R-07）",
          release_ok and stock(1)[0] == before + released_total,
          "释放前可售=%d 释放后可售=%d 应释放=%d" % (before, stock(1)[0], released_total))
    check("TC-S2-07", "释放后库存回到初始态：可售 5 / 占用 0",
          stock(1) == (5, 0), "stock=%s" % (stock(1),))

    first_ono, first_who = ok_orders[0][1], ok_orders[0][2]
    _, c, m, _ = cancel(first_ono, first_who)
    check("TC-S2-08", "重复取消同一订单返回 M-10 且库存不再释放（R-08）",
          c == "M-10" and stock(1) == (5, 0), "code=%s msg=%s stock=%s" % (c, m, stock(1)))

    # 释放后由其他买家再次购买
    c3, m3, ono3 = make_order("buyer03", 1, 1)
    check("TC-S2-11", "取消释放后，其他买家可再次下单成功（AC-15）",
          c3 == "0", "code=%s msg=%s" % (c3, m3))
    cancel(ono3, "buyer03")
    check("TC-S2-12", "清理后库存回到初始态：可售 5 / 占用 0",
          stock(1) == (5, 0), "stock=%s" % (stock(1),))
    return


def scenario_s2_timeout():
    print("\n================ 场景 S2b 待支付 10 分钟超时关闭（服务端时间） ================", flush=True)
    avail0 = stock(1)[0]
    occ0 = stock(1)[1]
    c, m, ono = make_order("buyer01", 1, 1)
    check("TC-S2-13", "下单后进入待支付，占用 1 件",
          c == "0" and stock(1) == (avail0 - 1, occ0 + 1),
          "code=%s stock=%s" % (c, stock(1)))
    st, code, msg, data = set_clock(11)
    check("TC-S2-14", "运营可推进演示教学时钟（服务端时间 +11 分钟，A-01）",
          code == "0" and data.get("clock_offset_minutes") == 11,
          "code=%s data=%s" % (code, json.dumps(data, ensure_ascii=False)))
    st, code, msg, data = close_expired()
    check("TC-S2-15", "服务端时间满 10 分钟后超时关闭，订单转已关闭且预扣释放一次（T-04/R-07）",
          code == "0" and order_of(ono)["status"] == "已关闭" and stock(1) == (avail0, occ0),
          "closed_count=%s status=%s stock=%s" % (data.get("closed_count"), order_of(ono)["status"], stock(1)))
    st, code, msg, data = close_expired()
    check("TC-S2-16", "重复关闭不多释放：再次关单 closed_count=0 且库存不变（R-08 / AC-09）",
          code == "0" and data.get("closed_count") == 0 and stock(1) == (avail0, occ0),
          "closed_count=%s stock=%s" % (data.get("closed_count"), stock(1)))
    st, code, msg, data = cancel(ono, "buyer01")
    check("TC-S2-17", "已关闭订单再主动取消返回 M-10（主动取消与超时关闭只生效一次）",
          code == "M-10" and stock(1) == (avail0, occ0),
          "code=%s msg=%s stock=%s" % (code, msg, stock(1)))
    set_clock(0)
    st, code, msg, data = api("GET", "/api/v1/admin/clock", "ops01")
    check("TC-S2-18", "演示教学时钟可复位为 0（仅平移服务端时间，10 分钟业务规则不变）",
          code == "0" and data.get("clock_offset_minutes") == 0,
          "code=%s data=%s" % (code, json.dumps(data, ensure_ascii=False)))
    return ono


# ==================================================================================
# 场景 S3：售前退款
# ==================================================================================

def scenario_s3():
    print("\n================ 场景 S3 售前退款（首次失败→客服重试→再次成功） ================", flush=True)
    avail0 = stock(1)[0]
    occ0 = stock(1)[1]
    c, m, ono = make_order("buyer02", 1, 2)
    check("TC-S3-01", "buyer02 下单 2 件成功（应付 20000 分）",
          c == "0" and order_of(ono)["total_amount"] == 20000, "code=%s msg=%s" % (c, m))
    pay("mock01", ono, "CH-S3-001", 20000)
    check("TC-S3-02", "支付成功 → 待发货，库存预扣 2 件",
          order_of(ono)["status"] == "待发货" and stock(1) == (avail0 - 2, occ0 + 2),
          "status=%s stock=%s" % (order_of(ono)["status"], stock(1)))

    st, code, msg, data = apply_refund(ono, "buyer02", "不想要了，申请整单退款")
    check("TC-S3-03", "买家申请整单售前退款 → 退款审核中（发货暂停，T-05/R-26）",
          code == "0" and order_of(ono)["status"] == "退款审核中",
          "code=%s status=%s" % (code, order_of(ono)["status"]))

    st, code, msg, data = api("POST", "/api/v1/orders/%s/shipment" % ono, "warehouse01",
                               {"carrier": "SF", "tracking_no": "SF7777"})
    check("TC-S3-04", "申请期间仓库登记发货被拒，订单状态不变（R-26 / AC-11）",
          code in ("M-07", "M-22") and order_of(ono)["status"] == "退款审核中",
          "实际 code=%s msg=%s status=%s" % (code, msg, order_of(ono)["status"]))

    st, code, msg, data = approve_refund(ono, "cs01", "同意整单退款")
    check("TC-S3-05", "客服同意并写明原因 → 退款处理中（T-08）",
          code == "0" and order_of(ono)["status"] == "退款处理中",
          "code=%s status=%s" % (code, order_of(ono)["status"]))

    st, code, msg, data = refund_cb("mock01", ono, "RF-S3-001", 20000, False)
    check("TC-S3-06", "渠道明确退款失败 → 返回 M-08，保留待处理记录，订单仍为退款处理中（T-09/E-12）",
          code == "M-08" and order_of(ono)["status"] == "退款处理中",
          "code=%s msg=%s status=%s" % (code, msg, order_of(ono)["status"]))
    check("TC-S3-07", "失败期间订单不回到可发货状态（R-29）",
          order_of(ono)["status"] != "待发货", "status=%s" % order_of(ono)["status"])

    st, code, msg, data = api("POST", "/api/v1/orders/%s/refund/retry" % ono, "cs01",
                               {"remark": "客服重试整单退款"})
    check("TC-S3-08", "客服重试退款登记成功，重试次数 +1（A-13）",
          code == "0" and order_of(ono)["refund_retry_count"] == 1,
          "code=%s retry=%s" % (code, order_of(ono)["refund_retry_count"]))

    st, code, msg, data = refund_cb("mock01", ono, "RF-S3-001", 20000, True)
    check("TC-S3-09", "渠道再次通知退款成功 → 订单转已退款（T-10）",
          code == "0" and order_of(ono)["status"] == "已退款",
          "code=%s msg=%s status=%s" % (code, msg, order_of(ono)["status"]))
    check("TC-S3-10", "正常售前退款恢复相应可售数量一次（+2），库存回到退款前水位（R-09 / AC-11）",
          stock(1) == (avail0, occ0), "stock=%s 期望=%s" % (stock(1), (avail0, occ0)))

    st, code, msg, data = refund_cb("mock01", ono, "RF-S3-001", 20000, True)
    check("TC-S3-11", "重复退款通知幂等：不重复退款、不重复恢复库存（R-19/R-30 / AC-13）",
          code == "0" and stock(1) == (avail0, occ0) and order_of(ono)["status"] == "已退款",
          "code=%s msg=%s data.result=%s stock=%s" % (code, msg, (data or {}).get("result"), stock(1)))

    st, code, msg, data = api("GET", "/api/v1/orders/%s" % ono, "buyer02")
    check("TC-S3-12", "买家可见退款结果：退款状态成功、金额 = 实收 20000 分（R-29/R-30）",
          code == "0" and data["refund_state"] == "成功" and data["total_amount"] == 20000,
          "refund_state=%s total=%s" % (data.get("refund_state"), data.get("total_amount")))

    st, code, msg, data = api("GET", "/api/v1/ops/stock-check/%s" % ono, "ops01")
    check("TC-S3-13", "运营逐单核查：库存恢复 1 次且一致（AC-11）",
          code == "0" and data["actual_restore_times"] == 1 and data["expected_restore_times"] == 1
          and data["consistent"] is True,
          "code=%s data=%s" % (code, json.dumps(data, ensure_ascii=False)))

    st, code, msg, data = api("POST", "/api/v1/orders/%s/shipment" % ono, "warehouse01",
                               {"carrier": "SF", "tracking_no": "SF8888"})
    check("TC-S3-14", "已退款订单不得再发货（F-03）",
          code == "M-11" and order_of(ono)["status"] == "已退款",
          "code=%s msg=%s status=%s" % (code, msg, order_of(ono)["status"]))

    st, code, msg, data = apply_refund(ono, "buyer02", "再退一次")
    check("TC-S3-15", "已退款订单再次申请退款被拒（F-06 终态不可回退）",
          code in ("M-10", "M-11"), "code=%s msg=%s" % (code, msg))
    return ono


# ==================================================================================
# 场景 S4：迟到支付
# ==================================================================================

def scenario_s4():
    print("\n================ 场景 S4 迟到支付 ================", flush=True)
    avail0 = stock(1)[0]
    occ0 = stock(1)[1]
    c, m, ono = make_order("buyer03", 1, 1)
    check("TC-S4-01", "buyer03 下单 1 件成功",
          c == "0", "code=%s msg=%s" % (c, m))
    set_clock(11)
    close_expired()
    set_clock(0)
    check("TC-S4-02", "订单因服务端时间满 10 分钟已关闭，预扣已释放一次",
          order_of(ono)["status"] == "已关闭" and stock(1) == (avail0, occ0),
          "status=%s stock=%s" % (order_of(ono)["status"], stock(1)))

    st, code, msg, data = pay("mock01", ono, "CH-LATE-001", 10000)
    check("TC-S4-03", "关闭后到达支付成功通知 → 返回 M-09 并生成异常支付待处理记录（T-11 / AC-10）",
          code == "M-09" and isinstance(data, dict) and data.get("event_id", 0) > 0,
          "code=%s msg=%s data=%s" % (code, msg, json.dumps(data, ensure_ascii=False)))
    event_id = (data or {}).get("event_id") if isinstance(data, dict) else None
    check("TC-S4-04", "迟到支付不改订单状态：订单保持已关闭终态（R-20 / F-01）",
          order_of(ono)["status"] == "已关闭", "status=%s" % order_of(ono)["status"])
    check("TC-S4-05", "迟到支付不重新占用库存（可售/占用不变，R-20）",
          stock(1) == (avail0, occ0), "stock=%s" % (stock(1),))

    st, code, msg, data = close_expired()
    check("TC-S4-06", "迟到支付后再次超时关单：closed_count=0，库存不多释放（R-08）",
          code == "0" and data.get("closed_count") == 0 and stock(1) == (avail0, occ0),
          "closed_count=%s stock=%s" % (data.get("closed_count"), stock(1)))

    st, code, msg, data = api("POST", "/api/v1/late-payment/%s/verify" % event_id, "cs01",
                               {"reason": "已核对渠道流水，确认为迟到支付"})
    check("TC-S4-07", "客服核实异常并记录原因 → 异常支付已核实（R-21）",
          code == "0", "code=%s msg=%s" % (code, msg))
    st, code, msg, data = api("POST", "/api/v1/late-payment/%s/verify" % event_id, "cs01",
                               {"reason": "重复核实"})
    check("TC-S4-08", "重复核实被拒（M-10），不产生第二笔业务结果（F-08）",
          code == "M-10", "code=%s msg=%s" % (code, msg))

    st, code, msg, data = api("POST", "/api/v1/late-payment/%s/refund/initiate" % event_id, "cs01",
                               {"refund_no": "LATE-REF-001", "reason": "订单已关闭，向渠道发起退款"})
    check("TC-S4-09", "客服对迟到支付发起退款 → 退款请求已登记并标注 M-26 不恢复库存",
          code == "0" and (data or {}).get("failure_code") == "M-26",
          "code=%s data=%s" % (code, json.dumps(data, ensure_ascii=False)))
    st, code, msg, data = api("POST", "/api/v1/late-payment/%s/refund/initiate" % event_id, "cs01",
                               {"refund_no": "LATE-REF-001", "reason": "重复发起"})
    check("TC-S4-10", "重复发起迟到支付退款被拒（M-10）",
          code == "M-10", "code=%s msg=%s" % (code, msg))

    st, code, msg, data = api("POST", "/api/v1/late-payment/refund/callback", "mock01",
                               {"event_id": event_id, "refund_no": "LATE-REF-001",
                                "amount": 10000, "success": True, "signature_valid": True})
    check("TC-S4-11", "渠道确认迟到支付退款成功",
          code == "0" and (data or {}).get("event_type") == "迟到支付退款成功",
          "code=%s msg=%s data=%s" % (code, msg, json.dumps(data, ensure_ascii=False)))
    check("TC-S4-12", "迟到支付退款不得再次恢复此前已释放数量（可售不二次增加，R-10/R-22）",
          stock(1) == (avail0, occ0), "stock=%s 期望=%s" % (stock(1), (avail0, occ0)))
    check("TC-S4-13", "迟到支付退款后订单仍为已关闭终态",
          order_of(ono)["status"] == "已关闭", "status=%s" % order_of(ono)["status"])

    st, code, msg, data = api("GET", "/api/v1/ops/stock-check/%s" % ono, "ops01")
    check("TC-S4-14", "运营逐单核查：本单未产生库存恢复（actual=0, expected=0, consistent=true）",
          code == "0" and data["actual_restore_times"] == 0 and data["expected_restore_times"] == 0
          and data["consistent"] is True,
          "code=%s data=%s" % (code, json.dumps(data, ensure_ascii=False)))

    s = summary()
    check("TC-S4-15", "运营汇总可识别迟到支付与迟到支付退款各 1 条（R-24 / AC-10）",
          s and s["late_payment_events"] >= 1 and s["late_payment_refunded_events"] >= 1,
          "summary=%s" % json.dumps(s, ensure_ascii=False))
    return ono, event_id


# ==================================================================================
# 场景 S5：操作竞争
# ==================================================================================

def scenario_s5():
    print("\n================ 场景 S5 操作竞争 ================", flush=True)

    # --- S5-1 退款与发货并发裁决 ---
    both = 0
    loser_codes = []
    for i in range(2):
        c, m, ono = make_order("buyer01", 1, 1)
        if c != "0":
            check("TC-S5-01", "并发用例前置：下单成功", False, "code=%s msg=%s" % (c, m))
            break
        pay("mock01", ono, "CH-S5-CONC-%d" % i, 10000)
        res = {}

        def do_refund(ono=ono):
            res["refund"] = apply_refund(ono, "buyer01", "并发申请退款")

        def do_ship(ono=ono, i=i):
            res["ship"] = api("POST", "/api/v1/orders/%s/shipment" % ono, "warehouse01",
                              {"carrier": "SF", "tracking_no": "CONC%d" % i})

        t1 = threading.Thread(target=do_refund)
        t2 = threading.Thread(target=do_ship)
        t1.start(); t2.start(); t1.join(); t2.join()
        r_code = res["refund"][1]
        s_code = res["ship"][1]
        st = order_of(ono)["status"]
        if r_code == "0" and s_code == "0":
            both += 1
        loser_codes.append((r_code, s_code, st))
        if r_code == "0":
            approve_refund(ono, "cs01", "并发分支收尾")
            refund_cb("mock01", ono, "RF-S5-CONC-%d" % i, 10000, True)
    check("TC-S5-01", "退款与发货并发：未出现「两者都成功」的非法双重结果（R-28 / AC-13）",
          both == 0, "并发轮次=%d 两者同时成功=%d 明细=%s" % (len(loser_codes), both, loser_codes))
    check("TC-S5-02", "退款与发货并发：后到者被明确拒绝并给出 M-xx 原因（A-09）",
          all((rc != "0" or sc != "0") and (rc.startswith("M-") or sc.startswith("M-"))
              for rc, sc, _ in loser_codes),
          "每轮 (退款码,发货码,最终状态)=%s" % loser_codes)
    check("TC-S5-03", "并发后订单状态唯一：要么退款链路（退款审核中/退款处理中），要么已发货",
          all(st in ("退款审核中", "退款处理中", "已发货", "已退款") for _, _, st in loser_codes),
          "最终状态集合=%s" % [st for _, _, st in loser_codes])

    # --- S5-2 重复支付通知 ---
    avail0 = stock(1)[0]
    occ0 = stock(1)[1]
    c, m, ono = make_order("buyer02", 1, 1)
    check("TC-S5-04", "前置：下单成功（1 件，待支付）",
          c == "0", "code=%s msg=%s" % (c, m))
    _, _, _, d1 = pay("mock01", ono, "CH-S5-REPEAT-001", 10000)
    _, _, _, d2 = pay("mock01", ono, "CH-S5-REPEAT-001", 10000)
    _, _, _, d3 = pay("mock01", ono, "CH-S5-REPEAT-001", 10000)
    check("TC-S5-05", "同一订单连续 3 次相同支付成功通知：仅第 1 次记款（R-15 / AC-06）",
          (d1 or {}).get("result") == "已记款"
          and (d2 or {}).get("result") == "重复支付通知已幂等处理，未重复记款"
          and (d3 or {}).get("result") == "重复支付通知已幂等处理，未重复记款",
          "r1=%s r2=%s r3=%s" % ((d1 or {}).get("result"), (d2 or {}).get("result"), (d3 or {}).get("result")))
    s_before = summary()["effective_payment_amount"]
    pay("mock01", ono, "CH-S5-REPEAT-001", 10000)
    s_after = summary()["effective_payment_amount"]
    check("TC-S5-06", "重复支付通知不重复记款：已收款合计不变",
          s_before == s_after, "before=%s after=%s" % (s_before, s_after))
    check("TC-S5-07", "重复支付通知库存占用不重复变化（R-12）",
          stock(1) == (avail0 - 1, occ0 + 1), "stock=%s" % (stock(1),))
    check("TC-S5-08", "重复支付通知后订单仅一次进入待发货",
          order_of(ono)["status"] == "待发货", "status=%s" % order_of(ono)["status"])
    # 收尾：完成退款以释放库存
    apply_refund(ono, "buyer02", "收尾释放库存")
    approve_refund(ono, "cs01", "收尾释放库存")
    refund_cb("mock01", ono, "RF-S5-REPEAT-001", 10000, True)
    check("TC-S5-09", "收尾：正常售前退款完成后库存回到释放前水位",
          stock(1) == (avail0, occ0), "stock=%s 期望=%s" % (stock(1), (avail0, occ0)))

    # --- S5-3 同一渠道交易号指向第二个订单（goods2） ---
    g2_avail = stock(2)[0]
    g2_occ = stock(2)[1]
    c, m, ono_x = make_order("buyer01", 2, 1)
    c2, m2, ono_y = make_order("buyer03", 2, 1)
    check("TC-S5-10", "前置：goods2 上创建 2 笔待支付订单",
          c == "0" and c2 == "0", "x=%s y=%s" % (c, c2))
    _, code, msg, _ = pay("mock01", ono_x, "CH-S5-SHARED-001", 10000)
    first_ok = code == "0"
    _, code, msg, _ = pay("mock01", ono_y, "CH-S5-SHARED-001", 10000)
    check("TC-S5-11", "同一渠道交易号关联第二个订单被拒（M-27 / R-16 / AC-08）",
          first_ok and code == "M-27", "code=%s msg=%s" % (code, msg))
    check("TC-S5-12", "被拒的第二单状态不变（仍待支付）",
          order_of(ono_y)["status"] == "待支付", "status=%s" % order_of(ono_y)["status"])
    cancel(ono_y, "buyer03")
    check("TC-S5-13", "清理：第二单取消后 goods2 占用回到 1（仅第一单占用）",
          stock(2) == (g2_avail - 1, g2_occ + 1), "stock=%s" % (stock(2),))
    # 收尾：释放 ono_x
    apply_refund(ono_x, "buyer01", "收尾释放库存")
    approve_refund(ono_x, "cs01", "收尾释放库存")
    refund_cb("mock01", ono_x, "RF-S5-SHARED-001", 10000, True)
    _, _, _, dup = refund_cb("mock01", ono_x, "RF-S5-SHARED-001", 10000, True)
    check("TC-S5-14", "重复退款通知幂等：结果为「重复退款通知已幂等处理」，且库存未二次恢复",
          (dup or {}).get("result") == "重复退款通知已幂等处理，未重复退款"
          and stock(2) == (g2_avail, g2_occ),
          "result=%s stock=%s 期望=%s" % ((dup or {}).get("result"), stock(2), (g2_avail, g2_occ)))
    return


# ==================================================================================
# 场景 E：边界与异常
# ==================================================================================

def scenario_edges():
    print("\n================ 场景 E 边界与异常 ================", flush=True)
    total_before = summary()["total_orders"]
    avail0 = stock(1)[0]
    occ0 = stock(1)[1]

    for cid, qty, title in [
        ("TC-E-01", 0, "数量 0 被拒"),
        ("TC-E-02", 3, "数量 3 被拒"),
        ("TC-E-03", -1, "数量 -1 被拒"),
    ]:
        code, msg, ono = make_order("buyer01", 1, qty)
        check(cid, title + " → M-03「每单数量只能是 1 或 2 件」（E-01）",
              code == "M-03" and ono is None, "code=%s msg=%s" % (code, msg))
    check("TC-E-04", "数量非法时不产生订单、不预扣库存",
          summary()["total_orders"] == total_before and stock(1) == (avail0, occ0),
          "total_orders %s -> %s stock=%s" % (total_before, summary()["total_orders"], stock(1)))

    code, msg, ono = make_order("buyer01", 0, 1)
    check("TC-E-05", "一单提交空商品（等价多商品非法）→ M-04「一单只能购买一种商品」（E-04）",
          code == "M-04", "code=%s msg=%s" % (code, msg))

    code, msg, ono = make_order("buyer01", 999, 1)
    check("TC-E-06", "下单不存在的商品 → M-01「商品未上架，不能购买」",
          code == "M-01", "code=%s msg=%s" % (code, msg))

    # E-02 购买已下架商品：服务端未提供上下架能力
    st_off, _ = http("POST", "/api/v1/admin/goods/1/status", "ops01", {"status": "下架"})
    st_put, _ = http("PUT", "/api/v1/goods/1", "ops01", {"status": "下架"})
    if st_off in (200, 201) and st_put in (200, 204):
        code, msg, _ = make_order("buyer01", 1, 1)
        check("TC-E-07", "购买已下架商品 → M-01（E-02）", code == "M-01", "code=%s msg=%s" % (code, msg))
    else:
        blocked("TC-E-07", "购买已下架商品（E-02）",
                "因实现限制未能执行：服务端未提供商品上架/下架接口"
                "（POST /admin/goods/1/status → HTTP %s；PUT /goods/1 → HTTP %s），"
                "demo-memory 预置的两个商品均为「在售」，无法构造下架商品；"
                "已登记为缺陷 D-02" % (st_off, st_put))

    # E-06 未支付订单登记发货 → M-18
    c, m, pend = make_order("buyer01", 1, 1)
    st, code, msg, data = api("POST", "/api/v1/orders/%s/shipment" % pend, "warehouse01",
                               {"carrier": "SF", "tracking_no": "E18"})
    check("TC-E-08", "未支付订单登记发货被拒 → M-18「只有合法待发货订单可登记发货」（E-06 / F-07）",
          code == "M-18" and order_of(pend)["status"] == "待支付",
          "code=%s msg=%s status=%s" % (code, msg, order_of(pend)["status"]))
    st, code, msg, data = api("POST", "/api/v1/orders/%s/shipment" % pend, "warehouse01",
                               {"carrier": "", "tracking_no": ""})
    check("TC-E-09", "承运方/运单号为空登记发货 → M-23（E-23）",
          code == "M-23", "code=%s msg=%s" % (code, msg))
    cancel(pend, "buyer01")

    # E-24 客服审核不写原因 → M-24
    c, m, ono = make_order("buyer01", 1, 1)
    pay("mock01", ono, "CH-E-001", 10000)
    apply_refund(ono, "buyer01", "申请退款")
    st, code, msg, data = api("POST", "/api/v1/orders/%s/refund/approve" % ono, "cs01", {"remark": ""})
    check("TC-E-10", "客服同意退款未写原因 → M-24「审核退款 / 核实异常必须写明原因」",
          code == "M-24" and order_of(ono)["status"] == "退款审核中",
          "code=%s msg=%s status=%s" % (code, msg, order_of(ono)["status"]))
    st, code, msg, data = api("POST", "/api/v1/orders/%s/refund/reject" % ono, "cs01", {"remark": ""})
    check("TC-E-11", "客服拒绝退款未写原因 → M-24",
          code == "M-24", "code=%s msg=%s" % (code, msg))

    # 客服拒绝分支：拒绝后回到待发货并允许继续发货（R-27 / AC-12）
    st, code, msg, data = api("POST", "/api/v1/orders/%s/refund/reject" % ono, "cs01",
                               {"remark": "商品无质量问题，拒绝退款"})
    check("TC-E-12", "客服拒绝退款并写明原因 → 订单回到待发货（T-07）",
          code == "0" and order_of(ono)["status"] == "待发货",
          "code=%s status=%s" % (code, order_of(ono)["status"]))
    st, code, msg, data = api("POST", "/api/v1/orders/%s/shipment" % ono, "warehouse01",
                               {"carrier": "SF", "tracking_no": "E12"})
    check("TC-E-13", "客服拒绝后允许仓库继续发货（R-27 / AC-12）",
          code == "0" and order_of(ono)["status"] == "已发货",
          "code=%s msg=%s status=%s" % (code, msg, order_of(ono)["status"]))
    st, code, msg, data = api("POST", "/api/v1/orders/%s/shipment" % ono, "warehouse01",
                               {"carrier": "SF", "tracking_no": "E12-REPEAT"})
    check("TC-E-14", "重复登记发货被拒 → M-19，且运单号不变（R-31 / AC-14）",
          code == "M-19" and order_of(ono)["shipment_tracking_no"] == "E12",
          "code=%s msg=%s tracking=%s" % (code, msg, order_of(ono)["shipment_tracking_no"]))
    st, code, msg, data = apply_refund(ono, "buyer01", "已发货后再申请退款")
    check("TC-E-15", "已发货订单申请售前退款被拒 → M-11「已发货订单不受理本题售前退款」（R-32 / F-02）",
          code == "M-11", "code=%s msg=%s" % (code, msg))

    # 待支付订单非法状态流转（改用 goods2，避免与 goods1 的峰值占用冲突）
    c, m, pend2 = make_order("buyer01", 2, 1)
    st, code, msg, data = apply_refund(pend2, "buyer01", "待支付就退")
    check("TC-E-16", "待支付订单申请退款 → M-05「该订单状态不允许此操作」（F-05 / F-07）",
          code == "M-05", "code=%s msg=%s" % (code, msg))
    st, code, msg, data = api("GET", "/api/v1/orders/ORD-NOT-EXIST-888", "ops01")
    check("TC-E-17", "查询未知订单 → M-30「支付通知指向未知订单，订单状态不变」（E-08）",
          code == "M-30", "code=%s msg=%s" % (code, msg))
    st, code, msg, data = api("POST", "/api/v1/late-payment/999999/verify", "cs01", {"reason": "核实未知事件"})
    check("TC-E-18", "核实未知异常事件 → M-14「异常记录不能通过直接修改订单状态消失」（E-13）",
          code == "M-14", "code=%s msg=%s" % (code, msg))
    st, code, msg, data = api("POST", "/api/v1/late-payment/999999/refund/initiate", "cs01",
                               {"refund_no": "X-1", "reason": "未知事件发起退款"})
    check("TC-E-19", "对未知异常事件发起迟到支付退款 → M-14",
          code == "M-14", "code=%s msg=%s" % (code, msg))

    # 超时后取消 → M-06
    c, m, exp = make_order("buyer01", 2, 1)
    set_clock(11)
    st, code, msg, data = cancel(exp, "buyer01")
    set_clock(0)
    check("TC-E-20", "待支付超时后再取消 → M-06「订单已超时关闭…占用已释放」",
          code == "M-06" and order_of(exp)["status"] == "已关闭",
          "code=%s msg=%s status=%s" % (code, msg, order_of(exp)["status"]))

    # 渠道超时通知分支（API-22）
    st, code, msg, data = api("POST", "/api/v1/payment/timeout", "mock01",
                               {"order_no": pend2, "channel_trade_no": "TMO-001", "reason": "模拟渠道通知超时"})
    check("TC-E-21", "模拟渠道超时通知：只登记审计，订单状态不变（E-16）",
          code == "0" and data.get("order_status_unchanged") is True
          and order_of(pend2)["status"] == "待支付",
          "code=%s data=%s" % (code, json.dumps(data, ensure_ascii=False)))
    st, code, msg, data = api("POST", "/api/v1/payment/timeout", "mock01",
                               {"order_no": pend2, "channel_trade_no": "TMO-001", "reason": "重复超时通知"})
    check("TC-E-22", "重复渠道超时通知幂等，不产生第二笔业务结果（F-08）",
          code == "0" and data.get("duplicate") is True,
          "code=%s data=%s" % (code, json.dumps(data, ensure_ascii=False)))

    # 金额整数分
    o = order_of(pend2)
    check("TC-E-23", "订单金额为整数分：total = unit_price × quantity 且为整型（C-01/C-14/A-03）",
          isinstance(o["total_amount"], int) and o["total_amount"] == o["unit_price"] * o["quantity"],
          "order=%s" % json.dumps({k: o[k] for k in ("unit_price", "quantity", "total_amount")}, ensure_ascii=False))

    # 已取消订单的迟到支付 → M-15 文案核对
    c, m, canc = make_order("buyer02", 2, 1)
    cancel(canc, "buyer02")
    _, code, msg, _ = pay("mock01", canc, "CH-E-CANCEL-001", 10000)
    check("TC-E-24", "已取消订单收到支付成功通知 → 不恢复订单（返回 M-15，F-01）",
          code == "M-15" and order_of(canc)["status"] == "已取消",
          "code=%s msg=%s status=%s" % (code, msg, order_of(canc)["status"]))

    cancel(pend2, "buyer01")

    # --- 支付通知三类校验失败（R-14 / R-17 / AC-07） ---
    c, m, paychk = make_order("buyer03", 2, 1)
    st, code, msg, data = pay("mock01", paychk, "CH-E-AMT-001", 9999)
    check("TC-E-25", "金额不符 → M-29，订单状态不变且处理结果可查（AC-07 / E-07）",
          code == "M-29" and order_of(paychk)["status"] == "待支付"
          and (data or {}).get("event_type") == "支付通知处理结果",
          "code=%s msg=%s data=%s" % (code, msg, json.dumps(data, ensure_ascii=False)))
    st, code, msg, data = pay("mock01", paychk, "CH-E-SIG-001", 10000, signature_valid=False)
    check("TC-E-26", "验签失败 → M-28，订单状态不变且处理结果可查（AC-07 / E-09）",
          code == "M-28" and order_of(paychk)["status"] == "待支付"
          and (data or {}).get("event_type") == "支付通知处理结果",
          "code=%s msg=%s data=%s" % (code, msg, json.dumps(data, ensure_ascii=False)))
    st, code, msg, data = pay("mock01", "ORD-NOT-EXIST-777", "CH-E-UNK-001", 10000)
    check("TC-E-27", "未知订单 → M-30，订单状态不变且处理结果可查（AC-07 / E-08）",
          code == "M-30" and (data or {}).get("event_type") == "支付通知处理结果",
          "code=%s msg=%s data=%s" % (code, msg, json.dumps(data, ensure_ascii=False)))
    probes = ["/api/v1/ops/payment-notices", "/api/v1/payment/notices", "/api/v1/ops/payments",
              "/api/v1/ops/notification-results", "/api/v1/payments", "/api/v1/ops/events"]
    probe_res = []
    for p in probes:
        stx, _ = http("GET", p, "cs01")
        probe_res.append((p, stx))
    check("TC-E-28", "支付通知处理结果有只读查询入口（AC-07 / R-17 / 原型 V-08「支付通知处理结果区」）",
          any(stx == 200 for _, stx in probe_res),
          "候选路径返回=%s；全部非 200 表示无此查询入口" % probe_res)
    cancel(paychk, "buyer03")
    return


# ==================================================================================
# 场景 R：权限隔离
# ==================================================================================

def scenario_permissions():
    print("\n================ 场景 R 权限隔离（5 个角色） ================", flush=True)
    # goods2 预置可售 2：pend（待支付，取消释放）+ paid（待发货，末尾退款释放）
    c, m, pend = make_order("buyer01", 2, 1)
    c2, m2, paid = make_order("buyer01", 2, 1)
    pay("mock01", paid, "CH-R-001", 10000)
    check("TC-R-01", "前置：buyer01 持有一笔待支付单与一笔待发货单",
          c == "0" and c2 == "0" and order_of(paid)["status"] == "待发货",
          "pend=%s paid=%s" % (c, c2))

    deny_cases = [
        ("TC-R-02", "买家越权查询他人订单", "GET", "/api/v1/orders/%s" % paid, "buyer02", None),
        ("TC-R-03", "买家越权取消他人待支付订单", "POST", "/api/v1/orders/%s/cancel" % pend, "buyer02", {}),
        ("TC-R-04", "买家越权对他人订单申请退款", "POST", "/api/v1/orders/%s/refund/apply" % paid, "buyer02", {"reason": "越权"}),
        ("TC-R-05", "仓库越权审核同意退款", "POST", "/api/v1/orders/%s/refund/approve" % paid, "warehouse01", {"remark": "越权"}),
        ("TC-R-06", "仓库越权审核拒绝退款", "POST", "/api/v1/orders/%s/refund/reject" % paid, "warehouse01", {"remark": "越权"}),
        ("TC-R-07", "客服越权登记发货", "POST", "/api/v1/orders/%s/shipment" % paid, "cs01", {"carrier": "SF", "tracking_no": "X"}),
        ("TC-R-08", "运营越权创建订单", "POST", "/api/v1/orders", "ops01", {"goods_id": 2, "quantity": 1}),
        ("TC-R-09", "买家越权发起支付通知", "POST", "/api/v1/payment/callback", "buyer01",
         {"order_no": pend, "channel_trade_no": "CH-R-BUYER", "amount": 10000, "signature_valid": True}),
        ("TC-R-10", "客服越权查看运营汇总", "GET", "/api/v1/ops/summary", "cs01", None),
        ("TC-R-11", "买家越权查看运营汇总", "GET", "/api/v1/ops/summary", "buyer01", None),
        ("TC-R-12", "买家越权进行库存逐单核查", "GET", "/api/v1/ops/stock-check/%s" % paid, "buyer01", None),
        ("TC-R-13", "客服越权调整演示时钟", "POST", "/api/v1/admin/clock", "cs01", {"offset_minutes": 5}),
        ("TC-R-14", "买家越权执行超时关单", "POST", "/api/v1/admin/orders/close-expired", "buyer01", {}),
        ("TC-R-15", "买家越权调整商品价格", "POST", "/api/v1/admin/goods/1/price", "buyer01", {"unit_price": 11000, "reason": "越权"}),
        ("TC-R-16", "买家越权处理迟到支付异常", "POST", "/api/v1/late-payment/1/verify", "buyer01", {"reason": "越权"}),
        ("TC-R-17", "买家越权发起迟到支付退款", "POST", "/api/v1/late-payment/1/refund/initiate", "buyer01",
         {"refund_no": "X-R", "reason": "越权"}),
        ("TC-R-18", "买家越权登记发货", "POST", "/api/v1/orders/%s/shipment" % paid, "buyer01",
         {"carrier": "SF", "tracking_no": "X"}),
    ]
    for cid, title, method, path, account, body in deny_cases:
        st, code, msg, data = api(method, path, account, body)
        check(cid, title + " → 明确拒绝 M-20 且不返回他人数据（R-33/R-34/R-37 / AC-16）",
              code == "M-20", "code=%s msg=%s" % (code, msg))

    allow_cases = [
        ("TC-R-19", "买家可查询本人订单（允许）", "GET", "/api/v1/orders/%s" % pend, "buyer01", None, "0"),
        ("TC-R-20", "买家可取消本人待支付订单（允许）", "POST", "/api/v1/orders/%s/cancel" % pend, "buyer01", {}, "0"),
        ("TC-R-21", "运营可查看汇总（允许）", "GET", "/api/v1/ops/summary", "ops01", None, "0"),
        ("TC-R-22", "客服可做库存逐单核查（允许）", "GET", "/api/v1/ops/stock-check/%s" % paid, "cs01", None, "0"),
        ("TC-R-23", "运营可执行超时关单（允许）", "POST", "/api/v1/admin/orders/close-expired", "ops01", {}, "0"),
        ("TC-R-24", "模拟渠道可发起支付通知（允许）", "POST", "/api/v1/payment/callback", "mock01",
         {"order_no": paid, "channel_trade_no": "CH-R-ALLOW", "amount": 10000, "signature_valid": True}, None),
    ]
    for cid, title, method, path, account, body, expect in allow_cases:
        st, code, msg, data = api(method, path, account, body)
        if expect is None:
            check(cid, title + "（不因权限被拒）", not (isinstance(code, str) and code == "M-20"),
                  "code=%s msg=%s" % (code, msg))
        else:
            check(cid, title, code == expect, "code=%s msg=%s" % (code, msg))

    # 仓库角色权限通过但因状态不合法被拒（证明不是 M-20）
    st, code, msg, data = api("POST", "/api/v1/orders/%s/shipment" % paid, "warehouse01",
                               {"carrier": "SF", "tracking_no": "R-OK"})
    check("TC-R-25", "仓库对合法待发货订单登记发货被允许（角色权限校验通过）",
          code == "0" and order_of(paid)["status"] == "已发货",
          "code=%s msg=%s status=%s" % (code, msg, order_of(paid)["status"]))

    # 身份可信性
    # 注意：Python 的 http.client 按 latin-1 编码请求头，伪造身份头一律用 ASCII 值，
    #       以免客户端编码异常干扰被测服务；伪造语义（服务端忽略 X-Role / X-User-Id）不受影响。
    st, code, msg, data = api("GET", "/api/v1/me", "buyer02",
                              extra_headers={"X-User-Id": "1001", "X-Role": "ops", "X-Buyer-Id": "1001"})
    check("TC-R-26", "身份由服务端解析：改 X-User-Id / X-Role 不改变服务端身份（R-33 / AC-16）",
          code == "0" and data["user_id"] == 1002 and data["role"] == "买家",
          "me=%s" % json.dumps(data, ensure_ascii=False))
    st, code, msg, data = api("GET", "/api/v1/orders/%s" % paid, "buyer02",
                              extra_headers={"X-User-Id": "1001", "X-Role": "ops"})
    check("TC-R-27", "改请求中的用户编号不能越权访问他人订单，仍返回 M-20",
          code == "M-20", "code=%s msg=%s" % (code, msg))
    st, payload = http("GET", "/api/v1/me", None, None, {"X-User-Id": "1001"})
    code = payload.get("code") if isinstance(payload, dict) else None
    msg = payload.get("message") if isinstance(payload, dict) else None
    check("TC-R-28", "缺少 X-Demo-Account 的请求被拒绝（PARAM_ERROR），身份不可自报",
          code == "PARAM_ERROR", "code=%s msg=%s" % (code, msg))
    st, payload = http("GET", "/api/v1/me", "hacker", None, {"X-Role": "ops"})
    code = payload.get("code") if isinstance(payload, dict) else None
    msg = payload.get("message") if isinstance(payload, dict) else None
    check("TC-R-29", "未知账号头被拒绝（PARAM_ERROR）",
          code == "PARAM_ERROR", "code=%s msg=%s" % (code, msg))
    return


# ==================================================================================
# 场景 D：数据一致性
# ==================================================================================

def scenario_consistency():
    print("\n================ 场景 D 数据一致性 ================", flush=True)
    g1 = goods(1)
    g2 = goods(2)
    check("TC-D-01", "商品 1 库存两列守恒：可售 + 占用 = 初始 5（R-03/A-10）",
          g1["available_stock"] + g1["occupied_stock"] == 5,
          "goods1=%s" % json.dumps(g1, ensure_ascii=False))
    check("TC-D-02", "商品 2 库存两列守恒：可售 + 占用 = 初始 2",
          g2["available_stock"] + g2["occupied_stock"] == 2,
          "goods2=%s" % json.dumps(g2, ensure_ascii=False))

    s = summary()
    check("TC-D-03", "运营核查能确认「无重复释放、无重复退款」（R-24 / AC-10 / M-17）："
          "被正确拒绝的重复操作不得被计为「发生了重复释放 / 重复退款」",
          s["no_duplicate_release_refund"] is True,
          "no_duplicate_release_refund=%s duplicate_release_noop_events=%s duplicate_refund_events=%s"
          "（本次运行中重复取消 / 重复关闭均被正确拒绝并只留痕、未产生第二笔业务结果）"
          % (s["no_duplicate_release_refund"], s["duplicate_release_noop_events"],
             s["duplicate_refund_events"]))

    # 审计流水与订单状态：不存在改写入口
    st, payload = http("DELETE", "/api/v1/orders/ORD-X", "ops01")
    check("TC-D-04", "不存在删除订单 / 异常记录的入口（DELETE 返回 404/405）",
          st in (404, 405), "http=%s body=%s" % (st, json.dumps(payload, ensure_ascii=False)))
    st, payload = http("POST", "/api/v1/orders/ORD-X/status", "ops01", {"status": "已发货"})
    check("TC-D-05", "不存在直接改写订单状态的接口（POST /orders/{no}/status 返回 404/405）",
          st in (404, 405), "http=%s body=%s" % (st, json.dumps(payload, ensure_ascii=False)))
    st, payload = http("PATCH", "/api/v1/orders/ORD-X", "ops01", {"status": "已发货"}, retries=2)
    check("TC-D-06", "不存在 PATCH 订单接口（返回 404/405）",
          st in (404, 405), "http=%s body=%s" % (st, json.dumps(payload, ensure_ascii=False)))

    # 运营汇总字段完整性（题面规则 8 / AC-02 / AC-18 / A-25 / 原型 V-04）
    required = {
        "已收款合计（分）": ("effective_payment_amount",),
        "已退款合计（分）": ("refunded_amount", "refund_amount", "effective_refund_amount",
                            "total_refund_amount", "refunded_amount_total"),
        "商品可售数量": ("available_stock", "goods_available_stock"),
        "异常记录数": ("anomaly_count", "exception_count", "abnormal_events", "anomaly_events"),
        "待处理数": ("pending_count", "pending_anomaly_count", "pending_exception_count"),
    }
    missing = [label for label, keys in required.items() if not any(k in s for k in keys)]
    check("TC-D-07", "运营汇总包含「已收款、已退款、可售数量、异常记录数、待处理数」（题面规则 8 / AC-02 / AC-18 / A-25 / 原型 V-04）",
          not missing, "缺失字段=%s；实际返回字段=%s" % (missing, sorted(s.keys())))

    # 按订单查询四类记录 / 只读审计流水
    probe_paths = [
        "/api/v1/orders/ORD-X/records", "/api/v1/ops/audit", "/api/v1/ops/records",
        "/api/v1/orders/ORD-X/audit", "/api/v1/payments", "/api/v1/audit",
        "/api/v1/ops/order-records/ORD-X",
    ]
    probes = []
    for p in probe_paths:
        st, _ = http("GET", p, "ops01")
        probes.append((p, st))
    st, code, msg, data = api("GET", "/api/v1/ops/stock-check/%s" % "ORD-PROBE-UNKNOWN", "ops01")
    found_record_api = False
    for p, stt in probes:
        if stt == 200:
            found_record_api = True
    check("TC-D-08", "提供「按订单查询收款/退款/发货/异常记录 + 只读审计流水」的查询接口（R-38 / AC-18 / AC-20 / N-17~N-19 / 原型 V-04 C-05）",
          found_record_api,
          "探测的候选路径及返回=%s；现有逐单只读接口仅 /api/v1/ops/stock-check/{order_no}，"
          "返回字段=%s，不含四类记录与审计流水" % (probes, sorted(data.keys()) if isinstance(data, dict) else []))

    # 异常记录不可通过改写订单状态消除
    s2 = summary()
    check("TC-D-09", "异常记录不能通过改写订单状态消除：迟到支付事件在全部操作后仍可查（R-23 / AC-17）",
          s2["late_payment_events"] >= 1 and s2["late_payment_refunded_events"] >= 1,
          "summary=%s" % json.dumps(s2, ensure_ascii=False))

    # 金额一致性
    s3 = summary()
    check("TC-D-10", "已收款合计为整数分且非负（C-01/A-03）",
          isinstance(s3["effective_payment_amount"], int) and s3["effective_payment_amount"] >= 0,
          "effective_payment_amount=%s" % s3["effective_payment_amount"])
    return


# ==================================================================================
# M-xx 错误码与文案映射
# ==================================================================================

def scenario_m_mapping():
    print("\n================ 场景 M 错误码与文案映射 ================", flush=True)
    bad = []
    for code, msg in sorted(OBSERVED_M.items()):
        expect = M_TABLE.get(code)
        if expect is None:
            bad.append((code, msg, "不在原型 3.3 文案表中"))
        elif msg != expect:
            bad.append((code, msg, expect))
    check("TC-M-01", "顶层业务拒绝码返回的 message 与原型 3.3 文案表逐字一致",
          not bad, "不一致项=%s" % json.dumps(bad, ensure_ascii=False))

    bad_event = []
    for code, reason in sorted(OBSERVED_EVENT_M.items()):
        expect = M_TABLE.get(code)
        if expect is None:
            bad_event.append((code, reason, "不在原型 3.3 文案表中"))
        elif reason != expect:
            bad_event.append((code, reason, expect))
    check("TC-M-04", "事件记录中 failure_code=M-xx 对应的 failure_reason 与原型 3.3 文案表逐字一致",
          not bad_event, "不一致项=%s" % json.dumps(bad_event, ensure_ascii=False))

    check("TC-M-02", "原型 3.3 共定义 30 个 M-xx 文案；本次运行触发到 %d 个不同错误码"
          % len(SEEN_CODES), True, "观察到的错误码=%s" % sorted(SEEN_CODES))
    missing = sorted(set(M_TABLE) - SEEN_CODES)
    info("TC-M-03", "本次黑盒运行未触发到的 M-xx 文案编号", "未触发=%s" % missing)
    info("TC-M-05", "顶层业务拒绝码实际返回文案", json.dumps(OBSERVED_M, ensure_ascii=False))
    info("TC-M-06", "事件记录 failure_code 实际返回文案", json.dumps(OBSERVED_EVENT_M, ensure_ascii=False))
    return missing


# ==================================================================================
# main
# ==================================================================================

def main():
    global BASE_URL
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--no-start", action="store_true")
    ap.add_argument("--port", type=int, default=18099)
    args = ap.parse_args()

    svc = None
    if args.base_url:
        BASE_URL = args.base_url
    if not args.no_start:
        svc = Service(args.port)
        BASE_URL = "http://127.0.0.1:%d" % args.port
        svc.build()
        svc.start()
    else:
        BASE_URL = args.base_url or BASE_URL

    print("\n>>> 服务模式确认:", json.dumps(http("GET", "/health")[1], ensure_ascii=False), flush=True)
    print(">>> 身份确认:", json.dumps(http("GET", "/api/v1/me", "buyer01")[1], ensure_ascii=False), flush=True)

    try:
        scenario_s2()          # 先用未消耗的商品做 20 并发抢单
        scenario_s2_timeout()
        scenario_s1()
        scenario_s3()
        scenario_s4()
        scenario_s5()
        scenario_edges()
        scenario_permissions()
        scenario_consistency()
        scenario_m_mapping()
    finally:
        if svc:
            svc.stop()

    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r[1] == "PASS")
    failed = sum(1 for r in RESULTS if r[1] == "FAIL")
    blocked_n = sum(1 for r in RESULTS if r[1] == "BLOCK")
    infos = sum(1 for r in RESULTS if r[1] == "INFO")
    print("\n================ 黑盒探测测试统计 ================", flush=True)
    print("用例总数: %d" % total, flush=True)
    print("通过:     %d" % passed, flush=True)
    print("失败:     %d" % failed, flush=True)
    print("阻塞:     %d" % blocked_n, flush=True)
    print("信息项:   %d" % infos, flush=True)
    if failed:
        print("\n---- 失败用例明细 ----", flush=True)
        for cid, verdict, title, detail in RESULTS:
            if verdict == "FAIL":
                print("[%s] %s | %s" % (cid, title, detail), flush=True)
    if blocked_n:
        print("\n---- 阻塞用例明细 ----", flush=True)
        for cid, verdict, title, detail in RESULTS:
            if verdict == "BLOCK":
                print("[%s] %s | %s" % (cid, title, detail), flush=True)
    print("\n---- 观察到的 M-xx 错误码与文案 ----", flush=True)
    for code, msg in sorted(OBSERVED_M.items()):
        print("%s = %s" % (code, msg), flush=True)
    print("\n未触发的 M-xx: %s" % sorted(set(M_TABLE) - SEEN_CODES), flush=True)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
