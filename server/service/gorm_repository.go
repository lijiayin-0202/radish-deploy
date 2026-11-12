package service

import (
	"context"
	"errors"
	"strings"
	"time"

	"shop-trade/server/model"

	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

// GormOrderRepository 是生产仓储。所有写操作由调用方包在 MySQL(InnoDB) 事务中。
type GormOrderRepository struct {
	db *gorm.DB
}

func NewGormOrderRepository(db *gorm.DB) OrderRepository {
	return &GormOrderRepository{db: db}
}

func notFoundAsNil(err error) error {
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil
	}
	return err
}

// WithTransaction 对已处理业务拒绝提交同一事务内的审计记录，对技术错误回滚。
func (r *GormOrderRepository) WithTransaction(ctx context.Context, fn func(OrderRepository) error) error {
	var txErr error
	err := r.db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		txErr = fn(&GormOrderRepository{db: tx})
		if txErr == nil {
			return nil
		}
		var bizErr *BizError
		if errors.As(txErr, &bizErr) && bizErr.Commit {
			return nil
		}
		return txErr
	})
	if err != nil {
		return err
	}
	return txErr
}

// LockGoods：MySQL InnoDB 行锁。goods.id 为主键，命中聚簇索引；
// 若改为未命中索引的条件，锁范围可能扩大甚至升级为表锁，引发超卖风险。
func (r *GormOrderRepository) LockGoods(ctx context.Context, goodsID uint64) (*model.Goods, error) {
	var goods model.Goods
	err := r.db.WithContext(ctx).
		Clauses(clause.Locking{Strength: "UPDATE"}).
		Where("id = ? AND deleted_at IS NULL", goodsID).
		First(&goods).Error
	if err != nil {
		if err := notFoundAsNil(err); err != nil {
			return nil, err
		}
		return nil, nil
	}
	return &goods, nil
}

// DecreaseGoodsStock：条件更新命中 goods.id 主键与 status 索引，依赖 InnoDB 行锁防超卖。
func (r *GormOrderRepository) DecreaseGoodsStock(ctx context.Context, goodsID uint64, quantity int) (bool, error) {
	res := r.db.WithContext(ctx).Model(&model.Goods{}).
		Where("id = ? AND status = ? AND available_stock >= ? AND deleted_at IS NULL", goodsID, GoodsStatusOnSale, quantity).
		Updates(map[string]interface{}{
			"available_stock": gorm.Expr("available_stock - ?", quantity),
			"occupied_stock":  gorm.Expr("occupied_stock + ?", quantity),
		})
	if res.Error != nil {
		return false, res.Error
	}
	return res.RowsAffected == 1, nil
}

// IncreaseGoodsStock：释放/恢复库存同样命中 goods.id 主键，避免表锁风险。
func (r *GormOrderRepository) IncreaseGoodsStock(ctx context.Context, goodsID uint64, quantity int) (bool, error) {
	res := r.db.WithContext(ctx).Model(&model.Goods{}).
		Where("id = ? AND occupied_stock >= ? AND deleted_at IS NULL", goodsID, quantity).
		Updates(map[string]interface{}{
			"available_stock": gorm.Expr("available_stock + ?", quantity),
			"occupied_stock":  gorm.Expr("occupied_stock - ?", quantity),
		})
	if res.Error != nil {
		return false, res.Error
	}
	return res.RowsAffected == 1, nil
}

// LockOrder：订单状态串行化依赖 order.id 主键行锁；首个提交者生效，后到者按当前状态拒绝。
func (r *GormOrderRepository) LockOrder(ctx context.Context, orderNo string) (*model.Order, error) {
	var order model.Order
	err := r.db.WithContext(ctx).
		Clauses(clause.Locking{Strength: "UPDATE"}).
		Where("order_no = ? AND deleted_at IS NULL", orderNo).
		First(&order).Error
	if err != nil {
		if err := notFoundAsNil(err); err != nil {
			return nil, err
		}
		return nil, nil
	}
	return &order, nil
}

// LockOrderByID：按主键加行锁读取订单（SELECT ... FOR UPDATE），用于事务内的并发裁决。
func (r *GormOrderRepository) LockOrderByID(ctx context.Context, orderID uint64) (*model.Order, error) {
	var order model.Order
	err := r.db.WithContext(ctx).
		Clauses(clause.Locking{Strength: "UPDATE"}).
		Where("id = ? AND deleted_at IS NULL", orderID).
		First(&order).Error
	if err != nil {
		if err := notFoundAsNil(err); err != nil {
			return nil, err
		}
		return nil, nil
	}
	return &order, nil
}

// GetOrder：按订单号读取订单（不加锁），用于只读查询场景。
func (r *GormOrderRepository) GetOrder(ctx context.Context, orderNo string) (*model.Order, error) {
	var order model.Order
	err := r.db.WithContext(ctx).Where("order_no = ? AND deleted_at IS NULL", orderNo).First(&order).Error
	if err != nil {
		if err := notFoundAsNil(err); err != nil {
			return nil, err
		}
		return nil, nil
	}
	return &order, nil
}

// CreateOrder：写入订单行；order_no 唯一约束兜底，防止同一订单号重复落库。
func (r *GormOrderRepository) CreateOrder(ctx context.Context, order *model.Order) error {
	return r.db.WithContext(ctx).Create(order).Error
}

// UpdateOrderIfStatus：按「主键 + 期望原状态」条件更新订单；受影响行数为 0 表示状态已被并发变更，调用方须拒绝本次操作。
func (r *GormOrderRepository) UpdateOrderIfStatus(ctx context.Context, order *model.Order, allowed []string, fields map[string]interface{}) (int64, error) {
	res := r.db.WithContext(ctx).Model(&model.Order{}).
		Where("id = ? AND status IN ? AND deleted_at IS NULL", order.ID, allowed).
		Updates(fields)
	return res.RowsAffected, res.Error
}

// UpdateOrderIfStatusAndStockNotRestored：退款成功并发时以 stock_restored = 0 作为额外条件，
// 保证正常售前退款只恢复一次库存；条件命中 order.id 主键与 idx_order_status。
func (r *GormOrderRepository) UpdateOrderIfStatusAndStockNotRestored(ctx context.Context, order *model.Order, allowed []string, fields map[string]interface{}) (int64, error) {
	res := r.db.WithContext(ctx).Model(&model.Order{}).
		Where("id = ? AND status IN ? AND stock_restored = 0 AND deleted_at IS NULL", order.ID, allowed).
		Updates(fields)
	return res.RowsAffected, res.Error
}

// ListExpiredPendingOrders：依赖 idx_order_status_expires(status, expires_at)；
// 返回的订单仍需逐笔在事务内重新加行锁，避免列表快照与并发提交不一致。
func (r *GormOrderRepository) ListExpiredPendingOrders(ctx context.Context, now time.Time, limit int) ([]model.Order, error) {
	var orders []model.Order
	err := r.db.WithContext(ctx).
		Where("status = ? AND expires_at <= ? AND deleted_at IS NULL", StatusPendingPayment, now).
		Limit(limit).
		Find(&orders).Error
	return orders, err
}

// GetPaymentByDedupKey：按幂等键读取支付/退款事件，用于重复通知与重复回调的幂等判定。
func (r *GormOrderRepository) GetPaymentByDedupKey(ctx context.Context, dedupKey string) (*model.Payment, error) {
	var payment model.Payment
	err := r.db.WithContext(ctx).
		Where("dedup_key = ? AND deleted_at IS NULL", dedupKey).
		First(&payment).Error
	if err != nil {
		if err := notFoundAsNil(err); err != nil {
			return nil, err
		}
		return nil, nil
	}
	return &payment, nil
}

// GetPaymentByID：按主键读取支付/退款/迟到支付异常事件。
func (r *GormOrderRepository) GetPaymentByID(ctx context.Context, eventID uint64) (*model.Payment, error) {
	var payment model.Payment
	err := r.db.WithContext(ctx).
		Where("id = ? AND deleted_at IS NULL", eventID).
		First(&payment).Error
	if err != nil {
		if err := notFoundAsNil(err); err != nil {
			return nil, err
		}
		return nil, nil
	}
	return &payment, nil
}

// HasPaymentEvent：判断指定关联事件是否已存在同类记录，用于只追加流水的重复拦截。
func (r *GormOrderRepository) HasPaymentEvent(ctx context.Context, relatedEventID uint64, eventType string) (bool, error) {
	var count int64
	err := r.db.WithContext(ctx).Model(&model.Payment{}).
		Where("related_event_id = ? AND event_type = ? AND deleted_at IS NULL", relatedEventID, eventType).
		Count(&count).Error
	return count > 0, err
}

// CreatePayment 只追加，不提供更新/删除入口。唯一键冲突映射为 ErrDuplicateDedupKey 以触发事务回滚。
func (r *GormOrderRepository) CreatePayment(ctx context.Context, payment *model.Payment) error {
	err := r.db.WithContext(ctx).Create(payment).Error
	if err == nil {
		return nil
	}
	if strings.Contains(strings.ToLower(err.Error()), "duplicate") {
		return ErrDuplicateDedupKey
	}
	return err
}

// CountOrders：统计订单总数，供运营核查汇总使用。
func (r *GormOrderRepository) CountOrders(ctx context.Context) (int64, error) {
	var count int64
	err := r.db.WithContext(ctx).Model(&model.Order{}).Where("deleted_at IS NULL").Count(&count).Error
	return count, err
}

// CountOrdersByStatus：按订单状态统计数量，供运营核查汇总使用。
func (r *GormOrderRepository) CountOrdersByStatus(ctx context.Context, status string) (int64, error) {
	var count int64
	err := r.db.WithContext(ctx).Model(&model.Order{}).
		Where("status = ? AND deleted_at IS NULL", status).
		Count(&count).Error
	return count, err
}

// CountPaymentsByEventType：按事件类型统计审计流水条数，供运营核查汇总使用。
func (r *GormOrderRepository) CountPaymentsByEventType(ctx context.Context, eventType string) (int64, error) {
	var count int64
	err := r.db.WithContext(ctx).Model(&model.Payment{}).
		Where("event_type = ? AND deleted_at IS NULL", eventType).
		Count(&count).Error
	return count, err
}

// CountPaymentsByResult：按处理结果统计审计流水条数，供运营核查汇总使用。
func (r *GormOrderRepository) CountPaymentsByResult(ctx context.Context, result string) (int64, error) {
	var count int64
	err := r.db.WithContext(ctx).Model(&model.Payment{}).
		Where("result = ? AND deleted_at IS NULL", result).
		Count(&count).Error
	return count, err
}

// SumEffectivePaymentsByEventType：按事件类型累加有效金额（单位分），仅统计 effective=1 的有效业务结果。
func (r *GormOrderRepository) SumEffectivePaymentsByEventType(ctx context.Context, eventType string) (int64, error) {
	var total int64
	err := r.db.WithContext(ctx).Model(&model.Payment{}).
		Select("COALESCE(SUM(amount), 0)").
		Where("event_type = ? AND effective IS NOT NULL AND deleted_at IS NULL", eventType).
		Scan(&total).Error
	return total, err
}

// 以下三个方法是「代码产物补齐」批次新增，供 ExtensionService 使用；
// 不改动上面任何既有仓储方法与 OrderRepository 接口。

// UpdateGoodsPrice 只更新商品单价，条件命中主键索引，不触碰订单金额快照。
func (r *GormOrderRepository) UpdateGoodsPrice(ctx context.Context, goodsID uint64, newPrice int64) error {
	return r.db.WithContext(ctx).Model(&model.Goods{}).
		Where("id = ? AND deleted_at IS NULL", goodsID).
		UpdateColumn("unit_price", newPrice).Error
}

// ListGoods 读商品列表，使调价结果能被 API-18 与 V-01 / V-03 页面立即看到。
func (r *GormOrderRepository) ListGoods(ctx context.Context) ([]model.Goods, error) {
	var goods []model.Goods
	err := r.db.WithContext(ctx).Where("deleted_at IS NULL").Order("id ASC").Find(&goods).Error
	return goods, err
}

// ListPaymentsByOrderNo 读同一订单的只追加审计流水，用于逐单统计库存恢复次数。
func (r *GormOrderRepository) ListPaymentsByOrderNo(ctx context.Context, orderNo string) ([]model.Payment, error) {
	var payments []model.Payment
	err := r.db.WithContext(ctx).
		Where("order_no = ? AND deleted_at IS NULL", orderNo).
		Order("id ASC").Find(&payments).Error
	return payments, err
}
