package v1

import (
	"github.com/gin-gonic/gin"

	"shop-trade/server/model"
	"shop-trade/server/service"
)

// model 层只有 gorm tag，没有 json tag；controller 在此统一转成 snake_case 响应，
// 与定稿接口清单、Apipost 用例和原型页面字段一致，且不改动 model / service 既有文件。
func orderView(o *model.Order) gin.H {
	if o == nil {
		return nil
	}
	return gin.H{
		"id":                      o.ID,
		"order_no":                o.OrderNo,
		"buyer_id":                o.BuyerID,
		"goods_id":                o.GoodsID,
		"goods_no":                o.GoodsNo,
		"goods_name":              o.GoodsName,
		"quantity":                o.Quantity,
		"unit_price":              o.UnitPrice,
		"total_amount":            o.TotalAmount,
		"status":                  o.Status,
		"expires_at":              o.ExpiresAt,
		"paid_at":                 o.PaidAt,
		"closed_at":               o.ClosedAt,
		"cancelled_at":            o.CancelledAt,
		"refund_kind":             o.RefundKind,
		"refund_reason":           o.RefundReason,
		"refund_state":            o.RefundState,
		"refund_retry_count":      o.RefundRetryCount,
		"refund_channel_trade_no": o.RefundChannelTradeNo,
		"refunded_at":             o.RefundedAt,
		"stock_restored":          o.StockRestored,
		"late_payment_refunded":   o.LatePaymentRefunded,
		"shipment_carrier":        o.ShipmentCarrier,
		"shipment_tracking_no":    o.ShipmentTrackingNo,
		"shipped_at":              o.ShippedAt,
	}
}

func paymentView(p *model.Payment) gin.H {
	if p == nil {
		return nil
	}
	return gin.H{
		"id":                    p.ID,
		"event_id":              p.ID,
		"order_id":              p.OrderID,
		"order_no":              p.OrderNo,
		"channel_trade_no":      p.ChannelTradeNo,
		"event_type":            p.EventType,
		"result":                p.Result,
		"amount":                p.Amount,
		"signature_valid":       p.SignatureValid,
		"failure_code":          p.FailureCode,
		"failure_reason":        p.FailureReason,
		"order_status_snapshot": p.OrderStatusSnapshot,
		"need_refund":           p.NeedRefund,
		"effective":             p.Effective,
		"occurred_at":           p.OccurredAt,
	}
}

func summaryView(s *service.OpsSummary) gin.H {
	if s == nil {
		return nil
	}
	return gin.H{
		"total_orders":                  s.TotalOrders,
		"effective_payment_amount":      s.EffectivePaymentAmount,
		"late_payment_events":           s.LatePaymentEvents,
		"late_payment_refunded_events":  s.LatePaymentRefundedEvents,
		"refunded_orders":               s.RefundedOrders,
		"shipped_orders":                s.ShippedOrders,
		"stock_restored_events":         s.StockRestoredEvents,
		"duplicate_release_noop_events": s.DuplicateReleaseNoopEvents,
		"duplicate_refund_events":       s.DuplicateRefundEvents,
		"no_duplicate_release_refund":   s.NoDuplicateReleaseRefund,
	}
}

func goodsViews(goods []model.Goods) []gin.H {
	items := make([]gin.H, 0, len(goods))
	for _, g := range goods {
		items = append(items, gin.H{
			"id":              g.ID,
			"goods_no":        g.GoodsNo,
			"name":            g.Name,
			"unit_price":      g.UnitPrice,
			"available_stock": g.AvailableStock,
			"occupied_stock":  g.OccupiedStock,
			"status":          g.Status,
		})
	}
	return items
}
