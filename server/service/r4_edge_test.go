package service

// 第四轮证据闭环：只新增边界 case 单元测试，不改动任何生产代码。
// 覆盖目标：审计辅助函数的写入失败分支、ExtensionService 剩余只读/错误路径，
// 以及金额/数量/身份边界。不新增业务状态机，不冒充真实 MySQL 或 race 证据。

import (
	"context"
	"errors"
	"testing"
	"time"

	"shop-trade/server/global"
	"shop-trade/server/model"
)

// r4ErrCreateRepo 只覆盖 CreatePayment，其余方法委托给真实演示仓储。
// 这样可以在不改动生产代码的前提下注入「审计写入失败」的技术错误。
type r4ErrCreateRepo struct {
	OrderRepository
	err error
}

func (r *r4ErrCreateRepo) CreatePayment(_ context.Context, _ *model.Payment) error {
	return r.err
}

func r4FailingAuditService() (*OrderService, *r4ErrCreateRepo, OrderRepository) {
	g := testGoods(5)
	g.ID = 1
	base := newMemoryRepository(g)
	r := &r4ErrCreateRepo{OrderRepository: base, err: errors.New("r4 audit write failed")}
	svc := NewOrderServiceWithClock(r, func() time.Time { return fixedTime })
	return svc, r, base
}

func r4WantTechError(t *testing.T, err error) {
	t.Helper()
	if err == nil || err.Error() != "r4 audit write failed" {
		t.Fatalf("期望审计写入技术错误，实际 %v", err)
	}
}

func TestR4AuditHelperErrorBranches(t *testing.T) {
	svc, failing, _ := r4FailingAuditService()
	actor := Actor{UserID: 1001, Role: RoleBuyer}

	if err := svc.denyAndLog(ctx, actor, "越权操作", "ORD-R4-1"); err != nil {
		r4WantTechError(t, err)
	} else {
		t.Fatal("denyAndLog 审计失败必须返回技术错误")
	}
	if err := svc.denyAndLogTx(ctx, failing, actor, "越权操作", "ORD-R4-1"); err != nil {
		r4WantTechError(t, err)
	} else {
		t.Fatal("denyAndLogTx 审计失败必须返回技术错误")
	}
	if p, err := svc.rejectOutsideTx(ctx, actor, "ORD-R4-1", "TR-R4-1", "支付通知", "M-10"); err == nil || p != nil {
		r4WantTechError(t, err)
	}
	if p, err := svc.rejectedPayment(ctx, failing, actor, 1, "ORD-R4-1", "TR-R4-1", "支付通知", "M-10", StatusPendingPayment, 10000, true); err == nil || p != nil {
		r4WantTechError(t, err)
	}
	if p, err := svc.noopPayment(ctx, failing, actor, 1, "ORD-R4-1", "TR-R4-1", "支付通知", ResultDuplicateNoop, "M-10", StatusPendingPayment, 10000); err == nil || p != nil {
		r4WantTechError(t, err)
	}
	if p, err := svc.duplicateRejectPayment(ctx, failing, actor, 1, "ORD-R4-1", "TR-R4-1", "重复操作", ResultDuplicateNoop, "M-10", StatusPendingPayment, 10000); err == nil || p != nil {
		r4WantTechError(t, err)
	}
}

func TestR4AuditHelperSuccessBranches(t *testing.T) {
	_, _, base := r4FailingAuditService()
	svc := NewOrderServiceWithClock(base, func() time.Time { return fixedTime })
	actor := Actor{UserID: 1001, Role: RoleBuyer}

	if err := svc.denyAndLog(ctx, actor, "越权操作", "ORD-R4-2"); err == nil {
		t.Fatal("denyAndLog 成功写入审计后仍须返回 M-20")
	} else {
		assertBizCode(t, err, "M-20")
	}
	if p, err := svc.rejectOutsideTx(ctx, actor, "ORD-R4-2", "TR-R4-2", "支付通知", "M-10"); err == nil || p == nil {
		t.Fatalf("rejectOutsideTx 应返回审计记录 + M-10：p=%v err=%v", p, err)
	} else {
		assertBizCode(t, err, "M-10")
	}
	if p, err := svc.noopPayment(ctx, base, actor, 1, "ORD-R4-2", "TR-R4-3", "支付通知", ResultDuplicateNoop, "M-10", StatusPendingPayment, 10000); err != nil || p == nil {
		t.Fatalf("noopPayment 应幂等成功且留痕：p=%v err=%v", p, err)
	}
	if p, err := svc.duplicateRejectPayment(ctx, base, actor, 1, "ORD-R4-2", "TR-R4-4", "重复操作", ResultDuplicateNoop, "M-10", StatusPendingPayment, 10000); err == nil || p == nil {
		t.Fatalf("duplicateRejectPayment 应留痕并返回拒绝：p=%v err=%v", p, err)
	} else {
		assertBizCode(t, err, "M-10")
	}
}

func TestR4ExtensionTimeoutExistingGetOrderError(t *testing.T) {
	s := newStubExt()
	s.existing = &model.Payment{GVA_MODEL: global.GVA_MODEL{ID: 7}}
	s.errAt, s.err = "GetOrder", errors.New("r4 order read failed")
	_, err := newStubExtService(s).HandleChannelTimeout(ctx, mockCh,
		ChannelTimeoutNotice{OrderNo: "ORD-EXT-1", ChannelTradeNo: "TO-R4-1"})
	if err == nil || err.Error() != "r4 order read failed" {
		t.Fatalf("已有 dedup 记录但查询订单失败时应返回技术错误，实际 %v", err)
	}
}

func TestR4ExtensionVerifyStockRestorationErrorBranches(t *testing.T) {
	ctx := context.Background()
	actor := Actor{UserID: 2001, Role: RoleOps}
	tech := errors.New("r4 repo failure")
	cases := []struct {
		name   string
		actor  Actor
		mutate func(*stubExtRepo)
		check  func(*testing.T, error)
	}{
		{"越权核查", Actor{UserID: 1001, Role: RoleBuyer}, nil, func(t *testing.T, e error) { isBizCode(t, e, "M-20") }},
		{"查询订单失败", actor, func(s *stubExtRepo) { s.errAt, s.err = "GetOrder", tech }, func(t *testing.T, e error) {
			if !errors.Is(e, tech) {
				t.Fatalf("期望技术错误，实际 %v", e)
			}
		}},
		{"订单不存在", actor, func(s *stubExtRepo) { s.order = nil }, func(t *testing.T, e error) {
			if !errors.Is(e, ErrOrderNotFound) {
				t.Fatalf("期望 ErrOrderNotFound，实际 %v", e)
			}
		}},
		{"查询支付流水失败", actor, func(s *stubExtRepo) { s.errAt, s.err = "ListPaymentsByOrderNo", tech }, func(t *testing.T, e error) {
			if !errors.Is(e, tech) {
				t.Fatalf("期望技术错误，实际 %v", e)
			}
		}},
		{"锁定商品失败", actor, func(s *stubExtRepo) { s.errAt, s.err = "LockGoods", tech }, func(t *testing.T, e error) {
			if !errors.Is(e, tech) {
				t.Fatalf("期望技术错误，实际 %v", e)
			}
		}},
		{"商品不存在", actor, func(s *stubExtRepo) { s.goods = nil }, func(t *testing.T, e error) {
			if !errors.Is(e, ErrGoodsNotFound) {
				t.Fatalf("期望 ErrGoodsNotFound，实际 %v", e)
			}
		}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			s := newStubExt()
			if tc.mutate != nil {
				tc.mutate(s)
			}
			_, err := newStubExtService(s).VerifyStockRestoration(ctx, tc.actor, "ORD-EXT-1")
			if err == nil {
				t.Fatal("期望返回错误")
			}
			tc.check(t, err)
		})
	}
}

func TestR4ExtensionVerifyStockRestorationDuplicateEvents(t *testing.T) {
	s := newStubExt()
	s.order.Status = StatusRefunded
	s.order.RefundKind = RefundKindPresale
	s.order.StockRestored = true
	s.payments = []model.Payment{
		{OrderNo: "ORD-EXT-1", EventType: EventStockRestore},
		{OrderNo: "ORD-EXT-1", EventType: EventStockRestore},
		{OrderNo: "ORD-EXT-1", EventType: EventStockRestore},
		{OrderNo: "ORD-EXT-1", EventType: EventStockRelease},
	}
	res, err := newStubExtService(s).VerifyStockRestoration(ctx,
		Actor{UserID: 4001, Role: RoleCustomerService}, "ORD-EXT-1")
	if err != nil {
		t.Fatalf("逐单核查应成功：%v", err)
	}
	if res.ExpectedRestoreTimes != 1 || res.ActualRestoreTimes != 3 || res.DuplicateRestoreEvents != 2 {
		t.Fatalf("重复恢复事件统计不符：%+v", res)
	}
	if res.Consistent || !res.StockRestoredFlag || res.Conclusion == messages["M-17"] {
		t.Fatalf("三次恢复事件必须判为不一致：%+v", res)
	}
	if res.AvailableStock != 5 || res.OccupiedStock != 0 {
		t.Fatalf("核查只读，不得改动库存：%+v", res)
	}
}

func TestR4ExtensionRequireRoleAuditFailureStillDenies(t *testing.T) {
	s := newStubExt()
	s.errAt, s.err = "CreatePayment", errors.New("r4 audit failed")
	_, err := newStubExtService(s).UpdateGoodsPrice(ctx,
		Actor{UserID: 1001, Role: RoleBuyer}, 1, 12000, "越权尝试")
	isBizCode(t, err, "M-20")
	if s.priceCalls != 0 {
		t.Fatal("越权时不得更新商品价格")
	}
}

func TestR4ExtensionPriceBoundaryValues(t *testing.T) {
	for _, price := range []int64{-1, -10000, -9223372036854775808} {
		s := newStubExt()
		_, err := newStubExtService(s).UpdateGoodsPrice(ctx,
			Actor{UserID: 2001, Role: RoleOps}, 1, price, "负数边界")
		if !errors.Is(err, ErrInvalidPrice) {
			t.Fatalf("price=%d 期望 ErrInvalidPrice，实际 %v", price, err)
		}
		if s.priceCalls != 0 {
			t.Fatalf("price=%d 不得写库", price)
		}
	}
}

func TestR4ExtensionDefaultClockIsUsable(t *testing.T) {
	s := newStubExt()
	res, err := NewExtensionService(s, nil).UpdateGoodsPrice(ctx,
		Actor{UserID: 2001, Role: RoleOps}, 1, 11000, "默认时钟")
	if err != nil || res.NewUnitPrice != 11000 {
		t.Fatalf("默认 time.Now 时钟应可用：res=%+v err=%v", res, err)
	}
	if len(s.payments) != 1 || s.payments[0].OccurredAt.IsZero() {
		t.Fatalf("默认时钟须写入审计时间：%+v", s.payments)
	}
}

func TestR4CreateOrderBoundaryQuantityAndIdentity(t *testing.T) {
	svc, repo := newTestService(5)
	cases := []struct {
		name     string
		actor    Actor
		quantity int
		code     string
	}{
		{"数量为零", buyer, 0, "M-03"},
		{"数量为三", buyer, 3, "M-03"},
		{"数量为负", buyer, -1, "M-03"},
		{"运营越权下单", ops, 1, "M-20"},
		{"空身份下单", Actor{}, 1, "M-20"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			_, err := svc.CreateOrder(ctx, tc.actor, 1, tc.quantity)
			assertBizCode(t, err, tc.code)
		})
	}
	avail, occupied := mustStock(t, repo, 1)
	if avail != 5 || occupied != 0 {
		t.Fatalf("边界下单不得消耗库存：available=%d occupied=%d", avail, occupied)
	}
}

func TestR4CreateOrderGoodsAndStockBoundaries(t *testing.T) {
	svc, repo := newTestService(5)
	if _, err := svc.CreateOrder(ctx, buyer, 0, 1); err != nil {
		assertBizCode(t, err, "M-04")
	} else {
		t.Fatal("goods_id=0 应返回 M-04")
	}
	if _, err := svc.CreateOrder(ctx, buyer, 999, 1); err != nil {
		assertBizCode(t, err, "M-01")
	} else {
		t.Fatal("不存在商品应返回 M-01")
	}
	for i := 0; i < 2; i++ {
		if _, err := svc.CreateOrder(ctx, buyer, 1, 2); err != nil {
			t.Fatalf("前两次下单应成功：%v", err)
		}
	}
	if _, err := svc.CreateOrder(ctx, buyer, 1, 2); err != nil {
		assertBizCode(t, err, "M-02")
	} else {
		t.Fatal("可售 1 件时下 2 件应返回 M-02，不得超卖")
	}
	avail, occupied := mustStock(t, repo, 1)
	if avail != 1 || occupied != 4 {
		t.Fatalf("库存守恒不符：available=%d occupied=%d", avail, occupied)
	}
}

func TestR4GetOrderBoundaryBranches(t *testing.T) {
	svc, _ := newTestService(5)
	if _, err := svc.GetOrder(ctx, ops, "NO-SUCH-ORDER"); err != nil {
		assertBizCode(t, err, "M-30")
	} else {
		t.Fatal("未知订单应返回 M-30")
	}
	o, err := svc.CreateOrder(ctx, buyer, 1, 1)
	if err != nil {
		t.Fatalf("下单失败：%v", err)
	}
	if _, err := svc.GetOrder(ctx, otherBuyer, o.OrderNo); err != nil {
		assertBizCode(t, err, "M-20")
	} else {
		t.Fatal("他人订单越权查询应返回 M-20")
	}
	if got, err := svc.GetOrder(ctx, ops, o.OrderNo); err != nil || got.OrderNo != o.OrderNo {
		t.Fatalf("运营应可查询任意订单：got=%v err=%v", got, err)
	}
}

// r4InjectRepo 把自身作为事务对象传给业务函数，用于注入事务内部的技术错误分支。
// 只用于单元测试，不改动生产仓储与业务代码。
type r4InjectRepo struct {
	OrderRepository
	failAt     string
	err        error
	falseStock bool
}

func (r *r4InjectRepo) WithTransaction(_ context.Context, fn func(OrderRepository) error) error {
	return fn(r)
}
func (r *r4InjectRepo) LockGoods(c context.Context, id uint64) (*model.Goods, error) {
	if r.failAt == "LockGoods" {
		return nil, r.err
	}
	return r.OrderRepository.LockGoods(c, id)
}
func (r *r4InjectRepo) DecreaseGoodsStock(c context.Context, id uint64, q int) (bool, error) {
	if r.failAt == "DecreaseGoodsStock" {
		return false, r.err
	}
	if r.falseStock {
		return false, nil
	}
	return r.OrderRepository.DecreaseGoodsStock(c, id, q)
}
func (r *r4InjectRepo) CreateOrder(c context.Context, o *model.Order) error {
	if r.failAt == "CreateOrder" {
		return r.err
	}
	return r.OrderRepository.CreateOrder(c, o)
}
func (r *r4InjectRepo) CreatePayment(c context.Context, p *model.Payment) error {
	if r.failAt == "CreatePayment" {
		return r.err
	}
	return r.OrderRepository.CreatePayment(c, p)
}

func TestR4CreateOrderTransactionErrorBranches(t *testing.T) {
	tech := errors.New("r4 injected repo failure")
	cases := []struct {
		name       string
		failAt     string
		falseStock bool
		wantBiz    string
	}{
		{"锁定商品技术错误", "LockGoods", false, ""},
		{"扣减库存技术错误", "DecreaseGoodsStock", false, ""},
		{"条件更新未命中返回缺货", "", true, "M-02"},
		{"创建订单技术错误", "CreateOrder", false, ""},
		{"创建审计技术错误", "CreatePayment", false, ""},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			g := testGoods(5)
			g.ID = 1
			base := newMemoryRepository(g)
			r := &r4InjectRepo{OrderRepository: base, failAt: tc.failAt, err: tech, falseStock: tc.falseStock}
			svc := NewOrderServiceWithClock(r, func() time.Time { return fixedTime })
			_, err := svc.CreateOrder(ctx, buyer, 1, 1)
			if err == nil {
				t.Fatal("期望返回错误")
			}
			if tc.wantBiz != "" {
				assertBizCode(t, err, tc.wantBiz)
			} else if !errors.Is(err, tech) {
				t.Fatalf("期望注入的技术错误，实际 %v", err)
			}
		})
	}
}

func TestR4ClockAndSummaryBoundaries(t *testing.T) {
	svc, _ := newTestService(5)
	if !svc.ServerTimeForDisplay().Equal(fixedTime) {
		t.Fatal("服务端时间必须由注入的时间源返回")
	}
	if _, err := svc.GetOpsSummary(ctx, buyer); err != nil {
		assertBizCode(t, err, "M-20")
	} else {
		t.Fatal("买家不得查看运营汇总，应返回 M-20")
	}
	if s, err := svc.GetOpsSummary(ctx, ops); err != nil || s == nil {
		t.Fatalf("运营汇总应成功：s=%v err=%v", s, err)
	}
}
