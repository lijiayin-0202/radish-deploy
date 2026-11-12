package service

import (
	"context"
	"errors"
	"sort"
	"sync"
	"time"

	"shop-trade/server/global"
	"shop-trade/server/model"
)

// memoryRepository 是演示模式（无 MySQL DSN）与单元测试草案共用的内存仓储。
// 它只保证进程内互斥与可演示性，不提供持久化，也不替代 MySQL(InnoDB) 事务 + 行锁：
// 服务重启后数据会丢失，正式第 1 轮并发证据必须由测试 Agent 在真实 MySQL(InnoDB) 环境重跑。
// 本文件只新增仓储实现，不改动 order_service.go / gorm_repository.go / types.go 的业务逻辑。
type memoryRepository struct {
	mu            sync.Mutex
	goods         map[uint64]*model.Goods
	orders        map[string]*model.Order
	ordersByID    map[uint64]*model.Order
	payments      []*model.Payment
	nextOrderID   uint64
	nextPaymentID uint64
}

// DemoGoods 返回演示模式预置商品（金额单位为分，活动商品可售 5 件）。
func DemoGoods() []model.Goods {
	return []model.Goods{
		{
			GVA_MODEL:      global.GVA_MODEL{ID: 1},
			GoodsNo:        "GOODS-ACT-001",
			Name:           "活动商品",
			UnitPrice:      10000,
			AvailableStock: 5,
			OccupiedStock:  0,
			Status:         GoodsStatusOnSale,
		},
		{
			GVA_MODEL:      global.GVA_MODEL{ID: 2},
			GoodsNo:        "GOODS-DEMO-002",
			Name:           "演示商品",
			UnitPrice:      10000,
			AvailableStock: 2,
			OccupiedStock:  0,
			Status:         GoodsStatusOnSale,
		},
	}
}

// NewDemoOrderRepository 构造可启动的演示仓储；main.go 在未配置 MySQL DSN 时使用。
func NewDemoOrderRepository() OrderRepository {
	goods := DemoGoods()
	ptrs := make([]*model.Goods, 0, len(goods))
	for i := range goods {
		ptrs = append(ptrs, &goods[i])
	}
	return newMemoryRepository(ptrs...)
}

func newMemoryRepository(goods ...*model.Goods) *memoryRepository {
	r := &memoryRepository{
		goods:      map[uint64]*model.Goods{},
		orders:     map[string]*model.Order{},
		ordersByID: map[uint64]*model.Order{},
		payments:   []*model.Payment{},
	}
	for _, g := range goods {
		r.goods[uint64(g.ID)] = cloneGoods(g)
	}
	return r
}

func cloneTimePtr(t *time.Time) *time.Time {
	if t == nil {
		return nil
	}
	c := *t
	return &c
}

func cloneGoods(g *model.Goods) *model.Goods {
	c := *g
	return &c
}

func cloneOrder(o *model.Order) *model.Order {
	c := *o
	c.PaidAt = cloneTimePtr(o.PaidAt)
	c.ClosedAt = cloneTimePtr(o.ClosedAt)
	c.CancelledAt = cloneTimePtr(o.CancelledAt)
	c.RefundApplyAt = cloneTimePtr(o.RefundApplyAt)
	c.RefundAuditAt = cloneTimePtr(o.RefundAuditAt)
	c.RefundedAt = cloneTimePtr(o.RefundedAt)
	c.ShippedAt = cloneTimePtr(o.ShippedAt)
	return &c
}

func clonePayment(p *model.Payment) *model.Payment {
	c := *p
	if p.DedupKey != nil {
		v := *p.DedupKey
		c.DedupKey = &v
	}
	if p.Effective != nil {
		v := *p.Effective
		c.Effective = &v
	}
	return &c
}

func (m *memoryRepository) cloneLocked() *memoryRepository {
	c := &memoryRepository{
		goods:         map[uint64]*model.Goods{},
		orders:        map[string]*model.Order{},
		ordersByID:    map[uint64]*model.Order{},
		payments:      make([]*model.Payment, 0, len(m.payments)),
		nextOrderID:   m.nextOrderID,
		nextPaymentID: m.nextPaymentID,
	}
	for k, v := range m.goods {
		c.goods[k] = cloneGoods(v)
	}
	for k, v := range m.orders {
		o := cloneOrder(v)
		c.orders[k] = o
		c.ordersByID[uint64(o.ID)] = o
	}
	for _, p := range m.payments {
		c.payments = append(c.payments, clonePayment(p))
	}
	return c
}

func (m *memoryRepository) assignLocked(src *memoryRepository) {
	src.mu.Lock()
	defer src.mu.Unlock()
	m.goods = src.goods
	m.orders = src.orders
	m.ordersByID = src.ordersByID
	m.payments = src.payments
	m.nextOrderID = src.nextOrderID
	m.nextPaymentID = src.nextPaymentID
}

func (m *memoryRepository) WithTransaction(_ context.Context, fn func(OrderRepository) error) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	snapshot := m.cloneLocked()
	tx := m.cloneLocked()
	err := fn(tx)
	if err != nil {
		var bizErr *BizError
		if errors.As(err, &bizErr) && bizErr.Commit {
			m.assignLocked(tx)
			return err
		}
		m.assignLocked(snapshot)
		return err
	}
	m.assignLocked(tx)
	return nil
}

func (m *memoryRepository) LockGoods(_ context.Context, goodsID uint64) (*model.Goods, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	g, ok := m.goods[goodsID]
	if !ok {
		return nil, nil
	}
	return cloneGoods(g), nil
}

func (m *memoryRepository) DecreaseGoodsStock(_ context.Context, goodsID uint64, quantity int) (bool, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	g, ok := m.goods[goodsID]
	if !ok || g.Status != GoodsStatusOnSale || g.AvailableStock < quantity {
		return false, nil
	}
	g.AvailableStock -= quantity
	g.OccupiedStock += quantity
	return true, nil
}

func (m *memoryRepository) IncreaseGoodsStock(_ context.Context, goodsID uint64, quantity int) (bool, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	g, ok := m.goods[goodsID]
	if !ok || g.OccupiedStock < quantity {
		return false, nil
	}
	g.AvailableStock += quantity
	g.OccupiedStock -= quantity
	return true, nil
}

func (m *memoryRepository) LockOrder(_ context.Context, orderNo string) (*model.Order, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	o, ok := m.orders[orderNo]
	if !ok {
		return nil, nil
	}
	return cloneOrder(o), nil
}

func (m *memoryRepository) LockOrderByID(_ context.Context, orderID uint64) (*model.Order, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	o, ok := m.ordersByID[orderID]
	if !ok {
		return nil, nil
	}
	return cloneOrder(o), nil
}

func (m *memoryRepository) GetOrder(_ context.Context, orderNo string) (*model.Order, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	o, ok := m.orders[orderNo]
	if !ok {
		return nil, nil
	}
	return cloneOrder(o), nil
}

func (m *memoryRepository) CreateOrder(_ context.Context, order *model.Order) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if _, exists := m.orders[order.OrderNo]; exists {
		return ErrDuplicateDedupKey
	}
	m.nextOrderID++
	order.ID = uint(m.nextOrderID)
	now := time.Now()
	order.CreatedAt = now
	order.UpdatedAt = now
	stored := cloneOrder(order)
	m.orders[order.OrderNo] = stored
	m.ordersByID[uint64(stored.ID)] = stored
	return nil
}

func (m *memoryRepository) UpdateOrderIfStatus(_ context.Context, order *model.Order, allowed []string, fields map[string]interface{}) (int64, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	stored, ok := m.ordersByID[uint64(order.ID)]
	if !ok || !contains(allowed, stored.Status) {
		return 0, nil
	}
	applyOrderFields(stored, fields)
	return 1, nil
}

func (m *memoryRepository) UpdateOrderIfStatusAndStockNotRestored(_ context.Context, order *model.Order, allowed []string, fields map[string]interface{}) (int64, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	stored, ok := m.ordersByID[uint64(order.ID)]
	if !ok || stored.StockRestored || !contains(allowed, stored.Status) {
		return 0, nil
	}
	applyOrderFields(stored, fields)
	return 1, nil
}

func applyOrderFields(o *model.Order, fields map[string]interface{}) {
	for k, v := range fields {
		switch k {
		case "status":
			o.Status = v.(string)
		case "paid_at":
			o.PaidAt = timeField(v)
		case "closed_at":
			o.ClosedAt = timeField(v)
		case "cancelled_at":
			o.CancelledAt = timeField(v)
		case "refund_kind":
			o.RefundKind = v.(string)
		case "refund_reason":
			o.RefundReason = v.(string)
		case "refund_apply_at":
			o.RefundApplyAt = timeField(v)
		case "refund_audit_at":
			o.RefundAuditAt = timeField(v)
		case "refund_auditor_id":
			o.RefundAuditorID = v.(uint64)
		case "refund_audit_remark":
			o.RefundAuditRemark = v.(string)
		case "refund_state":
			o.RefundState = v.(string)
		case "refund_retry_count":
			o.RefundRetryCount = v.(int)
		case "refund_channel_trade_no":
			o.RefundChannelTradeNo = v.(string)
		case "refunded_at":
			o.RefundedAt = timeField(v)
		case "stock_restored":
			o.StockRestored = v.(bool)
		case "late_payment_refunded":
			o.LatePaymentRefunded = v.(bool)
		case "shipment_carrier":
			o.ShipmentCarrier = v.(string)
		case "shipment_tracking_no":
			o.ShipmentTrackingNo = v.(string)
		case "shipped_at":
			o.ShippedAt = timeField(v)
		case "shipment_registered_by":
			o.ShipmentRegisteredBy = v.(uint64)
		}
	}
}

func timeField(v interface{}) *time.Time {
	switch t := v.(type) {
	case time.Time:
		c := t
		return &c
	case *time.Time:
		return cloneTimePtr(t)
	default:
		return nil
	}
}

func (m *memoryRepository) ListExpiredPendingOrders(_ context.Context, now time.Time, limit int) ([]model.Order, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	out := make([]model.Order, 0)
	for _, o := range m.orders {
		if o.Status == StatusPendingPayment && !o.ExpiresAt.After(now) {
			out = append(out, *cloneOrder(o))
			if limit > 0 && len(out) >= limit {
				break
			}
		}
	}
	return out, nil
}

func (m *memoryRepository) GetPaymentByDedupKey(_ context.Context, dedupKey string) (*model.Payment, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	for _, p := range m.payments {
		if p.DedupKey != nil && *p.DedupKey == dedupKey {
			return clonePayment(p), nil
		}
	}
	return nil, nil
}

func (m *memoryRepository) GetPaymentByID(_ context.Context, eventID uint64) (*model.Payment, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	for _, p := range m.payments {
		if uint64(p.ID) == eventID {
			return clonePayment(p), nil
		}
	}
	return nil, nil
}

func (m *memoryRepository) HasPaymentEvent(_ context.Context, relatedEventID uint64, eventType string) (bool, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	for _, p := range m.payments {
		if p.RelatedEventID == relatedEventID && p.EventType == eventType {
			return true, nil
		}
	}
	return false, nil
}

func (m *memoryRepository) CreatePayment(_ context.Context, payment *model.Payment) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if payment.DedupKey != nil {
		for _, p := range m.payments {
			if p.DedupKey != nil && *p.DedupKey == *payment.DedupKey {
				return ErrDuplicateDedupKey
			}
		}
	}
	m.nextPaymentID++
	payment.ID = uint(m.nextPaymentID)
	now := time.Now()
	payment.CreatedAt = now
	payment.UpdatedAt = now
	if payment.OccurredAt.IsZero() {
		payment.OccurredAt = now
	}
	m.payments = append(m.payments, clonePayment(payment))
	return nil
}

func (m *memoryRepository) CountOrders(_ context.Context) (int64, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	return int64(len(m.orders)), nil
}

func (m *memoryRepository) CountOrdersByStatus(_ context.Context, status string) (int64, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	var n int64
	for _, o := range m.orders {
		if o.Status == status {
			n++
		}
	}
	return n, nil
}

func (m *memoryRepository) CountPaymentsByEventType(_ context.Context, eventType string) (int64, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	var n int64
	for _, p := range m.payments {
		if p.EventType == eventType {
			n++
		}
	}
	return n, nil
}

func (m *memoryRepository) CountPaymentsByResult(_ context.Context, result string) (int64, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	var n int64
	for _, p := range m.payments {
		if p.Result == result {
			n++
		}
	}
	return n, nil
}

func (m *memoryRepository) SumEffectivePaymentsByEventType(_ context.Context, eventType string) (int64, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	var total int64
	for _, p := range m.payments {
		if p.Effective != nil && *p.Effective && p.EventType == eventType {
			total += p.Amount
		}
	}
	return total, nil
}

// 以下三个方法是「代码产物补齐」批次新增，供 ExtensionService 使用；
// 不改动上面任何既有仓储方法与 OrderRepository 接口。

func (m *memoryRepository) UpdateGoodsPrice(_ context.Context, goodsID uint64, newPrice int64) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	g, ok := m.goods[goodsID]
	if !ok {
		return ErrGoodsNotFound
	}
	g.UnitPrice = newPrice
	return nil
}

func (m *memoryRepository) ListGoods(_ context.Context) ([]model.Goods, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	ids := make([]uint64, 0, len(m.goods))
	for id := range m.goods {
		ids = append(ids, id)
	}
	sort.Slice(ids, func(i, j int) bool { return ids[i] < ids[j] })
	out := make([]model.Goods, 0, len(ids))
	for _, id := range ids {
		out = append(out, *cloneGoods(m.goods[id]))
	}
	return out, nil
}

func (m *memoryRepository) ListPaymentsByOrderNo(_ context.Context, orderNo string) ([]model.Payment, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	out := make([]model.Payment, 0)
	for _, p := range m.payments {
		if p.OrderNo == orderNo {
			out = append(out, *clonePayment(p))
		}
	}
	return out, nil
}
