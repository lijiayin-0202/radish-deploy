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

---

## 附录 A：逐接口测试契约（第四轮补齐）

> 本附录补齐 `API-01~API-23` 每个接口的**前置条件、后置断言、异常 case、边界入参示例**。
> 成功路径的真实单条输出见 `evidence/smoke/API-XX.txt`；异常路径的真实逐条输出见 `evidence/manual/*-异常场景手工测试记录.md`。
> 「边界入参示例」是契约样例；未标注「已实测」的条目尚未执行，不得写成运行结果。所有案例均在 `demo-memory` 模式执行，不代表真实 MySQL / CI / race 证据。

| 接口 | 前置条件 | 后置断言 | 异常 case | 边界入参示例（空 / 超长 / 越权 / 负数） |
| --- | --- | --- | --- | --- |
| API-01 | `X-Demo-Account` 为买家；商品在售；可售 ≥ quantity | `code=0`、`status=待支付`、`total_amount=unit_price×quantity`；可用库存扣减、占用增加；写一条预扣只追加审计 | M-01 商品不存在/下架、M-02 缺货、M-03 数量越界、M-04 goods_id=0、M-20 越权、PARAM_ERROR 参数绑定失败 | `goods_id=0`（M-04，已实测）；`quantity=0/3/-2`（M-03，已实测）；`goods_id=-1`（已实测）；`goods_id=999999999999999999`（已实测）；`ops01` 下单（M-20，已实测）；空 goods_id（已实测） |
| API-02 | 已解析身份；`order_no` 存在；买家仅可查本人订单 | `code=0` 且返回订单详情；金额快照与下单时一致 | M-20 越权、M-30 未知订单、PARAM_ERROR 空/超长单号 | 超长 `order_no`（300 字符）；`X-Demo-Account=buyer02` 查 buyer01 单（M-20，见 `TST-S5-07`） |
| API-03 | 订单属于当前买家且为待支付 | `code=0`；库存释放一次；写释放审计；订单变已取消 | M-05 订单不存在、M-06 状态不允许、M-10 重复取消、M-20 越权 | 重复取消（M-10，见 `TST-S2-03`，已实测）；空单号；负数单号；他人订单越权 |
| API-04 | `mock01`/运营；`channel_trade_no` 唯一；`amount` 与订单金额一致；`signature_valid=true` | 成功通知 `code=0`、订单转待发货；重复通知幂等不重复记款；迟到支付返回 M-09 且 `data.event_id` 可用 | M-09 迟到支付、M-25/M-27 重复/冲突、M-28 验签失败、M-29 金额不符、M-30 未知订单 | `amount=-1`；`signature_valid=false`（M-28，已实测）；超长交易号；`channel_trade_no` 空；同号重复通知（幂等，已实测） |
| API-05 | `ops01`；服务端时间已越过 `expires_at` | `code=0`、`closed_count` 准确；终态已关闭且释放库存；重复关单不二次释放 | M-06/M-10 重复关闭、M-20 越权、PARAM_ERROR `limit` 非法 | `limit=0/-1`；`limit` 超长数值；`buyer01` 调用（M-20） |
| API-06 | 买家本人订单、已支付且未发货 | `code=0`；订单进入退款申请；发货接口随后返回 M-22 | M-05 订单不存在、M-10 重复、M-11 状态不允许、M-20 越权、M-24 reason 缺失 | `reason` 空/超长 600 字符（已实测）；他人订单越权 |
| API-07 | 客服；退款申请待审核；`remark` 必填 | `code=0`；审核结论与原因写入只追加审计；发货可恢复 | M-05/M-10/M-24/M-20 | `remark` 空（M-24）；超长 remark；买家越权 |
| API-08 | 客服；退款申请待审核；`remark` 必填 | `code=0`；进入待渠道退款；期间发货 M-22 | M-05/M-10/M-24/M-20 | `remark` 空（M-24，已实测）；超长 remark；买家越权（M-20，已实测） |
| API-09 | 客服；渠道首次失败且保留待处理 | `code=0`；写重试登记，不重复退款 | M-08 渠道失败待处理、M-16 无可重试记录、M-24/M-20 | `remark` 空；超长；无失败记录时重试 |
| API-10 | `mock01`；`refund_channel_trade_no` 唯一；金额匹配 | `success=true` 时 `code=0`、订单已退款、库存恢复一次；`success=false` 返回 M-08 且保留待处理；重复通知幂等 | M-08/M-10/M-16/M-25/M-27/M-28/M-29/M-30 | `amount=-1`（已实测）；`signature_valid=false`（M-28，已实测）；同号重复通知（幂等，已实测）；超长交易号 |
| API-11 | 仓库；订单待发货且无退款申请；`carrier`/`tracking_no` 必填 | `code=0`；登记一次；重复返回 M-19；退款申请期间返回 M-22 | M-07/M-10/M-18/M-19/M-22/M-23/M-20 | `carrier` 空；`tracking_no` 超长；重复登记（M-19，已实测）；买家越权 |
| API-12 | 客服；`event_id` 为迟到支付异常记录 | `code=0`；写核实记录与原因，异常记录不消失 | M-14 事件不存在、M-24 reason 缺失、M-10 重复核实、M-20 越权 | `event_id=0/-1`；超长 reason；买家越权 |
| API-13 | 客服；异常已核实；`refund_no` 唯一 | `code=0`；生成迟到支付退款请求；订单终态不变 | M-09/M-10/M-24/M-26/M-20 | `refund_no` 空/超长；重复发起 |
| API-14 | `mock01`；`event_id`+`refund_no` 匹配 | `success=true` 时 `code=0` 且终态仍为已关闭；失败返回 M-08；重复通知幂等 | M-08/M-10/M-16/M-25~M-30 | `amount=-1`；`signature_valid=false`；重复通知；超长单号 |
| API-15 | 客服；迟到支付退款渠道失败待处理 | `code=0`；写重试登记，不二次恢复库存 | M-08/M-16/M-24/M-26/M-20 | `remark` 空；超长；无失败记录 |
| API-16 | `ops01` | `code=0`；订单/收款/异常/退款/发货/重复释放与重复退款汇总可核 | M-13/M-14/M-17/M-20 | `buyer01` 调用（M-20）；空身份 |
| API-17 | 同 API-02 | 返回 `status`、`is_terminal`、`total_amount`、`expires_at`、`refund_state`、`shipment_tracking_no` | M-20/M-30 | 空单号；超长单号；越权 |
| API-18 | 任一已解析身份 | `code=0`、`count` 与 `items` 一致；调价后显示新单价 | PARAM_ERROR 仓储失败 | 无入参；`X-Demo-Account` 未知身份 |
| API-19 | 任一已解析身份 | `account`/`user_id`/`role`/`mode` 全部由服务端映射；忽略 `X-Role`/`X-User-Id` | PARAM_ERROR 身份不可解析 | 伪造 `X-Role=运营`；伪造 `X-User-Id=2001`（见 `TST-S5-08`，已实测） |
| API-20 | GET 任一已解析身份；POST 仅 `ops01` | GET 返回 `mode`/`clock_offset_minutes`/`server_time`；POST `offset_minutes` 在 0~1440 | M-20 越权设置、PARAM_ERROR 越界 | `offset_minutes=-1/1441`；超长数值；买家 POST（M-20） |
| API-21 | `ops01`；`unit_price` 为正整数分；商品存在 | `code=0`；`old/new_unit_price`、`hint=M-12`、`constraint=M-13`、`audit_event_id`；**已有订单金额快照不变** | M-20 越权、PARAM_ERROR 价格/商品非法 | `unit_price=0/-100`（已实测）；`999999999999999999`（已实测）；`goods_id=999999`（已实测）；`buyer01` 调用（M-20，已实测）；`reason` 600 字符（已实测） |
| API-22 | `mock01`/运营；`channel_trade_no` 非空且唯一；订单存在 | `code=0`；`order_status_unchanged=true`；只登记只追加审计；重复 `duplicate=true`；**不改状态/库存** | M-30 未知订单、M-20 越权、PARAM_ERROR 空/超长 | 空交易号（已实测）；300 字符交易号（已实测）；未知订单（M-30，已实测）；买家越权（M-20，已实测）；同号重复（幂等，已实测） |
| API-23 | `ops01`/`cs01`；订单存在 | `code=0`；`expected/actual_restore_times`、`available/occupied_stock`、`consistent`、`conclusion`；只读 | M-17/M-26 不一致结论、M-20 越权、PARAM_ERROR 订单不存在 | 不存在订单（已实测）；300 字符单号（已实测）；`buyer01`（M-20，已实测）；未知身份（已实测）；`cs01` 合法只读（已实测） |

### A.1 逐接口 / 逐页面独立证据索引

| 类型 | 证据路径 |
| --- | --- |
| 接口成功路径 | `evidence/smoke/API-01.txt` ~ `evidence/smoke/API-23.txt`（每个接口单独一条，含请求、入参、真实响应与断言） |
| 健康检查 | `evidence/smoke/HEALTH.txt` |
| 静态页面 | `evidence/smoke/PAGE-index.txt`、`PAGE-V01.txt` ~ `PAGE-V08.txt` |
| 页面截图说明与访问断言 | `evidence/html-check/V01-*.md` ~ `V08-*.md`（如实注明未生成浏览器截图） |
| Skill 文件级冒烟 | `evidence/smoke/SKILL-*.txt` |
| 异常场景手工记录 | `evidence/manual/*-异常场景手工测试记录.md`（5 类共 30 条，逐条真实响应） |
| 采集脚本与原始输出 | `scripts/r4_evidence_suite.py`、`evidence/r4-suite-output.txt` |

---

## 附录 B：全量接口 × 边界维度矩阵（第五轮补齐）

> **维度定义**：`参数边界`（空 / 超长 / 负数 / 越界）、`状态边界`（各订单状态与库存水位下的合法结果）、
> `权限边界`（越权访问与角色隔离）、`幂等边界`（重复通知 / 重复操作不产生第二笔业务结果）、
> `并发边界`（共享并发访问下的唯一合法结果）。
>
> **标记口径**：`实测` = 仓库内已有**真实执行记录**并给出证据路径；`契约` = 附录 A 的契约样例，
> **尚未执行**，不得写成运行结果；`环境缺失` = 需要真实 MySQL(InnoDB) 行锁、`CGO_ENABLED=1` 的 race 探针
> 或独立测试/验收会话，当前**不可复现**，如实登记。
>
> **执行环境口径**：所有 `实测` 记录均在 `demo-memory` 模式执行，**不代表真实 MySQL / race / CI / 独立会话证据**。

### B.1 逐接口边界矩阵

| 接口 | 参数边界 | 状态边界 | 权限边界 | 幂等 / 重复边界 | 并发边界 | 本轮（第五轮）新增证据 |
| --- | --- | --- | --- | --- | --- | --- |
| API-01 下单 | 实测：空 `goods_id`→PARAM_ERROR；负数→PARAM_ERROR；`quantity=0/3/-2`→M-03；超长 `goods_id`→M-01；不存在商品→M-01 | 实测：`quantity=2` 合法上限成功；可售不足→M-02；可售耗尽→M-02；取消释放后可再下单 | 实测：`ops01` 下单→M-20 | 契约：同参重复下单各自成单（无幂等键） | 实测：20 并发成功 5 + M-02 15 = 20，库存守恒；真实 InnoDB 行锁=环境缺失 | `evidence/manual-round2/下单…md`（6 条）、`evidence/partial-closure/R-A2-03.md` |
| API-02 订单详情 | 契约：空 / 超长 `order_no` → PARAM_ERROR | 实测：服务重启后查同单→M-30（内存模式无持久化） | 契约：M-20 越权查他人订单 | 不适用（只读） | 不适用（只读） | `evidence/partial-closure/R-A2-01.md` |
| API-03 取消弃单 | 契约：空 / 负数单号 → PARAM_ERROR | 实测：待支付取消成功并释放库存；库存恢复后可直接再下单 | 契约：M-20 越权取消 | 实测（第一批/第四轮）：重复取消→M-10，库存只释放一次 | 环境缺失：与支付回调并发的行锁裁决未在真实 InnoDB 下执行 | `evidence/manual-round2/下单…md`（1 条） |
| API-04 支付通知 | 实测：`signature_valid=false`→M-28；`amount` 不符→M-29 | 实测：正常通知→待发货；迟到支付→M-09 并返回 `data.event_id`；未知订单→M-30 | 契约：非渠道角色调用→M-20 | 实测：同一 `channel_trade_no` 重复通知幂等（`duplicate=true`）；跨订单复用同号→M-27 | 环境缺失：并发重复通知的 MySQL 唯一键冲突未实测 | `evidence/partial-closure/R-A2-04.md` |
| API-05 超时关单 | 契约：`limit=0/-1`、超长数值 → PARAM_ERROR | 实测：服务端时间越过 `expires_at` 后关闭并释放库存；重复关单不二次释放 | 实测：`buyer01` 调用→M-20 | 实测：重复关单不二次释放 | 环境缺失：与下单并发的行锁裁决未在真实 InnoDB 下执行 | `evidence/partial-closure/R-A2-03.md` |
| API-06 申请退款 | 实测：`reason` 超长 600 字符→M-05；不存在订单→M-05 | 实测：待支付→M-05；已取消→M-05；审核中重复申请→M-10；已发货→M-11；已退款再申请→M-11 | 实测：买家越权审核→M-20 | 实测：审核中重复申请→M-10，不产生第二笔退款 | 契约：与发货并发→M-22（单测覆盖，真实行锁未执行） | `evidence/manual-round2/退款…md`（5 条） |
| API-07 退款拒绝 | 契约：`remark` 空 / 超长 → M-24 | 实测：待审核订单拒绝成功；拒绝后可恢复发货 | 实测：买家越权→M-20 | 契约：重复拒绝→M-10 | 不适用 | `evidence/smoke/API-07.txt` |
| API-08 退款同意 | 实测：`remark` 缺失→M-24 | 实测：待审核订单同意→待渠道退款；期间发货→M-22 | 实测：买家越权→M-20 | 契约：重复同意→M-10 | 不适用 | `evidence/smoke/API-08.txt` |
| API-09 退款重试 | 契约：`remark` 空 / 超长、无失败记录时重试 → M-16 / M-24 | 实测：渠道首次失败后登记重试成功；重试不重复退款 | 契约：非客服角色→M-20 | 实测：重试只写登记，不产生第二笔退款 | 不适用 | `evidence/smoke/API-09.txt` |
| API-10 退款通知 | 实测：`signature_valid=false`→M-28；`amount` 不符→M-29 | 实测：`success=true`→已退款并恢复一次库存；`success=false`→M-08 保留待处理 | 契约：非渠道角色→M-20 | 实测：同一 `refund_channel_trade_no` 重复成功/重复失败通知均幂等 | 环境缺失：并发重复退款的唯一键冲突未实测 | `evidence/partial-closure/R-A2-04.md` |
| API-11 登记发货 | 契约：`carrier` 空、`tracking_no` 超长 → M-23 | 实测：仅待发货可登记；退款审核中发货→M-07 / M-22；已发货→M-19 | 实测：买家越权→M-20 | 实测：重复登记发货→M-19 | 契约：与退款并发→M-22（单测覆盖，真实行锁未执行） | `evidence/smoke/API-11.txt` |
| API-12 核实迟到支付 | 契约：`event_id=0/-1`、超长 `reason` → M-14 / M-24 | 实测：核实成功并写原因；核实不改变订单终态（仍已关闭） | 契约：买家越权→M-20 | 契约：重复核实→M-10 | 不适用 | `evidence/smoke/API-12.txt` |
| API-13 发起迟到支付退款 | 契约：`refund_no` 空 / 超长 → M-24；重复发起→M-10 | 实测：发起成功；订单终态不变、不二次恢复库存 | 契约：买家越权→M-20 | 契约：重复发起→M-10 | 不适用 | `evidence/smoke/API-13.txt` |
| API-14 迟到支付退款通知 | 契约：`amount=-1`、验签失败、超长单号 → M-28 / M-29 | 实测：成功→已退款且订单仍为已关闭终态；失败→M-08 | 契约：非渠道角色→M-20 | 实测：重复成功 / 重复失败通知均幂等 | 环境缺失：并发唯一键冲突未实测 | `server/service/r5_edge2_test.go` |
| API-15 迟到支付退款重试 | 契约：`remark` 空 / 超长、无失败记录 → M-16 / M-24 | 实测：渠道失败后登记重试成功；不二次恢复已释放数量 | 契约：买家越权→M-20 | 实测：重试不重复退款 | 不适用 | `server/service/r5_edge2_test.go` |
| API-16 运营汇总 | 无入参 | 契约：M-13 / M-14 异常记录只追加不改写 | 实测：`buyer01` 调用→M-20 | 不适用 | 不适用 | `evidence/smoke/API-16.txt` |
| API-17 订单状态 | 契约：空 / 超长单号 → PARAM_ERROR | 实测：返回 `status` / `is_terminal` / `expires_at`；迟到支付后仍为已关闭终态 | 契约：M-20 越权 | 不适用 | 不适用 | `evidence/manual-round2/超时通知…md` |
| API-18 商品列表 | 无入参 | 实测：调价后 `unit_price` 立即反映新价；可售 / 占用随下单变化 | 实测：未知身份→PARAM_ERROR | 不适用 | 实测：并发下单后商品快照守恒 | `evidence/manual-round2/下单…md`、`evidence/manual-round2/调价…md` |
| API-19 身份解析 | 无入参 | 实测：7 个预置账号返回固定 `role` / `user_id` | 实测：伪造 `X-Role` / `X-User-Id` 一律忽略；未知账号→PARAM_ERROR | 不适用 | 不适用 | `evidence/partial-closure/R-A2-02.md` |
| API-20 演示教学时钟 | 实测：`offset_minutes` 越界 → PARAM_ERROR | 实测：推进后 10 分钟规则生效，订单可被超时关闭 | 实测：买家 POST→M-20 | 不适用 | 不适用 | `evidence/smoke/API-20.txt` |
| API-21 商品调价 | 实测：`unit_price=0/-100`、超长数值 → PARAM_ERROR；`goods_id=999999` → PARAM_ERROR；`reason` 超长 600 字符→成功；`reason` 为空→成功 | 实测：调价后新下单按新价；**调价前已存在订单金额快照不变（M-12）** | 实测：买家越权→M-20 | 实测：重复调价到同一价格成功，审计只追加 | 不适用 | `evidence/manual-round2/调价…md`（6 条） |
| API-22 渠道超时通知 | 实测：空 `channel_trade_no`、300 字符交易号 → PARAM_ERROR | 实测：已支付订单通知后状态不变；已取消订单通知后终态不被改写 | 实测：买家越权→M-20 | 实测：同一交易号重复通知→`duplicate=true`；同一订单另一交易号独立登记 | 不适用 | `evidence/manual-round2/超时通知…md`（5 条） |
| API-23 库存恢复逐单核查 | 实测：不存在订单号、300 字符单号 → PARAM_ERROR | 实测：待支付 / `quantity=2` / 已发货 → 期望恢复 0 次；已退款 → 期望恢复 1 次且 `consistent=true`；核查后可售数与后续下单结果一致 | 实测：买家越权→M-20；未知身份→M-20；`cs01` 合法只读 | 实测：重复退款通知不产生第二条库存恢复事件 | 不适用 | `evidence/manual-round2/库存恢复逐单核查…md`（5 条） |

### B.2 矩阵统计与仍存缺口

| 维度 | 覆盖情况 |
| --- | --- |
| 参数边界 | API-01 / 04 / 06 / 08 / 10 / 21 / 22 / 23 已有真实实测样本（第一批 30 条）；其余接口的空 / 超长 / 负数条目为附录 A 契约样例，**尚未执行** |
| 状态边界 | 第五轮新增第二批 28 条真实样本，覆盖待支付 / 待发货 / 退款审核中 / 退款处理中 / 已退款 / 已取消 / 已关闭 / 已发货八态与库存水位边界 |
| 权限边界 | API-01 / 04 / 06 / 08 / 11 / 16 / 19 / 21 / 22 / 23 已有真实越权样本（M-20 / PARAM_ERROR） |
| 幂等边界 | API-03 / 04 / 06 / 10 / 11 / 14 / 22 已有真实重复样本；API-07 / 08 / 09 / 12 / 13 / 15 的重复条目仍为契约样例 |
| 并发边界 | 仅 API-01 / API-18 有内存模式下的真实并发样本（20 并发守恒）；**真实 InnoDB 行锁与 `go test -race` 全部为环境缺失**，见 `evidence/partial-closure/R-A2-03.md` 与 `R-A2-04.md` |
| 仍存缺口 | ① 真实 MySQL(InnoDB) 实例与重启后查询实测；② `CGO_ENABLED=1` 的 race 探针；③ 唯一键冲突的真实报错样本；④ 独立测试 / 验收 Agent 会话产物；⑤ Apipost 正式运行导出 |

### B.3 本附录的证据索引

| 类型 | 证据路径 |
| --- | --- |
| 第一批参数级异常（30 条） | `evidence/manual/*-异常场景手工测试记录.md` |
| 第二批状态级异常（28 条） | `evidence/manual-round2/*.md`（下单 7 / 退款 5 / 调价 6 / 超时通知 5 / 库存核查 5） |
| 接口成功路径（单条） | `evidence/smoke/API-01.txt` ~ `evidence/smoke/API-23.txt` |
| 页面契约断言 | `evidence/html-check/V01-*.md` ~ `V08-*.md`（A1~A12） |
| partial 闭环核查 | `evidence/partial-closure/R-A2-01.md` ~ `R-B2-02.md`（11 份） |
| 单元测试 | `server/service/r4_edge_test.go`、`server/service/r5_edge_test.go`、`server/service/r5_edge2_test.go` |
| 采集脚本 | `scripts/r4_evidence_suite.py`、`scripts/r5_partial_closure.py`、`scripts/r5_partial_closure2.py`、`scripts/r5_manual2.py`、`scripts/r5_htmlcheck_enhance.py` |
