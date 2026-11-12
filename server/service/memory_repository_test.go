package service

// 竞态检测说明：go test ./... -race 需要 CGO_ENABLED=1 与可用的 C 编译器（gcc/clang）。
// PowerShell 开启方式：$env:CGO_ENABLED = "1"; go test ./... -race -count=1
// bash 开启方式：CGO_ENABLED=1 go test ./... -race -count=1
// 本机当前为 CGO_ENABLED=0，正式第 1 轮 race 证据须在开启 CGO 的环境执行。
//
// 原「仅用于单元测试草案」的内存仓储夹具已提升为生产文件
// server/service/demo_repository.go，供 main.go 演示模式与全部单元测试共用；
// 所有既有测试用例与断言均保留，本文件补齐演示仓储自身分支的断言。

import (
	"testing"
	"time"

	"shop-trade/server/model"
)

func TestDemoGoodsAndRepositoryBaseline(t *testing.T) {
	goods := DemoGoods()
	if len(goods) != 2 || goods[0].ID != 1 || goods[1].ID != 2 {
		t.Fatalf("unexpected demo goods list: %+v", goods)
	}
	if goods[0].UnitPrice != 10000 || goods[0].AvailableStock != 5 || goods[0].Status != GoodsStatusOnSale {
		t.Fatalf("activity goods baseline broken: %+v", goods[0])
	}

	repo := NewDemoOrderRepository()
	if repo == nil {
		t.Fatal("demo repository must not be nil")
	}
	g, err := repo.LockGoods(ctx, 1)
	if err != nil || g == nil || g.AvailableStock != 5 {
		t.Fatalf("demo repository goods not ready: g=%+v err=%v", g, err)
	}
	missing, err := repo.LockGoods(ctx, 999)
	if err != nil || missing != nil {
		t.Fatalf("unknown goods should be (nil, nil): %v %v", missing, err)
	}
}

func TestDemoRepositoryIdempotencyAndFieldBranches(t *testing.T) {
	repo := newMemoryRepository(testGoodsWithID())

	order := &model.Order{OrderNo: "DEMO-DUP"}
	if err := repo.CreateOrder(ctx, order); err != nil {
		t.Fatal(err)
	}
	if err := repo.CreateOrder(ctx, &model.Order{OrderNo: "DEMO-DUP"}); err != ErrDuplicateDedupKey {
		t.Fatalf("duplicate order must map to ErrDuplicateDedupKey, got %v", err)
	}

	dedup := "DEMO:PAY:1"
	p := &model.Payment{OrderNo: "DEMO-DUP", ChannelTradeNo: "PAY-1", DedupKey: &dedup, EventType: EventPaymentSuccess, Amount: 10000}
	if err := repo.CreatePayment(ctx, p); err != nil {
		t.Fatal(err)
	}
	if err := repo.CreatePayment(ctx, &model.Payment{OrderNo: "DEMO-DUP", ChannelTradeNo: "PAY-2", DedupKey: &dedup}); err != ErrDuplicateDedupKey {
		t.Fatalf("duplicate dedup key must be rejected, got %v", err)
	}
	found, err := repo.GetPaymentByID(ctx, uint64(p.ID))
	if err != nil || found == nil || found.ChannelTradeNo != "PAY-1" {
		t.Fatalf("payment query failed: %+v %v", found, err)
	}
	notFound, err := repo.GetPaymentByID(ctx, 99999)
	if err != nil || notFound != nil {
		t.Fatalf("unknown payment should be (nil, nil): %v %v", notFound, err)
	}
	byDedup, err := repo.GetPaymentByDedupKey(ctx, dedup)
	if err != nil || byDedup == nil {
		t.Fatalf("dedup lookup failed: %+v %v", byDedup, err)
	}
	if _, err := repo.GetPaymentByDedupKey(ctx, "MISSING"); err != nil {
		t.Fatal(err)
	}

	yes, err := repo.HasPaymentEvent(ctx, 1, EventPaymentSuccess)
	if err != nil || yes {
		t.Fatalf("unrelated event should be false: %v %v", yes, err)
	}

	now := time.Now()
	past := now.Add(-time.Minute)
	if got := timeField(now); got == nil || !got.Equal(now) {
		t.Fatal("timeField(time.Time) failed")
	}
	if got := timeField(&past); got == nil || !got.Equal(past) {
		t.Fatal("timeField(*time.Time) failed")
	}
	if got := timeField("not-a-time"); got != nil {
		t.Fatal("timeField default branch should be nil")
	}
	if got := cloneTimePtr(nil); got != nil {
		t.Fatal("cloneTimePtr(nil) should be nil")
	}

	o := &model.Order{}
	applyOrderFields(o, map[string]interface{}{
		"status":                  StatusWaitingShipment,
		"paid_at":                 now,
		"closed_at":               &past,
		"cancelled_at":            now,
		"refund_kind":             RefundKindPresale,
		"refund_reason":           "不想要了",
		"refund_apply_at":         now,
		"refund_audit_at":         now,
		"refund_auditor_id":       uint64(4001),
		"refund_audit_remark":     "同意整单退款",
		"refund_state":            RefundStatePending,
		"refund_retry_count":      1,
		"refund_channel_trade_no": "RF-1",
		"refunded_at":             now,
		"stock_restored":          true,
		"late_payment_refunded":   true,
		"shipment_carrier":        "顺丰",
		"shipment_tracking_no":    "SF-1",
		"shipped_at":              now,
		"shipment_registered_by":  uint64(3001),
		"unknown_field_ignored":   "ignored",
	})
	if o.Status != StatusWaitingShipment || o.RefundRetryCount != 1 || !o.StockRestored ||
		o.RefundChannelTradeNo != "RF-1" || o.ShipmentCarrier != "顺丰" {
		t.Fatalf("applyOrderFields did not cover branches: %+v", o)
	}
}

func TestDemoRepositoryAggregatesAndExpiredLimit(t *testing.T) {
	repo := newMemoryRepository(testGoodsWithID())
	expired := time.Now().Add(11 * time.Minute)
	for i := 0; i < 3; i++ {
		o := &model.Order{
			OrderNo:   []string{"E1", "E2", "E3"}[i],
			Status:    StatusPendingPayment,
			ExpiresAt: expired.Add(-time.Hour),
		}
		if err := repo.CreateOrder(ctx, o); err != nil {
			t.Fatal(err)
		}
	}
	list, err := repo.ListExpiredPendingOrders(ctx, expired, 1)
	if err != nil || len(list) != 1 {
		t.Fatalf("limit must be honoured: list=%v err=%v", list, err)
	}
	total, err := repo.CountOrders(ctx)
	if err != nil || total != 3 {
		t.Fatalf("CountOrders failed: %d %v", total, err)
	}
	n, err := repo.CountOrdersByStatus(ctx, StatusPendingPayment)
	if err != nil || n != 3 {
		t.Fatalf("CountOrdersByStatus failed: %d %v", n, err)
	}
	if err := repo.CreatePayment(ctx, &model.Payment{EventType: EventPaymentSuccess, Result: ResultPaid, Amount: 20000, Effective: boolPtr(true)}); err != nil {
		t.Fatal(err)
	}
	sum, err := repo.SumEffectivePaymentsByEventType(ctx, EventPaymentSuccess)
	if err != nil || sum != 20000 {
		t.Fatalf("effective sum failed: %d %v", sum, err)
	}
	cnt, err := repo.CountPaymentsByEventType(ctx, EventPaymentSuccess)
	if err != nil || cnt != 1 {
		t.Fatalf("event count failed: %d %v", cnt, err)
	}
	cnt, err = repo.CountPaymentsByResult(ctx, ResultPaid)
	if err != nil || cnt != 1 {
		t.Fatalf("result count failed: %d %v", cnt, err)
	}
	ok, err := repo.IncreaseGoodsStock(ctx, 1, 99)
	if err != nil || ok {
		t.Fatalf("over-release must fail: %v %v", ok, err)
	}
}
