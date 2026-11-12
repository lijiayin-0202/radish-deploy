package service

import (
	"context"
	"errors"
	"fmt"
	"sync/atomic"
	"time"

	"shop-trade/server/global"
	"shop-trade/server/model"
)

const (
	eventPaymentRejected        = "支付通知处理结果"
	eventRefundCallbackRejected = "退款通知处理结果"
	eventLateRefundCallback     = "迟到支付退款通知处理结果"
)

// OrderService 是题目 01 全部业务逻辑的唯一落点。
// 生产仓储使用 MySQL(InnoDB) 事务 + 行锁；所有状态变更、库存变化、收退款与审计事件在同一事务提交。
type OrderService struct {
	repo    OrderRepository
	now     func() time.Time
	timeout time.Duration
	seq     uint64
}

func NewOrderService(repo OrderRepository) *OrderService {
	return &OrderService{repo: repo, now: time.Now, timeout: 10 * time.Minute}
}

func NewDefaultOrderService() *OrderService {
	return NewOrderService(NewGormOrderRepository(global.GVA_DB))
}

func (s *OrderService) nextSeq() uint64 {
	return atomic.AddUint64(&s.seq, 1)
}

func (s *OrderService) newPayment(
	orderID uint64,
	orderNo string,
	channelTradeNo string,
	dedupKey string,
	eventType string,
	result string,
	failureCode string,
	reason string,
	statusSnapshot string,
	amount int64,
	signatureValid bool,
	effectiveResult bool,
	needRefund bool,
	restoredStock bool,
	relatedEventID uint64,
	operatorID uint64,
) *model.Payment {
	if channelTradeNo == "" {
		channelTradeNo = "EVENT:" + eventType
	}
	if reason == "" && failureCode != "" {
		reason = messages[failureCode]
	}
	p := &model.Payment{
		OrderID:             orderID,
		OrderNo:             orderNo,
		ChannelTradeNo:      channelTradeNo,
		EventType:           eventType,
		Result:              result,
		Amount:              amount,
		SignatureValid:      signatureValid,
		FailureCode:         failureCode,
		FailureReason:       reason,
		OrderStatusSnapshot: statusSnapshot,
		NeedRefund:          needRefund,
		RestoredStock:       restoredStock,
		RelatedEventID:      relatedEventID,
		OperatorID:          operatorID,
		OccurredAt:          s.now(),
	}
	if dedupKey != "" {
		p.DedupKey = stringPtr(dedupKey)
	}
	if effectiveResult {
		p.Effective = boolPtr(true)
	}
	return p
}

func (s *OrderService) requireRole(ctx context.Context, actor Actor, operation, orderNo string, allowed ...string) error {
	if actor.UserID == 0 || !contains(allowed, actor.Role) {
		return s.denyAndLog(ctx, actor, operation, orderNo)
	}
	return nil
}

func (s *OrderService) denyAndLog(ctx context.Context, actor Actor, operation, orderNo string) error {
	p := s.newPayment(0, orderNo, "AUTH:"+operation, "", EventPermissionDenied, ResultRejected, "M-20", operation, "", 0, true, false, false, false, 0, actor.UserID)
	if err := s.repo.CreatePayment(ctx, p); err != nil {
		return err
	}
	return fail("M-20")
}

func (s *OrderService) denyAndLogTx(ctx context.Context, tx OrderRepository, actor Actor, operation, orderNo string) error {
	p := s.newPayment(0, orderNo, "AUTH:"+operation, "", EventPermissionDenied, ResultRejected, "M-20", operation, "", 0, true, false, false, false, 0, actor.UserID)
	if err := tx.CreatePayment(ctx, p); err != nil {
		return err
	}
	return fail("M-20")
}

func (s *OrderService) assertBuyerOwnerTx(ctx context.Context, tx OrderRepository, actor Actor, operation string, order *model.Order) error {
	if order.BuyerID != actor.UserID {
		return s.denyAndLogTx(ctx, tx, actor, operation, order.OrderNo)
	}
	return nil
}

func (s *OrderService) rejectOutsideTx(ctx context.Context, actor Actor, orderNo, tradeNo, eventType, code string) (*model.Payment, error) {
	p := s.newPayment(0, orderNo, tradeNo, "", eventType, ResultRejected, code, "", "", 0, true, false, false, false, 0, actor.UserID)
	if err := s.repo.CreatePayment(ctx, p); err != nil {
		return nil, err
	}
	return p, fail(code)
}

func (s *OrderService) rejectedPayment(ctx context.Context, tx OrderRepository, actor Actor, orderID uint64, orderNo, tradeNo, eventType, code, snapshot string, amount int64, signatureValid bool) (*model.Payment, error) {
	p := s.newPayment(orderID, orderNo, tradeNo, "", eventType, ResultRejected, code, "", snapshot, amount, signatureValid, false, false, false, 0, actor.UserID)
	if err := tx.CreatePayment(ctx, p); err != nil {
		return nil, err
	}
	return p, fail(code)
}

func (s *OrderService) noopPayment(ctx context.Context, tx OrderRepository, actor Actor, orderID uint64, orderNo, tradeNo, eventType, result, code, snapshot string, amount int64) (*model.Payment, error) {
	p := s.newPayment(orderID, orderNo, tradeNo, "", eventType, result, code, "", snapshot, amount, true, false, false, false, 0, actor.UserID)
	if err := tx.CreatePayment(ctx, p); err != nil {
		return nil, err
	}
	return p, nil
}

// duplicateRejectPayment 用于人为重复操作：只追加一条重复操作留痕，并向调用方返回 M-xx 中文原因。
// 渠道通知的重复（支付/退款回调）仍由 noopPayment 以 nil error 幂等响应，避免模拟渠道持续重推。
func (s *OrderService) duplicateRejectPayment(ctx context.Context, tx OrderRepository, actor Actor, orderID uint64, orderNo, tradeNo, eventType, result, code, snapshot string, amount int64) (*model.Payment, error) {
	p, err := s.noopPayment(ctx, tx, actor, orderID, orderNo, tradeNo, eventType, result, code, snapshot, amount)
	if err != nil {
		return nil, err
	}
	return p, fail(code)
}

func (s *OrderService) closePendingOrder(ctx context.Context, tx OrderRepository, actor Actor, order *model.Order, now time.Time, targetStatus, eventType string) (bool, error) {
	fields := map[string]interface{}{"status": targetStatus}
	if targetStatus == StatusClosed {
		fields["closed_at"] = now
	} else {
		fields["cancelled_at"] = now
	}
	rows, err := tx.UpdateOrderIfStatus(ctx, order, []string{StatusPendingPayment}, fields)
	if err != nil {
		return false, err
	}
	if rows != 1 {
		// 并发风险点：重复关闭 / 取消与超时关闭竞争时，主键行锁后的条件更新 RowsAffected=0，
		// 不再释放库存，只追加一条重复操作留痕。
		_, err = s.noopPayment(ctx, tx, actor, uint64(order.ID), order.OrderNo, "CLOSE:"+order.OrderNo, eventType, ResultDuplicateNoop, "M-10", order.Status, 0)
		return false, err
	}
	order.Status = targetStatus
	if targetStatus == StatusClosed {
		order.ClosedAt = &now
	} else {
		order.CancelledAt = &now
	}
	goods, err := tx.LockGoods(ctx, order.GoodsID)
	if err != nil {
		return false, err
	}
	if goods == nil {
		return false, fmt.Errorf("goods %d not found during stock release", order.GoodsID)
	}
	ok, err := tx.IncreaseGoodsStock(ctx, order.GoodsID, order.Quantity)
	if err != nil {
		return false, err
	}
	if !ok {
		return false, fmt.Errorf("stock release condition not met for goods %d", order.GoodsID)
	}
	audit := s.newPayment(uint64(order.ID), order.OrderNo, "STOCK:"+order.OrderNo, "", EventStockRelease, ResultStockReleased, "", "", order.Status, 0, true, false, false, true, 0, actor.UserID)
	if err := tx.CreatePayment(ctx, audit); err != nil {
		return false, err
	}
	return true, nil
}

// CreateOrder：T-01。下单锁库存依赖 MySQL(InnoDB) 事务 + goods.id 行锁；条件更新命中主键防超卖。
func (s *OrderService) CreateOrder(ctx context.Context, actor Actor, goodsID uint64, quantity int) (*model.Order, error) {
	if err := s.requireRole(ctx, actor, "CreateOrder", "", RoleBuyer); err != nil {
		return nil, err
	}
	if goodsID == 0 {
		return nil, fail("M-04")
	}
	if quantity != 1 && quantity != 2 {
		return nil, fail("M-03")
	}
	var created *model.Order
	err := s.repo.WithTransaction(ctx, func(tx OrderRepository) error {
		goods, err := tx.LockGoods(ctx, goodsID)
		if err != nil {
			return err
		}
		if goods == nil || goods.Status != GoodsStatusOnSale {
			return fail("M-01")
		}
		if goods.AvailableStock < quantity {
			return fail("M-02")
		}
		ok, err := tx.DecreaseGoodsStock(ctx, goodsID, quantity)
		if err != nil {
			return err
		}
		if !ok {
			return fail("M-02")
		}
		now := s.now()
		order := &model.Order{
			OrderNo:     fmt.Sprintf("ORD-%d-%d-%d", now.UnixNano(), actor.UserID, s.nextSeq()),
			BuyerID:     actor.UserID,
			GoodsID:     goodsID,
			GoodsNo:     goods.GoodsNo,
			GoodsName:   goods.Name,
			Quantity:    quantity,
			UnitPrice:   goods.UnitPrice,
			TotalAmount: goods.UnitPrice * int64(quantity),
			Status:      StatusPendingPayment,
			ExpiresAt:   now.Add(s.timeout),
			RefundKind:  RefundKindNone,
			RefundState: RefundStateNone,
		}
		if err := tx.CreateOrder(ctx, order); err != nil {
			return err
		}
		audit := s.newPayment(uint64(order.ID), order.OrderNo, "ORDER:"+order.OrderNo, "", EventCreateOrder, ResultStockPreDeducted, "", "", order.Status, order.TotalAmount, true, false, false, false, 0, actor.UserID)
		if err := tx.CreatePayment(ctx, audit); err != nil {
			return err
		}
		created = order
		return nil
	})
	return created, err
}

// HandlePaymentCallback：T-02/T-11/F-08/F-09/F-10。有效支付通知幂等；迟到支付不改终态、不重占库存。
func (s *OrderService) HandlePaymentCallback(ctx context.Context, actor Actor, in PaymentCallback) (*model.Payment, error) {
	if err := s.requireRole(ctx, actor, "HandlePaymentCallback", in.OrderNo, RoleMockChannel, RoleOps); err != nil {
		return nil, err
	}
	if in.ChannelTradeNo == "" {
		return s.rejectOutsideTx(ctx, actor, in.OrderNo, "", eventPaymentRejected, "M-27")
	}
	dedupKey := DedupPayPrefix + in.ChannelTradeNo
	var out *model.Payment
	err := s.repo.WithTransaction(ctx, func(tx OrderRepository) error {
		existing, err := tx.GetPaymentByDedupKey(ctx, dedupKey)
		if err != nil {
			return err
		}
		if existing != nil {
			if existing.OrderNo != in.OrderNo {
				p, err := s.rejectedPayment(ctx, tx, actor, existing.OrderID, in.OrderNo, in.ChannelTradeNo, EventPaymentConflict, "M-27", "", in.Amount, true)
				out = p
				return err
			}
			p, err := s.noopPayment(ctx, tx, actor, existing.OrderID, in.OrderNo, in.ChannelTradeNo, EventRepeatPayment, ResultRepeatPaymentNoop, "M-25", existing.OrderStatusSnapshot, in.Amount)
			out = p
			return err
		}
		order, err := tx.LockOrder(ctx, in.OrderNo)
		if err != nil {
			return err
		}
		if order == nil {
			p, err := s.rejectedPayment(ctx, tx, actor, 0, in.OrderNo, in.ChannelTradeNo, eventPaymentRejected, "M-30", "", in.Amount, true)
			out = p
			return err
		}
		if !in.SignatureValid {
			p, err := s.rejectedPayment(ctx, tx, actor, uint64(order.ID), in.OrderNo, in.ChannelTradeNo, eventPaymentRejected, "M-28", order.Status, in.Amount, false)
			out = p
			return err
		}
		if in.Amount != order.TotalAmount {
			p, err := s.rejectedPayment(ctx, tx, actor, uint64(order.ID), in.OrderNo, in.ChannelTradeNo, eventPaymentRejected, "M-29", order.Status, in.Amount, true)
			out = p
			return err
		}
		if isTerminal(order.Status) {
			code := "M-09"
			if order.Status != StatusClosed {
				code = "M-15"
			}
			p := s.newPayment(uint64(order.ID), order.OrderNo, in.ChannelTradeNo, "", EventLatePayment, ResultLatePaymentPending, code, "", order.Status, in.Amount, true, false, true, false, 0, actor.UserID)
			if err := tx.CreatePayment(ctx, p); err != nil {
				return err
			}
			out = p
			return fail(code)
		}
		if order.Status != StatusPendingPayment {
			p, err := s.rejectedPayment(ctx, tx, actor, uint64(order.ID), in.OrderNo, in.ChannelTradeNo, eventPaymentRejected, "M-05", order.Status, in.Amount, true)
			out = p
			return err
		}
		now := s.now()
		if !now.Before(order.ExpiresAt) {
			// 并发风险点：超时订单在收到迟到支付时先按服务端时间关单并释放一次库存，
			// 再登记异常支付；不恢复订单、不重新占用库存。
			closed, err := s.closePendingOrder(ctx, tx, actor, order, now, StatusClosed, EventCloseExpired)
			if err != nil {
				return err
			}
			if !closed {
				p, err := s.rejectedPayment(ctx, tx, actor, uint64(order.ID), in.OrderNo, in.ChannelTradeNo, eventPaymentRejected, "M-10", order.Status, in.Amount, true)
				out = p
				return err
			}
			p := s.newPayment(uint64(order.ID), order.OrderNo, in.ChannelTradeNo, "", EventLatePayment, ResultLatePaymentPending, "M-09", "", order.Status, in.Amount, true, false, true, false, 0, actor.UserID)
			if err := tx.CreatePayment(ctx, p); err != nil {
				return err
			}
			out = p
			return fail("M-09")
		}
		fields := map[string]interface{}{"status": StatusWaitingShipment, "paid_at": now}
		rows, err := tx.UpdateOrderIfStatus(ctx, order, []string{StatusPendingPayment}, fields)
		if err != nil {
			return err
		}
		if rows != 1 {
			p, err := s.noopPayment(ctx, tx, actor, uint64(order.ID), in.OrderNo, in.ChannelTradeNo, EventRepeatPayment, ResultRepeatPaymentNoop, "M-25", order.Status, in.Amount)
			out = p
			return err
		}
		order.Status = StatusWaitingShipment
		order.PaidAt = &now
		// 幂等键 + uk_payment_channel_effective 保证同一渠道交易号只形成一条有效收款记录。
		p := s.newPayment(uint64(order.ID), order.OrderNo, in.ChannelTradeNo, dedupKey, EventPaymentSuccess, ResultPaid, "", "", order.Status, in.Amount, true, true, false, false, 0, actor.UserID)
		if err := tx.CreatePayment(ctx, p); err != nil {
			return err
		}
		out = p
		return nil
	})
	if errors.Is(err, ErrDuplicateDedupKey) {
		return s.rejectOutsideTx(ctx, actor, in.OrderNo, in.ChannelTradeNo, EventPaymentConflict, "M-27")
	}
	return out, err
}

// CancelOrder：T-03/T-04/T-12。买家主动取消与超时关闭竞争时，条件更新保证只释放一次。
func (s *OrderService) CancelOrder(ctx context.Context, actor Actor, orderNo string) (*model.Order, error) {
	if err := s.requireRole(ctx, actor, "CancelOrder", orderNo, RoleBuyer); err != nil {
		return nil, err
	}
	var out *model.Order
	err := s.repo.WithTransaction(ctx, func(tx OrderRepository) error {
		order, err := tx.LockOrder(ctx, orderNo)
		if err != nil {
			return err
		}
		if order == nil {
			return fail("M-30")
		}
		if err := s.assertBuyerOwnerTx(ctx, tx, actor, "CancelOrder", order); err != nil {
			return err
		}
		if isTerminal(order.Status) {
			_, err := s.duplicateRejectPayment(ctx, tx, actor, uint64(order.ID), orderNo, "CANCEL:"+orderNo, EventCancel, ResultDuplicateNoop, "M-10", order.Status, 0)
			return err
		}
		if order.Status != StatusPendingPayment {
			return fail("M-05")
		}
		now := s.now()
		if !now.Before(order.ExpiresAt) {
			closed, err := s.closePendingOrder(ctx, tx, actor, order, now, StatusClosed, EventCloseExpired)
			if err != nil {
				return err
			}
			if !closed {
				return fail("M-10")
			}
			out = order
			return fail("M-06")
		}
		ok, err := s.closePendingOrder(ctx, tx, actor, order, now, StatusCancelled, EventCancel)
		if err != nil {
			return err
		}
		if !ok {
			return fail("M-10")
		}
		out = order
		return nil
	})
	return out, err
}

// CloseExpiredOrders：T-04。列表依赖 idx_order_status_expires；逐笔在事务内重新按主键加行锁。
func (s *OrderService) CloseExpiredOrders(ctx context.Context, actor Actor, limit int) (int64, error) {
	if err := s.requireRole(ctx, actor, "CloseExpiredOrders", "", RoleOps); err != nil {
		return 0, err
	}
	if limit <= 0 {
		limit = 100
	}
	now := s.now()
	orders, err := s.repo.ListExpiredPendingOrders(ctx, now, limit)
	if err != nil {
		return 0, err
	}
	var closedCount int64
	for i := range orders {
		snapshot := orders[i]
		err := s.repo.WithTransaction(ctx, func(tx OrderRepository) error {
			order, err := tx.LockOrderByID(ctx, uint64(snapshot.ID))
			if err != nil {
				return err
			}
			if order == nil || order.Status != StatusPendingPayment || order.ExpiresAt.After(now) {
				return nil
			}
			ok, err := s.closePendingOrder(ctx, tx, actor, order, now, StatusClosed, EventCloseExpired)
			if err != nil {
				return err
			}
			if ok {
				closedCount++
			}
			return nil
		})
		if err != nil {
			return closedCount, err
		}
	}
	return closedCount, nil
}

// ApplyRefund：T-05。仅待发货订单可申请整单售前退款，申请期间发货暂停。
func (s *OrderService) ApplyRefund(ctx context.Context, actor Actor, orderNo, reason string) (*model.Order, error) {
	if err := s.requireRole(ctx, actor, "ApplyRefund", orderNo, RoleBuyer); err != nil {
		return nil, err
	}
	var out *model.Order
	err := s.repo.WithTransaction(ctx, func(tx OrderRepository) error {
		order, err := tx.LockOrder(ctx, orderNo)
		if err != nil {
			return err
		}
		if order == nil {
			return fail("M-30")
		}
		if err := s.assertBuyerOwnerTx(ctx, tx, actor, "ApplyRefund", order); err != nil {
			return err
		}
		if order.Status == StatusShipped || order.Status == StatusRefunded {
			return fail("M-11")
		}
		if order.Status == StatusRefundReview || order.Status == StatusRefundProcessing {
			return fail("M-10")
		}
		if order.Status != StatusWaitingShipment {
			return fail("M-05")
		}
		now := s.now()
		fields := map[string]interface{}{
			"status":          StatusRefundReview,
			"refund_kind":     RefundKindPresale,
			"refund_reason":   reason,
			"refund_apply_at": now,
			"refund_state":    "审核中",
		}
		rows, err := tx.UpdateOrderIfStatus(ctx, order, []string{StatusWaitingShipment}, fields)
		if err != nil {
			return err
		}
		if rows != 1 {
			return fail("M-10")
		}
		order.Status = StatusRefundReview
		order.RefundKind = RefundKindPresale
		order.RefundReason = reason
		order.RefundApplyAt = &now
		order.RefundState = "审核中"
		audit := s.newPayment(uint64(order.ID), orderNo, "REFUND_APPLY:"+orderNo, "", EventRefundApply, ResultRefundApplied, "", "", order.Status, order.TotalAmount, true, false, false, false, 0, actor.UserID)
		if err := tx.CreatePayment(ctx, audit); err != nil {
			return err
		}
		out = order
		return nil
	})
	return out, err
}

func (s *OrderService) RejectRefund(ctx context.Context, actor Actor, orderNo, remark string) (*model.Order, error) {
	if err := s.requireRole(ctx, actor, "RejectRefund", orderNo, RoleCustomerService); err != nil {
		return nil, err
	}
	if remark == "" {
		_, err := s.rejectOutsideTx(ctx, actor, orderNo, "REFUND_AUDIT:"+orderNo, EventRefundRejected, "M-24")
		return nil, err
	}
	var out *model.Order
	err := s.repo.WithTransaction(ctx, func(tx OrderRepository) error {
		order, err := tx.LockOrder(ctx, orderNo)
		if err != nil {
			return err
		}
		if order == nil {
			return fail("M-30")
		}
		if order.Status != StatusRefundReview {
			return fail("M-05")
		}
		now := s.now()
		fields := map[string]interface{}{
			"status":              StatusWaitingShipment,
			"refund_state":        RefundStateRejected,
			"refund_audit_at":     now,
			"refund_auditor_id":   actor.UserID,
			"refund_audit_remark": remark,
		}
		rows, err := tx.UpdateOrderIfStatus(ctx, order, []string{StatusRefundReview}, fields)
		if err != nil {
			return err
		}
		if rows != 1 {
			return fail("M-10")
		}
		order.Status = StatusWaitingShipment
		order.RefundState = RefundStateRejected
		order.RefundAuditAt = &now
		order.RefundAuditorID = actor.UserID
		order.RefundAuditRemark = remark
		audit := s.newPayment(uint64(order.ID), orderNo, "REFUND_REJECT:"+orderNo, "", EventRefundRejected, ResultRefundRejected, "", remark, order.Status, order.TotalAmount, true, false, false, false, 0, actor.UserID)
		if err := tx.CreatePayment(ctx, audit); err != nil {
			return err
		}
		out = order
		return nil
	})
	return out, err
}

func (s *OrderService) ApproveRefund(ctx context.Context, actor Actor, orderNo, remark string) (*model.Order, error) {
	if err := s.requireRole(ctx, actor, "ApproveRefund", orderNo, RoleCustomerService); err != nil {
		return nil, err
	}
	if remark == "" {
		_, err := s.rejectOutsideTx(ctx, actor, orderNo, "REFUND_AUDIT:"+orderNo, EventRefundApproved, "M-24")
		return nil, err
	}
	var out *model.Order
	err := s.repo.WithTransaction(ctx, func(tx OrderRepository) error {
		order, err := tx.LockOrder(ctx, orderNo)
		if err != nil {
			return err
		}
		if order == nil {
			return fail("M-30")
		}
		if order.Status != StatusRefundReview {
			return fail("M-05")
		}
		now := s.now()
		fields := map[string]interface{}{
			"status":              StatusRefundProcessing,
			"refund_kind":         RefundKindPresale,
			"refund_state":        RefundStatePending,
			"refund_audit_at":     now,
			"refund_auditor_id":   actor.UserID,
			"refund_audit_remark": remark,
		}
		rows, err := tx.UpdateOrderIfStatus(ctx, order, []string{StatusRefundReview}, fields)
		if err != nil {
			return err
		}
		if rows != 1 {
			return fail("M-10")
		}
		order.Status = StatusRefundProcessing
		order.RefundKind = RefundKindPresale
		order.RefundState = RefundStatePending
		order.RefundAuditAt = &now
		order.RefundAuditorID = actor.UserID
		order.RefundAuditRemark = remark
		audit := s.newPayment(uint64(order.ID), orderNo, "REFUND_APPROVE:"+orderNo, "", EventRefundApproved, ResultRefundApproved, "", remark, order.Status, order.TotalAmount, true, false, false, false, 0, actor.UserID)
		if err := tx.CreatePayment(ctx, audit); err != nil {
			return err
		}
		out = order
		return nil
	})
	return out, err
}

func (s *OrderService) RetryRefund(ctx context.Context, actor Actor, orderNo, remark string) (*model.Order, error) {
	if err := s.requireRole(ctx, actor, "RetryRefund", orderNo, RoleCustomerService); err != nil {
		return nil, err
	}
	if remark == "" {
		_, err := s.rejectOutsideTx(ctx, actor, orderNo, "REFUND_RETRY:"+orderNo, EventRefundRetry, "M-24")
		return nil, err
	}
	var out *model.Order
	err := s.repo.WithTransaction(ctx, func(tx OrderRepository) error {
		order, err := tx.LockOrder(ctx, orderNo)
		if err != nil {
			return err
		}
		if order == nil {
			return fail("M-30")
		}
		if order.Status != StatusRefundProcessing || order.RefundState != RefundStateFailed {
			return fail("M-05")
		}
		fields := map[string]interface{}{
			"refund_state":        RefundStatePending,
			"refund_retry_count":  order.RefundRetryCount + 1,
			"refund_audit_remark": remark,
		}
		rows, err := tx.UpdateOrderIfStatus(ctx, order, []string{StatusRefundProcessing}, fields)
		if err != nil {
			return err
		}
		if rows != 1 {
			return fail("M-10")
		}
		order.RefundState = RefundStatePending
		order.RefundRetryCount++
		order.RefundAuditRemark = remark
		audit := s.newPayment(uint64(order.ID), orderNo, "REFUND_RETRY:"+orderNo, "", EventRefundRetry, ResultRefundRetried, "", remark, order.Status, order.TotalAmount, true, false, false, false, 0, actor.UserID)
		if err := tx.CreatePayment(ctx, audit); err != nil {
			return err
		}
		out = order
		return nil
	})
	return out, err
}

// HandleRefundCallback：T-09/T-10/F-08。重复退款通知幂等，退款与发货并发由订单行锁裁决。
func (s *OrderService) HandleRefundCallback(ctx context.Context, actor Actor, in RefundCallback) (*model.Payment, error) {
	if err := s.requireRole(ctx, actor, "HandleRefundCallback", in.OrderNo, RoleMockChannel, RoleOps); err != nil {
		return nil, err
	}
	if in.RefundChannelTradeNo == "" {
		return s.rejectOutsideTx(ctx, actor, in.OrderNo, "", eventRefundCallbackRejected, "M-27")
	}
	dedupOK := DedupRefundOKPrefix + in.RefundChannelTradeNo
	dedupFail := DedupRefundFailPrefix + in.RefundChannelTradeNo
	var out *model.Payment
	err := s.repo.WithTransaction(ctx, func(tx OrderRepository) error {
		existingOK, err := tx.GetPaymentByDedupKey(ctx, dedupOK)
		if err != nil {
			return err
		}
		if existingOK != nil {
			if existingOK.OrderNo != in.OrderNo {
				p, err := s.rejectedPayment(ctx, tx, actor, existingOK.OrderID, in.OrderNo, in.RefundChannelTradeNo, eventRefundCallbackRejected, "M-27", "", in.Amount, true)
				out = p
				return err
			}
			p, err := s.noopPayment(ctx, tx, actor, existingOK.OrderID, in.OrderNo, in.RefundChannelTradeNo, EventRepeatRefund, ResultRepeatRefundNoop, "M-25", existingOK.OrderStatusSnapshot, in.Amount)
			out = p
			return err
		}
		existingFail, err := tx.GetPaymentByDedupKey(ctx, dedupFail)
		if err != nil {
			return err
		}
		if existingFail != nil && !in.Success {
			p, err := s.noopPayment(ctx, tx, actor, existingFail.OrderID, in.OrderNo, in.RefundChannelTradeNo, EventRepeatRefund, ResultDuplicateNoop, "M-10", existingFail.OrderStatusSnapshot, in.Amount)
			out = p
			return err
		}
		order, err := tx.LockOrder(ctx, in.OrderNo)
		if err != nil {
			return err
		}
		if order == nil {
			p, err := s.rejectedPayment(ctx, tx, actor, 0, in.OrderNo, in.RefundChannelTradeNo, eventRefundCallbackRejected, "M-30", "", in.Amount, true)
			out = p
			return err
		}
		if !in.SignatureValid {
			p, err := s.rejectedPayment(ctx, tx, actor, uint64(order.ID), in.OrderNo, in.RefundChannelTradeNo, eventRefundCallbackRejected, "M-28", order.Status, in.Amount, false)
			out = p
			return err
		}
		if in.Amount != order.TotalAmount {
			p, err := s.rejectedPayment(ctx, tx, actor, uint64(order.ID), in.OrderNo, in.RefundChannelTradeNo, eventRefundCallbackRejected, "M-29", order.Status, in.Amount, true)
			out = p
			return err
		}
		if order.Status == StatusRefunded {
			p, err := s.noopPayment(ctx, tx, actor, uint64(order.ID), in.OrderNo, in.RefundChannelTradeNo, EventRepeatRefund, ResultRepeatRefundNoop, "M-10", order.Status, in.Amount)
			out = p
			return err
		}
		if order.Status != StatusRefundProcessing || (order.RefundState != RefundStatePending && order.RefundState != RefundStateFailed) {
			p, err := s.rejectedPayment(ctx, tx, actor, uint64(order.ID), in.OrderNo, in.RefundChannelTradeNo, eventRefundCallbackRejected, "M-05", order.Status, in.Amount, true)
			out = p
			return err
		}
		now := s.now()
		if !in.Success {
			fields := map[string]interface{}{
				"refund_state":            RefundStateFailed,
				"refund_channel_trade_no": in.RefundChannelTradeNo,
				"refund_audit_remark":     "渠道明确退款失败，保留待处理记录",
			}
			rows, err := tx.UpdateOrderIfStatus(ctx, order, []string{StatusRefundProcessing}, fields)
			if err != nil {
				return err
			}
			if rows != 1 {
				p, err := s.noopPayment(ctx, tx, actor, uint64(order.ID), in.OrderNo, in.RefundChannelTradeNo, EventRepeatRefund, ResultDuplicateNoop, "M-10", order.Status, in.Amount)
				out = p
				return err
			}
			order.RefundState = RefundStateFailed
			order.RefundChannelTradeNo = in.RefundChannelTradeNo
			order.RefundAuditRemark = "渠道明确退款失败，保留待处理记录"
			p := s.newPayment(uint64(order.ID), in.OrderNo, in.RefundChannelTradeNo, dedupFail, EventRefundFailed, ResultRefundFailedPending, "M-08", "", order.Status, in.Amount, true, false, false, false, 0, actor.UserID)
			if err := tx.CreatePayment(ctx, p); err != nil {
				return err
			}
			out = p
			return fail("M-08")
		}
		// 并发风险点：stock_restored = 0 与 order.id 主键行锁共同保证退款成功只恢复一次库存。
		fields := map[string]interface{}{
			"status":                  StatusRefunded,
			"refund_state":            RefundStateSuccess,
			"refund_channel_trade_no": in.RefundChannelTradeNo,
			"refunded_at":             now,
			"stock_restored":          true,
		}
		rows, err := tx.UpdateOrderIfStatusAndStockNotRestored(ctx, order, []string{StatusRefundProcessing}, fields)
		if err != nil {
			return err
		}
		if rows != 1 {
			p, err := s.noopPayment(ctx, tx, actor, uint64(order.ID), in.OrderNo, in.RefundChannelTradeNo, EventRepeatRefund, ResultRepeatRefundNoop, "M-10", order.Status, in.Amount)
			out = p
			return err
		}
		order.Status = StatusRefunded
		order.RefundState = RefundStateSuccess
		order.RefundChannelTradeNo = in.RefundChannelTradeNo
		order.RefundedAt = &now
		order.StockRestored = true
		if order.RefundKind == RefundKindPresale && !order.LatePaymentRefunded {
			goods, err := tx.LockGoods(ctx, order.GoodsID)
			if err != nil {
				return err
			}
			if goods == nil {
				return fmt.Errorf("goods %d not found during refund stock restore", order.GoodsID)
			}
			ok, err := tx.IncreaseGoodsStock(ctx, order.GoodsID, order.Quantity)
			if err != nil {
				return err
			}
			if !ok {
				return fmt.Errorf("stock restore condition not met for goods %d", order.GoodsID)
			}
			audit := s.newPayment(uint64(order.ID), in.OrderNo, "REFUND_STOCK:"+in.RefundChannelTradeNo, "", EventStockRestore, ResultStockRestored, "", "", order.Status, 0, true, false, false, true, 0, actor.UserID)
			if err := tx.CreatePayment(ctx, audit); err != nil {
				return err
			}
		}
		p := s.newPayment(uint64(order.ID), in.OrderNo, in.RefundChannelTradeNo, dedupOK, EventRefundSuccess, ResultRefundSucceeded, "", "", order.Status, in.Amount, true, true, false, false, 0, actor.UserID)
		if err := tx.CreatePayment(ctx, p); err != nil {
			return err
		}
		out = p
		return nil
	})
	if errors.Is(err, ErrDuplicateDedupKey) {
		return s.rejectOutsideTx(ctx, actor, in.OrderNo, in.RefundChannelTradeNo, EventRepeatRefund, "M-10")
	}
	return out, err
}

// RegisterShipment：T-06/F-04/F-08。发货与退款并发时首个事务提交者生效，后到者按当前状态拒绝。
func (s *OrderService) RegisterShipment(ctx context.Context, actor Actor, orderNo, carrier, trackingNo string) (*model.Payment, error) {
	if err := s.requireRole(ctx, actor, "RegisterShipment", orderNo, RoleWarehouse); err != nil {
		return nil, err
	}
	if carrier == "" || trackingNo == "" {
		return s.rejectOutsideTx(ctx, actor, orderNo, "SHIP:"+orderNo, EventShipment, "M-23")
	}
	dedupKey := DedupShipmentPrefix + orderNo
	var out *model.Payment
	err := s.repo.WithTransaction(ctx, func(tx OrderRepository) error {
		existing, err := tx.GetPaymentByDedupKey(ctx, dedupKey)
		if err != nil {
			return err
		}
		if existing != nil {
			p, err := s.duplicateRejectPayment(ctx, tx, actor, existing.OrderID, orderNo, "SHIP:"+orderNo, EventShipment, ResultDuplicateNoop, "M-19", existing.OrderStatusSnapshot, 0)
			out = p
			return err
		}
		order, err := tx.LockOrder(ctx, orderNo)
		if err != nil {
			return err
		}
		if order == nil {
			return fail("M-30")
		}
		if order.Status == StatusRefundReview || order.Status == StatusRefundProcessing {
			p, err := s.rejectedPayment(ctx, tx, actor, uint64(order.ID), orderNo, "SHIP:"+orderNo, EventShipment, "M-22", order.Status, 0, true)
			out = p
			return err
		}
		if order.Status == StatusShipped {
			p, err := s.rejectedPayment(ctx, tx, actor, uint64(order.ID), orderNo, "SHIP:"+orderNo, EventShipment, "M-19", order.Status, 0, true)
			out = p
			return err
		}
		if order.Status == StatusRefunded {
			p, err := s.rejectedPayment(ctx, tx, actor, uint64(order.ID), orderNo, "SHIP:"+orderNo, EventShipment, "M-11", order.Status, 0, true)
			out = p
			return err
		}
		if order.Status != StatusWaitingShipment {
			p, err := s.rejectedPayment(ctx, tx, actor, uint64(order.ID), orderNo, "SHIP:"+orderNo, EventShipment, "M-18", order.Status, 0, true)
			out = p
			return err
		}
		now := s.now()
		fields := map[string]interface{}{
			"status":                 StatusShipped,
			"shipment_carrier":       carrier,
			"shipment_tracking_no":   trackingNo,
			"shipped_at":             now,
			"shipment_registered_by": actor.UserID,
		}
		rows, err := tx.UpdateOrderIfStatus(ctx, order, []string{StatusWaitingShipment}, fields)
		if err != nil {
			return err
		}
		if rows != 1 {
			p, err := s.duplicateRejectPayment(ctx, tx, actor, uint64(order.ID), orderNo, "SHIP:"+orderNo, EventShipment, ResultDuplicateNoop, "M-19", order.Status, 0)
			out = p
			return err
		}
		order.Status = StatusShipped
		order.ShipmentCarrier = carrier
		order.ShipmentTrackingNo = trackingNo
		order.ShippedAt = &now
		order.ShipmentRegisteredBy = actor.UserID
		p := s.newPayment(uint64(order.ID), orderNo, "SHIP:"+orderNo, dedupKey, EventShipment, ResultShipmentRegistered, "", "", order.Status, 0, true, true, false, false, 0, actor.UserID)
		if err := tx.CreatePayment(ctx, p); err != nil {
			return err
		}
		out = p
		return nil
	})
	if errors.Is(err, ErrDuplicateDedupKey) {
		return s.rejectOutsideTx(ctx, actor, orderNo, "SHIP:"+orderNo, EventShipment, "M-19")
	}
	return out, err
}

// VerifyLatePayment：T-11 旁路。原异常记录不修改、不删除，只追加核实事件。
func (s *OrderService) VerifyLatePayment(ctx context.Context, actor Actor, eventID uint64, reason string) (*model.Payment, error) {
	if err := s.requireRole(ctx, actor, "VerifyLatePayment", "", RoleCustomerService); err != nil {
		return nil, err
	}
	if reason == "" {
		return s.rejectOutsideTx(ctx, actor, "", "LATE_VERIFY", EventLatePaymentVerified, "M-24")
	}
	var out *model.Payment
	err := s.repo.WithTransaction(ctx, func(tx OrderRepository) error {
		origin, err := tx.GetPaymentByID(ctx, eventID)
		if err != nil {
			return err
		}
		if origin == nil || origin.EventType != EventLatePayment || origin.Result != ResultLatePaymentPending {
			return fail("M-14")
		}
		verified, err := tx.HasPaymentEvent(ctx, eventID, EventLatePaymentVerified)
		if err != nil {
			return err
		}
		if verified {
			p, err := s.duplicateRejectPayment(ctx, tx, actor, origin.OrderID, origin.OrderNo, "LATE_VERIFY", EventLatePaymentVerified, ResultDuplicateNoop, "M-10", origin.OrderStatusSnapshot, origin.Amount)
			out = p
			return err
		}
		p := s.newPayment(origin.OrderID, origin.OrderNo, "LATE_VERIFY:"+origin.ChannelTradeNo, "", EventLatePaymentVerified, ResultLatePaymentVerified, "", reason, origin.OrderStatusSnapshot, origin.Amount, true, false, false, false, uint64(origin.ID), actor.UserID)
		if err := tx.CreatePayment(ctx, p); err != nil {
			return err
		}
		out = p
		return nil
	})
	return out, err
}

// InitiateLatePaymentRefund：T-11 旁路。订单状态不变，不恢复此前已释放库存。
func (s *OrderService) InitiateLatePaymentRefund(ctx context.Context, actor Actor, eventID uint64, refundNo, reason string) (*model.Payment, error) {
	if err := s.requireRole(ctx, actor, "InitiateLatePaymentRefund", "", RoleCustomerService); err != nil {
		return nil, err
	}
	if refundNo == "" {
		return s.rejectOutsideTx(ctx, actor, "", "LATE_REFUND_REQ", EventLateRefundRequest, "M-27")
	}
	if reason == "" {
		return s.rejectOutsideTx(ctx, actor, "", "LATE_REFUND_REQ:"+refundNo, EventLateRefundRequest, "M-24")
	}
	dedupReq := DedupLateRefundReqPrefix + refundNo
	var out *model.Payment
	err := s.repo.WithTransaction(ctx, func(tx OrderRepository) error {
		origin, err := tx.GetPaymentByID(ctx, eventID)
		if err != nil {
			return err
		}
		if origin == nil || origin.EventType != EventLatePayment || origin.Result != ResultLatePaymentPending {
			return fail("M-14")
		}
		verified, err := tx.HasPaymentEvent(ctx, eventID, EventLatePaymentVerified)
		if err != nil {
			return err
		}
		if !verified {
			return fail("M-24")
		}
		existing, err := tx.GetPaymentByDedupKey(ctx, dedupReq)
		if err != nil {
			return err
		}
		if existing != nil {
			p, err := s.duplicateRejectPayment(ctx, tx, actor, origin.OrderID, origin.OrderNo, refundNo, EventLateRefundRequest, ResultDuplicateNoop, "M-10", origin.OrderStatusSnapshot, origin.Amount)
			out = p
			return err
		}
		p := s.newPayment(origin.OrderID, origin.OrderNo, refundNo, dedupReq, EventLateRefundRequest, ResultLateRefundRequested, "M-26", reason, origin.OrderStatusSnapshot, origin.Amount, true, false, true, false, uint64(origin.ID), actor.UserID)
		if err := tx.CreatePayment(ctx, p); err != nil {
			return err
		}
		out = p
		return nil
	})
	if errors.Is(err, ErrDuplicateDedupKey) {
		return s.rejectOutsideTx(ctx, actor, "", refundNo, EventLateRefundRequest, "M-10")
	}
	return out, err
}

// HandleLatePaymentRefundCallback：迟到支付退款成功不二次恢复库存，订单保持已关闭终态。
func (s *OrderService) HandleLatePaymentRefundCallback(ctx context.Context, actor Actor, in LateRefundCallback) (*model.Payment, error) {
	if err := s.requireRole(ctx, actor, "HandleLatePaymentRefundCallback", "", RoleMockChannel, RoleOps); err != nil {
		return nil, err
	}
	if in.RefundNo == "" {
		return s.rejectOutsideTx(ctx, actor, "", "", eventLateRefundCallback, "M-27")
	}
	dedupOK := DedupLateRefundOKPrefix + in.RefundNo
	dedupFail := DedupLateRefundFailPrefix + in.RefundNo
	dedupReq := DedupLateRefundReqPrefix + in.RefundNo
	var out *model.Payment
	err := s.repo.WithTransaction(ctx, func(tx OrderRepository) error {
		existingOK, err := tx.GetPaymentByDedupKey(ctx, dedupOK)
		if err != nil {
			return err
		}
		if existingOK != nil {
			p, err := s.noopPayment(ctx, tx, actor, existingOK.OrderID, existingOK.OrderNo, in.RefundNo, EventRepeatRefund, ResultRepeatRefundNoop, "M-25", existingOK.OrderStatusSnapshot, in.Amount)
			out = p
			return err
		}
		existingFail, err := tx.GetPaymentByDedupKey(ctx, dedupFail)
		if err != nil {
			return err
		}
		if existingFail != nil && !in.Success {
			p, err := s.noopPayment(ctx, tx, actor, existingFail.OrderID, existingFail.OrderNo, in.RefundNo, EventRepeatRefund, ResultDuplicateNoop, "M-10", existingFail.OrderStatusSnapshot, in.Amount)
			out = p
			return err
		}
		origin, err := tx.GetPaymentByID(ctx, in.EventID)
		if err != nil {
			return err
		}
		if origin == nil || origin.EventType != EventLatePayment || origin.Result != ResultLatePaymentPending {
			return fail("M-14")
		}
		verified, err := tx.HasPaymentEvent(ctx, in.EventID, EventLatePaymentVerified)
		if err != nil {
			return err
		}
		requested, err := tx.GetPaymentByDedupKey(ctx, dedupReq)
		if err != nil {
			return err
		}
		if !verified || requested == nil {
			return fail("M-24")
		}
		order, err := tx.LockOrder(ctx, origin.OrderNo)
		if err != nil {
			return err
		}
		if order == nil || order.Status != StatusClosed {
			return fail("M-15")
		}
		if !in.SignatureValid {
			p, err := s.rejectedPayment(ctx, tx, actor, uint64(order.ID), origin.OrderNo, in.RefundNo, eventLateRefundCallback, "M-28", order.Status, in.Amount, false)
			out = p
			return err
		}
		if in.Amount != origin.Amount || in.Amount != order.TotalAmount {
			p, err := s.rejectedPayment(ctx, tx, actor, uint64(order.ID), origin.OrderNo, in.RefundNo, eventLateRefundCallback, "M-29", order.Status, in.Amount, true)
			out = p
			return err
		}
		if !in.Success {
			p := s.newPayment(uint64(order.ID), origin.OrderNo, in.RefundNo, dedupFail, EventLateRefundFailed, ResultLateRefundFailed, "M-08", messages["M-26"], order.Status, in.Amount, true, false, false, false, uint64(origin.ID), actor.UserID)
			if err := tx.CreatePayment(ctx, p); err != nil {
				return err
			}
			out = p
			return fail("M-08")
		}
		p := s.newPayment(uint64(order.ID), origin.OrderNo, in.RefundNo, dedupOK, EventLateRefundSuccess, ResultLateRefundSucceeded, "M-26", messages["M-26"], order.Status, in.Amount, true, true, false, false, uint64(origin.ID), actor.UserID)
		if err := tx.CreatePayment(ctx, p); err != nil {
			return err
		}
		out = p
		return nil
	})
	if errors.Is(err, ErrDuplicateDedupKey) {
		return s.rejectOutsideTx(ctx, actor, "", in.RefundNo, EventRepeatRefund, "M-10")
	}
	return out, err
}

func (s *OrderService) RetryLatePaymentRefund(ctx context.Context, actor Actor, eventID uint64, refundNo, remark string) (*model.Payment, error) {
	if err := s.requireRole(ctx, actor, "RetryLatePaymentRefund", "", RoleCustomerService); err != nil {
		return nil, err
	}
	if remark == "" {
		return s.rejectOutsideTx(ctx, actor, "", "LATE_REFUND_RETRY:"+refundNo, EventLateRefundRetry, "M-24")
	}
	var out *model.Payment
	err := s.repo.WithTransaction(ctx, func(tx OrderRepository) error {
		origin, err := tx.GetPaymentByID(ctx, eventID)
		if err != nil {
			return err
		}
		if origin == nil || origin.EventType != EventLatePayment {
			return fail("M-14")
		}
		verified, err := tx.HasPaymentEvent(ctx, eventID, EventLatePaymentVerified)
		if err != nil {
			return err
		}
		requested, err := tx.GetPaymentByDedupKey(ctx, DedupLateRefundReqPrefix+refundNo)
		if err != nil {
			return err
		}
		if !verified || requested == nil {
			return fail("M-24")
		}
		p := s.newPayment(origin.OrderID, origin.OrderNo, refundNo, "", EventLateRefundRetry, ResultLateRefundRetried, "M-26", remark, origin.OrderStatusSnapshot, origin.Amount, true, false, false, false, uint64(origin.ID), actor.UserID)
		if err := tx.CreatePayment(ctx, p); err != nil {
			return err
		}
		out = p
		return nil
	})
	return out, err
}

func (s *OrderService) GetOrder(ctx context.Context, actor Actor, orderNo string) (*model.Order, error) {
	if err := s.requireRole(ctx, actor, "GetOrder", orderNo, RoleBuyer, RoleOps, RoleWarehouse, RoleCustomerService); err != nil {
		return nil, err
	}
	order, err := s.repo.GetOrder(ctx, orderNo)
	if err != nil {
		return nil, err
	}
	if order == nil {
		return nil, fail("M-30")
	}
	if actor.Role == RoleBuyer && order.BuyerID != actor.UserID {
		return nil, s.denyAndLog(ctx, actor, "GetOrder", orderNo)
	}
	return order, nil
}

func (s *OrderService) GetOpsSummary(ctx context.Context, actor Actor) (*OpsSummary, error) {
	if err := s.requireRole(ctx, actor, "GetOpsSummary", "", RoleOps); err != nil {
		return nil, err
	}
	summary := &OpsSummary{}
	var err error
	if summary.TotalOrders, err = s.repo.CountOrders(ctx); err != nil {
		return nil, err
	}
	if summary.EffectivePaymentAmount, err = s.repo.SumEffectivePaymentsByEventType(ctx, EventPaymentSuccess); err != nil {
		return nil, err
	}
	if summary.LatePaymentEvents, err = s.repo.CountPaymentsByEventType(ctx, EventLatePayment); err != nil {
		return nil, err
	}
	if summary.LatePaymentRefundedEvents, err = s.repo.CountPaymentsByEventType(ctx, EventLateRefundSuccess); err != nil {
		return nil, err
	}
	if summary.RefundedOrders, err = s.repo.CountOrdersByStatus(ctx, StatusRefunded); err != nil {
		return nil, err
	}
	if summary.ShippedOrders, err = s.repo.CountOrdersByStatus(ctx, StatusShipped); err != nil {
		return nil, err
	}
	if summary.StockRestoredEvents, err = s.repo.CountPaymentsByEventType(ctx, EventStockRestore); err != nil {
		return nil, err
	}
	if summary.DuplicateReleaseNoopEvents, err = s.repo.CountPaymentsByResult(ctx, ResultDuplicateNoop); err != nil {
		return nil, err
	}
	if summary.DuplicateRefundEvents, err = s.repo.CountPaymentsByResult(ctx, ResultRepeatRefundNoop); err != nil {
		return nil, err
	}
	summary.NoDuplicateReleaseRefund = summary.DuplicateReleaseNoopEvents == 0 && summary.DuplicateRefundEvents == 0
	return summary, nil
}
