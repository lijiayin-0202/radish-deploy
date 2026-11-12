package router

import (
	"github.com/gin-gonic/gin"

	"shop-trade/server/api/v1"
)

// OrderRouter 按 GVA 原生方式把 controller 方法注册到 /api/v1 路由组。
type OrderRouter struct{}

func (OrderRouter) InitOrderRouter(r *gin.RouterGroup, api *v1.OrderApi) {
	// 身份、商品与演示时钟（辅助演示，不含题外业务）
	r.GET("/me", api.Me)
	r.GET("/goods", api.ListGoods)
	r.GET("/admin/clock", api.GetClock)
	r.POST("/admin/clock", api.SetClock)

	// 商品与下单、订单查询、状态查询、取消
	r.POST("/orders", api.CreateOrder)
	r.GET("/orders/:order_no", api.GetOrder)
	r.GET("/orders/:order_no/status", api.GetOrderStatus)
	r.POST("/orders/:order_no/cancel", api.CancelOrder)

	// 模拟支付渠道通知与超时关单
	r.POST("/payment/callback", api.HandlePaymentCallback)
	r.POST("/admin/orders/close-expired", api.CloseExpiredOrders)

	// 售前整单退款：申请、审核、重试、渠道回调
	r.POST("/orders/:order_no/refund/apply", api.ApplyRefund)
	r.POST("/orders/:order_no/refund/reject", api.RejectRefund)
	r.POST("/orders/:order_no/refund/approve", api.ApproveRefund)
	r.POST("/orders/:order_no/refund/retry", api.RetryRefund)
	r.POST("/refund/callback", api.HandleRefundCallback)

	// 发货登记
	r.POST("/orders/:order_no/shipment", api.RegisterShipment)

	// 迟到支付异常：核实、发起退款、渠道回调、重试
	r.POST("/late-payment/:event_id/verify", api.VerifyLatePayment)
	r.POST("/late-payment/:event_id/refund/initiate", api.InitiateLatePaymentRefund)
	r.POST("/late-payment/refund/callback", api.HandleLatePaymentRefundCallback)
	r.POST("/late-payment/refund/retry", api.RetryLatePaymentRefund)

	// 运营核查
	r.GET("/ops/summary", api.GetOpsSummary)
}
