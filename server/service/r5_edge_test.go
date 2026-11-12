package service

// 第五轮证据闭环：只新增边界 case 单元测试，不改动任何生产代码。
// 覆盖 closePendingOrder / 支付回调 / 取消 / 超时关单的技术错误与边界分支、demo 仓储与 types.go 工具函数。
// 不新增业务状态机，不冒充真实 MySQL(InnoDB) 行锁、race 或 CI 证据。

import (
	"context"
	"errors"
	"strings"
	"testing"
	"time"

	"shop-trade/server/model"
)

const r5TechMsg = "r5 injected repository failure"

// r5Repo 包装内存仓储并把自身作为事务对象传入，用于注入事务内部的技术错误分支。
type r5Repo struct {
	OrderRepository
	failAt string
	err    error
	calls  map[string]int
}

func (r *r5Repo) WithTransaction(_ context.Context, fn func(OrderRepository) error) error {
	return fn(r)
}

func (r *r5Repo) LockOrder(c context.Context, no string) (*model.Order, error) {
	if r.failAt == "LockOrder" {
		return nil, r.err
	}
	return r.OrderRepository.LockOrder(c, no)
}

func (r *r5Repo) LockOrderByID(c context.Context, id uint64) (*model.Order, error) {
	if r.failAt == "LockOrderByID" {
		return nil, r.err
	}
	if r.failAt == "LockOrderByIDNil" {
		return nil, nil
	}
	return r.OrderRepository.LockOrderByID(c, id)
}

func (r *r5Repo) GetOrder(c context.Context, no string) (*model.Order, error) {
	if r.failAt == "GetOrder" {
		return nil, r.err
	}
	return r.OrderRepository.GetOrder(c, no)
}

func (r *r5Repo) GetPaymentByDedupKey(c context.Context, k string) (*model.Payment, error) {
	switch r.failAt {
	case "GetPaymentByDedupKey":
		return nil, r.err
	case "GetPaymentByDedupKey2", "GetPaymentByDedupKey3":
		r.calls["gpd"]++
		n := 2
		if r.failAt == "GetPaymentByDedupKey3" {
			n = 3
		}
		if r.calls["gpd"] == n {
			return nil, r.err
		}
	}
	return r.OrderRepository.GetPaymentByDedupKey(c, k)
}

func (r *r5Repo) GetPaymentByID(c context.Context, id uint64) (*model.Payment, error) {
	if r.failAt == "GetPaymentByID" {
		return nil, r.err
	}
	return r.OrderRepository.GetPaymentByID(c, id)
}

func (r *r5Repo) HasPaymentEvent(c context.Context, refID uint64, eventType string) (bool, error) {
	if r.failAt == "HasPaymentEvent" {
		return false, r.err
	}
	return r.OrderRepository.HasPaymentEvent(c, refID, eventType)
}

func (r *r5Repo) LockGoods(c context.Context, id uint64) (*model.Goods, error) {
	if r.failAt == "LockGoods" {
		return nil, r.err
	}
	if r.failAt == "LockGoodsNil" {
		return nil, nil
	}
	return r.OrderRepository.LockGoods(c, id)
}

func (r *r5Repo) IncreaseGoodsStock(c context.Context, id uint64, q int) (bool, error) {
	if r.failAt == "IncreaseGoodsStock" {
		return false, r.err
	}
	if r.failAt == "IncreaseGoodsStockFalse" {
		return false, nil
	}
	return r.OrderRepository.IncreaseGoodsStock(c, id, q)
}

func (r *r5Repo) UpdateOrderIfStatus(c context.Context, o *model.Order, allowed []string, f map[string]interface{}) (int64, error) {
	if r.failAt == "UpdateOrderIfStatus" {
		return 0, r.err
	}
	if r.failAt == "UpdateOrderIfStatusZero" {
		return 0, nil
	}
	return r.OrderRepository.UpdateOrderIfStatus(c, o, allowed, f)
}

func (r *r5Repo) UpdateOrderIfStatusAndStockNotRestored(c context.Context, o *model.Order, allowed []string, f map[string]interface{}) (int64, error) {
	if r.failAt == "UpdateOrderIfStatusAndStockNotRestored" {
		return 0, r.err
	}
	if r.failAt == "UpdateOrderIfStatusAndStockNotRestoredZero" {
		return 0, nil
	}
	return r.OrderRepository.UpdateOrderIfStatusAndStockNotRestored(c, o, allowed, f)
}

func (r *r5Repo) CreatePayment(c context.Context, p *model.Payment) error {
	if r.failAt == "CreatePayment" {
		return r.err
	}
	if r.failAt == "CreatePaymentDup" {
		return ErrDuplicateDedupKey
	}
	return r.OrderRepository.CreatePayment(c, p)
}

func (r *r5Repo) ListExpiredPendingOrders(c context.Context, now time.Time, limit int) ([]model.Order, error) {
	if r.failAt == "ListExpiredPendingOrders" {
		return nil, r.err
	}
	return r.OrderRepository.ListExpiredPendingOrders(c, now, limit)
}

func (r *r5Repo) CountOrders(c context.Context) (int64, error) {
	if r.failAt == "CountOrders" {
		return 0, r.err
	}
	return r.OrderRepository.CountOrders(c)
}

func r5Seeded(t *testing.T, failAt string, seed func(*testing.T, *OrderService)) (*OrderService, *r5Repo, *memoryRepository) {
	t.Helper()
	base := newMemoryRepository(testGoodsWithID())
	clean := NewOrderServiceWithClock(base, func() time.Time { return fixedTime })
	if seed != nil {
		seed(t, clean)
	}
	r := &r5Repo{OrderRepository: base, failAt: failAt, err: errors.New(r5TechMsg), calls: map[string]int{}}
	return NewOrderServiceWithClock(r, func() time.Time { return fixedTime }), r, base
}

func r5WantTech(t *testing.T, err error) {
	t.Helper()
	if err == nil || !strings.Contains(err.Error(), r5TechMsg) {
		t.Fatalf("期望注入技术错误 %q，实际 %v", r5TechMsg, err)
	}
}

func r5SeedOrder(t *testing.T, svc *OrderService) *model.Order {
	t.Helper()
	o, err := svc.CreateOrder(ctx, buyer, 1, 1)
	if err != nil {
		t.Fatalf("造单失败：%v", err)
	}
	return o
}

func r5SeedPaid(t *testing.T, svc *OrderService) *model.Order {
	t.Helper()
	o := r5SeedOrder(t, svc)
	p, err := svc.HandlePaymentCallback(ctx, mockCh, PaymentCallback{
		OrderNo: o.OrderNo, ChannelTradeNo: "PAY-" + o.OrderNo, Amount: o.TotalAmount, SignatureValid: true,
	})
	if err != nil || p == nil {
		t.Fatalf("支付回调失败：p=%v err=%v", p, err)
	}
	return o
}

func r5SeedRefundReview(t *testing.T, svc *OrderService) *model.Order {
	t.Helper()
	o := r5SeedPaid(t, svc)
	if _, err := svc.ApplyRefund(ctx, buyer, o.OrderNo, "用户不想要了"); err != nil {
		t.Fatalf("申请退款失败：%v", err)
	}
	return o
}

func r5SeedRefundProcessing(t *testing.T, svc *OrderService) *model.Order {
	t.Helper()
	o := r5SeedRefundReview(t, svc)
	if _, err := svc.ApproveRefund(ctx, cs, o.OrderNo, "同意退款"); err != nil {
		t.Fatalf("审核通过失败：%v", err)
	}
	return o
}

func r5SeedRefundFailed(t *testing.T, svc *OrderService) *model.Order {
	t.Helper()
	o := r5SeedRefundProcessing(t, svc)
	_, err := svc.HandleRefundCallback(ctx, mockCh, RefundCallback{
		OrderNo: o.OrderNo, RefundChannelTradeNo: "RF-FAIL-" + o.OrderNo,
		Amount: o.TotalAmount, SignatureValid: true, Success: false,
	})
	if err == nil {
		t.Fatal("渠道退款失败应返回 M-08")
	}
	assertBizCode(t, err, "M-08")
	return o
}

func r5SeedRefunded(t *testing.T, svc *OrderService) *model.Order {
	t.Helper()
	o := r5SeedRefundProcessing(t, svc)
	if _, err := svc.HandleRefundCallback(ctx, mockCh, RefundCallback{
		OrderNo: o.OrderNo, RefundChannelTradeNo: "RF-OK-" + o.OrderNo,
		Amount: o.TotalAmount, SignatureValid: true, Success: true,
	}); err != nil {
		t.Fatalf("退款成功回调失败：%v", err)
	}
	return o
}

func r5SeedLateEvent(t *testing.T, svc *OrderService) (*model.Order, uint64) {
	t.Helper()
	o := r5SeedOrder(t, svc)
	svc.now = func() time.Time { return fixedTime.Add(11 * time.Minute) }
	p, err := svc.HandlePaymentCallback(ctx, mockCh, PaymentCallback{
		OrderNo: o.OrderNo, ChannelTradeNo: "LATE-" + o.OrderNo, Amount: o.TotalAmount, SignatureValid: true,
	})
	if p == nil || err == nil {
		t.Fatalf("迟到支付应登记事件并返回 M-09：p=%v err=%v", p, err)
	}
	assertBizCode(t, err, "M-09")
	return o, uint64(p.ID)
}

func r5LateBase(t *testing.T) (*memoryRepository, uint64) {
	t.Helper()
	base := newMemoryRepository(testGoodsWithID())
	clean := NewOrderServiceWithClock(base, func() time.Time { return fixedTime })
	_, eventID := r5SeedLateEvent(t, clean)
	return base, eventID
}

func r5VerifiedBase(t *testing.T) (*memoryRepository, uint64) {
	t.Helper()
	base, eventID := r5LateBase(t)
	clean := NewOrderServiceWithClock(base, func() time.Time { return fixedTime })
	if _, err := clean.VerifyLatePayment(ctx, cs, eventID, "核实为重复通知"); err != nil {
		t.Fatalf("核实失败：%v", err)
	}
	return base, eventID
}

func r5RequestedBase(t *testing.T) (*memoryRepository, uint64) {
	t.Helper()
	base, eventID := r5VerifiedBase(t)
	clean := NewOrderServiceWithClock(base, func() time.Time { return fixedTime })
	if _, err := clean.InitiateLatePaymentRefund(ctx, cs, eventID, "LR-1", "向买家退回"); err != nil {
		t.Fatalf("发起迟到退款失败：%v", err)
	}
	return base, eventID
}

func r5Wrap(base OrderRepository, failAt string) *OrderService {
	return NewOrderServiceWithClock(&r5Repo{
		OrderRepository: base, failAt: failAt, err: errors.New(r5TechMsg), calls: map[string]int{},
	}, func() time.Time { return fixedTime })
}

func TestR5TypesHelperFunctions(t *testing.T) {
	if got := (&BizError{Code: "M-01"}).Error(); got != "M-01" {
		t.Fatalf("空 Message 应只返回 Code：%q", got)
	}
	if got := (&BizError{Code: "M-01", Message: "原因"}).Error(); got != "M-01: 原因" {
		t.Fatalf("带 Message 应返回 Code: Message：%q", got)
	}
	assertBizCode(t, fail("M-03"), "M-03")
	if err := failWithDetail("M-03", "额外说明"); err == nil || !strings.Contains(err.Error(), "额外说明") {
		t.Fatalf("failWithDetail 应拼接明细：%v", err)
	}
	assertBizCode(t, failWithDetail("M-03", ""), "M-03")
	for _, s := range []string{StatusCancelled, StatusClosed, StatusRefunded, StatusShipped} {
		if !isTerminal(s) {
			t.Fatalf("%s 应为终态", s)
		}
	}
	for _, s := range []string{StatusPendingPayment, StatusWaitingShipment, StatusRefundReview, StatusRefundProcessing, ""} {
		if isTerminal(s) {
			t.Fatalf("%s 不应为终态", s)
		}
	}
	if !contains([]string{"a", "b"}, "b") || contains([]string{"a"}, "b") || contains(nil, "a") {
		t.Fatal("contains 边界判定错误")
	}
	if p := boolPtr(true); p == nil || !*p {
		t.Fatal("boolPtr 应返回值指针")
	}
	if p := stringPtr("x"); p == nil || *p != "x" {
		t.Fatal("stringPtr 应返回值指针")
	}
}

func TestR5ClosePendingOrderInjectedBranches(t *testing.T) {
	cases := []struct {
		name    string
		failAt  string
		wantBiz string
		wantMsg string
	}{
		{"条件更新技术错误", "UpdateOrderIfStatus", "", ""},
		{"条件更新未命中记重复留痕", "UpdateOrderIfStatusZero", "M-10", ""},
		{"锁商品技术错误", "LockGoods", "", ""},
		{"商品查询为空", "LockGoodsNil", "", "not found during stock release"},
		{"恢复库存技术错误", "IncreaseGoodsStock", "", ""},
		{"恢复库存条件不满足", "IncreaseGoodsStockFalse", "", "stock release condition not met"},
		{"释放审计写入失败", "CreatePayment", "", ""},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			var no string
			svc, _, _ := r5Seeded(t, tc.failAt, func(t *testing.T, s *OrderService) { no = r5SeedOrder(t, s).OrderNo })
			_, err := svc.CancelOrder(ctx, buyer, no)
			if err == nil {
				t.Fatal("期望返回错误")
			}
			if tc.wantBiz != "" {
				assertBizCode(t, err, tc.wantBiz)
			} else if tc.wantMsg != "" {
				if !strings.Contains(err.Error(), tc.wantMsg) {
					t.Fatalf("期望错误含 %q，实际 %v", tc.wantMsg, err)
				}
			} else {
				r5WantTech(t, err)
			}
		})
	}
}

func TestR5CancelOrderBoundaryBranches(t *testing.T) {
	t.Run("运营越权取消M20", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "", func(t *testing.T, s *OrderService) { no = r5SeedOrder(t, s).OrderNo })
		_, err := svc.CancelOrder(ctx, ops, no)
		assertBizCode(t, err, "M-20")
	})
	t.Run("锁定订单技术错误", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "LockOrder", func(t *testing.T, s *OrderService) { no = r5SeedOrder(t, s).OrderNo })
		r5WantTech(t, mustCancelErr(svc, no))
	})
	t.Run("已支付订单不可取消M05", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "", func(t *testing.T, s *OrderService) { no = r5SeedPaid(t, s).OrderNo })
		_, err := svc.CancelOrder(ctx, buyer, no)
		assertBizCode(t, err, "M-05")
	})
	t.Run("重复取消幂等M10", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "", func(t *testing.T, s *OrderService) {
			no = r5SeedOrder(t, s).OrderNo
			if _, err := s.CancelOrder(ctx, buyer, no); err != nil {
				t.Fatalf("首次取消应成功：%v", err)
			}
		})
		_, err := svc.CancelOrder(ctx, buyer, no)
		assertBizCode(t, err, "M-10")
	})
	t.Run("过期取消并发未命中M10", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "UpdateOrderIfStatusZero", func(t *testing.T, s *OrderService) { no = r5SeedOrder(t, s).OrderNo })
		svc.now = func() time.Time { return fixedTime.Add(11 * time.Minute) }
		_, err := svc.CancelOrder(ctx, buyer, no)
		assertBizCode(t, err, "M-10")
	})
	t.Run("过期取消库存恢复技术错误", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "IncreaseGoodsStock", func(t *testing.T, s *OrderService) { no = r5SeedOrder(t, s).OrderNo })
		svc.now = func() time.Time { return fixedTime.Add(11 * time.Minute) }
		r5WantTech(t, mustCancelErr(svc, no))
	})
}

func mustCancelErr(svc *OrderService, no string) error {
	_, err := svc.CancelOrder(ctx, buyer, no)
	if err == nil {
		return errors.New("expected error but got nil")
	}
	return err
}

func TestR5CloseExpiredOrdersBranches(t *testing.T) {
	t.Run("limit非正走默认值", func(t *testing.T) {
		svc, _, _ := r5Seeded(t, "", nil)
		n, err := svc.CloseExpiredOrders(ctx, ops, 0)
		if err != nil || n != 0 {
			t.Fatalf("无过期订单时 limit=0 应返回 0：n=%d err=%v", n, err)
		}
	})
	t.Run("列表查询技术错误", func(t *testing.T) {
		svc, _, _ := r5Seeded(t, "ListExpiredPendingOrders", nil)
		_, err := svc.CloseExpiredOrders(ctx, ops, 10)
		r5WantTech(t, err)
	})
	t.Run("逐单锁定技术错误", func(t *testing.T) {
		svc, _, _ := r5Seeded(t, "LockOrderByID", func(t *testing.T, s *OrderService) { r5SeedOrder(t, s) })
		svc.now = func() time.Time { return fixedTime.Add(11 * time.Minute) }
		_, err := svc.CloseExpiredOrders(ctx, ops, 10)
		r5WantTech(t, err)
	})
	t.Run("锁定结果消失时跳过", func(t *testing.T) {
		svc, _, _ := r5Seeded(t, "LockOrderByIDNil", func(t *testing.T, s *OrderService) { r5SeedOrder(t, s) })
		svc.now = func() time.Time { return fixedTime.Add(11 * time.Minute) }
		n, err := svc.CloseExpiredOrders(ctx, ops, 10)
		if err != nil || n != 0 {
			t.Fatalf("订单消失应跳过不计数：n=%d err=%v", n, err)
		}
	})
	t.Run("库存恢复技术错误向上传播", func(t *testing.T) {
		svc, _, _ := r5Seeded(t, "IncreaseGoodsStock", func(t *testing.T, s *OrderService) { r5SeedOrder(t, s) })
		svc.now = func() time.Time { return fixedTime.Add(11 * time.Minute) }
		_, err := svc.CloseExpiredOrders(ctx, ops, 10)
		r5WantTech(t, err)
	})
	t.Run("正常关单并恢复一次库存", func(t *testing.T) {
		var no string
		svc, _, base := r5Seeded(t, "", func(t *testing.T, s *OrderService) { no = r5SeedOrder(t, s).OrderNo })
		svc.now = func() time.Time { return fixedTime.Add(11 * time.Minute) }
		n, err := svc.CloseExpiredOrders(ctx, ops, 10)
		if err != nil || n != 1 {
			t.Fatalf("应关闭 1 笔：n=%d err=%v", n, err)
		}
		o, err := base.GetOrder(ctx, no)
		if err != nil || o.Status != StatusClosed || o.ClosedAt == nil {
			t.Fatalf("订单应为已关闭：o=%+v err=%v", o, err)
		}
		avail, occupied := mustStock(t, base, 1)
		if avail != 5 || occupied != 0 {
			t.Fatalf("库存应恢复一次：available=%d occupied=%d", avail, occupied)
		}
	})
}

func TestR5HandlePaymentCallbackErrorBranches(t *testing.T) {
	pay := func(no, trade string, amount int64, sign bool) PaymentCallback {
		return PaymentCallback{OrderNo: no, ChannelTradeNo: trade, Amount: amount, SignatureValid: sign}
	}
	t.Run("空交易号M27", func(t *testing.T) {
		svc, _, _ := r5Seeded(t, "", nil)
		_, err := svc.HandlePaymentCallback(ctx, mockCh, pay("ORD-X", "", 10000, true))
		assertBizCode(t, err, "M-27")
	})
	t.Run("幂等查询技术错误", func(t *testing.T) {
		svc, _, _ := r5Seeded(t, "GetPaymentByDedupKey", nil)
		r5WantTech(t, mustPayErr(svc, pay("ORD-X", "TR-1", 10000, true)))
	})
	t.Run("锁定订单技术错误", func(t *testing.T) {
		svc, _, _ := r5Seeded(t, "LockOrder", nil)
		r5WantTech(t, mustPayErr(svc, pay("ORD-X", "TR-1", 10000, true)))
	})
	t.Run("未知订单M30", func(t *testing.T) {
		svc, _, _ := r5Seeded(t, "", nil)
		_, err := svc.HandlePaymentCallback(ctx, mockCh, pay("ORD-NOPE", "TR-1", 10000, true))
		assertBizCode(t, err, "M-30")
	})
	t.Run("验签失败M28", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "", func(t *testing.T, s *OrderService) { no = r5SeedOrder(t, s).OrderNo })
		_, err := svc.HandlePaymentCallback(ctx, mockCh, pay(no, "TR-1", 10000, false))
		assertBizCode(t, err, "M-28")
	})
	t.Run("金额不符M29", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "", func(t *testing.T, s *OrderService) { no = r5SeedOrder(t, s).OrderNo })
		_, err := svc.HandlePaymentCallback(ctx, mockCh, pay(no, "TR-1", 1, true))
		assertBizCode(t, err, "M-29")
	})
	t.Run("已取消订单支付记异常M15", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "", func(t *testing.T, s *OrderService) {
			no = r5SeedOrder(t, s).OrderNo
			if _, err := s.CancelOrder(ctx, buyer, no); err != nil {
				t.Fatalf("取消失败：%v", err)
			}
		})
		p, err := svc.HandlePaymentCallback(ctx, mockCh, pay(no, "TR-LATE-1", 10000, true))
		assertBizCode(t, err, "M-15")
		if p == nil || p.EventType != EventLatePayment {
			t.Fatalf("应登记迟到支付异常事件：p=%+v", p)
		}
	})
	t.Run("终态异常审计写入失败", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "CreatePayment", func(t *testing.T, s *OrderService) {
			no = r5SeedOrder(t, s).OrderNo
			if _, err := s.CancelOrder(ctx, buyer, no); err != nil {
				t.Fatalf("取消失败：%v", err)
			}
		})
		r5WantTech(t, mustPayErr(svc, pay(no, "TR-LATE-2", 10000, true)))
	})
	t.Run("待发货订单重复支付M05", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "", func(t *testing.T, s *OrderService) { no = r5SeedPaid(t, s).OrderNo })
		_, err := svc.HandlePaymentCallback(ctx, mockCh, pay(no, "TR-NEW-1", 10000, true))
		assertBizCode(t, err, "M-05")
	})
	t.Run("过期支付并发未命中M10", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "UpdateOrderIfStatusZero", func(t *testing.T, s *OrderService) { no = r5SeedOrder(t, s).OrderNo })
		svc.now = func() time.Time { return fixedTime.Add(11 * time.Minute) }
		_, err := svc.HandlePaymentCallback(ctx, mockCh, pay(no, "TR-LATE-3", 10000, true))
		assertBizCode(t, err, "M-10")
	})
	t.Run("过期支付登记异常M09", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "", func(t *testing.T, s *OrderService) { no = r5SeedOrder(t, s).OrderNo })
		svc.now = func() time.Time { return fixedTime.Add(11 * time.Minute) }
		p, err := svc.HandlePaymentCallback(ctx, mockCh, pay(no, "TR-LATE-4", 10000, true))
		assertBizCode(t, err, "M-09")
		if p == nil || p.EventType != EventLatePayment {
			t.Fatalf("应登记迟到支付事件：p=%+v", p)
		}
	})
	t.Run("状态更新未命中记重复支付留痕", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "UpdateOrderIfStatusZero", func(t *testing.T, s *OrderService) { no = r5SeedOrder(t, s).OrderNo })
		p, err := svc.HandlePaymentCallback(ctx, mockCh, pay(no, "TR-1", 10000, true))
		if err != nil || p == nil || p.Result != ResultRepeatPaymentNoop {
			t.Fatalf("并发未命中应幂等留痕：p=%+v err=%v", p, err)
		}
	})
	t.Run("唯一键冲突映射传播", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "CreatePaymentDup", func(t *testing.T, s *OrderService) { no = r5SeedOrder(t, s).OrderNo })
		_, err := svc.HandlePaymentCallback(ctx, mockCh, pay(no, "TR-DUP-1", 10000, true))
		if !errors.Is(err, ErrDuplicateDedupKey) {
			t.Fatalf("唯一键冲突应传播 ErrDuplicateDedupKey：%v", err)
		}
	})
}

func mustPayErr(svc *OrderService, in PaymentCallback) error {
	_, err := svc.HandlePaymentCallback(ctx, mockCh, in)
	if err == nil {
		return errors.New("expected error but got nil")
	}
	return err
}
