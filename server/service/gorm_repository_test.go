package service

// 竞态检测说明：go test ./... -race 需要 CGO_ENABLED=1 与可用 C 编译器（gcc/clang）。
// PowerShell：$env:CGO_ENABLED = "1"; go test ./... -race -count=1
// bash：CGO_ENABLED=1 go test ./... -race -count=1

import (
	"errors"
	"strings"
	"testing"
	"time"

	"github.com/DATA-DOG/go-sqlmock"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"

	"shop-trade/server/global"
	"shop-trade/server/model"
)

// 本文件是开发会话内的单元测试草案：用 sqlmock 覆盖自编 GORM 数据访问代码，
// 不排除自编数据库访问代码，也不替代测试 Agent 在真实 MySQL(InnoDB) 上执行的第 1 轮门禁。
type mockEnv struct {
	repo   *GormOrderRepository
	db     *gorm.DB
	mock   sqlmock.Sqlmock
	raw    interface{ Close() error }
	sqlLog []string
}

func (e *mockEnv) sqlText() string { return strings.Join(e.sqlLog, "\n") }

func (e *mockEnv) close(t *testing.T) {
	t.Helper()
	if err := e.mock.ExpectationsWereMet(); err != nil {
		t.Fatalf("unmet sqlmock expectations: %v", err)
	}
	_ = e.raw.Close()
}

func newMockEnv(t *testing.T) *mockEnv {
	t.Helper()
	e := &mockEnv{}
	matcher := sqlmock.QueryMatcherFunc(func(expectedSQL, actualSQL string) error {
		e.sqlLog = append(e.sqlLog, actualSQL)
		return nil
	})
	rawDB, mock, err := sqlmock.New(sqlmock.QueryMatcherOption(matcher))
	if err != nil {
		t.Fatal(err)
	}
	e.mock = mock
	e.raw = rawDB
	gormDB, err := gorm.Open(
		mysql.New(mysql.Config{Conn: rawDB, SkipInitializeWithVersion: true}),
		&gorm.Config{Logger: logger.Default.LogMode(logger.Silent), SkipDefaultTransaction: true},
	)
	if err != nil {
		t.Fatal(err)
	}
	e.db = gormDB
	e.repo = NewGormOrderRepository(gormDB).(*GormOrderRepository)
	return e
}

func goodsRows() *sqlmock.Rows {
	return sqlmock.NewRows([]string{"id", "goods_no", "name", "unit_price", "available_stock", "occupied_stock", "status"}).
		AddRow(1, "GOODS-ACT-001", "活动商品", 10000, 5, 0, GoodsStatusOnSale)
}

func orderRows() *sqlmock.Rows {
	return sqlmock.NewRows([]string{"id", "order_no", "buyer_id", "goods_id", "quantity", "unit_price", "total_amount", "status", "expires_at", "stock_restored"}).
		AddRow(1, "NO-1", 1001, 1, 2, 10000, 20000, StatusPendingPayment, fixedTime.Add(10*time.Minute), false)
}

func paymentRows() *sqlmock.Rows {
	return sqlmock.NewRows([]string{"id", "order_id", "order_no", "channel_trade_no", "event_type", "result", "amount"}).
		AddRow(7, 1, "NO-1", "PAY-1", EventPaymentSuccess, ResultPaid, 20000)
}

func TestGormRepositoryTransactionAndErrorMapping(t *testing.T) {
	if err := notFoundAsNil(gorm.ErrRecordNotFound); err != nil {
		t.Fatalf("record-not-found should become nil, got %v", err)
	}
	tech := errors.New("db down")
	if err := notFoundAsNil(tech); !errors.Is(err, tech) {
		t.Fatalf("technical error should be preserved, got %v", err)
	}

	e := newMockEnv(t)
	defer e.close(t)

	e.mock.ExpectBegin()
	e.mock.ExpectCommit()
	if err := e.repo.WithTransaction(ctx, func(OrderRepository) error { return nil }); err != nil {
		t.Fatalf("empty transaction failed: %v", err)
	}

	biz := fail("M-10")
	e.mock.ExpectBegin()
	e.mock.ExpectCommit()
	err := e.repo.WithTransaction(ctx, func(OrderRepository) error { return biz })
	if !errors.Is(err, biz) {
		t.Fatalf("business rejection should commit audit and return BizError, got %v", err)
	}

	e.mock.ExpectBegin()
	e.mock.ExpectRollback()
	err = e.repo.WithTransaction(ctx, func(OrderRepository) error { return tech })
	if !errors.Is(err, tech) {
		t.Fatalf("technical error should rollback, got %v", err)
	}

	old := global.GVA_DB
	global.GVA_DB = e.db
	defer func() { global.GVA_DB = old }()
	if svc := NewDefaultOrderService(); svc == nil || svc.repo == nil {
		t.Fatal("default service constructor must bind GVA_DB")
	}
}

func TestGormRepositoryRowLockAndStockUpdates(t *testing.T) {
	e := newMockEnv(t)
	defer e.close(t)

	e.mock.ExpectQuery(".*").WillReturnRows(goodsRows())
	g, err := e.repo.LockGoods(ctx, 1)
	if err != nil || g == nil || g.AvailableStock != 5 {
		t.Fatalf("LockGoods failed: g=%+v err=%v", g, err)
	}
	if !strings.Contains(e.sqlText(), "FOR UPDATE") {
		t.Fatal("goods row lock must use SELECT ... FOR UPDATE")
	}

	e.mock.ExpectQuery(".*").WillReturnError(gorm.ErrRecordNotFound)
	g, err = e.repo.LockGoods(ctx, 99)
	if err != nil || g != nil {
		t.Fatalf("missing goods should be (nil, nil), got %v %v", g, err)
	}
	e.mock.ExpectQuery(".*").WillReturnError(errors.New("lock failed"))
	if _, err = e.repo.LockGoods(ctx, 1); err == nil {
		t.Fatal("lock error must be propagated")
	}

	e.mock.ExpectExec(".*").WillReturnResult(sqlmock.NewResult(0, 1))
	ok, err := e.repo.DecreaseGoodsStock(ctx, 1, 2)
	if err != nil || !ok {
		t.Fatalf("decrease stock failed: ok=%v err=%v", ok, err)
	}
	e.mock.ExpectExec(".*").WillReturnResult(sqlmock.NewResult(0, 0))
	ok, err = e.repo.DecreaseGoodsStock(ctx, 1, 99)
	if err != nil || ok {
		t.Fatalf("oversell condition update must affect 0 rows: ok=%v err=%v", ok, err)
	}
	if !strings.Contains(e.sqlText(), "available_stock >= ?") {
		t.Fatal("decrease must use atomic available_stock >= quantity condition")
	}
	e.mock.ExpectExec(".*").WillReturnError(errors.New("update failed"))
	if _, err = e.repo.DecreaseGoodsStock(ctx, 1, 1); err == nil {
		t.Fatal("decrease error must be propagated")
	}

	e.mock.ExpectExec(".*").WillReturnResult(sqlmock.NewResult(0, 1))
	ok, err = e.repo.IncreaseGoodsStock(ctx, 1, 2)
	if err != nil || !ok {
		t.Fatalf("increase stock failed: ok=%v err=%v", ok, err)
	}
	e.mock.ExpectExec(".*").WillReturnResult(sqlmock.NewResult(0, 0))
	ok, err = e.repo.IncreaseGoodsStock(ctx, 1, 99)
	if err != nil || ok {
		t.Fatalf("over-release must affect 0 rows: ok=%v err=%v", ok, err)
	}
	if !strings.Contains(e.sqlText(), "occupied_stock >= ?") {
		t.Fatal("increase must use occupied_stock >= quantity condition")
	}
	e.mock.ExpectExec(".*").WillReturnError(errors.New("release failed"))
	if _, err = e.repo.IncreaseGoodsStock(ctx, 1, 1); err == nil {
		t.Fatal("increase error must be propagated")
	}
}

func TestGormRepositoryOrderQueriesAndConditionalUpdates(t *testing.T) {
	e := newMockEnv(t)
	defer e.close(t)

	for _, query := range []func() (*model.Order, error){
		func() (*model.Order, error) { return e.repo.LockOrder(ctx, "NO-1") },
		func() (*model.Order, error) { return e.repo.LockOrderByID(ctx, 1) },
		func() (*model.Order, error) { return e.repo.GetOrder(ctx, "NO-1") },
	} {
		e.mock.ExpectQuery(".*").WillReturnRows(orderRows())
		o, err := query()
		if err != nil || o == nil || o.OrderNo != "NO-1" {
			t.Fatalf("order query failed: o=%+v err=%v", o, err)
		}
	}
	if !strings.Contains(e.sqlText(), "FOR UPDATE") {
		t.Fatal("order state transitions must lock the order row")
	}

	for _, query := range []func() (*model.Order, error){
		func() (*model.Order, error) { return e.repo.LockOrder(ctx, "MISSING") },
		func() (*model.Order, error) { return e.repo.LockOrderByID(ctx, 999) },
		func() (*model.Order, error) { return e.repo.GetOrder(ctx, "MISSING") },
	} {
		e.mock.ExpectQuery(".*").WillReturnError(gorm.ErrRecordNotFound)
		o, err := query()
		if err != nil || o != nil {
			t.Fatalf("missing order should be (nil, nil), got %v %v", o, err)
		}
	}
	e.mock.ExpectQuery(".*").WillReturnError(errors.New("query failed"))
	if _, err := e.repo.GetOrder(ctx, "NO-1"); err == nil {
		t.Fatal("order query error must be propagated")
	}

	e.mock.ExpectQuery(".*").WillReturnRows(orderRows())
	orders, err := e.repo.ListExpiredPendingOrders(ctx, fixedTime.Add(11*time.Minute), 10)
	if err != nil || len(orders) != 1 {
		t.Fatalf("expired list failed: orders=%v err=%v", orders, err)
	}
	e.mock.ExpectQuery(".*").WillReturnError(errors.New("list failed"))
	if _, err = e.repo.ListExpiredPendingOrders(ctx, fixedTime, 10); err == nil {
		t.Fatal("expired list error must be propagated")
	}

	fields := map[string]interface{}{"status": StatusWaitingShipment}
	e.mock.ExpectExec(".*").WillReturnResult(sqlmock.NewResult(0, 1))
	rows, err := e.repo.UpdateOrderIfStatus(ctx, &model.Order{GVA_MODEL: global.GVA_MODEL{}}, []string{StatusPendingPayment}, fields)
	if err != nil || rows != 1 {
		t.Fatalf("conditional update failed: rows=%d err=%v", rows, err)
	}
	e.mock.ExpectExec(".*").WillReturnError(errors.New("update failed"))
	if _, err = e.repo.UpdateOrderIfStatus(ctx, &model.Order{}, []string{StatusPendingPayment}, fields); err == nil {
		t.Fatal("conditional update error must be propagated")
	}
	e.mock.ExpectExec(".*").WillReturnResult(sqlmock.NewResult(0, 1))
	rows, err = e.repo.UpdateOrderIfStatusAndStockNotRestored(ctx, &model.Order{}, []string{StatusRefundProcessing}, fields)
	if err != nil || rows != 1 {
		t.Fatalf("stock-restored guarded update failed: rows=%d err=%v", rows, err)
	}
	if !strings.Contains(e.sqlText(), "stock_restored = 0") {
		t.Fatal("refund success must be guarded by stock_restored = 0")
	}
	e.mock.ExpectExec(".*").WillReturnError(errors.New("update failed"))
	if _, err = e.repo.UpdateOrderIfStatusAndStockNotRestored(ctx, &model.Order{}, []string{StatusRefundProcessing}, fields); err == nil {
		t.Fatal("guarded update error must be propagated")
	}

	e.mock.ExpectExec(".*").WillReturnResult(sqlmock.NewResult(1, 1))
	if err := e.repo.CreateOrder(ctx, &model.Order{OrderNo: "NO-2"}); err != nil {
		t.Fatalf("CreateOrder failed: %v", err)
	}
	e.mock.ExpectExec(".*").WillReturnError(errors.New("insert failed"))
	if err := e.repo.CreateOrder(ctx, &model.Order{OrderNo: "NO-3"}); err == nil {
		t.Fatal("CreateOrder error must be propagated")
	}
}

func TestGormRepositoryAppendOnlyPayments(t *testing.T) {
	e := newMockEnv(t)
	defer e.close(t)

	for _, query := range []func() (*model.Payment, error){
		func() (*model.Payment, error) { return e.repo.GetPaymentByDedupKey(ctx, "PAY:NO-1") },
		func() (*model.Payment, error) { return e.repo.GetPaymentByID(ctx, 7) },
	} {
		e.mock.ExpectQuery(".*").WillReturnRows(paymentRows())
		p, err := query()
		if err != nil || p == nil || p.ChannelTradeNo != "PAY-1" {
			t.Fatalf("payment query failed: p=%+v err=%v", p, err)
		}
	}
	for _, query := range []func() (*model.Payment, error){
		func() (*model.Payment, error) { return e.repo.GetPaymentByDedupKey(ctx, "MISSING") },
		func() (*model.Payment, error) { return e.repo.GetPaymentByID(ctx, 999) },
	} {
		e.mock.ExpectQuery(".*").WillReturnError(gorm.ErrRecordNotFound)
		p, err := query()
		if err != nil || p != nil {
			t.Fatalf("missing payment should be (nil, nil), got %v %v", p, err)
		}
	}
	e.mock.ExpectQuery(".*").WillReturnError(errors.New("query failed"))
	if _, err := e.repo.GetPaymentByID(ctx, 7); err == nil {
		t.Fatal("payment query error must be propagated")
	}
	e.mock.ExpectQuery(".*").WillReturnError(errors.New("query failed"))
	if _, err := e.repo.GetPaymentByDedupKey(ctx, "PAY:NO-1"); err == nil {
		t.Fatal("dedup query error must be propagated")
	}

	e.mock.ExpectQuery(".*").WillReturnRows(sqlmock.NewRows([]string{"count(*)"}).AddRow(1))
	yes, err := e.repo.HasPaymentEvent(ctx, 7, EventLatePaymentVerified)
	if err != nil || !yes {
		t.Fatalf("HasPaymentEvent should be true: %v %v", yes, err)
	}
	e.mock.ExpectQuery(".*").WillReturnRows(sqlmock.NewRows([]string{"count(*)"}).AddRow(0))
	yes, err = e.repo.HasPaymentEvent(ctx, 7, EventLatePaymentVerified)
	if err != nil || yes {
		t.Fatalf("HasPaymentEvent should be false: %v %v", yes, err)
	}
	e.mock.ExpectQuery(".*").WillReturnError(errors.New("count failed"))
	if _, err = e.repo.HasPaymentEvent(ctx, 7, EventLatePaymentVerified); err == nil {
		t.Fatal("HasPaymentEvent error must be propagated")
	}

	e.mock.ExpectExec(".*").WillReturnResult(sqlmock.NewResult(1, 1))
	if err := e.repo.CreatePayment(ctx, &model.Payment{OrderNo: "NO-1"}); err != nil {
		t.Fatalf("CreatePayment failed: %v", err)
	}
	e.mock.ExpectExec(".*").WillReturnError(errors.New("Error 1062: Duplicate entry for key uk_payment_dedup_key"))
	if err := e.repo.CreatePayment(ctx, &model.Payment{OrderNo: "NO-1"}); !errors.Is(err, ErrDuplicateDedupKey) {
		t.Fatalf("duplicate key must map to ErrDuplicateDedupKey, got %v", err)
	}
	e.mock.ExpectExec(".*").WillReturnError(errors.New("insert failed"))
	if err := e.repo.CreatePayment(ctx, &model.Payment{OrderNo: "NO-1"}); err == nil {
		t.Fatal("CreatePayment error must be propagated")
	}
	if strings.Contains(strings.ToUpper(e.sqlText()), " UPDATE ") || strings.Contains(strings.ToUpper(e.sqlText()), " DELETE ") {
		t.Fatal("payment repository must be append-only")
	}
}

func TestGormRepositoryOpsSummaryQueries(t *testing.T) {
	e := newMockEnv(t)
	defer e.close(t)

	e.mock.ExpectQuery(".*").WillReturnRows(sqlmock.NewRows([]string{"count(*)"}).AddRow(3))
	n, err := e.repo.CountOrders(ctx)
	if err != nil || n != 3 {
		t.Fatalf("CountOrders failed: %d %v", n, err)
	}
	e.mock.ExpectQuery(".*").WillReturnRows(sqlmock.NewRows([]string{"count(*)"}).AddRow(2))
	n, err = e.repo.CountOrdersByStatus(ctx, StatusWaitingShipment)
	if err != nil || n != 2 {
		t.Fatalf("CountOrdersByStatus failed: %d %v", n, err)
	}
	e.mock.ExpectQuery(".*").WillReturnRows(sqlmock.NewRows([]string{"count(*)"}).AddRow(1))
	n, err = e.repo.CountPaymentsByEventType(ctx, EventPaymentSuccess)
	if err != nil || n != 1 {
		t.Fatalf("CountPaymentsByEventType failed: %d %v", n, err)
	}
	e.mock.ExpectQuery(".*").WillReturnRows(sqlmock.NewRows([]string{"count(*)"}).AddRow(4))
	n, err = e.repo.CountPaymentsByResult(ctx, ResultPaid)
	if err != nil || n != 4 {
		t.Fatalf("CountPaymentsByResult failed: %d %v", n, err)
	}
	e.mock.ExpectQuery(".*").WillReturnRows(sqlmock.NewRows([]string{"total"}).AddRow(20000))
	total, err := e.repo.SumEffectivePaymentsByEventType(ctx, EventPaymentSuccess)
	if err != nil || total != 20000 {
		t.Fatalf("SumEffectivePaymentsByEventType failed: %d %v", total, err)
	}
	if !strings.Contains(e.sqlText(), "effective IS NOT NULL") {
		t.Fatal("ops summary must only sum effective business results")
	}
	for _, query := range []func() error{
		func() error { _, err := e.repo.CountOrders(ctx); return err },
		func() error { _, err := e.repo.CountOrdersByStatus(ctx, StatusShipped); return err },
		func() error { _, err := e.repo.CountPaymentsByEventType(ctx, EventRefundSuccess); return err },
		func() error { _, err := e.repo.CountPaymentsByResult(ctx, ResultPaid); return err },
		func() error { _, err := e.repo.SumEffectivePaymentsByEventType(ctx, EventPaymentSuccess); return err },
	} {
		e.mock.ExpectQuery(".*").WillReturnError(errors.New("aggregate failed"))
		if err := query(); err == nil {
			t.Fatal("aggregate error must be propagated")
		}
	}
}

func TestBizErrorHelpers(t *testing.T) {
	bare := &BizError{Code: "M-01"}
	if bare.Error() != "M-01" {
		t.Fatalf("unexpected bare error text: %s", bare.Error())
	}
	detailed := failWithDetail("M-01", "库存不足")
	var bizErr *BizError
	if !errors.As(detailed, &bizErr) || !strings.Contains(bizErr.Error(), "库存不足") {
		t.Fatalf("unexpected detailed error: %v", detailed)
	}
}
