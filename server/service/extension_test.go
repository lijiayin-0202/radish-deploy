package service

// 竞态检测说明：go test ./... -race 需要 CGO_ENABLED=1 与可用 C 编译器。
// PowerShell：$env:CGO_ENABLED = "1"; go test ./... -race -count=1
// 本文件覆盖「代码产物补齐」批次新增的 ExtensionService 与演示仓储扩展方法，
// 不改动下单 / 退款主业务，也不冒充真实 MySQL(InnoDB) 的并发证据。

import (
	"context"
	"errors"
	"testing"
	"time"

	"shop-trade/server/global"
	"shop-trade/server/model"
)

var extensionNow = time.Date(2026, 11, 12, 10, 0, 0, 0, time.UTC)

type stubExtRepo struct {
	goods        *model.Goods
	order        *model.Order
	payments     []model.Payment
	existing     *model.Payment
	err          error
	errAt        string
	lockGoodsErr error
	nextID       uint
	priceCalls   int
}

func (s *stubExtRepo) LockGoods(context.Context, uint64) (*model.Goods, error) {
	if s.lockGoodsErr != nil {
		return nil, s.lockGoodsErr
	}
	if s.errAt == "LockGoods" {
		return nil, s.err
	}
	return s.goods, nil
}

func (s *stubExtRepo) GetOrder(context.Context, string) (*model.Order, error) {
	if s.errAt == "GetOrder" {
		return nil, s.err
	}
	return s.order, nil
}

func (s *stubExtRepo) GetPaymentByDedupKey(context.Context, string) (*model.Payment, error) {
	if s.errAt == "GetPaymentByDedupKey" {
		return nil, s.err
	}
	return s.existing, nil
}

func (s *stubExtRepo) CreatePayment(_ context.Context, p *model.Payment) error {
	if s.errAt == "CreatePayment" {
		return s.err
	}
	s.nextID++
	p.ID = s.nextID
	s.payments = append(s.payments, *p)
	return nil
}

func (s *stubExtRepo) UpdateGoodsPrice(_ context.Context, _ uint64, price int64) error {
	if s.errAt == "UpdateGoodsPrice" {
		return s.err
	}
	s.priceCalls++
	if s.goods != nil {
		s.goods.UnitPrice = price
	}
	return nil
}

func (s *stubExtRepo) ListGoods(context.Context) ([]model.Goods, error) {
	if s.errAt == "ListGoods" {
		return nil, s.err
	}
	if s.goods == nil {
		return []model.Goods{}, nil
	}
	return []model.Goods{*s.goods}, nil
}

func (s *stubExtRepo) ListPaymentsByOrderNo(_ context.Context, orderNo string) ([]model.Payment, error) {
	if s.errAt == "ListPaymentsByOrderNo" {
		return nil, s.err
	}
	out := []model.Payment{}
	for _, p := range s.payments {
		if p.OrderNo == orderNo {
			out = append(out, p)
		}
	}
	return out, nil
}

func newStubExt() *stubExtRepo {
	return &stubExtRepo{
		goods: &model.Goods{
			GVA_MODEL: global.GVA_MODEL{ID: 1}, GoodsNo: "GOODS-ACT-001", Name: "活动商品",
			UnitPrice: 10000, AvailableStock: 5, Status: GoodsStatusOnSale,
		},
		order: &model.Order{
			GVA_MODEL: global.GVA_MODEL{ID: 2}, OrderNo: "ORD-EXT-1", BuyerID: 1001,
			GoodsID: 1, GoodsNo: "GOODS-ACT-001", Quantity: 1, UnitPrice: 10000,
			TotalAmount: 10000, Status: StatusPendingPayment, RefundKind: RefundKindNone,
		},
	}
}

func newStubExtService(s *stubExtRepo) *ExtensionService {
	return NewExtensionService(s, func() time.Time { return extensionNow })
}

func isBizCode(t *testing.T, err error, code string) {
	t.Helper()
	var biz *BizError
	if !errors.As(err, &biz) || biz.Code != code {
		t.Fatalf("期望 BizError code=%s，实际 %v", code, err)
	}
}

func TestExtensionUpdateGoodsPriceSuccess(t *testing.T) {
	s := newStubExt()
	res, err := newStubExtService(s).UpdateGoodsPrice(context.Background(), Actor{UserID: 2001, Role: RoleOps}, 1, 12000, "活动价格调整")
	if err != nil {
		t.Fatalf("调价应成功：%v", err)
	}
	if res.OldUnitPrice != 10000 || res.NewUnitPrice != 12000 || res.GoodsNo != "GOODS-ACT-001" {
		t.Fatalf("调价结果不符：%+v", res)
	}
	if res.Hint != messages["M-12"] || res.Constraint != messages["M-13"] {
		t.Fatalf("必须回传 M-12 / M-13 约束提示：%+v", res)
	}
	if s.priceCalls != 1 || s.goods.UnitPrice != 12000 {
		t.Fatalf("仓储未被正确更新：calls=%d price=%d", s.priceCalls, s.goods.UnitPrice)
	}
	if len(s.payments) != 1 || s.payments[0].EventType != EventGoodsPriceChanged || s.payments[0].Effective != nil {
		t.Fatalf("调价必须写一条只追加审计：%+v", s.payments)
	}
	if !s.payments[0].OccurredAt.Equal(extensionNow) || res.AuditEventID != 1 {
		t.Fatalf("审计时间与事件 ID 不正确：%+v", s.payments[0])
	}
}

func TestExtensionUpdateGoodsPriceRejectionsAndErrors(t *testing.T) {
	ctx := context.Background()
	cases := []struct {
		name   string
		actor  Actor
		price  int64
		mutate func(*stubExtRepo)
		check  func(*testing.T, error)
	}{
		{"非运营越权", Actor{UserID: 1001, Role: RoleBuyer}, 12000, nil, func(t *testing.T, e error) { isBizCode(t, e, "M-20") }},
		{"空身份", Actor{}, 12000, nil, func(t *testing.T, e error) { isBizCode(t, e, "M-20") }},
		{"金额非正", Actor{UserID: 2001, Role: RoleOps}, 0, nil, func(t *testing.T, e error) {
			if !errors.Is(e, ErrInvalidPrice) {
				t.Fatalf("期望 ErrInvalidPrice，实际 %v", e)
			}
		}},
		{"商品不存在", Actor{UserID: 2001, Role: RoleOps}, 12000, func(s *stubExtRepo) { s.goods = nil }, func(t *testing.T, e error) {
			if !errors.Is(e, ErrGoodsNotFound) {
				t.Fatalf("期望 ErrGoodsNotFound，实际 %v", e)
			}
		}},
		{"读商品技术错误", Actor{UserID: 2001, Role: RoleOps}, 12000, func(s *stubExtRepo) {
			s.errAt, s.err = "LockGoods", errors.New("db read failed")
		}, func(t *testing.T, e error) {
			if e == nil || e.Error() != "db read failed" {
				t.Fatalf("期望技术错误，实际 %v", e)
			}
		}},
		{"写价格技术错误", Actor{UserID: 2001, Role: RoleOps}, 12000, func(s *stubExtRepo) {
			s.errAt, s.err = "UpdateGoodsPrice", errors.New("db write failed")
		}, func(t *testing.T, e error) {
			if e == nil || e.Error() != "db write failed" {
				t.Fatalf("期望技术错误，实际 %v", e)
			}
		}},
		{"审计写入失败", Actor{UserID: 2001, Role: RoleOps}, 12000, func(s *stubExtRepo) {
			s.errAt, s.err = "CreatePayment", errors.New("audit failed")
		}, func(t *testing.T, e error) {
			if e == nil || e.Error() != "audit failed" {
				t.Fatalf("期望技术错误，实际 %v", e)
			}
		}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			s := newStubExt()
			if tc.mutate != nil {
				tc.mutate(s)
			}
			_, err := newStubExtService(s).UpdateGoodsPrice(ctx, tc.actor, 1, tc.price, "原因")
			if err == nil {
				t.Fatal("期望返回错误")
			}
			tc.check(t, err)
		})
	}
}

func TestExtensionChannelTimeoutSuccessAndIdempotency(t *testing.T) {
	ctx := context.Background()
	notice := ChannelTimeoutNotice{OrderNo: "ORD-EXT-1", ChannelTradeNo: "TO-1", Reason: "渠道通知超时"}
	s := newStubExt()
	ext := newStubExtService(s)
	res, err := ext.HandleChannelTimeout(ctx, Actor{UserID: 5001, Role: RoleMockChannel}, notice)
	if err != nil {
		t.Fatalf("超时通知应成功：%v", err)
	}
	if res.Duplicate || !res.OrderStatusUnchanged || res.OrderStatus != StatusPendingPayment || res.EventID != 1 {
		t.Fatalf("超时通知结果不符：%+v", res)
	}
	if len(s.payments) != 1 || s.payments[0].EventType != EventChannelTimeout || s.payments[0].DedupKey == nil {
		t.Fatalf("必须写一条带 dedup key 的只追加审计：%+v", s.payments)
	}
	if *s.payments[0].DedupKey != DedupTimeoutPrefix+"TO-1" {
		t.Fatalf("dedup key 不正确：%s", *s.payments[0].DedupKey)
	}
	if s.order.Status != StatusPendingPayment || s.goods.AvailableStock != 5 {
		t.Fatal("超时通知不得改订单状态或库存")
	}

	// 重复通知：已有 dedup 记录，幂等成功且不新增第二条审计。
	s.existing = &s.payments[0]
	again, err := ext.HandleChannelTimeout(ctx, Actor{UserID: 2001, Role: RoleOps}, notice)
	if err != nil {
		t.Fatalf("重复通知应幂等成功：%v", err)
	}
	if !again.Duplicate || again.EventID != 1 || len(s.payments) != 1 {
		t.Fatalf("重复通知不得产生第二笔结果：%+v", again)
	}
}

func TestExtensionChannelTimeoutRejectionsAndErrors(t *testing.T) {
	ctx := context.Background()
	notice := ChannelTimeoutNotice{OrderNo: "ORD-EXT-1", ChannelTradeNo: "TO-1"}
	cases := []struct {
		name   string
		actor  Actor
		mutate func(*stubExtRepo)
		check  func(*testing.T, error)
	}{
		{"越权", Actor{UserID: 1001, Role: RoleBuyer}, nil, func(t *testing.T, e error) { isBizCode(t, e, "M-20") }},
		{"未知订单", Actor{UserID: 5001, Role: RoleMockChannel}, func(s *stubExtRepo) { s.order = nil }, func(t *testing.T, e error) {
			isBizCode(t, e, "M-30")
		}},
		{"查询 dedup 失败", Actor{UserID: 5001, Role: RoleMockChannel}, func(s *stubExtRepo) {
			s.errAt, s.err = "GetPaymentByDedupKey", errors.New("dedup read failed")
		}, func(t *testing.T, e error) {
			if e == nil || e.Error() != "dedup read failed" {
				t.Fatalf("期望技术错误，实际 %v", e)
			}
		}},
		{"查询订单失败", Actor{UserID: 5001, Role: RoleMockChannel}, func(s *stubExtRepo) {
			s.errAt, s.err = "GetOrder", errors.New("order read failed")
		}, func(t *testing.T, e error) {
			if e == nil || e.Error() != "order read failed" {
				t.Fatalf("期望技术错误，实际 %v", e)
			}
		}},
		{"审计失败", Actor{UserID: 5001, Role: RoleMockChannel}, func(s *stubExtRepo) {
			s.errAt, s.err = "CreatePayment", errors.New("audit failed")
		}, func(t *testing.T, e error) {
			if e == nil || e.Error() != "audit failed" {
				t.Fatalf("期望技术错误，实际 %v", e)
			}
		}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			s := newStubExt()
			if tc.mutate != nil {
				tc.mutate(s)
			}
			_, err := newStubExtService(s).HandleChannelTimeout(ctx, tc.actor, notice)
			if err == nil {
				t.Fatal("期望返回错误")
			}
			tc.check(t, err)
		})
	}
}

func TestExtensionChannelTimeoutDuplicateConflictAndExistingWithoutOrder(t *testing.T) {
	ctx := context.Background()
	s := newStubExt()
	s.errAt, s.err = "CreatePayment", ErrDuplicateDedupKey
	ext := newStubExtService(s)
	res, err := ext.HandleChannelTimeout(ctx, Actor{UserID: 5001, Role: RoleMockChannel},
		ChannelTimeoutNotice{OrderNo: "ORD-EXT-1", ChannelTradeNo: "TO-1"})
	if err != nil || !res.Duplicate || !res.OrderStatusUnchanged {
		t.Fatalf("唯一键冲突应按幂等成功处理：res=%+v err=%v", res, err)
	}

	s2 := newStubExt()
	s2.existing = &model.Payment{GVA_MODEL: global.GVA_MODEL{ID: 9}}
	s2.order = nil
	res2, err := NewExtensionService(s2, nil).HandleChannelTimeout(ctx,
		Actor{UserID: 2001, Role: RoleOps}, ChannelTimeoutNotice{OrderNo: "ORD-EXT-1", ChannelTradeNo: "TO-2"})
	if err != nil || !res2.Duplicate || res2.EventID != 9 || res2.OrderStatus != "" {
		t.Fatalf("已有 dedup 记录且订单不可见时应仍幂等成功：res=%+v err=%v", res2, err)
	}
}

func TestExtensionVerifyStockRestorationBranches(t *testing.T) {
	ctx := context.Background()
	actor := Actor{UserID: 2001, Role: RoleOps}
	cases := []struct {
		name       string
		status     string
		kind       string
		events     []model.Payment
		wantExpect int
		wantActual int
		consistent bool
		conclusion string
	}{
		{"正常售前退款恢复一次", StatusRefunded, RefundKindPresale,
			[]model.Payment{{OrderNo: "ORD-EXT-1", EventType: EventStockRestore}}, 1, 1, true, messages["M-17"]},
		{"迟到支付终态不得二次恢复", StatusClosed, RefundKindLate, nil, 0, 0, true, messages["M-17"]},
		{"已退款但缺恢复事件", StatusRefunded, RefundKindPresale, nil, 1, 0, false, "库存恢复事件数与订单终态不符，需核查退款流程"},
		{"迟到支付多出恢复事件", StatusClosed, RefundKindLate,
			[]model.Payment{{OrderNo: "ORD-EXT-1", EventType: EventStockRestore}}, 0, 1, false, messages["M-26"]},
		{"非恢复事件不计入", StatusCancelled, RefundKindNone,
			[]model.Payment{{OrderNo: "ORD-EXT-1", EventType: EventStockRelease}}, 0, 0, true, messages["M-17"]},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			s := newStubExt()
			s.order.Status = tc.status
			s.order.RefundKind = tc.kind
			s.payments = append([]model.Payment{}, tc.events...)
			res, err := newStubExtService(s).VerifyStockRestoration(ctx, actor, "ORD-EXT-1")
			if err != nil {
				t.Fatalf("逐单核查应成功：%v", err)
			}
			if res.ExpectedRestoreTimes != tc.wantExpect || res.ActualRestoreTimes != tc.wantActual ||
				res.Consistent != tc.consistent || res.Conclusion != tc.conclusion {
				t.Fatalf("核查结果不符：%+v", res)
			}
			if res.AvailableStock != 5 || res.UnitPriceSnapshot != 10000 || res.GoodsID != 1 {
				t.Fatalf("核查必须带出商品库存与金额快照：%+v", res)
			}
		})
	}
}

func TestExtensionVerifyStockRestorationRejectionsAndErrors(t *testing.T) {
	ctx := context.Background()
	cases := []struct {
		name   string
		actor  Actor
		mutate func(*stubExtRepo)
		check  func(*testing.T, error)
	}{
		{"越权", Actor{UserID: 1001, Role: RoleBuyer}, nil, func(t *testing.T, e error) { isBizCode(t, e, "M-20") }},
		{"订单不存在", Actor{UserID: 4001, Role: RoleCustomerService}, func(s *stubExtRepo) { s.order = nil }, func(t *testing.T, e error) {
			if !errors.Is(e, ErrOrderNotFound) {
				t.Fatalf("期望 ErrOrderNotFound，实际 %v", e)
			}
		}},
		{"商品不存在", Actor{UserID: 2001, Role: RoleOps}, func(s *stubExtRepo) { s.goods = nil }, func(t *testing.T, e error) {
			if !errors.Is(e, ErrGoodsNotFound) {
				t.Fatalf("期望 ErrGoodsNotFound，实际 %v", e)
			}
		}},
		{"读订单失败", Actor{UserID: 2001, Role: RoleOps}, func(s *stubExtRepo) {
			s.errAt, s.err = "GetOrder", errors.New("order read failed")
		}, func(t *testing.T, e error) {
			if e == nil || e.Error() != "order read failed" {
				t.Fatalf("期望技术错误，实际 %v", e)
			}
		}},
		{"读流水失败", Actor{UserID: 2001, Role: RoleOps}, func(s *stubExtRepo) {
			s.errAt, s.err = "ListPaymentsByOrderNo", errors.New("payment read failed")
		}, func(t *testing.T, e error) {
			if e == nil || e.Error() != "payment read failed" {
				t.Fatalf("期望技术错误，实际 %v", e)
			}
		}},
		{"读商品失败", Actor{UserID: 2001, Role: RoleOps}, func(s *stubExtRepo) {
			// 流水查询成功，仅商品读取失败，逐单覆盖 LockGoods 的技术错误分支。
			s.lockGoodsErr = errors.New("goods read failed")
		}, func(t *testing.T, e error) {
			if e == nil || e.Error() != "goods read failed" {
				t.Fatalf("期望技术错误，实际 %v", e)
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

func TestExtensionDemoRepositoryMethods(t *testing.T) {
	ctx := context.Background()
	base := NewDemoOrderRepository()
	repo, ok := base.(ExtensionRepository)
	if !ok {
		t.Fatal("演示仓储必须实现 ExtensionRepository")
	}
	goods, err := repo.ListGoods(ctx)
	if err != nil || len(goods) != 2 || goods[0].ID != 1 || goods[1].ID != 2 {
		t.Fatalf("商品列表应稳定按 ID 排序：len=%d err=%v goods=%+v", len(goods), err, goods)
	}
	if err := repo.UpdateGoodsPrice(ctx, 1, 15000); err != nil {
		t.Fatalf("调价应成功：%v", err)
	}
	goods, _ = repo.ListGoods(ctx)
	if goods[0].UnitPrice != 15000 || goods[1].UnitPrice != 10000 {
		t.Fatalf("调价只应影响目标商品：%+v", goods)
	}
	if err := repo.UpdateGoodsPrice(ctx, 999, 1); !errors.Is(err, ErrGoodsNotFound) {
		t.Fatalf("不存在的商品应报 ErrGoodsNotFound，实际 %v", err)
	}
	_ = repo.CreatePayment(ctx, &model.Payment{OrderNo: "ORD-A", EventType: EventStockRestore})
	_ = repo.CreatePayment(ctx, &model.Payment{OrderNo: "ORD-B", EventType: EventPaymentSuccess})
	rows, err := repo.ListPaymentsByOrderNo(ctx, "ORD-A")
	if err != nil || len(rows) != 1 || rows[0].EventType != EventStockRestore {
		t.Fatalf("逐单流水过滤不正确：len=%d err=%v rows=%+v", len(rows), err, rows)
	}
}

func TestExtensionServiceDefaultClockAndAuditFailureStillDenies(t *testing.T) {
	s := newStubExt()
	// 默认时间源（now=nil）必须可用。
	ext := NewExtensionService(s, nil)
	res, err := ext.UpdateGoodsPrice(context.Background(), Actor{UserID: 2001, Role: RoleOps}, 1, 11000, "")
	if err != nil || res.NewUnitPrice != 11000 {
		t.Fatalf("默认时间源下应成功：res=%+v err=%v", res, err)
	}
	// 越权时即使审计写入失败，也必须返回 M-20。
	s2 := newStubExt()
	s2.errAt, s2.err = "CreatePayment", errors.New("audit down")
	_, err = NewExtensionService(s2, nil).VerifyStockRestoration(context.Background(), Actor{UserID: 1001, Role: RoleBuyer}, "ORD-EXT-1")
	isBizCode(t, err, "M-20")
}
