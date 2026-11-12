package service

// 第五轮证据闭环（第二部分）：退款申请/审核/回调、发货、迟到支付旁路、GetOrder 与 demo 仓储边界。
// 只新增测试，不改动任何生产代码；不冒充真实 MySQL(InnoDB) 行锁、race 或 CI 证据。

import (
	"errors"
	"strings"
	"testing"
	"time"

	"shop-trade/server/model"
)

func TestR5ApplyRefundBoundaryBranches(t *testing.T) {
	t.Run("运营越权申请M20", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "", func(t *testing.T, s *OrderService) { no = r5SeedPaid(t, s).OrderNo })
		_, err := svc.ApplyRefund(ctx, ops, no, "越权")
		assertBizCode(t, err, "M-20")
	})
	t.Run("锁定订单技术错误", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "LockOrder", func(t *testing.T, s *OrderService) { no = r5SeedPaid(t, s).OrderNo })
		r5WantTech(t, mustApplyErr(svc, no))
	})
	t.Run("他人订单越权M20", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "", func(t *testing.T, s *OrderService) { no = r5SeedPaid(t, s).OrderNo })
		_, err := svc.ApplyRefund(ctx, otherBuyer, no, "他人订单")
		assertBizCode(t, err, "M-20")
	})
	t.Run("已发货订单不可退款M11", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "", func(t *testing.T, s *OrderService) {
			no = r5SeedPaid(t, s).OrderNo
			if _, err := s.RegisterShipment(ctx, warehouse, no, "顺丰", "SF-1"); err != nil {
				t.Fatalf("发货失败：%v", err)
			}
		})
		_, err := svc.ApplyRefund(ctx, buyer, no, "已发货申请")
		assertBizCode(t, err, "M-11")
	})
	t.Run("审核中重复申请M10", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "", func(t *testing.T, s *OrderService) { no = r5SeedRefundReview(t, s).OrderNo })
		_, err := svc.ApplyRefund(ctx, buyer, no, "重复申请")
		assertBizCode(t, err, "M-10")
	})
	t.Run("待支付订单不可退款M05", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "", func(t *testing.T, s *OrderService) { no = r5SeedOrder(t, s).OrderNo })
		_, err := svc.ApplyRefund(ctx, buyer, no, "未支付申请")
		assertBizCode(t, err, "M-05")
	})
	t.Run("条件更新技术错误", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "UpdateOrderIfStatus", func(t *testing.T, s *OrderService) { no = r5SeedPaid(t, s).OrderNo })
		r5WantTech(t, mustApplyErr(svc, no))
	})
	t.Run("条件更新未命中M10", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "UpdateOrderIfStatusZero", func(t *testing.T, s *OrderService) { no = r5SeedPaid(t, s).OrderNo })
		_, err := svc.ApplyRefund(ctx, buyer, no, "并发申请")
		assertBizCode(t, err, "M-10")
	})
	t.Run("申请审计写入失败", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "CreatePayment", func(t *testing.T, s *OrderService) { no = r5SeedPaid(t, s).OrderNo })
		r5WantTech(t, mustApplyErr(svc, no))
	})
}

func mustApplyErr(svc *OrderService, no string) error {
	_, err := svc.ApplyRefund(ctx, buyer, no, "边界用例")
	if err == nil {
		return errors.New("expected error but got nil")
	}
	return err
}

func TestR5RefundAuditErrorBranches(t *testing.T) {
	seedReview := func(t *testing.T, s *OrderService) string { return r5SeedRefundReview(t, s).OrderNo }
	seedFailed := func(t *testing.T, s *OrderService) string { return r5SeedRefundFailed(t, s).OrderNo }
	seedPaidNo := func(t *testing.T, s *OrderService) string { return r5SeedPaid(t, s).OrderNo }
	cases := []struct {
		name   string
		failAt string
		seed   func(*testing.T, *OrderService) string
		call   func(*OrderService, string) error
		want   string
	}{
		{"拒绝-锁定订单技术错误", "LockOrder", seedReview, func(s *OrderService, no string) error {
			_, err := s.RejectRefund(ctx, cs, no, "拒绝原因")
			return err
		}, ""},
		{"拒绝-非审核状态M05", "", seedPaidNo, func(s *OrderService, no string) error {
			_, err := s.RejectRefund(ctx, cs, no, "拒绝原因")
			return err
		}, "M-05"},
		{"拒绝-条件更新技术错误", "UpdateOrderIfStatus", seedReview, func(s *OrderService, no string) error {
			_, err := s.RejectRefund(ctx, cs, no, "拒绝原因")
			return err
		}, ""},
		{"拒绝-条件更新未命中M10", "UpdateOrderIfStatusZero", seedReview, func(s *OrderService, no string) error {
			_, err := s.RejectRefund(ctx, cs, no, "拒绝原因")
			return err
		}, "M-10"},
		{"拒绝-审计写入失败", "CreatePayment", seedReview, func(s *OrderService, no string) error {
			_, err := s.RejectRefund(ctx, cs, no, "拒绝原因")
			return err
		}, ""},
		{"同意-锁定订单技术错误", "LockOrder", seedReview, func(s *OrderService, no string) error {
			_, err := s.ApproveRefund(ctx, cs, no, "同意原因")
			return err
		}, ""},
		{"同意-非审核状态M05", "", seedPaidNo, func(s *OrderService, no string) error {
			_, err := s.ApproveRefund(ctx, cs, no, "同意原因")
			return err
		}, "M-05"},
		{"同意-条件更新技术错误", "UpdateOrderIfStatus", seedReview, func(s *OrderService, no string) error {
			_, err := s.ApproveRefund(ctx, cs, no, "同意原因")
			return err
		}, ""},
		{"同意-条件更新未命中M10", "UpdateOrderIfStatusZero", seedReview, func(s *OrderService, no string) error {
			_, err := s.ApproveRefund(ctx, cs, no, "同意原因")
			return err
		}, "M-10"},
		{"同意-审计写入失败", "CreatePayment", seedReview, func(s *OrderService, no string) error {
			_, err := s.ApproveRefund(ctx, cs, no, "同意原因")
			return err
		}, ""},
		{"重试-锁定订单技术错误", "LockOrder", seedFailed, func(s *OrderService, no string) error {
			_, err := s.RetryRefund(ctx, cs, no, "重试原因")
			return err
		}, ""},
		{"重试-非失败状态M05", "", seedReview, func(s *OrderService, no string) error {
			_, err := s.RetryRefund(ctx, cs, no, "重试原因")
			return err
		}, "M-05"},
		{"重试-条件更新技术错误", "UpdateOrderIfStatus", seedFailed, func(s *OrderService, no string) error {
			_, err := s.RetryRefund(ctx, cs, no, "重试原因")
			return err
		}, ""},
		{"重试-条件更新未命中M10", "UpdateOrderIfStatusZero", seedFailed, func(s *OrderService, no string) error {
			_, err := s.RetryRefund(ctx, cs, no, "重试原因")
			return err
		}, "M-10"},
		{"重试-审计写入失败", "CreatePayment", seedFailed, func(s *OrderService, no string) error {
			_, err := s.RetryRefund(ctx, cs, no, "重试原因")
			return err
		}, ""},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			var no string
			svc, _, _ := r5Seeded(t, tc.failAt, func(t *testing.T, s *OrderService) { no = tc.seed(t, s) })
			err := tc.call(svc, no)
			if err == nil {
				t.Fatal("期望返回错误")
			}
			if tc.want != "" {
				assertBizCode(t, err, tc.want)
			} else {
				r5WantTech(t, err)
			}
		})
	}
	t.Run("重试成功恢复待处理", func(t *testing.T) {
		var o *model.Order
		svc, _, base := r5Seeded(t, "", func(t *testing.T, s *OrderService) { o = r5SeedRefundFailed(t, s) })
		got, err := svc.RetryRefund(ctx, cs, o.OrderNo, "渠道已恢复")
		if err != nil || got.RefundState != RefundStatePending || got.RefundRetryCount != 1 {
			t.Fatalf("重试后应为待处理且计数+1：got=%+v err=%v", got, err)
		}
		stored, _ := base.GetOrder(ctx, o.OrderNo)
		if stored.RefundState != RefundStatePending || stored.RefundRetryCount != 1 {
			t.Fatalf("仓储状态未更新：%+v", stored)
		}
	})
}

func TestR5HandleRefundCallbackErrorBranches(t *testing.T) {
	rc := func(no, trade string, amount int64, sign, success bool) RefundCallback {
		return RefundCallback{OrderNo: no, RefundChannelTradeNo: trade, Amount: amount, SignatureValid: sign, Success: success}
	}
	t.Run("空退款交易号M27", func(t *testing.T) {
		svc, _, _ := r5Seeded(t, "", nil)
		_, err := svc.HandleRefundCallback(ctx, mockCh, rc("ORD-X", "", 10000, true, true))
		assertBizCode(t, err, "M-27")
	})
	t.Run("成功幂等查询技术错误", func(t *testing.T) {
		svc, _, _ := r5Seeded(t, "GetPaymentByDedupKey", nil)
		r5WantTech(t, mustRefundCbErr(svc, rc("ORD-X", "RT-1", 10000, true, true)))
	})
	t.Run("失败幂等查询技术错误", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "GetPaymentByDedupKey2", func(t *testing.T, s *OrderService) { no = r5SeedRefundProcessing(t, s).OrderNo })
		r5WantTech(t, mustRefundCbErr(svc, rc(no, "RT-2", 10000, true, false)))
	})
	t.Run("同一退款交易号归属他单M27", func(t *testing.T) {
		var o *model.Order
		svc, _, _ := r5Seeded(t, "", func(t *testing.T, s *OrderService) { o = r5SeedRefunded(t, s) })
		_, err := svc.HandleRefundCallback(ctx, mockCh, rc("ORD-OTHER", "RF-OK-"+o.OrderNo, 10000, true, true))
		assertBizCode(t, err, "M-27")
	})
	t.Run("重复成功退款通知幂等留痕", func(t *testing.T) {
		var o *model.Order
		svc, _, _ := r5Seeded(t, "", func(t *testing.T, s *OrderService) { o = r5SeedRefunded(t, s) })
		p, err := svc.HandleRefundCallback(ctx, mockCh, rc(o.OrderNo, "RF-OK-"+o.OrderNo, 10000, true, true))
		if err != nil || p == nil || p.Result != ResultRepeatRefundNoop {
			t.Fatalf("重复成功通知应幂等留痕：p=%+v err=%v", p, err)
		}
	})
	t.Run("重复失败退款通知幂等留痕", func(t *testing.T) {
		var o *model.Order
		svc, _, _ := r5Seeded(t, "", func(t *testing.T, s *OrderService) { o = r5SeedRefundFailed(t, s) })
		p, err := svc.HandleRefundCallback(ctx, mockCh, rc(o.OrderNo, "RF-FAIL-"+o.OrderNo, 10000, true, false))
		if err != nil || p == nil || p.Result != ResultDuplicateNoop {
			t.Fatalf("重复失败通知应幂等留痕：p=%+v err=%v", p, err)
		}
	})
	t.Run("锁定订单技术错误", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "LockOrder", func(t *testing.T, s *OrderService) { no = r5SeedRefundProcessing(t, s).OrderNo })
		r5WantTech(t, mustRefundCbErr(svc, rc(no, "RT-3", 10000, true, true)))
	})
	t.Run("未知订单M30", func(t *testing.T) {
		svc, _, _ := r5Seeded(t, "", nil)
		_, err := svc.HandleRefundCallback(ctx, mockCh, rc("ORD-NOPE", "RT-4", 10000, true, true))
		assertBizCode(t, err, "M-30")
	})
	t.Run("验签失败M28", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "", func(t *testing.T, s *OrderService) { no = r5SeedRefundProcessing(t, s).OrderNo })
		_, err := svc.HandleRefundCallback(ctx, mockCh, rc(no, "RT-5", 10000, false, true))
		assertBizCode(t, err, "M-28")
	})
	t.Run("金额不符M29", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "", func(t *testing.T, s *OrderService) { no = r5SeedRefundProcessing(t, s).OrderNo })
		_, err := svc.HandleRefundCallback(ctx, mockCh, rc(no, "RT-6", 1, true, true))
		assertBizCode(t, err, "M-29")
	})
	t.Run("已退款订单新交易号幂等留痕", func(t *testing.T) {
		var o *model.Order
		svc, _, _ := r5Seeded(t, "", func(t *testing.T, s *OrderService) { o = r5SeedRefunded(t, s) })
		p, err := svc.HandleRefundCallback(ctx, mockCh, rc(o.OrderNo, "RT-NEW-1", 10000, true, true))
		if err != nil || p == nil || p.Result != ResultRepeatRefundNoop {
			t.Fatalf("已退款新交易号应幂等留痕：p=%+v err=%v", p, err)
		}
	})
	t.Run("非退款处理中订单M05", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "", func(t *testing.T, s *OrderService) { no = r5SeedPaid(t, s).OrderNo })
		_, err := svc.HandleRefundCallback(ctx, mockCh, rc(no, "RT-7", 10000, true, true))
		assertBizCode(t, err, "M-05")
	})
	t.Run("失败登记条件更新未命中留痕", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "UpdateOrderIfStatusZero", func(t *testing.T, s *OrderService) { no = r5SeedRefundProcessing(t, s).OrderNo })
		p, err := svc.HandleRefundCallback(ctx, mockCh, rc(no, "RT-8", 10000, true, false))
		if err != nil || p == nil || p.Result != ResultDuplicateNoop {
			t.Fatalf("失败登记未命中应幂等留痕：p=%+v err=%v", p, err)
		}
	})
	t.Run("退款成功库存守卫未命中留痕", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "UpdateOrderIfStatusAndStockNotRestoredZero", func(t *testing.T, s *OrderService) { no = r5SeedRefundProcessing(t, s).OrderNo })
		p, err := svc.HandleRefundCallback(ctx, mockCh, rc(no, "RT-9", 10000, true, true))
		if err != nil || p == nil || p.Result != ResultRepeatRefundNoop {
			t.Fatalf("库存守卫未命中应幂等留痕：p=%+v err=%v", p, err)
		}
	})
	t.Run("恢复库存锁商品技术错误", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "LockGoods", func(t *testing.T, s *OrderService) { no = r5SeedRefundProcessing(t, s).OrderNo })
		r5WantTech(t, mustRefundCbErr(svc, rc(no, "RT-10", 10000, true, true)))
	})
	t.Run("恢复库存商品为空", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "LockGoodsNil", func(t *testing.T, s *OrderService) { no = r5SeedRefundProcessing(t, s).OrderNo })
		_, err := svc.HandleRefundCallback(ctx, mockCh, rc(no, "RT-11", 10000, true, true))
		if err == nil || !strings.Contains(err.Error(), "not found during refund stock restore") {
			t.Fatalf("期望商品缺失错误，实际 %v", err)
		}
	})
	t.Run("恢复库存技术错误", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "IncreaseGoodsStock", func(t *testing.T, s *OrderService) { no = r5SeedRefundProcessing(t, s).OrderNo })
		r5WantTech(t, mustRefundCbErr(svc, rc(no, "RT-12", 10000, true, true)))
	})
	t.Run("恢复库存条件不满足", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "IncreaseGoodsStockFalse", func(t *testing.T, s *OrderService) { no = r5SeedRefundProcessing(t, s).OrderNo })
		_, err := svc.HandleRefundCallback(ctx, mockCh, rc(no, "RT-13", 10000, true, true))
		if err == nil || !strings.Contains(err.Error(), "stock restore condition not met") {
			t.Fatalf("期望恢复条件错误，实际 %v", err)
		}
	})
	t.Run("唯一键冲突传播", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "CreatePaymentDup", func(t *testing.T, s *OrderService) { no = r5SeedRefundProcessing(t, s).OrderNo })
		_, err := svc.HandleRefundCallback(ctx, mockCh, rc(no, "RT-14", 10000, true, true))
		if !errors.Is(err, ErrDuplicateDedupKey) {
			t.Fatalf("唯一键冲突应传播：%v", err)
		}
	})
}

func mustRefundCbErr(svc *OrderService, in RefundCallback) error {
	_, err := svc.HandleRefundCallback(ctx, mockCh, in)
	if err == nil {
		return errors.New("expected error but got nil")
	}
	return err
}

func TestR5RegisterShipmentBranches(t *testing.T) {
	t.Run("买家越权发货M20", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "", func(t *testing.T, s *OrderService) { no = r5SeedPaid(t, s).OrderNo })
		_, err := svc.RegisterShipment(ctx, buyer, no, "顺丰", "SF-1")
		assertBizCode(t, err, "M-20")
	})
	t.Run("空承运商M23", func(t *testing.T) {
		svc, _, _ := r5Seeded(t, "", nil)
		_, err := svc.RegisterShipment(ctx, warehouse, "ORD-X", "", "")
		assertBizCode(t, err, "M-23")
	})
	t.Run("幂等查询技术错误", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "GetPaymentByDedupKey", func(t *testing.T, s *OrderService) { no = r5SeedPaid(t, s).OrderNo })
		_, err := svc.RegisterShipment(ctx, warehouse, no, "顺丰", "SF-1")
		r5WantTech(t, err)
	})
	t.Run("重复发货幂等M19", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "", func(t *testing.T, s *OrderService) {
			no = r5SeedPaid(t, s).OrderNo
			if _, err := s.RegisterShipment(ctx, warehouse, no, "顺丰", "SF-1"); err != nil {
				t.Fatalf("首次发货失败：%v", err)
			}
		})
		_, err := svc.RegisterShipment(ctx, warehouse, no, "顺丰", "SF-2")
		assertBizCode(t, err, "M-19")
	})
	t.Run("锁定订单技术错误", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "LockOrder", func(t *testing.T, s *OrderService) { no = r5SeedPaid(t, s).OrderNo })
		_, err := svc.RegisterShipment(ctx, warehouse, no, "顺丰", "SF-1")
		r5WantTech(t, err)
	})
	t.Run("未知订单M30", func(t *testing.T) {
		svc, _, _ := r5Seeded(t, "", nil)
		_, err := svc.RegisterShipment(ctx, warehouse, "ORD-NOPE", "顺丰", "SF-1")
		assertBizCode(t, err, "M-30")
	})
	t.Run("退款审核中暂停发货M22", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "", func(t *testing.T, s *OrderService) { no = r5SeedRefundReview(t, s).OrderNo })
		_, err := svc.RegisterShipment(ctx, warehouse, no, "顺丰", "SF-1")
		assertBizCode(t, err, "M-22")
	})
	t.Run("已退款订单不可发货M11", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "", func(t *testing.T, s *OrderService) { no = r5SeedRefunded(t, s).OrderNo })
		_, err := svc.RegisterShipment(ctx, warehouse, no, "顺丰", "SF-1")
		assertBizCode(t, err, "M-11")
	})
	t.Run("待支付订单不可发货M18", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "", func(t *testing.T, s *OrderService) { no = r5SeedOrder(t, s).OrderNo })
		_, err := svc.RegisterShipment(ctx, warehouse, no, "顺丰", "SF-1")
		assertBizCode(t, err, "M-18")
	})
	t.Run("条件更新技术错误", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "UpdateOrderIfStatus", func(t *testing.T, s *OrderService) { no = r5SeedPaid(t, s).OrderNo })
		_, err := svc.RegisterShipment(ctx, warehouse, no, "顺丰", "SF-1")
		r5WantTech(t, err)
	})
	t.Run("条件更新未命中M19", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "UpdateOrderIfStatusZero", func(t *testing.T, s *OrderService) { no = r5SeedPaid(t, s).OrderNo })
		_, err := svc.RegisterShipment(ctx, warehouse, no, "顺丰", "SF-1")
		assertBizCode(t, err, "M-19")
	})
	t.Run("发货审计写入失败", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "CreatePayment", func(t *testing.T, s *OrderService) { no = r5SeedPaid(t, s).OrderNo })
		_, err := svc.RegisterShipment(ctx, warehouse, no, "顺丰", "SF-1")
		r5WantTech(t, err)
	})
	t.Run("唯一键冲突传播", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "CreatePaymentDup", func(t *testing.T, s *OrderService) { no = r5SeedPaid(t, s).OrderNo })
		_, err := svc.RegisterShipment(ctx, warehouse, no, "顺丰", "SF-1")
		if !errors.Is(err, ErrDuplicateDedupKey) {
			t.Fatalf("唯一键冲突应传播：%v", err)
		}
	})
}

func TestR5VerifyLatePaymentBranches(t *testing.T) {
	t.Run("买家越权核实M20", func(t *testing.T) {
		base, eventID := r5LateBase(t)
		_, err := r5Wrap(base, "").VerifyLatePayment(ctx, buyer, eventID, "核实")
		assertBizCode(t, err, "M-20")
	})
	t.Run("空原因M24", func(t *testing.T) {
		base, eventID := r5LateBase(t)
		_, err := r5Wrap(base, "").VerifyLatePayment(ctx, cs, eventID, "")
		assertBizCode(t, err, "M-24")
	})
	t.Run("查询事件技术错误", func(t *testing.T) {
		base, eventID := r5LateBase(t)
		_, err := r5Wrap(base, "GetPaymentByID").VerifyLatePayment(ctx, cs, eventID, "核实")
		r5WantTech(t, err)
	})
	t.Run("事件不存在M14", func(t *testing.T) {
		base, _ := r5LateBase(t)
		_, err := r5Wrap(base, "").VerifyLatePayment(ctx, cs, 999999, "核实")
		assertBizCode(t, err, "M-14")
	})
	t.Run("核实查询技术错误", func(t *testing.T) {
		base, eventID := r5LateBase(t)
		_, err := r5Wrap(base, "HasPaymentEvent").VerifyLatePayment(ctx, cs, eventID, "核实")
		r5WantTech(t, err)
	})
	t.Run("重复核实幂等M10", func(t *testing.T) {
		base, eventID := r5VerifiedBase(t)
		_, err := r5Wrap(base, "").VerifyLatePayment(ctx, cs, eventID, "再次核实")
		assertBizCode(t, err, "M-10")
	})
	t.Run("核实审计写入失败", func(t *testing.T) {
		base, eventID := r5LateBase(t)
		_, err := r5Wrap(base, "CreatePayment").VerifyLatePayment(ctx, cs, eventID, "核实")
		r5WantTech(t, err)
	})
	t.Run("核实成功只追加不改原记录", func(t *testing.T) {
		base, eventID := r5LateBase(t)
		p, err := r5Wrap(base, "").VerifyLatePayment(ctx, cs, eventID, "核实为重复通知")
		if err != nil || p == nil || p.EventType != EventLatePaymentVerified || p.RelatedEventID != eventID {
			t.Fatalf("核实事件不符：p=%+v err=%v", p, err)
		}
		origin, _ := base.GetPaymentByID(ctx, eventID)
		if origin == nil || origin.Result != ResultLatePaymentPending {
			t.Fatalf("原异常记录不得被修改：%+v", origin)
		}
	})
}

func TestR5InitiateLatePaymentRefundBranches(t *testing.T) {
	t.Run("空退款单号M27", func(t *testing.T) {
		base, eventID := r5VerifiedBase(t)
		_, err := r5Wrap(base, "").InitiateLatePaymentRefund(ctx, cs, eventID, "", "原因")
		assertBizCode(t, err, "M-27")
	})
	t.Run("空原因M24", func(t *testing.T) {
		base, eventID := r5VerifiedBase(t)
		_, err := r5Wrap(base, "").InitiateLatePaymentRefund(ctx, cs, eventID, "LR-X", "")
		assertBizCode(t, err, "M-24")
	})
	t.Run("查询事件技术错误", func(t *testing.T) {
		base, eventID := r5VerifiedBase(t)
		_, err := r5Wrap(base, "GetPaymentByID").InitiateLatePaymentRefund(ctx, cs, eventID, "LR-X", "原因")
		r5WantTech(t, err)
	})
	t.Run("事件不存在M14", func(t *testing.T) {
		base, _ := r5VerifiedBase(t)
		_, err := r5Wrap(base, "").InitiateLatePaymentRefund(ctx, cs, 999999, "LR-X", "原因")
		assertBizCode(t, err, "M-14")
	})
	t.Run("核实查询技术错误", func(t *testing.T) {
		base, eventID := r5VerifiedBase(t)
		_, err := r5Wrap(base, "HasPaymentEvent").InitiateLatePaymentRefund(ctx, cs, eventID, "LR-X", "原因")
		r5WantTech(t, err)
	})
	t.Run("未核实不得发起M24", func(t *testing.T) {
		base, eventID := r5LateBase(t)
		_, err := r5Wrap(base, "").InitiateLatePaymentRefund(ctx, cs, eventID, "LR-X", "原因")
		assertBizCode(t, err, "M-24")
	})
	t.Run("请求幂等查询技术错误", func(t *testing.T) {
		base, eventID := r5VerifiedBase(t)
		_, err := r5Wrap(base, "GetPaymentByDedupKey").InitiateLatePaymentRefund(ctx, cs, eventID, "LR-X", "原因")
		r5WantTech(t, err)
	})
	t.Run("重复发起幂等M10", func(t *testing.T) {
		base, eventID := r5RequestedBase(t)
		_, err := r5Wrap(base, "").InitiateLatePaymentRefund(ctx, cs, eventID, "LR-1", "再次发起")
		assertBizCode(t, err, "M-10")
	})
	t.Run("请求审计写入失败", func(t *testing.T) {
		base, eventID := r5VerifiedBase(t)
		_, err := r5Wrap(base, "CreatePayment").InitiateLatePaymentRefund(ctx, cs, eventID, "LR-X", "原因")
		r5WantTech(t, err)
	})
	t.Run("唯一键冲突传播", func(t *testing.T) {
		base, eventID := r5VerifiedBase(t)
		_, err := r5Wrap(base, "CreatePaymentDup").InitiateLatePaymentRefund(ctx, cs, eventID, "LR-X", "原因")
		if !errors.Is(err, ErrDuplicateDedupKey) {
			t.Fatalf("唯一键冲突应传播：%v", err)
		}
	})
}

func TestR5RetryLatePaymentRefundBranches(t *testing.T) {
	t.Run("空备注M24", func(t *testing.T) {
		base, eventID := r5RequestedBase(t)
		_, err := r5Wrap(base, "").RetryLatePaymentRefund(ctx, cs, eventID, "LR-1", "")
		assertBizCode(t, err, "M-24")
	})
	t.Run("查询事件技术错误", func(t *testing.T) {
		base, eventID := r5RequestedBase(t)
		_, err := r5Wrap(base, "GetPaymentByID").RetryLatePaymentRefund(ctx, cs, eventID, "LR-1", "备注")
		r5WantTech(t, err)
	})
	t.Run("事件不存在M14", func(t *testing.T) {
		base, _ := r5RequestedBase(t)
		_, err := r5Wrap(base, "").RetryLatePaymentRefund(ctx, cs, 999999, "LR-X", "备注")
		assertBizCode(t, err, "M-14")
	})
	t.Run("核实查询技术错误", func(t *testing.T) {
		base, eventID := r5RequestedBase(t)
		_, err := r5Wrap(base, "HasPaymentEvent").RetryLatePaymentRefund(ctx, cs, eventID, "LR-1", "备注")
		r5WantTech(t, err)
	})
	t.Run("请求查询技术错误", func(t *testing.T) {
		base, eventID := r5RequestedBase(t)
		_, err := r5Wrap(base, "GetPaymentByDedupKey").RetryLatePaymentRefund(ctx, cs, eventID, "LR-1", "备注")
		r5WantTech(t, err)
	})
	t.Run("未发起请求不得重试M24", func(t *testing.T) {
		base, eventID := r5VerifiedBase(t)
		_, err := r5Wrap(base, "").RetryLatePaymentRefund(ctx, cs, eventID, "LR-NONE", "备注")
		assertBizCode(t, err, "M-24")
	})
	t.Run("重试审计写入失败", func(t *testing.T) {
		base, eventID := r5RequestedBase(t)
		_, err := r5Wrap(base, "CreatePayment").RetryLatePaymentRefund(ctx, cs, eventID, "LR-1", "备注")
		r5WantTech(t, err)
	})
	t.Run("重试成功只追加", func(t *testing.T) {
		base, eventID := r5RequestedBase(t)
		p, err := r5Wrap(base, "").RetryLatePaymentRefund(ctx, cs, eventID, "LR-1", "渠道已恢复")
		if err != nil || p == nil || p.EventType != EventLateRefundRetry {
			t.Fatalf("重试事件不符：p=%+v err=%v", p, err)
		}
	})
}

func TestR5HandleLatePaymentRefundCallbackBranches(t *testing.T) {
	lc := func(eventID uint64, refundNo string, amount int64, sign, success bool) LateRefundCallback {
		return LateRefundCallback{EventID: eventID, RefundNo: refundNo, Amount: amount, SignatureValid: sign, Success: success}
	}
	t.Run("空退款单号M27", func(t *testing.T) {
		base, _ := r5RequestedBase(t)
		_, err := r5Wrap(base, "").HandleLatePaymentRefundCallback(ctx, mockCh, lc(1, "", 10000, true, true))
		assertBizCode(t, err, "M-27")
	})
	t.Run("成功幂等查询技术错误", func(t *testing.T) {
		base, eventID := r5RequestedBase(t)
		_, err := r5Wrap(base, "GetPaymentByDedupKey").HandleLatePaymentRefundCallback(ctx, mockCh, lc(eventID, "LR-1", 10000, true, true))
		r5WantTech(t, err)
	})
	t.Run("重复成功通知幂等M25", func(t *testing.T) {
		base, eventID := r5RequestedBase(t)
		clean := NewOrderServiceWithClock(base, func() time.Time { return fixedTime })
		if _, err := clean.HandleLatePaymentRefundCallback(ctx, mockCh, lc(eventID, "LR-1", 10000, true, true)); err != nil {
			t.Fatalf("首次成功回调失败：%v", err)
		}
		p, err := r5Wrap(base, "").HandleLatePaymentRefundCallback(ctx, mockCh, lc(eventID, "LR-1", 10000, true, true))
		if err != nil || p == nil || p.Result != ResultRepeatRefundNoop {
			t.Fatalf("重复成功通知应幂等留痕：p=%+v err=%v", p, err)
		}
	})
	t.Run("重复失败通知幂等M10", func(t *testing.T) {
		base, eventID := r5RequestedBase(t)
		clean := NewOrderServiceWithClock(base, func() time.Time { return fixedTime })
		_, err := clean.HandleLatePaymentRefundCallback(ctx, mockCh, lc(eventID, "LR-1", 10000, true, false))
		assertBizCode(t, err, "M-08")
		p, err := r5Wrap(base, "").HandleLatePaymentRefundCallback(ctx, mockCh, lc(eventID, "LR-1", 10000, true, false))
		if err != nil || p == nil || p.Result != ResultDuplicateNoop {
			t.Fatalf("重复失败通知应幂等留痕：p=%+v err=%v", p, err)
		}
	})
	t.Run("查询事件技术错误", func(t *testing.T) {
		base, eventID := r5RequestedBase(t)
		_, err := r5Wrap(base, "GetPaymentByID").HandleLatePaymentRefundCallback(ctx, mockCh, lc(eventID, "LR-1", 10000, true, true))
		r5WantTech(t, err)
	})
	t.Run("事件不存在M14", func(t *testing.T) {
		base, _ := r5RequestedBase(t)
		_, err := r5Wrap(base, "").HandleLatePaymentRefundCallback(ctx, mockCh, lc(999999, "LR-X", 10000, true, true))
		assertBizCode(t, err, "M-14")
	})
	t.Run("核实查询技术错误", func(t *testing.T) {
		base, eventID := r5RequestedBase(t)
		_, err := r5Wrap(base, "HasPaymentEvent").HandleLatePaymentRefundCallback(ctx, mockCh, lc(eventID, "LR-1", 10000, true, true))
		r5WantTech(t, err)
	})
	t.Run("请求查询技术错误", func(t *testing.T) {
		base, eventID := r5RequestedBase(t)
		_, err := r5Wrap(base, "GetPaymentByDedupKey3").HandleLatePaymentRefundCallback(ctx, mockCh, lc(eventID, "LR-1", 10000, true, true))
		r5WantTech(t, err)
	})
	t.Run("未发起请求M24", func(t *testing.T) {
		base, eventID := r5VerifiedBase(t)
		_, err := r5Wrap(base, "").HandleLatePaymentRefundCallback(ctx, mockCh, lc(eventID, "LR-NONE", 10000, true, true))
		assertBizCode(t, err, "M-24")
	})
	t.Run("锁定订单技术错误", func(t *testing.T) {
		base, eventID := r5RequestedBase(t)
		_, err := r5Wrap(base, "LockOrder").HandleLatePaymentRefundCallback(ctx, mockCh, lc(eventID, "LR-1", 10000, true, true))
		r5WantTech(t, err)
	})
	t.Run("验签失败M28", func(t *testing.T) {
		base, eventID := r5RequestedBase(t)
		_, err := r5Wrap(base, "").HandleLatePaymentRefundCallback(ctx, mockCh, lc(eventID, "LR-1", 10000, false, true))
		assertBizCode(t, err, "M-28")
	})
	t.Run("金额不符M29", func(t *testing.T) {
		base, eventID := r5RequestedBase(t)
		_, err := r5Wrap(base, "").HandleLatePaymentRefundCallback(ctx, mockCh, lc(eventID, "LR-1", 1, true, true))
		assertBizCode(t, err, "M-29")
	})
	t.Run("渠道失败保留待处理M08", func(t *testing.T) {
		base, eventID := r5RequestedBase(t)
		_, err := r5Wrap(base, "").HandleLatePaymentRefundCallback(ctx, mockCh, lc(eventID, "LR-1", 10000, true, false))
		assertBizCode(t, err, "M-08")
	})
	t.Run("成功审计写入失败", func(t *testing.T) {
		base, eventID := r5RequestedBase(t)
		_, err := r5Wrap(base, "CreatePayment").HandleLatePaymentRefundCallback(ctx, mockCh, lc(eventID, "LR-1", 10000, true, true))
		r5WantTech(t, err)
	})
	t.Run("唯一键冲突传播", func(t *testing.T) {
		base, eventID := r5RequestedBase(t)
		_, err := r5Wrap(base, "CreatePaymentDup").HandleLatePaymentRefundCallback(ctx, mockCh, lc(eventID, "LR-1", 10000, true, true))
		if !errors.Is(err, ErrDuplicateDedupKey) {
			t.Fatalf("唯一键冲突应传播：%v", err)
		}
	})
}

func TestR5GetOrderBoundaryBranches(t *testing.T) {
	t.Run("空角色M20", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "", func(t *testing.T, s *OrderService) { no = r5SeedOrder(t, s).OrderNo })
		_, err := svc.GetOrder(ctx, Actor{}, no)
		assertBizCode(t, err, "M-20")
	})
	t.Run("仓储查询技术错误", func(t *testing.T) {
		var no string
		svc, _, _ := r5Seeded(t, "GetOrder", func(t *testing.T, s *OrderService) { no = r5SeedOrder(t, s).OrderNo })
		_, err := svc.GetOrder(ctx, buyer, no)
		r5WantTech(t, err)
	})
	t.Run("汇总计数技术错误", func(t *testing.T) {
		svc, _, _ := r5Seeded(t, "CountOrders", nil)
		_, err := svc.GetOpsSummary(ctx, ops)
		r5WantTech(t, err)
	})
}

func TestR5DemoRepositoryBoundaryBranches(t *testing.T) {
	t.Run("扣减库存商品不存在", func(t *testing.T) {
		repo := newMemoryRepository(testGoodsWithID())
		ok, err := repo.DecreaseGoodsStock(ctx, 999, 1)
		if ok || err != nil {
			t.Fatalf("不存在商品应返回 false,nil：ok=%v err=%v", ok, err)
		}
	})
	t.Run("扣减库存商品已下架", func(t *testing.T) {
		off := testGoodsWithID()
		off.Status = "下架"
		repo := newMemoryRepository(off)
		ok, err := repo.DecreaseGoodsStock(ctx, 1, 1)
		if ok || err != nil {
			t.Fatalf("下架商品应返回 false,nil：ok=%v err=%v", ok, err)
		}
	})
	t.Run("恢复库存占用不足", func(t *testing.T) {
		repo := newMemoryRepository(testGoodsWithID())
		ok, err := repo.IncreaseGoodsStock(ctx, 1, 10)
		if ok || err != nil {
			t.Fatalf("占用不足应返回 false,nil：ok=%v err=%v", ok, err)
		}
	})
	t.Run("按主键锁定不存在订单", func(t *testing.T) {
		repo := newMemoryRepository(testGoodsWithID())
		o, err := repo.LockOrderByID(ctx, 999)
		if o != nil || err != nil {
			t.Fatalf("不存在订单应返回 nil,nil：o=%v err=%v", o, err)
		}
	})
	t.Run("条件更新订单不存在", func(t *testing.T) {
		repo := newMemoryRepository(testGoodsWithID())
		rows, err := repo.UpdateOrderIfStatus(ctx, &model.Order{}, []string{StatusPendingPayment}, map[string]interface{}{"status": StatusCancelled})
		if rows != 0 || err != nil {
			t.Fatalf("不存在订单应返回 0,nil：rows=%d err=%v", rows, err)
		}
	})
	t.Run("条件更新状态不允许", func(t *testing.T) {
		repo := newMemoryRepository(testGoodsWithID())
		svc := NewOrderServiceWithClock(repo, func() time.Time { return fixedTime })
		o := r5SeedOrder(t, svc)
		rows, err := repo.UpdateOrderIfStatus(ctx, o, []string{StatusShipped}, map[string]interface{}{"status": StatusCancelled})
		if rows != 0 || err != nil {
			t.Fatalf("状态不允许应返回 0,nil：rows=%d err=%v", rows, err)
		}
	})
	t.Run("库存守卫更新已恢复订单", func(t *testing.T) {
		repo := newMemoryRepository(testGoodsWithID())
		svc := NewOrderServiceWithClock(repo, func() time.Time { return fixedTime })
		o := r5SeedRefunded(t, svc)
		stored, err := repo.GetOrder(ctx, o.OrderNo)
		if err != nil || !stored.StockRestored {
			t.Fatalf("前置应已恢复库存：%+v err=%v", stored, err)
		}
		rows, err := repo.UpdateOrderIfStatusAndStockNotRestored(ctx, stored, []string{StatusRefunded}, map[string]interface{}{"status": StatusClosed})
		if rows != 0 || err != nil {
			t.Fatalf("已恢复订单应返回 0,nil：rows=%d err=%v", rows, err)
		}
	})
	t.Run("重复创建订单映射唯一键冲突", func(t *testing.T) {
		repo := newMemoryRepository(testGoodsWithID())
		svc := NewOrderServiceWithClock(repo, func() time.Time { return fixedTime })
		o := r5SeedOrder(t, svc)
		dup := *o
		if err := repo.CreateOrder(ctx, &dup); !errors.Is(err, ErrDuplicateDedupKey) {
			t.Fatalf("重复订单应返回 ErrDuplicateDedupKey：%v", err)
		}
	})
}
