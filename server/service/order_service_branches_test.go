package service

// 竞态检测说明：go test ./... -race 需要 CGO_ENABLED=1 与可用 C 编译器（gcc/clang）。
// PowerShell：$env:CGO_ENABLED = "1"; go test ./... -race -count=1
// bash：CGO_ENABLED=1 go test ./... -race -count=1

import (
	"context"
	"errors"
	"testing"
	"time"

	"shop-trade/server/model"
)

// 本文件补齐 service 层异常与重复操作分支，仍属开发会话单元测试草案。
// 所有断言读取 service 返回的真实结果，不写死成功、不删失败 case。

func refundProcessingFixture(t *testing.T, svc *OrderService, payTradeNo string) (string, int64) {
	t.Helper()
	order, err := svc.CreateOrder(ctx, buyer, 1, 2)
	if err != nil {
		t.Fatal(err)
	}
	payOrder(t, svc, order.OrderNo, payTradeNo)
	if _, err := svc.ApplyRefund(ctx, buyer, order.OrderNo, "不想要了"); err != nil {
		t.Fatal(err)
	}
	if _, err := svc.ApproveRefund(ctx, cs, order.OrderNo, "同意整单退款"); err != nil {
		t.Fatal(err)
	}
	return order.OrderNo, order.TotalAmount
}

func latePaymentFixture(t *testing.T) (*OrderService, *memoryRepository, uint64, string, int64) {
	t.Helper()
	svc, repo := newTestService(5)
	order, err := svc.CreateOrder(ctx, buyer, 1, 2)
	if err != nil {
		t.Fatal(err)
	}
	svc.now = func() time.Time { return fixedTime.Add(11 * time.Minute) }
	_, err = svc.HandlePaymentCallback(ctx, mockCh, PaymentCallback{
		OrderNo: order.OrderNo, ChannelTradeNo: "LATE-BRANCH-1", Amount: 20000, SignatureValid: true,
	})
	assertBizCode(t, err, "M-09")
	event := findPaymentByResult(t, repo, ResultLatePaymentPending)
	return svc, repo, uint64(event.ID), order.OrderNo, order.TotalAmount
}

func setOrderStatusForTest(repo *memoryRepository, orderNo, status string) {
	repo.mu.Lock()
	defer repo.mu.Unlock()
	repo.orders[orderNo].Status = status
}

func TestRefundCallbackBranchCoverage(t *testing.T) {
	svc, _ := newTestService(5)
	orderNo, amount := refundProcessingFixture(t, svc, "RF-PAY-BRANCH")

	_, err := svc.HandleRefundCallback(ctx, mockCh, RefundCallback{
		OrderNo: orderNo, RefundChannelTradeNo: "RF-B1", Amount: amount, SignatureValid: false,
	})
	assertBizCode(t, err, "M-28")

	_, err = svc.HandleRefundCallback(ctx, mockCh, RefundCallback{
		OrderNo: orderNo, RefundChannelTradeNo: "RF-B2", Amount: amount - 1, SignatureValid: true,
	})
	assertBizCode(t, err, "M-29")

	_, err = svc.HandleRefundCallback(ctx, mockCh, RefundCallback{
		OrderNo: "UNKNOWN", RefundChannelTradeNo: "RF-B3", Amount: amount, SignatureValid: true,
	})
	assertBizCode(t, err, "M-30")

	order2, _ := svc.CreateOrder(ctx, buyer, 1, 1)
	payOrder(t, svc, order2.OrderNo, "RF-PAY-BRANCH-2")
	_, err = svc.HandleRefundCallback(ctx, mockCh, RefundCallback{
		OrderNo: order2.OrderNo, RefundChannelTradeNo: "RF-B4", Amount: 10000, SignatureValid: true,
	})
	assertBizCode(t, err, "M-05")

	failed := RefundCallback{
		OrderNo: orderNo, RefundChannelTradeNo: "RF-B1", Amount: amount, SignatureValid: true, Success: false,
	}
	_, err = svc.HandleRefundCallback(ctx, mockCh, failed)
	assertBizCode(t, err, "M-08")
	res, err := svc.HandleRefundCallback(ctx, mockCh, failed)
	if err != nil || res == nil || res.Result != ResultDuplicateNoop {
		t.Fatalf("duplicate failed refund callback must be idempotent: res=%v err=%v", res, err)
	}

	failed.Success = true
	res, err = svc.HandleRefundCallback(ctx, mockCh, failed)
	if err != nil || res == nil || res.Result != ResultRefundSucceeded {
		t.Fatalf("retry refund should succeed: res=%v err=%v", res, err)
	}

	_, err = svc.HandleRefundCallback(ctx, mockCh, RefundCallback{
		OrderNo: "ANOTHER-ORDER", RefundChannelTradeNo: "RF-B1", Amount: amount, SignatureValid: true, Success: true,
	})
	assertBizCode(t, err, "M-27")

	res, err = svc.HandleRefundCallback(ctx, mockCh, RefundCallback{
		OrderNo: orderNo, RefundChannelTradeNo: "RF-BRAND-NEW", Amount: amount, SignatureValid: true, Success: true,
	})
	if err != nil || res == nil || res.Result != ResultRepeatRefundNoop {
		t.Fatalf("refunded order must reject second refund: res=%v err=%v", res, err)
	}
}

func TestLatePaymentRefundBranchCoverage(t *testing.T) {
	svc, repo, eventID, orderNo, amount := latePaymentFixture(t)
	valid := LateRefundCallback{
		EventID: eventID, RefundNo: "LR-1", Amount: amount, SignatureValid: true, Success: true,
	}

	_, err := svc.HandleLatePaymentRefundCallback(ctx, mockCh, valid)
	assertBizCode(t, err, "M-24")
	_, err = svc.RetryLatePaymentRefund(ctx, cs, eventID, "LR-1", "客服重试")
	assertBizCode(t, err, "M-24")
	_, err = svc.HandleLatePaymentRefundCallback(ctx, mockCh, LateRefundCallback{EventID: eventID, Amount: amount})
	assertBizCode(t, err, "M-27")
	_, err = svc.HandleLatePaymentRefundCallback(ctx, buyer, valid)
	assertBizCode(t, err, "M-20")
	missing := valid
	missing.EventID = 99999
	_, err = svc.HandleLatePaymentRefundCallback(ctx, mockCh, missing)
	assertBizCode(t, err, "M-14")

	if _, err := svc.VerifyLatePayment(ctx, cs, eventID, "客服核实迟到支付"); err != nil {
		t.Fatal(err)
	}
	_, err = svc.VerifyLatePayment(ctx, cs, eventID, "重复核实")
	assertBizCode(t, err, "M-10")
	_, err = svc.HandleLatePaymentRefundCallback(ctx, mockCh, valid)
	assertBizCode(t, err, "M-24")

	if _, err := svc.InitiateLatePaymentRefund(ctx, cs, eventID, "LR-1", "核实后发起退款"); err != nil {
		t.Fatal(err)
	}
	_, err = svc.InitiateLatePaymentRefund(ctx, cs, eventID, "LR-1", "重复发起")
	assertBizCode(t, err, "M-10")

	badSign := valid
	badSign.SignatureValid = false
	_, err = svc.HandleLatePaymentRefundCallback(ctx, mockCh, badSign)
	assertBizCode(t, err, "M-28")
	badAmount := valid
	badAmount.Amount = amount - 1
	_, err = svc.HandleLatePaymentRefundCallback(ctx, mockCh, badAmount)
	assertBizCode(t, err, "M-29")

	failed := valid
	failed.Success = false
	_, err = svc.HandleLatePaymentRefundCallback(ctx, mockCh, failed)
	assertBizCode(t, err, "M-08")
	res, err := svc.HandleLatePaymentRefundCallback(ctx, mockCh, failed)
	if err != nil || res == nil || res.Result != ResultDuplicateNoop {
		t.Fatalf("duplicate failed late refund must be idempotent: res=%v err=%v", res, err)
	}

	res, err = svc.HandleLatePaymentRefundCallback(ctx, mockCh, valid)
	if err != nil || res == nil || res.Result != ResultLateRefundSucceeded {
		t.Fatalf("late refund should succeed without changing terminal state: res=%v err=%v", res, err)
	}
	res, err = svc.HandleLatePaymentRefundCallback(ctx, mockCh, valid)
	if err != nil || res == nil || res.Result != ResultRepeatRefundNoop {
		t.Fatalf("duplicate late refund must not create second refund: res=%v err=%v", res, err)
	}
	if o := mustOrder(t, svc, orderNo); o.Status != StatusClosed {
		t.Fatalf("late refund must keep closed terminal state, got %s", o.Status)
	}

	retried, err := svc.RetryLatePaymentRefund(ctx, cs, eventID, "LR-1", "客服登记重试")
	if err != nil || retried == nil || retried.Result != ResultLateRefundRetried {
		t.Fatalf("late refund retry failed: res=%v err=%v", retried, err)
	}
	_, err = svc.RetryLatePaymentRefund(ctx, cs, 99999, "LR-1", "客服登记重试")
	assertBizCode(t, err, "M-14")
	_, err = svc.RetryLatePaymentRefund(ctx, cs, eventID, "LR-1", "")
	assertBizCode(t, err, "M-24")
	_, err = svc.RetryLatePaymentRefund(ctx, buyer, eventID, "LR-1", "越权重试")
	assertBizCode(t, err, "M-20")

	setOrderStatusForTest(repo, orderNo, StatusWaitingShipment)
	second := valid
	second.RefundNo = "LR-2"
	if _, err := svc.InitiateLatePaymentRefund(ctx, cs, eventID, "LR-2", "第二次退款请求"); err != nil {
		t.Fatal(err)
	}
	_, err = svc.HandleLatePaymentRefundCallback(ctx, mockCh, second)
	assertBizCode(t, err, "M-15")
}

type opsFaultRepository struct {
	OrderRepository
	failAt int
	calls  int
}

func (f *opsFaultRepository) next() error {
	f.calls++
	if f.calls == f.failAt {
		return errors.New("injected database error")
	}
	return nil
}

func (f *opsFaultRepository) CountOrders(c context.Context) (int64, error) {
	if err := f.next(); err != nil {
		return 0, err
	}
	return f.OrderRepository.CountOrders(c)
}

func (f *opsFaultRepository) SumEffectivePaymentsByEventType(c context.Context, eventType string) (int64, error) {
	if err := f.next(); err != nil {
		return 0, err
	}
	return f.OrderRepository.SumEffectivePaymentsByEventType(c, eventType)
}

func (f *opsFaultRepository) CountPaymentsByEventType(c context.Context, eventType string) (int64, error) {
	if err := f.next(); err != nil {
		return 0, err
	}
	return f.OrderRepository.CountPaymentsByEventType(c, eventType)
}

func (f *opsFaultRepository) CountOrdersByStatus(c context.Context, status string) (int64, error) {
	if err := f.next(); err != nil {
		return 0, err
	}
	return f.OrderRepository.CountOrdersByStatus(c, status)
}

func (f *opsFaultRepository) CountPaymentsByResult(c context.Context, result string) (int64, error) {
	if err := f.next(); err != nil {
		return 0, err
	}
	return f.OrderRepository.CountPaymentsByResult(c, result)
}

func TestOpsSummaryFaultBranches(t *testing.T) {
	for step := 1; step <= 9; step++ {
		base := newMemoryRepository(testGoodsWithID())
		faulty := &opsFaultRepository{OrderRepository: base, failAt: step}
		svc := NewOrderService(faulty)
		svc.now = func() time.Time { return fixedTime }
		if _, err := svc.GetOpsSummary(ctx, ops); err == nil {
			t.Fatalf("ops summary step %d should propagate repository error", step)
		}
	}
	svc, _ := newTestService(5)
	summary, err := svc.GetOpsSummary(ctx, ops)
	if err != nil || summary == nil || !summary.NoDuplicateReleaseRefund {
		t.Fatalf("clean ops summary failed: %+v %v", summary, err)
	}
}

func testGoodsWithID() *model.Goods {
	g := testGoods(5)
	g.ID = 1
	return g
}

type duplicateCreateRepository struct {
	OrderRepository
	inTx    bool
	trigger string
}

func (d *duplicateCreateRepository) WithTransaction(c context.Context, fn func(OrderRepository) error) error {
	return d.OrderRepository.WithTransaction(c, func(tx OrderRepository) error {
		return fn(&duplicateCreateRepository{OrderRepository: tx, inTx: true, trigger: d.trigger})
	})
}

func (d *duplicateCreateRepository) CreatePayment(c context.Context, p *model.Payment) error {
	if d.inTx && p.DedupKey != nil && p.ChannelTradeNo == d.trigger {
		return ErrDuplicateDedupKey
	}
	return d.OrderRepository.CreatePayment(c, p)
}

func TestDuplicateDedupKeyMappedToChineseReason(t *testing.T) {
	svc := NewOrderService(&duplicateCreateRepository{
		OrderRepository: newMemoryRepository(testGoodsWithID()), trigger: "PAY-DEDUP",
	})
	svc.now = func() time.Time { return fixedTime }
	order, err := svc.CreateOrder(ctx, buyer, 1, 1)
	if err != nil {
		t.Fatal(err)
	}
	_, err = svc.HandlePaymentCallback(ctx, mockCh, PaymentCallback{
		OrderNo: order.OrderNo, ChannelTradeNo: "PAY-DEDUP", Amount: order.TotalAmount, SignatureValid: true,
	})
	assertBizCode(t, err, "M-27")

	svc2 := NewOrderService(&duplicateCreateRepository{
		OrderRepository: newMemoryRepository(testGoodsWithID()), trigger: "RF-DEDUP",
	})
	svc2.now = func() time.Time { return fixedTime }
	orderNo, amount := refundProcessingFixture(t, svc2, "RF-PAY-DEDUP")
	_, err = svc2.HandleRefundCallback(ctx, mockCh, RefundCallback{
		OrderNo: orderNo, RefundChannelTradeNo: "RF-DEDUP", Amount: amount, SignatureValid: true, Success: true,
	})
	assertBizCode(t, err, "M-10")
}

func TestPaymentAndCancelTerminalBranches(t *testing.T) {
	svc, _ := newTestService(5)
	cancelled, _ := svc.CreateOrder(ctx, buyer, 1, 1)
	if _, err := svc.CancelOrder(ctx, buyer, cancelled.OrderNo); err != nil {
		t.Fatal(err)
	}
	_, err := svc.HandlePaymentCallback(ctx, mockCh, PaymentCallback{
		OrderNo: cancelled.OrderNo, ChannelTradeNo: "PAY-CANCELLED", Amount: 10000, SignatureValid: true,
	})
	assertBizCode(t, err, "M-15")

	paid, _ := svc.CreateOrder(ctx, buyer, 1, 1)
	payOrder(t, svc, paid.OrderNo, "PAY-ALREADY")
	_, err = svc.HandlePaymentCallback(ctx, mockCh, PaymentCallback{
		OrderNo: paid.OrderNo, ChannelTradeNo: "PAY-SECOND", Amount: 10000, SignatureValid: true,
	})
	assertBizCode(t, err, "M-05")

	shipped, _ := svc.CreateOrder(ctx, buyer, 1, 1)
	payOrder(t, svc, shipped.OrderNo, "PAY-SHIP-BRANCH")
	if _, err := svc.RegisterShipment(ctx, warehouse, shipped.OrderNo, "顺丰", "SF-BRANCH"); err != nil {
		t.Fatal(err)
	}
	_, err = svc.CancelOrder(ctx, buyer, shipped.OrderNo)
	assertBizCode(t, err, "M-10")
	_, err = svc.ApplyRefund(ctx, buyer, shipped.OrderNo, "已发货申请退款")
	assertBizCode(t, err, "M-11")

	svc2, repo := newTestService(5)
	expired, _ := svc2.CreateOrder(ctx, buyer, 1, 1)
	svc2.now = func() time.Time { return fixedTime.Add(11 * time.Minute) }
	_, err = svc2.CancelOrder(ctx, buyer, expired.OrderNo)
	assertBizCode(t, err, "M-06")
	if o := mustOrder(t, svc2, expired.OrderNo); o.Status != StatusClosed {
		t.Fatalf("expired cancel should close order, got %s", o.Status)
	}
	if available, occupied := mustStock(t, repo, 1); available != 5 || occupied != 0 {
		t.Fatalf("expired cancel should release stock once: %d/%d", available, occupied)
	}
	closed, err := svc2.CloseExpiredOrders(ctx, ops, 0)
	if err != nil || closed != 0 {
		t.Fatalf("no pending expired order should remain: closed=%d err=%v", closed, err)
	}
}

func TestRefundAuditAndShipmentRejections(t *testing.T) {
	svc, _ := newTestService(5)
	for name, call := range map[string]func() error{
		"RejectRefund":  func() error { _, err := svc.RejectRefund(ctx, cs, "UNKNOWN", "备注"); return err },
		"ApproveRefund": func() error { _, err := svc.ApproveRefund(ctx, cs, "UNKNOWN", "备注"); return err },
		"RetryRefund":   func() error { _, err := svc.RetryRefund(ctx, cs, "UNKNOWN", "备注"); return err },
	} {
		if err := call(); err == nil {
			t.Fatalf("%s on unknown order must be rejected", name)
		} else {
			assertBizCode(t, err, "M-30")
		}
	}

	pending, _ := svc.CreateOrder(ctx, buyer, 1, 1)
	_, err := svc.RejectRefund(ctx, cs, pending.OrderNo, "备注")
	assertBizCode(t, err, "M-05")
	_, err = svc.ApproveRefund(ctx, cs, pending.OrderNo, "备注")
	assertBizCode(t, err, "M-05")
	_, err = svc.RetryRefund(ctx, cs, pending.OrderNo, "备注")
	assertBizCode(t, err, "M-05")

	_, err = svc.RegisterShipment(ctx, warehouse, "UNKNOWN", "顺丰", "SF-UNKNOWN")
	assertBizCode(t, err, "M-30")
	_, err = svc.RegisterShipment(ctx, warehouse, pending.OrderNo, "顺丰", "SF-PENDING")
	assertBizCode(t, err, "M-18")

	refunded, _ := svc.CreateOrder(ctx, buyer, 1, 1)
	payOrder(t, svc, refunded.OrderNo, "PAY-REFUNDED-BRANCH")
	if _, err := svc.ApplyRefund(ctx, buyer, refunded.OrderNo, "不想要了"); err != nil {
		t.Fatal(err)
	}
	if _, err := svc.ApproveRefund(ctx, cs, refunded.OrderNo, "同意整单退款"); err != nil {
		t.Fatal(err)
	}
	res, err := svc.HandleRefundCallback(ctx, mockCh, RefundCallback{
		OrderNo: refunded.OrderNo, RefundChannelTradeNo: "RF-REFUNDED-BRANCH",
		Amount: 10000, SignatureValid: true, Success: true,
	})
	if err != nil || res == nil || res.Result != ResultRefundSucceeded {
		t.Fatalf("refund for shipment rejection setup failed: res=%v err=%v", res, err)
	}
	_, err = svc.RegisterShipment(ctx, warehouse, refunded.OrderNo, "顺丰", "SF-REFUNDED")
	assertBizCode(t, err, "M-11")
	_, err = svc.RejectRefund(ctx, cs, refunded.OrderNo, "重复审核")
	assertBizCode(t, err, "M-05")
	_, err = svc.ApproveRefund(ctx, cs, refunded.OrderNo, "重复审核")
	assertBizCode(t, err, "M-05")
	_, err = svc.RetryRefund(ctx, cs, refunded.OrderNo, "重复重试")
	assertBizCode(t, err, "M-05")
}

type zeroRowsRepository struct {
	OrderRepository
	inTx bool
}

func (z *zeroRowsRepository) WithTransaction(c context.Context, fn func(OrderRepository) error) error {
	return z.OrderRepository.WithTransaction(c, func(tx OrderRepository) error {
		return fn(&zeroRowsRepository{OrderRepository: tx, inTx: true})
	})
}

func (z *zeroRowsRepository) UpdateOrderIfStatus(c context.Context, order *model.Order, allowed []string, fields map[string]interface{}) (int64, error) {
	if z.inTx {
		return 0, nil
	}
	return z.OrderRepository.UpdateOrderIfStatus(c, order, allowed, fields)
}

func TestConcurrentConditionUpdateMissLeavesAuditOnly(t *testing.T) {
	svc := NewOrderService(&zeroRowsRepository{OrderRepository: newMemoryRepository(testGoodsWithID())})
	svc.now = func() time.Time { return fixedTime }
	order, err := svc.CreateOrder(ctx, buyer, 1, 1)
	if err != nil {
		t.Fatal(err)
	}
	_, err = svc.CancelOrder(ctx, buyer, order.OrderNo)
	assertBizCode(t, err, "M-10")
	if o := mustOrder(t, svc, order.OrderNo); o.Status != StatusPendingPayment {
		t.Fatalf("condition update miss must not change order state, got %s", o.Status)
	}
}
