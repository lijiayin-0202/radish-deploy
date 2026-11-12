package service

// 竞态检测说明：go test ./... -race 需要 CGO_ENABLED=1 与可用 C 编译器（gcc/clang）。
// PowerShell：$env:CGO_ENABLED = "1"; go test ./... -race -count=1
// bash：CGO_ENABLED=1 go test ./... -race -count=1

import (
	"context"
	"errors"
	"sync"
	"testing"
	"time"

	"shop-trade/server/model"
)

var (
	ctx        = context.Background()
	fixedTime  = time.Date(2026, 11, 12, 10, 0, 0, 0, time.UTC)
	buyer      = Actor{UserID: 1001, Role: RoleBuyer}
	otherBuyer = Actor{UserID: 1002, Role: RoleBuyer}
	ops        = Actor{UserID: 2001, Role: RoleOps}
	warehouse  = Actor{UserID: 3001, Role: RoleWarehouse}
	cs         = Actor{UserID: 4001, Role: RoleCustomerService}
	mockCh     = Actor{UserID: 5001, Role: RoleMockChannel}
)

func assertBizCode(t *testing.T, err error, code string) {
	t.Helper()
	if err == nil {
		t.Fatalf("expected BizError %s, got nil", code)
	}
	var bizErr *BizError
	if !errors.As(err, &bizErr) || bizErr.Code != code {
		t.Fatalf("expected BizError %s, got %v", code, err)
	}
}

func testGoods(stock int) *model.Goods {
	return &model.Goods{
		GVA_MODEL:      model.Goods{}.GVA_MODEL,
		GoodsNo:        "GOODS-ACT-001",
		Name:           "活动商品",
		UnitPrice:      10000,
		AvailableStock: stock,
		Status:         GoodsStatusOnSale,
	}
}

func newTestService(stock int) (*OrderService, *memoryRepository) {
	g := testGoods(stock)
	g.ID = 1
	repo := newMemoryRepository(g)
	svc := NewOrderService(repo)
	svc.now = func() time.Time { return fixedTime }
	return svc, repo
}

func mustStock(t *testing.T, repo *memoryRepository, goodsID uint64) (int, int) {
	t.Helper()
	g, err := repo.LockGoods(ctx, goodsID)
	if err != nil || g == nil {
		t.Fatalf("LockGoods failed: g=%v err=%v", g, err)
	}
	return g.AvailableStock, g.OccupiedStock
}

func mustOrder(t *testing.T, svc *OrderService, orderNo string) *model.Order {
	t.Helper()
	order, err := svc.GetOrder(ctx, ops, orderNo)
	if err != nil || order == nil {
		t.Fatalf("GetOrder failed: order=%v err=%v", order, err)
	}
	return order
}

func findPaymentByResult(t *testing.T, repo *memoryRepository, result string) *model.Payment {
	t.Helper()
	repo.mu.Lock()
	defer repo.mu.Unlock()
	for _, p := range repo.payments {
		if p.Result == result {
			return clonePayment(p)
		}
	}
	t.Fatalf("payment result %s not found", result)
	return nil
}

func payOrder(t *testing.T, svc *OrderService, orderNo, tradeNo string) {
	t.Helper()
	order := mustOrder(t, svc, orderNo)
	res, err := svc.HandlePaymentCallback(ctx, mockCh, PaymentCallback{
		OrderNo:        orderNo,
		ChannelTradeNo: tradeNo,
		Amount:         order.TotalAmount,
		SignatureValid: true,
	})
	if err != nil || res == nil || res.Result != ResultPaid {
		t.Fatalf("payment callback failed: res=%v err=%v", res, err)
	}
}

func countEvent(t *testing.T, repo *memoryRepository, eventType string) int64 {
	t.Helper()
	n, err := repo.CountPaymentsByEventType(ctx, eventType)
	if err != nil {
		t.Fatal(err)
	}
	return n
}

func countResult(t *testing.T, repo *memoryRepository, result string) int64 {
	t.Helper()
	n, err := repo.CountPaymentsByResult(ctx, result)
	if err != nil {
		t.Fatal(err)
	}
	return n
}

func TestCreateOrderNormalAndValidation(t *testing.T) {
	svc, repo := newTestService(5)
	order, err := svc.CreateOrder(ctx, buyer, 1, 2)
	if err != nil || order == nil {
		t.Fatalf("CreateOrder failed: %v", err)
	}
	if order.Status != StatusPendingPayment || order.TotalAmount != 20000 || !order.ExpiresAt.Equal(fixedTime.Add(10*time.Minute)) {
		t.Fatalf("unexpected order: %+v", order)
	}
	available, occupied := mustStock(t, repo, 1)
	if available != 3 || occupied != 2 {
		t.Fatalf("stock mismatch available=%d occupied=%d", available, occupied)
	}

	_, err = svc.CreateOrder(ctx, buyer, 0, 1)
	assertBizCode(t, err, "M-04")
	_, err = svc.CreateOrder(ctx, buyer, 1, 3)
	assertBizCode(t, err, "M-03")
	_, err = svc.CreateOrder(ctx, ops, 1, 1)
	assertBizCode(t, err, "M-20")

	offSvc, offRepo := newTestService(5)
	g, _ := offRepo.LockGoods(ctx, 1)
	g.Status = "下架"
	offRepo.goods[1] = g
	_, err = offSvc.CreateOrder(ctx, buyer, 1, 1)
	assertBizCode(t, err, "M-01")

	shortSvc, _ := newTestService(0)
	_, err = shortSvc.CreateOrder(ctx, buyer, 1, 1)
	assertBizCode(t, err, "M-02")
}

func TestPaymentCallbackNormalIdempotencyAndRejections(t *testing.T) {
	svc, repo := newTestService(5)
	order, err := svc.CreateOrder(ctx, buyer, 1, 2)
	if err != nil {
		t.Fatal(err)
	}
	in := PaymentCallback{OrderNo: order.OrderNo, ChannelTradeNo: "PAY-1", Amount: 20000, SignatureValid: true}
	res, err := svc.HandlePaymentCallback(ctx, mockCh, in)
	if err != nil || res.Result != ResultPaid {
		t.Fatalf("payment failed: %v %v", res, err)
	}
	if o := mustOrder(t, svc, order.OrderNo); o.Status != StatusWaitingShipment {
		t.Fatalf("unexpected status %s", o.Status)
	}
	if countEvent(t, repo, EventPaymentSuccess) != 1 {
		t.Fatal("effective payment should be exactly one")
	}
	res, err = svc.HandlePaymentCallback(ctx, mockCh, in)
	if err != nil || res.Result != ResultRepeatPaymentNoop {
		t.Fatalf("repeat payment failed: %v %v", res, err)
	}
	if countEvent(t, repo, EventPaymentSuccess) != 1 {
		t.Fatal("repeat payment must not add effective record")
	}

	order2, _ := svc.CreateOrder(ctx, buyer, 1, 1)
	_, err = svc.HandlePaymentCallback(ctx, mockCh, PaymentCallback{OrderNo: order2.OrderNo, ChannelTradeNo: "PAY-1", Amount: 10000, SignatureValid: true})
	assertBizCode(t, err, "M-27")
	_, err = svc.HandlePaymentCallback(ctx, mockCh, PaymentCallback{OrderNo: "UNKNOWN", ChannelTradeNo: "PAY-X", Amount: 10000, SignatureValid: true})
	assertBizCode(t, err, "M-30")
	_, err = svc.HandlePaymentCallback(ctx, mockCh, PaymentCallback{OrderNo: order2.OrderNo, ChannelTradeNo: "PAY-BAD-SIGN", Amount: 10000, SignatureValid: false})
	assertBizCode(t, err, "M-28")
	_, err = svc.HandlePaymentCallback(ctx, mockCh, PaymentCallback{OrderNo: order2.OrderNo, ChannelTradeNo: "PAY-BAD-AMT", Amount: 9999, SignatureValid: true})
	assertBizCode(t, err, "M-29")
	_, err = svc.HandlePaymentCallback(ctx, mockCh, PaymentCallback{OrderNo: order2.OrderNo, ChannelTradeNo: "", Amount: 10000, SignatureValid: true})
	assertBizCode(t, err, "M-27")
	_, err = svc.HandlePaymentCallback(ctx, buyer, PaymentCallback{OrderNo: order2.OrderNo, ChannelTradeNo: "PAY-ROLE", Amount: 10000, SignatureValid: true})
	assertBizCode(t, err, "M-20")
}

func TestCancelCloseExpiredAndDuplicateRelease(t *testing.T) {
	svc, repo := newTestService(5)
	order1, _ := svc.CreateOrder(ctx, buyer, 1, 1)
	order2, _ := svc.CreateOrder(ctx, buyer, 1, 1)
	_, err := svc.CancelOrder(ctx, buyer, order1.OrderNo)
	if err != nil {
		t.Fatal(err)
	}
	if o := mustOrder(t, svc, order1.OrderNo); o.Status != StatusCancelled {
		t.Fatalf("unexpected status %s", o.Status)
	}
	_, err = svc.CancelOrder(ctx, buyer, order1.OrderNo)
	assertBizCode(t, err, "M-10")
	_, err = svc.CancelOrder(ctx, otherBuyer, order2.OrderNo)
	assertBizCode(t, err, "M-20")

	svc.now = func() time.Time { return fixedTime.Add(11 * time.Minute) }
	closed, err := svc.CloseExpiredOrders(ctx, ops, 10)
	if err != nil || closed != 1 {
		t.Fatalf("CloseExpiredOrders failed: closed=%d err=%v", closed, err)
	}
	if o := mustOrder(t, svc, order2.OrderNo); o.Status != StatusClosed {
		t.Fatalf("unexpected status %s", o.Status)
	}
	available, occupied := mustStock(t, repo, 1)
	if available != 5 || occupied != 0 {
		t.Fatalf("stock should be fully released: available=%d occupied=%d", available, occupied)
	}
	_, err = svc.CloseExpiredOrders(ctx, buyer, 10)
	assertBizCode(t, err, "M-20")
}

func TestPresaleRefundFailureRetrySuccessAndDuplicate(t *testing.T) {
	svc, repo := newTestService(5)
	order, _ := svc.CreateOrder(ctx, buyer, 1, 2)
	payOrder(t, svc, order.OrderNo, "PAY-REFUND")

	if _, err := svc.ApplyRefund(ctx, buyer, order.OrderNo, "不想要了"); err != nil {
		t.Fatal(err)
	}
	if o := mustOrder(t, svc, order.OrderNo); o.Status != StatusRefundReview {
		t.Fatalf("unexpected status %s", o.Status)
	}
	_, err := svc.RegisterShipment(ctx, warehouse, order.OrderNo, "顺丰", "SF123")
	assertBizCode(t, err, "M-22")
	if _, err := svc.RejectRefund(ctx, cs, order.OrderNo, "补充材料后恢复可发货"); err != nil {
		t.Fatal(err)
	}
	if o := mustOrder(t, svc, order.OrderNo); o.Status != StatusWaitingShipment {
		t.Fatalf("unexpected status %s", o.Status)
	}
	if _, err := svc.ApplyRefund(ctx, buyer, order.OrderNo, "再次申请"); err != nil {
		t.Fatal(err)
	}
	if _, err := svc.ApproveRefund(ctx, cs, order.OrderNo, "同意整单退款"); err != nil {
		t.Fatal(err)
	}

	cb := RefundCallback{OrderNo: order.OrderNo, RefundChannelTradeNo: "RF-1", Amount: 20000, SignatureValid: true, Success: false}
	_, err = svc.HandleRefundCallback(ctx, mockCh, cb)
	assertBizCode(t, err, "M-08")
	if o := mustOrder(t, svc, order.OrderNo); o.RefundState != RefundStateFailed {
		t.Fatalf("unexpected refund state %s", o.RefundState)
	}
	if _, err := svc.RetryRefund(ctx, cs, order.OrderNo, "客服重试"); err != nil {
		t.Fatal(err)
	}
	cb.Success = true
	res, err := svc.HandleRefundCallback(ctx, mockCh, cb)
	if err != nil || res.Result != ResultRefundSucceeded {
		t.Fatalf("refund success failed: %v %v", res, err)
	}
	if o := mustOrder(t, svc, order.OrderNo); o.Status != StatusRefunded || !o.StockRestored {
		t.Fatalf("unexpected refunded order: %+v", o)
	}
	available, occupied := mustStock(t, repo, 1)
	if available != 5 || occupied != 0 {
		t.Fatalf("stock should be restored once: available=%d occupied=%d", available, occupied)
	}
	if countEvent(t, repo, EventStockRestore) != 1 {
		t.Fatal("stock restore event should be exactly one")
	}
	res, err = svc.HandleRefundCallback(ctx, mockCh, cb)
	if err != nil || res.Result != ResultRepeatRefundNoop {
		t.Fatalf("duplicate refund callback failed: %v %v", res, err)
	}
	if countEvent(t, repo, EventStockRestore) != 1 {
		t.Fatal("duplicate refund must not restore stock again")
	}
}

func TestRefundShipmentCompetitionAndShipmentValidation(t *testing.T) {
	svc, _ := newTestService(5)
	order, _ := svc.CreateOrder(ctx, buyer, 1, 1)
	payOrder(t, svc, order.OrderNo, "PAY-RACE")

	_, err := svc.RegisterShipment(ctx, warehouse, order.OrderNo, "", "")
	assertBizCode(t, err, "M-23")
	_, err = svc.RegisterShipment(ctx, buyer, order.OrderNo, "顺丰", "SF1")
	assertBizCode(t, err, "M-20")

	type result struct{ err error }
	ch := make(chan result, 2)
	var wg sync.WaitGroup
	wg.Add(2)
	go func() {
		defer wg.Done()
		_, err := svc.ApplyRefund(ctx, buyer, order.OrderNo, "并发申请")
		ch <- result{err: err}
	}()
	go func() {
		defer wg.Done()
		_, err := svc.RegisterShipment(ctx, warehouse, order.OrderNo, "顺丰", "SF-RACE")
		ch <- result{err: err}
	}()
	wg.Wait()
	close(ch)
	var successes int
	for r := range ch {
		if r.err == nil {
			successes++
		}
	}
	if successes != 1 {
		t.Fatalf("refund/shipment competition should yield exactly one legal result, got %d", successes)
	}
	o := mustOrder(t, svc, order.OrderNo)
	if o.Status != StatusRefundReview && o.Status != StatusShipped {
		t.Fatalf("refund/shipment competition must yield exactly one legal state, got %s", o.Status)
	}

	svc2, _ := newTestService(5)
	order2, _ := svc2.CreateOrder(ctx, buyer, 1, 1)
	payOrder(t, svc2, order2.OrderNo, "PAY-SHIP")
	res, err := svc2.RegisterShipment(ctx, warehouse, order2.OrderNo, "顺丰", "SF-OK")
	if err != nil || res.Result != ResultShipmentRegistered {
		t.Fatalf("shipment failed: %v %v", res, err)
	}
	_, err = svc2.RegisterShipment(ctx, warehouse, order2.OrderNo, "顺丰", "SF-OK-2")
	assertBizCode(t, err, "M-19")
}

func TestLatePaymentRefundNoSecondStockRestore(t *testing.T) {
	svc, repo := newTestService(5)
	order, _ := svc.CreateOrder(ctx, buyer, 1, 2)
	svc.now = func() time.Time { return fixedTime.Add(11 * time.Minute) }
	lateRes, err := svc.HandlePaymentCallback(ctx, mockCh, PaymentCallback{
		OrderNo:        order.OrderNo,
		ChannelTradeNo: "LATE-PAY-1",
		Amount:         20000,
		SignatureValid: true,
	})
	assertBizCode(t, err, "M-09")
	if lateRes == nil || lateRes.Result != ResultLatePaymentPending {
		t.Fatalf("late payment record missing: %+v", lateRes)
	}
	if o := mustOrder(t, svc, order.OrderNo); o.Status != StatusClosed {
		t.Fatalf("late payment must keep closed terminal state, got %s", o.Status)
	}
	available, occupied := mustStock(t, repo, 1)
	if available != 5 || occupied != 0 {
		t.Fatalf("late payment should not re-occupy stock: %d/%d", available, occupied)
	}
	lateEvent := findPaymentByResult(t, repo, ResultLatePaymentPending)
	if _, err := svc.VerifyLatePayment(ctx, cs, uint64(lateEvent.ID), "客服核实迟到支付"); err != nil {
		t.Fatal(err)
	}
	if _, err := svc.InitiateLatePaymentRefund(ctx, cs, uint64(lateEvent.ID), "LATE-RF-1", "核实后发起退款"); err != nil {
		t.Fatal(err)
	}
	_, err = svc.HandleLatePaymentRefundCallback(ctx, mockCh, LateRefundCallback{
		EventID:        uint64(lateEvent.ID),
		RefundNo:       "LATE-RF-1",
		Amount:         20000,
		SignatureValid: true,
		Success:        true,
	})
	if err != nil {
		t.Fatal(err)
	}
	if o := mustOrder(t, svc, order.OrderNo); o.Status != StatusClosed {
		t.Fatalf("late refund must not change terminal status, got %s", o.Status)
	}
	available, occupied = mustStock(t, repo, 1)
	if available != 5 || occupied != 0 {
		t.Fatalf("late refund must not restore stock twice: %d/%d", available, occupied)
	}
	if countEvent(t, repo, EventLateRefundSuccess) != 1 {
		t.Fatal("late refund success should be exactly one")
	}
	_, err = svc.HandleLatePaymentRefundCallback(ctx, mockCh, LateRefundCallback{
		EventID:        uint64(lateEvent.ID),
		RefundNo:       "LATE-RF-1",
		Amount:         20000,
		SignatureValid: true,
		Success:        true,
	})
	if err != nil {
		t.Fatal(err)
	}
	if countEvent(t, repo, EventLateRefundSuccess) != 1 {
		t.Fatal("duplicate late refund must not create second refund")
	}
}

func TestServiceValidationBranchesAndOpsSummary(t *testing.T) {
	svc, repo := newTestService(5)
	order, _ := svc.CreateOrder(ctx, buyer, 1, 1)

	if _, err := svc.GetOrder(ctx, otherBuyer, order.OrderNo); !errors.Is(err, nil) {
		var bizErr *BizError
		if !errors.As(err, &bizErr) || bizErr.Code != "M-20" {
			t.Fatalf("expected M-20, got %v", err)
		}
	} else {
		t.Fatal("expected other buyer to be denied")
	}
	if _, err := svc.GetOrder(ctx, ops, order.OrderNo); err != nil {
		t.Fatal(err)
	}
	if _, err := svc.GetOpsSummary(ctx, buyer); !errors.Is(err, nil) {
		assertBizCode(t, err, "M-20")
	} else {
		t.Fatal("expected non-ops to be denied")
	}
	summary, err := svc.GetOpsSummary(ctx, ops)
	if err != nil || summary == nil || !summary.NoDuplicateReleaseRefund {
		t.Fatalf("ops summary failed: %v %+v", err, summary)
	}

	_, err = svc.ApplyRefund(ctx, buyer, "UNKNOWN", "x")
	assertBizCode(t, err, "M-30")
	_, err = svc.ApplyRefund(ctx, buyer, order.OrderNo, "x")
	assertBizCode(t, err, "M-05")
	_, err = svc.RejectRefund(ctx, cs, order.OrderNo, "")
	assertBizCode(t, err, "M-24")
	_, err = svc.ApproveRefund(ctx, cs, order.OrderNo, "")
	assertBizCode(t, err, "M-24")
	_, err = svc.RetryRefund(ctx, cs, order.OrderNo, "")
	assertBizCode(t, err, "M-24")
	_, err = svc.VerifyLatePayment(ctx, cs, 999, "")
	assertBizCode(t, err, "M-24")
	_, err = svc.InitiateLatePaymentRefund(ctx, cs, 999, "", "x")
	assertBizCode(t, err, "M-27")
	_, err = svc.InitiateLatePaymentRefund(ctx, cs, 999, "RF", "")
	assertBizCode(t, err, "M-24")
	_, err = svc.HandleLatePaymentRefundCallback(ctx, mockCh, LateRefundCallback{})
	assertBizCode(t, err, "M-27")
	_, err = svc.RetryLatePaymentRefund(ctx, cs, 999, "RF", "")
	assertBizCode(t, err, "M-24")
	_, err = svc.HandleRefundCallback(ctx, mockCh, RefundCallback{OrderNo: order.OrderNo})
	assertBizCode(t, err, "M-27")
	_, err = svc.GetOrder(ctx, buyer, "UNKNOWN")
	assertBizCode(t, err, "M-30")
	_, err = svc.CancelOrder(ctx, buyer, "UNKNOWN")
	assertBizCode(t, err, "M-30")

	_ = repo
}

func TestConcurrentCreateOrderDraftNotFormalEvidence(t *testing.T) {
	svc, repo := newTestService(5)
	type result struct{ err error }
	ch := make(chan result, 20)
	var wg sync.WaitGroup
	for i := 0; i < 20; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			_, err := svc.CreateOrder(ctx, Actor{UserID: uint64(9000), Role: RoleBuyer}, 1, 1)
			ch <- result{err: err}
		}()
	}
	wg.Wait()
	close(ch)
	var success int
	for r := range ch {
		if r.err == nil {
			success++
		} else {
			assertBizCode(t, r.err, "M-02")
		}
	}
	if success != 5 {
		t.Fatalf("draft concurrency expected 5 successes, got %d", success)
	}
	available, occupied := mustStock(t, repo, 1)
	if available != 0 || occupied != 5 {
		t.Fatalf("stock conservation failed: available=%d occupied=%d", available, occupied)
	}
}
