package v1

import (
	"errors"
	"net/http"
	"strconv"
	"strings"

	"github.com/gin-gonic/gin"

	"shop-trade/server/model"
	"shop-trade/server/service"
)

// 竞态检测说明：本 controller 不参与 go test -race 之外的竞态验证；并发安全由 service 事务保证。
// 执行 go test ./... -race 前需开启 CGO：$env:CGO_ENABLED = "1"（PowerShell）或 CGO_ENABLED=1（bash）。

// demoAccounts 是服务端预置账号映射。身份只由 X-Demo-Account 解析，
// 请求里的 X-Role / X-User-Id 一律忽略，改编号不能越权，满足题面「角色身份必须可信」。
var demoAccounts = map[string]service.Actor{
	"buyer01":     {UserID: 1001, Role: service.RoleBuyer},
	"buyer02":     {UserID: 1002, Role: service.RoleBuyer},
	"buyer03":     {UserID: 1003, Role: service.RoleBuyer},
	"ops01":       {UserID: 2001, Role: service.RoleOps},
	"warehouse01": {UserID: 3001, Role: service.RoleWarehouse},
	"cs01":        {UserID: 4001, Role: service.RoleCustomerService},
	"mock01":      {UserID: 5001, Role: service.RoleMockChannel},
}

// GoodsLister 由 initialize 层注入：MySQL 模式读 goods 表，演示模式返回预置商品。
type GoodsLister func() ([]model.Goods, error)

// ClockReader 由 initialize.DemoClock 实现，供运营推进演示教学时钟。
type ClockReader interface {
	OffsetMinutes() int
	SetOffsetMinutes(int)
}

// OrderApi 是 GVA 风格的 controller，只做参数绑定、身份解析与响应封装，业务逻辑全部在 service。
type OrderApi struct {
	svc         *service.OrderService
	goodsLister GoodsLister
	clock       ClockReader
	mode        string
}

func NewOrderApi(svc *service.OrderService, goodsLister GoodsLister, clock ClockReader, mode string) *OrderApi {
	return &OrderApi{svc: svc, goodsLister: goodsLister, clock: clock, mode: mode}
}

type response struct {
	Code    string      `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data"`
}

func ok(c *gin.Context, data interface{}) {
	c.JSON(http.StatusOK, response{Code: "0", Message: "ok", Data: data})
}

func paramError(c *gin.Context, message string) {
	c.JSON(http.StatusBadRequest, response{Code: "PARAM_ERROR", Message: message, Data: nil})
}

// writeErr 把已处理业务拒绝以 M-xx 中文原因返回；技术错误不向客户端泄露内部细节。
// 可选 data 用于携带同事务内已提交的只追加审计记录（例如迟到支付异常事件的 event_id）。
func writeErr(c *gin.Context, err error, data ...interface{}) {
	var payload interface{}
	if len(data) > 0 {
		payload = data[0]
	}
	var bizErr *service.BizError
	if errors.As(err, &bizErr) {
		c.JSON(http.StatusOK, response{Code: bizErr.Code, Message: bizErr.Message, Data: payload})
		return
	}
	c.JSON(http.StatusInternalServerError, response{Code: "INTERNAL_ERROR", Message: "服务内部错误，请稍后重试", Data: nil})
}

func (a *OrderApi) actor(c *gin.Context) (service.Actor, bool) {
	account := strings.TrimSpace(c.GetHeader("X-Demo-Account"))
	actor, exists := demoAccounts[account]
	if !exists {
		paramError(c, "缺少或未知 X-Demo-Account；身份由服务端预置账号解析，X-Role / X-User-Id 不作为身份依据")
		return service.Actor{}, false
	}
	return actor, true
}

func bindJSON(c *gin.Context, req interface{}) bool {
	if err := c.ShouldBindJSON(req); err != nil {
		paramError(c, "请求体不是合法 JSON 或字段类型不正确："+err.Error())
		return false
	}
	return true
}

func boolOrTrue(v *bool) bool {
	if v == nil {
		return true
	}
	return *v
}

func parseUintParam(c *gin.Context, name string) (uint64, bool) {
	v, err := strconv.ParseUint(c.Param(name), 10, 64)
	if err != nil {
		paramError(c, name+" 必须是正整数")
		return 0, false
	}
	return v, true
}

// Me 返回服务端解析出的身份，用于验证改请求用户编号不能越权。
func (a *OrderApi) Me(c *gin.Context) {
	actor, valid := a.actor(c)
	if !valid {
		return
	}
	ok(c, gin.H{
		"account": strings.TrimSpace(c.GetHeader("X-Demo-Account")),
		"user_id": actor.UserID,
		"role":    actor.Role,
		"mode":    a.mode,
	})
}

// ListGoods 返回商品列表（金额单位为分）。
func (a *OrderApi) ListGoods(c *gin.Context) {
	if _, valid := a.actor(c); !valid {
		return
	}
	goods, err := a.goodsLister()
	if err != nil {
		writeErr(c, err)
		return
	}
	ok(c, gin.H{"items": goodsViews(goods), "count": len(goods)})
}

type createOrderReq struct {
	GoodsID  uint64 `json:"goods_id"`
	Quantity int    `json:"quantity"`
}

// CreateOrder POST /api/v1/orders
func (a *OrderApi) CreateOrder(c *gin.Context) {
	actor, valid := a.actor(c)
	if !valid {
		return
	}
	var req createOrderReq
	if !bindJSON(c, &req) {
		return
	}
	order, err := a.svc.CreateOrder(c.Request.Context(), actor, req.GoodsID, req.Quantity)
	if err != nil {
		writeErr(c, err)
		return
	}
	ok(c, orderView(order))
}

// GetOrder GET /api/v1/orders/{order_no}
func (a *OrderApi) GetOrder(c *gin.Context) {
	actor, valid := a.actor(c)
	if !valid {
		return
	}
	order, err := a.svc.GetOrder(c.Request.Context(), actor, c.Param("order_no"))
	if err != nil {
		writeErr(c, err)
		return
	}
	ok(c, orderView(order))
}

// GetOrderStatus GET /api/v1/orders/{order_no}/status
func (a *OrderApi) GetOrderStatus(c *gin.Context) {
	actor, valid := a.actor(c)
	if !valid {
		return
	}
	order, err := a.svc.GetOrder(c.Request.Context(), actor, c.Param("order_no"))
	if err != nil {
		writeErr(c, err)
		return
	}
	terminal := map[string]bool{
		service.StatusCancelled: true,
		service.StatusClosed:    true,
		service.StatusRefunded:  true,
		service.StatusShipped:   true,
	}[order.Status]
	ok(c, gin.H{
		"order_no":             order.OrderNo,
		"status":               order.Status,
		"is_terminal":          terminal,
		"total_amount":         order.TotalAmount,
		"expires_at":           order.ExpiresAt,
		"refund_state":         order.RefundState,
		"shipment_tracking_no": order.ShipmentTrackingNo,
	})
}

// CancelOrder POST /api/v1/orders/{order_no}/cancel
func (a *OrderApi) CancelOrder(c *gin.Context) {
	actor, valid := a.actor(c)
	if !valid {
		return
	}
	order, err := a.svc.CancelOrder(c.Request.Context(), actor, c.Param("order_no"))
	if err != nil {
		writeErr(c, err)
		return
	}
	ok(c, orderView(order))
}

type paymentCallbackReq struct {
	OrderNo        string `json:"order_no"`
	ChannelTradeNo string `json:"channel_trade_no"`
	Amount         int64  `json:"amount"`
	SignatureValid *bool  `json:"signature_valid"`
}

// HandlePaymentCallback POST /api/v1/payment/callback
// 该接口即可控 HTTP 模拟支付渠道通知入口：signature_valid=false / amount 不符 / 未知订单 / 重复交易号均可触发。
func (a *OrderApi) HandlePaymentCallback(c *gin.Context) {
	actor, valid := a.actor(c)
	if !valid {
		return
	}
	var req paymentCallbackReq
	if !bindJSON(c, &req) {
		return
	}
	p, err := a.svc.HandlePaymentCallback(c.Request.Context(), actor, service.PaymentCallback{
		OrderNo:        req.OrderNo,
		ChannelTradeNo: req.ChannelTradeNo,
		Amount:         req.Amount,
		SignatureValid: boolOrTrue(req.SignatureValid),
	})
	if err != nil {
		writeErr(c, err, paymentView(p))
		return
	}
	ok(c, paymentView(p))
}

type closeExpiredReq struct {
	Limit int `json:"limit"`
}

// CloseExpiredOrders POST /api/v1/admin/orders/close-expired
func (a *OrderApi) CloseExpiredOrders(c *gin.Context) {
	actor, valid := a.actor(c)
	if !valid {
		return
	}
	var req closeExpiredReq
	if c.Request.ContentLength != 0 {
		if err := c.ShouldBindJSON(&req); err != nil {
			paramError(c, "请求体不是合法 JSON："+err.Error())
			return
		}
	}
	limit := req.Limit
	if limit <= 0 {
		limit = 100
	}
	closed, err := a.svc.CloseExpiredOrders(c.Request.Context(), actor, limit)
	if err != nil {
		writeErr(c, err)
		return
	}
	ok(c, gin.H{"closed_count": closed, "clock_offset_minutes": a.clock.OffsetMinutes()})
}

type reasonReq struct {
	Reason string `json:"reason"`
}

// ApplyRefund POST /api/v1/orders/{order_no}/refund/apply
func (a *OrderApi) ApplyRefund(c *gin.Context) {
	actor, valid := a.actor(c)
	if !valid {
		return
	}
	var req reasonReq
	if !bindJSON(c, &req) {
		return
	}
	order, err := a.svc.ApplyRefund(c.Request.Context(), actor, c.Param("order_no"), req.Reason)
	if err != nil {
		writeErr(c, err)
		return
	}
	ok(c, orderView(order))
}

type remarkReq struct {
	Remark string `json:"remark"`
}

// RejectRefund POST /api/v1/orders/{order_no}/refund/reject
func (a *OrderApi) RejectRefund(c *gin.Context) {
	actor, valid := a.actor(c)
	if !valid {
		return
	}
	var req remarkReq
	if !bindJSON(c, &req) {
		return
	}
	order, err := a.svc.RejectRefund(c.Request.Context(), actor, c.Param("order_no"), req.Remark)
	if err != nil {
		writeErr(c, err)
		return
	}
	ok(c, orderView(order))
}

// ApproveRefund POST /api/v1/orders/{order_no}/refund/approve
func (a *OrderApi) ApproveRefund(c *gin.Context) {
	actor, valid := a.actor(c)
	if !valid {
		return
	}
	var req remarkReq
	if !bindJSON(c, &req) {
		return
	}
	order, err := a.svc.ApproveRefund(c.Request.Context(), actor, c.Param("order_no"), req.Remark)
	if err != nil {
		writeErr(c, err)
		return
	}
	ok(c, orderView(order))
}

// RetryRefund POST /api/v1/orders/{order_no}/refund/retry
func (a *OrderApi) RetryRefund(c *gin.Context) {
	actor, valid := a.actor(c)
	if !valid {
		return
	}
	var req remarkReq
	if !bindJSON(c, &req) {
		return
	}
	order, err := a.svc.RetryRefund(c.Request.Context(), actor, c.Param("order_no"), req.Remark)
	if err != nil {
		writeErr(c, err)
		return
	}
	ok(c, orderView(order))
}

type refundCallbackReq struct {
	OrderNo              string `json:"order_no"`
	RefundChannelTradeNo string `json:"refund_channel_trade_no"`
	Amount               int64  `json:"amount"`
	SignatureValid       *bool  `json:"signature_valid"`
	Success              *bool  `json:"success"`
}

// HandleRefundCallback POST /api/v1/refund/callback
func (a *OrderApi) HandleRefundCallback(c *gin.Context) {
	actor, valid := a.actor(c)
	if !valid {
		return
	}
	var req refundCallbackReq
	if !bindJSON(c, &req) {
		return
	}
	p, err := a.svc.HandleRefundCallback(c.Request.Context(), actor, service.RefundCallback{
		OrderNo:              req.OrderNo,
		RefundChannelTradeNo: req.RefundChannelTradeNo,
		Amount:               req.Amount,
		SignatureValid:       boolOrTrue(req.SignatureValid),
		Success:              boolOrTrue(req.Success),
	})
	if err != nil {
		writeErr(c, err, paymentView(p))
		return
	}
	ok(c, paymentView(p))
}

type shipmentReq struct {
	Carrier    string `json:"carrier"`
	TrackingNo string `json:"tracking_no"`
}

// RegisterShipment POST /api/v1/orders/{order_no}/shipment
func (a *OrderApi) RegisterShipment(c *gin.Context) {
	actor, valid := a.actor(c)
	if !valid {
		return
	}
	var req shipmentReq
	if !bindJSON(c, &req) {
		return
	}
	p, err := a.svc.RegisterShipment(c.Request.Context(), actor, c.Param("order_no"), req.Carrier, req.TrackingNo)
	if err != nil {
		writeErr(c, err, paymentView(p))
		return
	}
	ok(c, paymentView(p))
}

// VerifyLatePayment POST /api/v1/late-payment/{event_id}/verify
func (a *OrderApi) VerifyLatePayment(c *gin.Context) {
	actor, valid := a.actor(c)
	if !valid {
		return
	}
	eventID, valid := parseUintParam(c, "event_id")
	if !valid {
		return
	}
	var req reasonReq
	if !bindJSON(c, &req) {
		return
	}
	p, err := a.svc.VerifyLatePayment(c.Request.Context(), actor, eventID, req.Reason)
	if err != nil {
		writeErr(c, err, paymentView(p))
		return
	}
	ok(c, paymentView(p))
}

type initiateLateRefundReq struct {
	RefundNo string `json:"refund_no"`
	Reason   string `json:"reason"`
}

// InitiateLatePaymentRefund POST /api/v1/late-payment/{event_id}/refund/initiate
func (a *OrderApi) InitiateLatePaymentRefund(c *gin.Context) {
	actor, valid := a.actor(c)
	if !valid {
		return
	}
	eventID, valid := parseUintParam(c, "event_id")
	if !valid {
		return
	}
	var req initiateLateRefundReq
	if !bindJSON(c, &req) {
		return
	}
	p, err := a.svc.InitiateLatePaymentRefund(c.Request.Context(), actor, eventID, req.RefundNo, req.Reason)
	if err != nil {
		writeErr(c, err, paymentView(p))
		return
	}
	ok(c, paymentView(p))
}

type lateRefundCallbackReq struct {
	EventID        uint64 `json:"event_id"`
	RefundNo       string `json:"refund_no"`
	Amount         int64  `json:"amount"`
	SignatureValid *bool  `json:"signature_valid"`
	Success        *bool  `json:"success"`
}

// HandleLatePaymentRefundCallback POST /api/v1/late-payment/refund/callback
func (a *OrderApi) HandleLatePaymentRefundCallback(c *gin.Context) {
	actor, valid := a.actor(c)
	if !valid {
		return
	}
	var req lateRefundCallbackReq
	if !bindJSON(c, &req) {
		return
	}
	p, err := a.svc.HandleLatePaymentRefundCallback(c.Request.Context(), actor, service.LateRefundCallback{
		EventID:        req.EventID,
		RefundNo:       req.RefundNo,
		Amount:         req.Amount,
		SignatureValid: boolOrTrue(req.SignatureValid),
		Success:        boolOrTrue(req.Success),
	})
	if err != nil {
		writeErr(c, err, paymentView(p))
		return
	}
	ok(c, paymentView(p))
}

type lateRefundRetryReq struct {
	EventID  uint64 `json:"event_id"`
	RefundNo string `json:"refund_no"`
	Remark   string `json:"remark"`
}

// RetryLatePaymentRefund POST /api/v1/late-payment/refund/retry
func (a *OrderApi) RetryLatePaymentRefund(c *gin.Context) {
	actor, valid := a.actor(c)
	if !valid {
		return
	}
	var req lateRefundRetryReq
	if !bindJSON(c, &req) {
		return
	}
	p, err := a.svc.RetryLatePaymentRefund(c.Request.Context(), actor, req.EventID, req.RefundNo, req.Remark)
	if err != nil {
		writeErr(c, err, paymentView(p))
		return
	}
	ok(c, paymentView(p))
}

// GetOpsSummary GET /api/v1/ops/summary
func (a *OrderApi) GetOpsSummary(c *gin.Context) {
	actor, valid := a.actor(c)
	if !valid {
		return
	}
	summary, err := a.svc.GetOpsSummary(c.Request.Context(), actor)
	if err != nil {
		writeErr(c, err)
		return
	}
	ok(c, summaryView(summary))
}

// GetClock GET /api/v1/admin/clock
func (a *OrderApi) GetClock(c *gin.Context) {
	_, valid := a.actor(c)
	if !valid {
		return
	}
	ok(c, gin.H{
		"mode":                 a.mode,
		"clock_offset_minutes": a.clock.OffsetMinutes(),
		"server_time":          a.svc.ServerTimeForDisplay(),
	})
}

type clockReq struct {
	OffsetMinutes int `json:"offset_minutes"`
}

// SetClock POST /api/v1/admin/clock：仅演示模式 + 运营角色可推进服务端时间。
// 10 分钟超时业务规则不变，只是把服务端时间整体平移，测试与线上演示规则一致。
func (a *OrderApi) SetClock(c *gin.Context) {
	actor, valid := a.actor(c)
	if !valid {
		return
	}
	if actor.Role != service.RoleOps {
		writeErr(c, &service.BizError{Code: "M-20", Message: "无权限 / 越权：只有运营可调整演示时钟"})
		return
	}
	if a.mode != "demo-memory" {
		paramError(c, "演示教学时钟仅在 demo-memory 模式可用，MySQL 模式请使用真实时间")
		return
	}
	var req clockReq
	if !bindJSON(c, &req) {
		return
	}
	if req.OffsetMinutes < 0 || req.OffsetMinutes > 1440 {
		paramError(c, "offset_minutes 必须在 0~1440 之间")
		return
	}
	a.clock.SetOffsetMinutes(req.OffsetMinutes)
	ok(c, gin.H{"clock_offset_minutes": req.OffsetMinutes, "server_time": a.svc.ServerTimeForDisplay()})
}
