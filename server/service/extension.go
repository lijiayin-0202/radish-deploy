package service

import (
	"context"
	"errors"
	"fmt"
	"time"

	"shop-trade/server/model"
)

// 本文件是「代码产物补齐」批次新增的扩展能力，只补齐第二轮门禁复核报告列出的三项分支：
// 商品调价入口（原型 V-03 / M-12）、渠道超时通知分支、库存恢复逐单核查（R-A1-07）。
//
// 约束：不改动 order_service.go / types.go / schema.sql / model.go 的下单与退款主业务；
// 新增逻辑不触发关单、不释放库存、不改写订单状态，只做商品维护、只追加审计与只读核查。
// 「缓存恢复」按报告 R-A1-07 的「售前退款库存恢复」口径实现，不引入缓存组件。

var (
	// ErrGoodsNotFound / ErrOrderNotFound 是资源类错误，由 controller 统一转成 PARAM_ERROR。
	ErrGoodsNotFound = errors.New("goods not found")
	ErrOrderNotFound = errors.New("order not found")
	// ErrInvalidPrice 表示调价金额不是正整数分。
	ErrInvalidPrice = errors.New("invalid unit price")
)

const (
	// 新增事件类型只用于只追加审计，不复用 M-01~M-30 失败原因编号，也不扩展状态机。
	EventGoodsPriceChanged = "商品调价"
	EventChannelTimeout    = "渠道超时通知"

	ResultPriceChanged = "商品价格已调整，已有订单金额快照不变"
	ResultTimeoutNoop  = "渠道超时通知已登记，订单状态不变"

	DedupTimeoutPrefix = "TIMEOUT:"
)

// ExtensionRepository 是本批次新增的扩展仓储能力。
// 前四个方法复用既有 OrderRepository 实现，后三个方法由两个仓储各自新增；
// OrderRepository 接口与既有实现方法本身均不改动。
type ExtensionRepository interface {
	LockGoods(context.Context, uint64) (*model.Goods, error)
	GetOrder(context.Context, string) (*model.Order, error)
	GetPaymentByDedupKey(context.Context, string) (*model.Payment, error)
	CreatePayment(context.Context, *model.Payment) error
	UpdateGoodsPrice(context.Context, uint64, int64) error
	ListGoods(context.Context) ([]model.Goods, error)
	ListPaymentsByOrderNo(context.Context, string) ([]model.Payment, error)
}

// ExtensionService 只依赖扩展仓储接口，便于单元测试注入。
type ExtensionService struct {
	repo ExtensionRepository
	now  func() time.Time
}

func NewExtensionService(repo ExtensionRepository, now func() time.Time) *ExtensionService {
	if now == nil {
		now = time.Now
	}
	return &ExtensionService{repo: repo, now: now}
}

// GoodsPriceResult 是运营调价结果，明确已有订单金额快照不受影响。
type GoodsPriceResult struct {
	GoodsID      uint64 `json:"goods_id"`
	GoodsNo      string `json:"goods_no"`
	GoodsName    string `json:"goods_name"`
	OldUnitPrice int64  `json:"old_unit_price"`
	NewUnitPrice int64  `json:"new_unit_price"`
	OperatorID   uint64 `json:"operator_id"`
	Reason       string `json:"reason"`
	Hint         string `json:"hint"`
	Constraint   string `json:"constraint"`
	AuditEventID uint64 `json:"audit_event_id"`
}

// ChannelTimeoutNotice 是可控模拟渠道发出的超时通知。
type ChannelTimeoutNotice struct {
	OrderNo        string `json:"order_no"`
	ChannelTradeNo string `json:"channel_trade_no"`
	Reason         string `json:"reason"`
}

// ChannelTimeoutResult 明确「通知只登记、订单状态不变」。
type ChannelTimeoutResult struct {
	EventID              uint64 `json:"event_id"`
	OrderNo              string `json:"order_no"`
	OrderStatus          string `json:"order_status"`
	ChannelTradeNo       string `json:"channel_trade_no"`
	Duplicate            bool   `json:"duplicate"`
	OrderStatusUnchanged bool   `json:"order_status_unchanged"`
	Notice               string `json:"notice"`
}

// StockCheckResult 是逐单库存恢复核查结果，供 V-04 / V-07 演示查看。
type StockCheckResult struct {
	OrderNo                string `json:"order_no"`
	OrderStatus            string `json:"order_status"`
	RefundKind             string `json:"refund_kind"`
	Quantity               int    `json:"quantity"`
	UnitPriceSnapshot      int64  `json:"unit_price_snapshot"`
	GoodsID                uint64 `json:"goods_id"`
	GoodsNo                string `json:"goods_no"`
	AvailableStock         int    `json:"available_stock"`
	OccupiedStock          int    `json:"occupied_stock"`
	StockRestoredFlag      bool   `json:"stock_restored_flag"`
	ExpectedRestoreTimes   int    `json:"expected_restore_times"`
	ActualRestoreTimes     int    `json:"actual_restore_times"`
	DuplicateRestoreEvents int    `json:"duplicate_restore_events"`
	Consistent             bool   `json:"consistent"`
	Conclusion             string `json:"conclusion"`
}

func (s *ExtensionService) appendAudit(ctx context.Context, p *model.Payment) error {
	p.OccurredAt = s.now()
	return s.repo.CreatePayment(ctx, p)
}

func (s *ExtensionService) requireRole(ctx context.Context, actor Actor, operation, orderNo string, allowed ...string) error {
	if actor.UserID != 0 && contains(allowed, actor.Role) {
		return nil
	}
	// 越权同样留只追加审计；审计写入失败不改变「必须拒绝」的结论。
	_ = s.appendAudit(ctx, &model.Payment{
		OrderNo:        orderNo,
		ChannelTradeNo: "EVENT:权限拒绝",
		EventType:      EventPermissionDenied,
		Result:         ResultRejected,
		FailureCode:    "M-20",
		FailureReason:  fmt.Sprintf("%s（操作：%s）", messages["M-20"], operation),
		SignatureValid: false,
		OperatorID:     actor.UserID,
	})
	return fail("M-20")
}

// UpdateGoodsPrice 仅允许运营调价；订单保存下单时金额快照，因此调价天然不影响既有订单。
// 同时写入只追加审计，并回传 M-12 / M-13 约束提示，不提供改写订单状态的入口。
func (s *ExtensionService) UpdateGoodsPrice(ctx context.Context, actor Actor, goodsID uint64, newPrice int64, reason string) (*GoodsPriceResult, error) {
	if err := s.requireRole(ctx, actor, "商品调价", "", RoleOps); err != nil {
		return nil, err
	}
	if newPrice <= 0 {
		return nil, ErrInvalidPrice
	}
	goods, err := s.repo.LockGoods(ctx, goodsID)
	if err != nil {
		return nil, err
	}
	if goods == nil {
		return nil, ErrGoodsNotFound
	}
	oldPrice := goods.UnitPrice
	if err := s.repo.UpdateGoodsPrice(ctx, goodsID, newPrice); err != nil {
		return nil, err
	}
	audit := &model.Payment{
		ChannelTradeNo: "EVENT:商品调价",
		EventType:      EventGoodsPriceChanged,
		Result:         ResultPriceChanged,
		Amount:         newPrice,
		SignatureValid: true,
		FailureReason:  reason,
		OperatorID:     actor.UserID,
	}
	if err := s.appendAudit(ctx, audit); err != nil {
		return nil, err
	}
	return &GoodsPriceResult{
		GoodsID:      goodsID,
		GoodsNo:      goods.GoodsNo,
		GoodsName:    goods.Name,
		OldUnitPrice: oldPrice,
		NewUnitPrice: newPrice,
		OperatorID:   actor.UserID,
		Reason:       reason,
		Hint:         messages["M-12"],
		Constraint:   messages["M-13"],
		AuditEventID: uint64(audit.ID),
	}, nil
}

// HandleChannelTimeout 补齐可控模拟渠道的「超时通知」分支。
// 关键口径：超时通知只登记只追加审计、不改订单状态、不关单、不释放库存；
// 10 分钟超时关单仍由服务端时间经 API-05 触发。重复通知按幂等成功处理。
func (s *ExtensionService) HandleChannelTimeout(ctx context.Context, actor Actor, notice ChannelTimeoutNotice) (*ChannelTimeoutResult, error) {
	if err := s.requireRole(ctx, actor, "渠道超时通知", notice.OrderNo, RoleMockChannel, RoleOps); err != nil {
		return nil, err
	}
	dedupKey := DedupTimeoutPrefix + notice.ChannelTradeNo
	result := &ChannelTimeoutResult{
		OrderNo:              notice.OrderNo,
		ChannelTradeNo:       notice.ChannelTradeNo,
		OrderStatusUnchanged: true,
	}
	if existing, err := s.repo.GetPaymentByDedupKey(ctx, dedupKey); err != nil {
		return nil, err
	} else if existing != nil {
		order, err := s.repo.GetOrder(ctx, notice.OrderNo)
		if err != nil {
			return nil, err
		}
		if order != nil {
			result.OrderStatus = order.Status
		}
		result.EventID = uint64(existing.ID)
		result.Duplicate = true
		result.Notice = "重复渠道超时通知已幂等处理，未产生第二笔业务结果；订单状态不变"
		return result, nil
	}
	order, err := s.repo.GetOrder(ctx, notice.OrderNo)
	if err != nil {
		return nil, err
	}
	if order == nil {
		return nil, fail("M-30")
	}
	audit := &model.Payment{
		OrderID:             uint64(order.ID),
		OrderNo:             notice.OrderNo,
		ChannelTradeNo:      notice.ChannelTradeNo,
		DedupKey:            stringPtr(dedupKey),
		EventType:           EventChannelTimeout,
		Result:              ResultTimeoutNoop,
		FailureReason:       notice.Reason,
		OrderStatusSnapshot: order.Status,
		SignatureValid:      true,
		OperatorID:          actor.UserID,
	}
	if err := s.appendAudit(ctx, audit); err != nil {
		if !errors.Is(err, ErrDuplicateDedupKey) {
			return nil, err
		}
		// 并发重复通知：唯一键兜底生效，按幂等成功处理。
		result.Duplicate = true
		result.OrderStatus = order.Status
		result.Notice = "并发重复渠道超时通知已幂等处理，未产生第二笔业务结果；订单状态不变"
		return result, nil
	}
	result.EventID = uint64(audit.ID)
	result.OrderStatus = order.Status
	result.Notice = "渠道超时通知已登记为只追加审计；订单状态不变，超时关单仍由服务端 10 分钟规则触发"
	return result, nil
}

// VerifyStockRestoration 按订单号逐单核对退款库存恢复次数与商品可售/占用数量。
// 只读，不修改任何订单或库存；结论引用既有 M-17 / M-26 文案，不新增失败原因编号。
func (s *ExtensionService) VerifyStockRestoration(ctx context.Context, actor Actor, orderNo string) (*StockCheckResult, error) {
	if err := s.requireRole(ctx, actor, "库存恢复逐单核查", orderNo, RoleOps, RoleCustomerService); err != nil {
		return nil, err
	}
	order, err := s.repo.GetOrder(ctx, orderNo)
	if err != nil {
		return nil, err
	}
	if order == nil {
		return nil, ErrOrderNotFound
	}
	payments, err := s.repo.ListPaymentsByOrderNo(ctx, orderNo)
	if err != nil {
		return nil, err
	}
	actual := 0
	for _, p := range payments {
		if p.EventType == EventStockRestore {
			actual++
		}
	}
	goods, err := s.repo.LockGoods(ctx, order.GoodsID)
	if err != nil {
		return nil, err
	}
	if goods == nil {
		return nil, ErrGoodsNotFound
	}
	expected := 0
	if order.RefundKind == RefundKindPresale && order.Status == StatusRefunded {
		expected = 1
	}
	duplicate := actual - expected
	if duplicate < 0 {
		duplicate = 0
	}
	conclusion := messages["M-17"]
	if actual != expected {
		if expected == 0 {
			conclusion = messages["M-26"]
		} else {
			conclusion = "库存恢复事件数与订单终态不符，需核查退款流程"
		}
	}
	return &StockCheckResult{
		OrderNo:                order.OrderNo,
		OrderStatus:            order.Status,
		RefundKind:             order.RefundKind,
		Quantity:               order.Quantity,
		UnitPriceSnapshot:      order.UnitPrice,
		GoodsID:                order.GoodsID,
		GoodsNo:                goods.GoodsNo,
		AvailableStock:         goods.AvailableStock,
		OccupiedStock:          goods.OccupiedStock,
		StockRestoredFlag:      order.StockRestored,
		ExpectedRestoreTimes:   expected,
		ActualRestoreTimes:     actual,
		DuplicateRestoreEvents: duplicate,
		Consistent:             actual == expected,
		Conclusion:             conclusion,
	}, nil
}
