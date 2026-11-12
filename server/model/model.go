package model

import (
	"time"

	"shop-trade/server/global"
)

// Goods 商品表；金额单位为分；一单仅引用一个 goods_id。
type Goods struct {
	global.GVA_MODEL
	GoodsNo        string `gorm:"column:goods_no;type:varchar(64);not null;uniqueIndex:uk_goods_goods_no;comment:商品编号"`
	Name           string `gorm:"column:name;type:varchar(128);not null;comment:商品名称"`
	UnitPrice      int64  `gorm:"column:unit_price;type:bigint;not null;comment:单价（分）"`
	AvailableStock int    `gorm:"column:available_stock;type:int;not null;default:0;index:idx_goods_available_stock;comment:可售数量"`
	OccupiedStock  int    `gorm:"column:occupied_stock;type:int;not null;default:0;comment:预扣占用数量"`
	Status         string `gorm:"column:status;type:varchar(32);not null;index:idx_goods_status;comment:在售/下架"`
}

func (Goods) TableName() string { return "goods" }

// Order 订单表；表名 order 为 MySQL 保留字，GORM 会自动使用反引号转义。
// 一单一商品：仅保存 goods_id、goods_no、quantity 与下单时价格快照。
type Order struct {
	global.GVA_MODEL
	OrderNo              string     `gorm:"column:order_no;type:varchar(64);not null;uniqueIndex:uk_order_order_no;comment:订单号"`
	BuyerID              uint64     `gorm:"column:buyer_id;type:bigint unsigned;not null;index:idx_order_buyer_status,priority:1;comment:买家ID"`
	GoodsID              uint64     `gorm:"column:goods_id;type:bigint unsigned;not null;index:idx_order_goods_id;comment:单一商品ID"`
	GoodsNo              string     `gorm:"column:goods_no;type:varchar(64);not null;comment:下单时商品编号快照"`
	GoodsName            string     `gorm:"column:goods_name;type:varchar(128);not null;comment:下单时商品名称快照"`
	Quantity             int        `gorm:"column:quantity;type:int;not null;comment:数量1或2"`
	UnitPrice            int64      `gorm:"column:unit_price;type:bigint;not null;comment:下单时单价（分）"`
	TotalAmount          int64      `gorm:"column:total_amount;type:bigint;not null;comment:应付金额（分）"`
	Status               string     `gorm:"column:status;type:varchar(32);not null;index:idx_order_status;index:idx_order_status_expires,priority:1;comment:订单状态"`
	ExpiresAt            time.Time  `gorm:"column:expires_at;type:datetime(3);not null;index:idx_order_status_expires,priority:2;comment:服务端10分钟到期时间"`
	PaidAt               *time.Time `gorm:"column:paid_at;type:datetime(3);comment:支付时间"`
	ClosedAt             *time.Time `gorm:"column:closed_at;type:datetime(3);comment:超时关闭时间"`
	CancelledAt          *time.Time `gorm:"column:cancelled_at;type:datetime(3);comment:主动取消时间"`
	RefundKind           string     `gorm:"column:refund_kind;type:varchar(32);not null;default:'';comment:退款类型"`
	RefundReason         string     `gorm:"column:refund_reason;type:varchar(512);not null;default:'';comment:退款申请原因"`
	RefundApplyAt        *time.Time `gorm:"column:refund_apply_at;type:datetime(3);comment:退款申请时间"`
	RefundAuditAt        *time.Time `gorm:"column:refund_audit_at;type:datetime(3);comment:退款审核时间"`
	RefundAuditorID      uint64     `gorm:"column:refund_auditor_id;type:bigint unsigned;not null;default:0;comment:客服ID"`
	RefundAuditRemark    string     `gorm:"column:refund_audit_remark;type:varchar(512);not null;default:'';comment:审核/核实原因"`
	RefundState          string     `gorm:"column:refund_state;type:varchar(32);not null;default:'';comment:退款处理子状态"`
	RefundRetryCount     int        `gorm:"column:refund_retry_count;type:int;not null;default:0;comment:退款重试次数"`
	RefundChannelTradeNo string     `gorm:"column:refund_channel_trade_no;type:varchar(128);index:idx_order_refund_channel_trade_no;comment:退款渠道交易号"`
	RefundedAt           *time.Time `gorm:"column:refunded_at;type:datetime(3);comment:退款成功时间"`
	StockRestored        bool       `gorm:"column:stock_restored;type:tinyint(1);not null;default:0;comment:正常售前退款是否已恢复库存一次"`
	LatePaymentRefunded  bool       `gorm:"column:late_payment_refunded;type:tinyint(1);not null;default:0;comment:迟到支付退款是否完成"`
	ShipmentCarrier      string     `gorm:"column:shipment_carrier;type:varchar(128);not null;default:'';comment:承运方"`
	ShipmentTrackingNo   string     `gorm:"column:shipment_tracking_no;type:varchar(128);not null;default:'';comment:运单号"`
	ShippedAt            *time.Time `gorm:"column:shipped_at;type:datetime(3);comment:发货登记时间"`
	ShipmentRegisteredBy uint64     `gorm:"column:shipment_registered_by;type:bigint unsigned;not null;default:0;comment:仓库操作人ID"`
}

func (Order) TableName() string { return "order" }

// Payment 支付记录表，同时承载支付通知处理结果、异常支付、退款回调和只追加审计事件。
// effective/dedup_key 仅用于有效业务结果幂等；审计事件 effective 为空，可重复追加。
type Payment struct {
	global.GVA_MODEL
	OrderID             uint64    `gorm:"column:order_id;type:bigint unsigned;not null;default:0;index:idx_payment_order_id;comment:订单ID"`
	OrderNo             string    `gorm:"column:order_no;type:varchar(64);not null;default:'';index:idx_payment_order_no;comment:订单号"`
	ChannelTradeNo      string    `gorm:"column:channel_trade_no;type:varchar(128);not null;uniqueIndex:uk_payment_channel_effective,priority:1;comment:渠道交易号"`
	DedupKey            *string   `gorm:"column:dedup_key;type:varchar(191);uniqueIndex:uk_payment_dedup_key;comment:幂等键"`
	Effective           *bool     `gorm:"column:effective;type:tinyint(1);uniqueIndex:uk_payment_channel_effective,priority:2;comment:是否有效业务结果"`
	EventType           string    `gorm:"column:event_type;type:varchar(64);not null;index:idx_payment_event_type;comment:事件类型"`
	Result              string    `gorm:"column:result;type:varchar(64);not null;index:idx_payment_result;comment:处理结果"`
	Amount              int64     `gorm:"column:amount;type:bigint;not null;default:0;comment:金额（分）"`
	SignatureValid      bool      `gorm:"column:signature_valid;type:tinyint(1);not null;default:1;comment:验签是否通过"`
	FailureCode         string    `gorm:"column:failure_code;type:varchar(16);comment:M-xx失败原因编号"`
	FailureReason       string    `gorm:"column:failure_reason;type:varchar(512);not null;default:'';comment:中文失败/拒绝原因"`
	OrderStatusSnapshot string    `gorm:"column:order_status_snapshot;type:varchar(32);not null;default:'';comment:事件发生时订单状态"`
	NeedRefund          bool      `gorm:"column:need_refund;type:tinyint(1);not null;default:0;comment:是否需要客服发起退款"`
	RestoredStock       bool      `gorm:"column:restored_stock;type:tinyint(1);not null;default:0;comment:本事件是否恢复库存"`
	RelatedEventID      uint64    `gorm:"column:related_event_id;type:bigint unsigned;not null;default:0;index:idx_payment_related_event_id;comment:关联异常事件ID"`
	OperatorID          uint64    `gorm:"column:operator_id;type:bigint unsigned;not null;default:0;comment:操作人ID"`
	OccurredAt          time.Time `gorm:"column:occurred_at;type:datetime(3);not null;index:idx_payment_occurred_at;comment:事件发生时间"`
}

func (Payment) TableName() string { return "payment" }
