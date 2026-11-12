# shop-trade 接口清单草案（待学生确认）

> 来源：本轮问答「授权按 service 推导」。本文件不是已定稿接口设计，不生成 API/Router 代码。路径、方法、请求体、响应体、鉴权头均为新增假设，正式 Apipost 第 2 轮与浏览器第 3 轮前须由学生确认。

## 通用约定（假设）

- Base URL：`{{base_url}}`。
- 角色由服务端上下文解析；本草案以 `X-Role`、`X-User-Id` 表示，不代表真实鉴权实现。
- 金额一律整数「分」。
- 所有失败 / 拒绝返回中文原因与 `M-xx` 编号，不返回空结果、不写死成功。
- 模拟支付渠道入口：`{{mock_channel_base_url}}/trigger`，仅用于可控 HTTP 模拟服务，不得宣称为真实第三方接入成果。

| 编号 | 方法 | 路径 | service 方法 | 允许角色 | 主要请求字段 | 主要响应字段 | 典型 M-xx |
| --- | --- | --- | --- | --- | --- | --- | --- |
| API-01 | POST | `/api/v1/orders` | `CreateOrder` | 买家 | `goods_id`、`quantity` | `order_no`、`status=待支付`、`total_amount`、`expires_at` | M-01~M-04、M-20 |
| API-02 | GET | `/api/v1/orders/{order_no}` | `GetOrder` | 买家/运营/仓库/客服 | 路径 `order_no` | 订单详情 | M-20 |
| API-03 | POST | `/api/v1/orders/{order_no}/cancel` | `CancelOrder` | 买家 | 路径 `order_no` | 取消/关闭结果 | M-05、M-06、M-10、M-20 |
| API-04 | POST | `/api/v1/payment/callback` | `HandlePaymentCallback` | 模拟渠道/运营 | `order_no`、`channel_trade_no`、`amount`、`signature_valid` | 支付处理结果 | M-09、M-10、M-25、M-27~M-30 |
| API-05 | POST | `/api/v1/admin/orders/close-expired` | `CloseExpiredOrders` | 运营 | `limit` | `closed_count` | M-06、M-10、M-20 |
| API-06 | POST | `/api/v1/orders/{order_no}/refund/apply` | `ApplyRefund` | 买家 | `reason` | 退款申请结果 | M-05、M-10、M-11、M-20 |
| API-07 | POST | `/api/v1/orders/{order_no}/refund/reject` | `RejectRefund` | 客服 | `remark` | 审核结果 | M-05、M-10、M-24 |
| API-08 | POST | `/api/v1/orders/{order_no}/refund/approve` | `ApproveRefund` | 客服 | `remark` | 审核结果 | M-05、M-10、M-24 |
| API-09 | POST | `/api/v1/orders/{order_no}/refund/retry` | `RetryRefund` | 客服 | `remark` | 重试登记结果 | M-05、M-08、M-16、M-24 |
| API-10 | POST | `/api/v1/refund/callback` | `HandleRefundCallback` | 模拟渠道/运营 | `order_no`、`refund_channel_trade_no`、`amount`、`success`、`signature_valid` | 退款回调结果 | M-08、M-10、M-16、M-25、M-27~M-30 |
| API-11 | POST | `/api/v1/orders/{order_no}/shipment` | `RegisterShipment` | 仓库 | `carrier`、`tracking_no` | 发货结果 | M-07、M-10、M-18、M-19、M-22、M-23 |
| API-12 | POST | `/api/v1/late-payment/{event_id}/verify` | `VerifyLatePayment` | 客服 | `reason` | 核实记录 | M-14、M-24、M-20 |
| API-13 | POST | `/api/v1/late-payment/{event_id}/refund/initiate` | `InitiateLatePaymentRefund` | 客服 | `refund_no`、`reason` | 迟到支付退款请求 | M-09、M-10、M-24、M-26 |
| API-14 | POST | `/api/v1/late-payment/refund/callback` | `HandleLatePaymentRefundCallback` | 模拟渠道/运营 | `event_id`、`refund_no`、`amount`、`success`、`signature_valid` | 迟到支付退款回调结果 | M-08、M-10、M-16、M-25~M-30 |
| API-15 | POST | `/api/v1/late-payment/refund/retry` | `RetryLatePaymentRefund` | 客服 | `event_id`、`refund_no`、`remark` | 重试登记结果 | M-08、M-16、M-24、M-26 |
| API-16 | GET | `/api/v1/ops/summary` | `GetOpsSummary` | 运营 | 无 | 订单、收款、异常、退款、发货、重复释放/重复退款汇总 | M-13、M-14、M-17、M-20 |

> 禁止项：购物车、一单多商品、部分退款、售后退货、真实支付渠道、真实物流、多商户、题外功能。
