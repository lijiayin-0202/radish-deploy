# shop-trade 接口清单 v1.0（定稿）

> 状态：**已定稿并与实现一致**。本文件取代 `docs/interface-list-draft.md` 草案（草案保留为历史版本，不再作为用例依据）。
> 对齐依据：题目 01 八条业务规则、需求文档 `AC-01~AC-25`、原型设计文档 `V-01~V-08` 与 `M-01~M-30`、任务规划 `TST-S1~S5`。
> 实现落点：`main.go`、`server/initialize/router.go`、`server/router/order.go`、`server/api/v1/order.go`、`server/api/v1/views.go`。
> 业务逻辑全部在 `server/service/`，controller 只做参数绑定、身份解析与响应封装。
> 增量版本：**v1.1**（见第 6 节）。`API-01~API-20` 的路径、方法与字段保持不变，v1.0 定稿内容与 Apipost 48 用例继续有效。

## 1. 通用约定（定稿）

| 项 | 约定 |
| --- | --- |
| Base URL | `http://127.0.0.1:8080`；可用 `GVA_ADDR` 覆盖 |
| 运行模式 | 配置 `GVA_MYSQL_DSN` 时为 `mysql-innodb`（InnoDB 事务 + 行锁，持久化）；未配置时为 `demo-memory`（内存仓储，可启动但不持久化） |
| 健康检查 | `GET /health` → `{"status":"ok","mode":"..."}` |
| 身份 | 请求头 `X-Demo-Account`，服务端映射预置账号 → `{user_id, role}`；`X-Role` / `X-User-Id` **一律忽略**，改请求中的用户编号不能越权 |
| 预置账号 | `buyer01`(1001/买家)、`buyer02`(1002/买家)、`buyer03`(1003/买家)、`ops01`(2001/运营)、`warehouse01`(3001/仓库)、`cs01`(4001/客服)、`mock01`(5001/模拟渠道) |
| 统一响应 | `{"code":"0","message":"ok","data":{...}}`；业务拒绝为 `code=M-xx` + 中文 `message`（HTTP 200，便于渠道回调不再重推）；参数错误 HTTP 400 `PARAM_ERROR`；技术错误 HTTP 500 `INTERNAL_ERROR` |
| 金额 | 一律整数「分」；一单一种商品、数量 1 或 2 |
| 字段风格 | 响应统一 snake_case（controller `views.go` 转换，model 层不改） |
| 模拟渠道 | `POST /api/v1/payment/callback`、`POST /api/v1/refund/callback`、`POST /api/v1/late-payment/refund/callback` 即可控通知入口；用 `signature_valid` / `success` / `amount` / `channel_trade_no` 触发成功、失败、验签失败、金额不符、未知订单、重复通知。不得宣称为真实第三方接入成果 |
| 迟到支付事件 ID | `POST /api/v1/payment/callback` 返回 `M-09` 时，响应 `data.event_id` 即异常支付待处理记录 ID，供客服核实与发起退款 |
| 演示教学时钟 | `POST /api/v1/admin/clock`（仅 `demo-memory` + 运营）整体平移服务端时间；**10 分钟超时业务规则不变**，测试与线上演示规则一致 |
| 失败原因 | 一律引用 `M-01~M-30` 中文文案，不返回空结果、不写死成功 |

## 2. 接口表（API-01~API-20）

| 编号 | 方法 | 路径 | service 方法 | 允许角色 / 账号 | 主要请求字段 | 主要响应字段 | 典型 M-xx | 对应视图 / 验收 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| API-01 | POST | `/api/v1/orders` | `CreateOrder` | 买家 / `buyer01` | `goods_id`、`quantity` | `order_no`、`status=待支付`、`total_amount`、`expires_at` | M-01~M-04、M-20 | V-01 / AC-02 |
| API-02 | GET | `/api/v1/orders/{order_no}` | `GetOrder` | 买家/运营/仓库/客服 | 路径 `order_no` | 订单详情 | M-20 | V-02 / AC-16 |
| API-03 | POST | `/api/v1/orders/{order_no}/cancel` | `CancelOrder` | 买家 | 路径 `order_no` | 取消/关闭结果 | M-05、M-06、M-10、M-20 | V-02 / AC-09 |
| API-04 | POST | `/api/v1/payment/callback` | `HandlePaymentCallback` | 模拟渠道/运营 / `mock01` | `order_no`、`channel_trade_no`、`amount`、`signature_valid` | 支付处理结果；迟到支付含 `event_id` | M-09、M-10、M-25、M-27~M-30 | V-04 / AC-06~08、AC-10 |
| API-05 | POST | `/api/v1/admin/orders/close-expired` | `CloseExpiredOrders` | 运营 / `ops01` | `limit`（可选，默认 100） | `closed_count`、`clock_offset_minutes` | M-06、M-10、M-20 | V-04 / AC-09 |
| API-06 | POST | `/api/v1/orders/{order_no}/refund/apply` | `ApplyRefund` | 买家 | `reason` | 退款申请结果 | M-05、M-10、M-11、M-20 | V-02 / AC-11 |
| API-07 | POST | `/api/v1/orders/{order_no}/refund/reject` | `RejectRefund` | 客服 / `cs01` | `remark`（必填） | 审核结果 | M-05、M-10、M-24 | V-07 / AC-12 |
| API-08 | POST | `/api/v1/orders/{order_no}/refund/approve` | `ApproveRefund` | 客服 | `remark`（必填） | 审核结果 | M-05、M-10、M-24 | V-07 / AC-11 |
| API-09 | POST | `/api/v1/orders/{order_no}/refund/retry` | `RetryRefund` | 客服 | `remark`（必填） | 重试登记结果 | M-05、M-08、M-16、M-24 | V-07 / AC-11 |
| API-10 | POST | `/api/v1/refund/callback` | `HandleRefundCallback` | 模拟渠道/运营 / `mock01` | `order_no`、`refund_channel_trade_no`、`amount`、`success`、`signature_valid` | 退款回调结果 | M-08、M-10、M-16、M-25、M-27~M-30 | V-07 / AC-11、AC-13 |
| API-11 | POST | `/api/v1/orders/{order_no}/shipment` | `RegisterShipment` | 仓库 / `warehouse01` | `carrier`、`tracking_no` | 发货结果 | M-07、M-10、M-18、M-19、M-22、M-23 | V-06 / AC-02、AC-14 |
| API-12 | POST | `/api/v1/late-payment/{event_id}/verify` | `VerifyLatePayment` | 客服 | `reason`（必填） | 核实记录 | M-14、M-24、M-20 | V-08 / AC-10 |
| API-13 | POST | `/api/v1/late-payment/{event_id}/refund/initiate` | `InitiateLatePaymentRefund` | 客服 | `refund_no`、`reason` | 迟到支付退款请求 | M-09、M-10、M-24、M-26 | V-08 / AC-10 |
| API-14 | POST | `/api/v1/late-payment/refund/callback` | `HandleLatePaymentRefundCallback` | 模拟渠道/运营 / `mock01` | `event_id`、`refund_no`、`amount`、`success`、`signature_valid` | 迟到支付退款回调结果 | M-08、M-10、M-16、M-25~M-30 | V-08 / AC-10 |
| API-15 | POST | `/api/v1/late-payment/refund/retry` | `RetryLatePaymentRefund` | 客服 | `event_id`、`refund_no`、`remark` | 重试登记结果 | M-08、M-16、M-24、M-26 | V-08 / AC-10 |
| API-16 | GET | `/api/v1/ops/summary` | `GetOpsSummary` | 运营 | 无 | 订单、收款、异常、退款、发货、重复释放/重复退款汇总 | M-13、M-14、M-17、M-20 | V-04 / AC-18 |
| API-17 | GET | `/api/v1/orders/{order_no}/status` | `GetOrder` | 同 API-02 | 路径 `order_no` | `order_no`、`status`、`is_terminal`、`total_amount`、`expires_at`、`refund_state`、`shipment_tracking_no` | M-20 | V-02 / AC-09 |
| API-18 | GET | `/api/v1/goods` | 注入的 `GoodsLister` | 全部已解析身份 | 无 | `items`（`goods_no`、`unit_price`、`available_stock`、`occupied_stock`、`status`）、`count` | PARAM_ERROR | V-01 / AC-02 |
| API-19 | GET | `/api/v1/me` | controller 身份解析 | 全部已解析身份 | 无 | `account`、`user_id`、`role`、`mode` | PARAM_ERROR | AC-16 |
| API-20 | GET / POST | `/api/v1/admin/clock` | `ServerTimeForDisplay` / `DemoClock` | 全部查询；仅运营可设置 | POST：`offset_minutes`（0~1440） | `mode`、`clock_offset_minutes`、`server_time` | M-20、PARAM_ERROR | AC-25（演示教学时钟一致） |

## 3. 五组强制演示场景 → 接口序列

| 场景 | 接口序列 | 收尾核查 |
| --- | --- | --- |
| `TST-S1` 活动正常成交 | API-01 → API-04 → API-17 → API-11 → API-11（重复应 M-19） | API-16 |
| `TST-S2` 缺货与弃单 / 并发库存 | API-01×20（并发由 Apipost 或 `go test -race` 执行）→ API-03 → API-03（重复应 M-10）→ API-05（演示时钟 +11 分钟触发关闭） | API-16、库存守恒 |
| `TST-S3` 售前退款 | API-01 → API-04 → API-06 → API-11（应 M-22）→ API-08 → API-10(success=false，应 M-08) → API-09 → API-10(success=true) → API-10（重复幂等） | API-17、API-16 |
| `TST-S4` 迟到支付 | API-01 → API-20 → API-05 → API-04（应 M-09，取 `event_id`）→ API-16 → API-12 → API-13 → API-14(success=false) → API-15 → API-14(success=true) | API-17（仍为已关闭）、API-16 |
| `TST-S5` 操作竞争 | API-01 → API-04 → API-04（重复应幂等）→ API-04(验签失败/金额不符/未知订单)→ API-06 与 API-11 并发 → API-02（越权 M-20，篡改编号仍 M-20） | API-16 |

可复现脚本：`scripts/demo-five-scenarios.ps1`（HTTP 演示，非第 2 轮正式证据）。

## 4. 运行方式

```powershell
# 演示模式（内存，可直接启动）
go run main.go
# 或编译出可执行二进制
go build -o shop-trade.exe .
# 持久化模式（MySQL InnoDB，先用 schema.sql 初始化）
$env:GVA_MYSQL_DSN = "<从环境变量注入，不写入仓库>"
go run main.go
```

## 5. 禁止项

购物车、一单多商品、部分退款、售后退货、签收与售后物流、多商户、真实支付渠道、真实物流、促销优惠、完整财务系统；直接改写订单状态消除异常、删除业务记录、人工调账、重复退款/发货。

## 6. v1.1 增量接口（代码产物补齐批次）

> `API-01~API-20` 的路径、方法、请求与响应字段**全部不变**；第 3 节五组场景序列与已重建的 Apipost 48 用例继续有效。
> 本节只登记第二轮门禁复核报告「① 代码 / 产物缺陷」整改新增的 3 个接口，不改下单、退款主业务。

| 编号 | 方法 | 路径 | service 方法 | 允许角色 / 账号 | 主要请求字段 | 主要响应字段 | 典型 M-xx | 对应视图 / 验收 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| API-21 | POST | `/api/v1/admin/goods/{goods_id}/price` | `ExtensionService.UpdateGoodsPrice` | 运营 / `ops01` | `unit_price`（正整数分）、`reason` | `old_unit_price`、`new_unit_price`、`hint=M-12`、`constraint=M-13`、`audit_event_id` | M-20、PARAM_ERROR | V-03 / R-A1-02 |
| API-22 | POST | `/api/v1/payment/timeout` | `ExtensionService.HandleChannelTimeout` | 模拟渠道 / 运营 | `order_no`、`channel_trade_no`、`reason` | `event_id`、`order_status`、`duplicate`、`order_status_unchanged=true` | M-30、M-20 | V-08 / R-A1-04 |
| API-23 | GET | `/api/v1/ops/stock-check/{order_no}` | `ExtensionService.VerifyStockRestoration` | 运营 / 客服 | 路径 `order_no` | `expected_restore_times`、`actual_restore_times`、`available_stock`、`occupied_stock`、`consistent`、`conclusion` | M-17、M-26、M-20 | V-04 / V-07 / R-A1-07 |

### 6.1 静态页面（非接口）

| 路径 | 视图 | 用途 |
| --- | --- | --- |
| `GET /` / `GET /static/index.html` | 首页 | 八视图导航、运行方式与证据边界说明 |
| `GET /static/v01-goods.html` | V-01 商品浏览（买家） | 查看商品单价、可售/占用库存并下单 |
| `GET /static/v02-orders.html` | V-02 我的订单（买家） | 按 `order_no` 查看订单、状态、金额快照与取消 |
| `GET /static/v03-goods-admin.html` | V-03 商品管理（运营） | 查看库存与调用 API-21 调价 |
| `GET /static/v04-ops-summary.html` | V-04 运营核查（运营） | 汇总、库存与 API-23 逐单核查 |
| `GET /static/v05-shipment-list.html` | V-05 待发货（仓库） | 按订单号核对状态与库存 |
| `GET /static/v06-shipment-form.html` | V-06 发货录入（仓库） | 承运方 / 运单号登记 |
| `GET /static/v07-refund-review.html` | V-07 退款审核（客服） | 同意 / 拒绝 / 重试、渠道通知、库存核查 |
| `GET /static/v08-late-payment.html` | V-08 迟到支付异常（客服） | 异常核实、退款发起、API-22 超时通知 |

静态资源由 `engine.Static("/static", "resource/static")` 提供，纯 HTML + 原生 JS（`app.css` / `app.js`），不引入 Vue 或前端构建。

### 6.2 增量边界

- API-22 只登记只追加审计，**不关单、不释放库存、不改订单状态**；10 分钟超时关单仍由服务端时间经 API-05 触发；重复通知按 `TIMEOUT:` dedup key 幂等。
- API-23 只读，不修改订单与库存；「缓存恢复」按报告 `R-A1-07` 的「售前退款库存恢复逐单核查」口径实现，**不引入缓存组件**。
- 不新增 `M-xx` 失败原因编号、不扩展 8 状态状态机、不改动 `OrderRepository` 接口与 `order_service.go`。
- 静态页面与 CI 注释模板只是代码产物；第 3 轮浏览器验收、CI 运行与部署仍属过程/环境证据，不得冒充。
