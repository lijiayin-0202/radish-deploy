package service

import (
	"context"
	"errors"
	"fmt"
	"time"

	"shop-trade/server/model"
)

// ErrDuplicateDedupKey 表示唯一幂等键冲突。该错误必须触发事务回滚，
// 再由 service 外层追加一条只追加审计记录并返回明确 M-xx 原因。
var ErrDuplicateDedupKey = errors.New("duplicate dedup key")

const (
	RoleBuyer           = "买家"
	RoleOps             = "运营"
	RoleWarehouse       = "仓库"
	RoleCustomerService = "客服"
	RoleMockChannel     = "模拟渠道"

	GoodsStatusOnSale = "在售"

	StatusPendingPayment   = "待支付"
	StatusCancelled        = "已取消"
	StatusClosed           = "已关闭"
	StatusWaitingShipment  = "待发货"
	StatusRefundReview     = "退款审核中"
	StatusRefundProcessing = "退款处理中"
	StatusRefunded         = "已退款"
	StatusShipped          = "已发货"

	RefundKindNone    = "未申请"
	RefundKindPresale = "正常售前退款"
	RefundKindLate    = "迟到支付退款"

	RefundStateNone     = "未申请"
	RefundStatePending  = "待处理"
	RefundStateFailed   = "渠道失败待处理"
	RefundStateSuccess  = "成功"
	RefundStateRejected = "已拒绝"

	EventCreateOrder         = "下单成功"
	EventCancel              = "买家取消"
	EventCloseExpired        = "超时关单"
	EventStockRelease        = "库存释放"
	EventStockRestore        = "售前退款恢复库存"
	EventPaymentSuccess      = "支付成功"
	EventRepeatPayment       = "重复支付通知"
	EventLatePayment         = "迟到支付"
	EventLatePaymentVerified = "异常支付已核实"
	EventLateRefundRequest   = "迟到支付退款请求"
	EventLateRefundSuccess   = "迟到支付退款成功"
	EventLateRefundFailed    = "迟到支付退款失败"
	EventLateRefundRetry     = "迟到支付退款重试"
	EventRefundApply         = "退款申请"
	EventRefundApproved      = "退款审核同意"
	EventRefundRejected      = "退款审核拒绝"
	EventRefundRetry         = "退款重试"
	EventRefundSuccess       = "退款成功通知"
	EventRefundFailed        = "退款失败通知"
	EventRepeatRefund        = "重复退款通知"
	EventShipment            = "发货登记"
	EventPermissionDenied    = "权限拒绝"
	EventPaymentConflict     = "渠道交易号冲突"

	ResultStockPreDeducted    = "库存预扣成功"
	ResultStockReleased       = "预扣已释放"
	ResultStockRestored       = "可售数量已恢复一次"
	ResultPaid                = "已记款"
	ResultRepeatPaymentNoop   = "重复支付通知已幂等处理，未重复记款"
	ResultLatePaymentPending  = "异常支付待处理"
	ResultLatePaymentVerified = "异常支付已核实"
	ResultLateRefundRequested = "迟到支付退款请求已登记"
	ResultLateRefundSucceeded = "迟到支付退款成功，未二次恢复库存"
	ResultLateRefundFailed    = "迟到支付退款失败待处理"
	ResultLateRefundRetried   = "迟到支付退款重试已登记"
	ResultRefundApplied       = "退款申请已受理，发货暂停"
	ResultRefundApproved      = "退款审核同意，待模拟渠道处理"
	ResultRefundRejected      = "退款审核拒绝，恢复可发货"
	ResultRefundRetried       = "退款重试已登记"
	ResultRefundSucceeded     = "退款成功"
	ResultRefundFailedPending = "退款失败待处理"
	ResultRepeatRefundNoop    = "重复退款通知已幂等处理，未重复退款"
	ResultShipmentRegistered  = "发货登记成功"
	ResultDuplicateNoop       = "重复操作未产生第二笔业务结果"
	ResultRejected            = "已拒绝"
	ResultCancelled           = "订单已取消，预扣已释放一次"
	ResultClosed              = "订单已关闭，预扣已释放一次"

	DedupPayPrefix            = "PAY:"
	DedupRefundOKPrefix       = "REFUND_OK:"
	DedupRefundFailPrefix     = "REFUND_FAIL:"
	DedupLateRefundOKPrefix   = "LATE_REFUND_OK:"
	DedupLateRefundFailPrefix = "LATE_REFUND_FAIL:"
	DedupLateRefundReqPrefix  = "LATE_REFUND_REQ:"
	DedupShipmentPrefix       = "SHIP:"
)

var messages = map[string]string{
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

// BizError 是已处理的业务拒绝。Commit=true 表示事务内的只追加审计记录需要提交，
// 但 service 仍向调用方返回中文 M-xx 原因。
type BizError struct {
	Code    string
	Message string
	Commit  bool
}

func (e *BizError) Error() string {
	if e.Message == "" {
		return e.Code
	}
	return fmt.Sprintf("%s: %s", e.Code, e.Message)
}

func fail(code string) error {
	return &BizError{Code: code, Message: messages[code], Commit: true}
}

func failWithDetail(code, detail string) error {
	msg := messages[code]
	if detail != "" {
		msg = fmt.Sprintf("%s；%s", msg, detail)
	}
	return &BizError{Code: code, Message: msg, Commit: true}
}

func isTerminal(status string) bool {
	switch status {
	case StatusCancelled, StatusClosed, StatusRefunded, StatusShipped:
		return true
	default:
		return false
	}
}

func contains(values []string, target string) bool {
	for _, v := range values {
		if v == target {
			return true
		}
	}
	return false
}

func boolPtr(v bool) *bool       { return &v }
func stringPtr(v string) *string { return &v }

// Actor 由 API 层从服务端身份上下文解析后传入；service 不信任客户端自报身份。
type Actor struct {
	UserID uint64
	Role   string
}

type PaymentCallback struct {
	OrderNo        string
	ChannelTradeNo string
	Amount         int64
	SignatureValid bool
}

type RefundCallback struct {
	OrderNo              string
	RefundChannelTradeNo string
	Amount               int64
	SignatureValid       bool
	Success              bool
}

type LateRefundCallback struct {
	EventID        uint64
	RefundNo       string
	Amount         int64
	SignatureValid bool
	Success        bool
}

type OpsSummary struct {
	TotalOrders                int64
	EffectivePaymentAmount     int64
	LatePaymentEvents          int64
	LatePaymentRefundedEvents  int64
	RefundedOrders             int64
	ShippedOrders              int64
	StockRestoredEvents        int64
	DuplicateReleaseNoopEvents int64
	DuplicateRefundEvents      int64
	NoDuplicateReleaseRefund   bool
}

// OrderRepository 把 GORM 数据访问封装在 service 包内，便于 service 单测覆盖。
// 生产实现使用 MySQL(InnoDB) 事务 + 行锁；测试草案使用内存仓储，不作为正式并发证据。
type OrderRepository interface {
	WithTransaction(ctx context.Context, fn func(OrderRepository) error) error
	LockGoods(ctx context.Context, goodsID uint64) (*model.Goods, error)
	DecreaseGoodsStock(ctx context.Context, goodsID uint64, quantity int) (bool, error)
	IncreaseGoodsStock(ctx context.Context, goodsID uint64, quantity int) (bool, error)
	LockOrder(ctx context.Context, orderNo string) (*model.Order, error)
	LockOrderByID(ctx context.Context, orderID uint64) (*model.Order, error)
	GetOrder(ctx context.Context, orderNo string) (*model.Order, error)
	CreateOrder(ctx context.Context, order *model.Order) error
	UpdateOrderIfStatus(ctx context.Context, order *model.Order, allowed []string, fields map[string]interface{}) (int64, error)
	UpdateOrderIfStatusAndStockNotRestored(ctx context.Context, order *model.Order, allowed []string, fields map[string]interface{}) (int64, error)
	ListExpiredPendingOrders(ctx context.Context, now time.Time, limit int) ([]model.Order, error)
	GetPaymentByDedupKey(ctx context.Context, dedupKey string) (*model.Payment, error)
	GetPaymentByID(ctx context.Context, eventID uint64) (*model.Payment, error)
	HasPaymentEvent(ctx context.Context, relatedEventID uint64, eventType string) (bool, error)
	CreatePayment(ctx context.Context, payment *model.Payment) error
	CountOrders(ctx context.Context) (int64, error)
	CountOrdersByStatus(ctx context.Context, status string) (int64, error)
	CountPaymentsByEventType(ctx context.Context, eventType string) (int64, error)
	CountPaymentsByResult(ctx context.Context, result string) (int64, error)
	SumEffectivePaymentsByEventType(ctx context.Context, eventType string) (int64, error)
}
