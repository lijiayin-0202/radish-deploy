package v1

// 竞态检测说明：go test ./... -race 需要 CGO_ENABLED=1 与可用 C 编译器。
// PowerShell：$env:CGO_ENABLED = "1"; go test ./... -race -count=1
// bash：CGO_ENABLED=1 go test ./... -race -count=1
// 本文件用 httptest 覆盖 controller 层全部接口的成功与拒绝分支，不改动业务逻辑。

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"

	"shop-trade/server/model"
	"shop-trade/server/service"
)

type testClock struct{ offset int }

func (c *testClock) OffsetMinutes() int     { return c.offset }
func (c *testClock) SetOffsetMinutes(n int) { c.offset = n }
func (c *testClock) Now() time.Time         { return time.Now().Add(time.Duration(c.offset) * time.Minute) }

func newTestEngine(mode string) (*gin.Engine, *testClock) {
	gin.SetMode(gin.TestMode)
	clock := &testClock{}
	svc := service.NewOrderServiceWithClock(service.NewDemoOrderRepository(), clock.Now)
	api := NewOrderApi(svc, func() ([]model.Goods, error) { return service.DemoGoods(), nil }, clock, mode)
	engine := gin.New()
	engine.GET("/health", Health)
	group := engine.Group("/api/v1")
	// 与 server/router/order.go 保持同一路径清单；不在测试中导入 router 以避免包循环。
	group.GET("/me", api.Me)
	group.GET("/goods", api.ListGoods)
	group.GET("/admin/clock", api.GetClock)
	group.POST("/admin/clock", api.SetClock)
	group.POST("/orders", api.CreateOrder)
	group.GET("/orders/:order_no", api.GetOrder)
	group.GET("/orders/:order_no/status", api.GetOrderStatus)
	group.POST("/orders/:order_no/cancel", api.CancelOrder)
	group.POST("/payment/callback", api.HandlePaymentCallback)
	group.POST("/admin/orders/close-expired", api.CloseExpiredOrders)
	group.POST("/orders/:order_no/refund/apply", api.ApplyRefund)
	group.POST("/orders/:order_no/refund/reject", api.RejectRefund)
	group.POST("/orders/:order_no/refund/approve", api.ApproveRefund)
	group.POST("/orders/:order_no/refund/retry", api.RetryRefund)
	group.POST("/refund/callback", api.HandleRefundCallback)
	group.POST("/orders/:order_no/shipment", api.RegisterShipment)
	group.POST("/late-payment/:event_id/verify", api.VerifyLatePayment)
	group.POST("/late-payment/:event_id/refund/initiate", api.InitiateLatePaymentRefund)
	group.POST("/late-payment/refund/callback", api.HandleLatePaymentRefundCallback)
	group.POST("/late-payment/refund/retry", api.RetryLatePaymentRefund)
	group.GET("/ops/summary", api.GetOpsSummary)
	return engine, clock
}

func doRequest(engine *gin.Engine, method, path, account string, body interface{}, extra map[string]string) (int, map[string]interface{}) {
	var req *http.Request
	if body == nil {
		req = httptest.NewRequest(method, path, nil)
	} else {
		raw, _ := json.Marshal(body)
		req = httptest.NewRequest(method, path, bytes.NewReader(raw))
		req.Header.Set("Content-Type", "application/json")
	}
	if account != "" {
		req.Header.Set("X-Demo-Account", account)
	}
	for k, v := range extra {
		req.Header.Set(k, v)
	}
	w := httptest.NewRecorder()
	engine.ServeHTTP(w, req)
	resp := map[string]interface{}{}
	_ = json.Unmarshal(w.Body.Bytes(), &resp)
	return w.Code, resp
}

func codeOf(resp map[string]interface{}) string { return fmt.Sprint(resp["code"]) }

func dataOf(t *testing.T, resp map[string]interface{}) map[string]interface{} {
	t.Helper()
	data, ok := resp["data"].(map[string]interface{})
	if !ok {
		t.Fatalf("响应缺少 data：%v", resp)
	}
	return data
}

func expectCode(t *testing.T, resp map[string]interface{}, want string) {
	t.Helper()
	if got := codeOf(resp); got != want {
		t.Fatalf("期望 code=%s，实际 %s，响应=%v", want, got, resp)
	}
}

func createPaidOrder(t *testing.T, engine *gin.Engine, goodsID uint64, quantity int, amount int64, tradeNo string) string {
	t.Helper()
	status, resp := doRequest(engine, http.MethodPost, "/api/v1/orders", "buyer01",
		map[string]interface{}{"goods_id": goodsID, "quantity": quantity}, nil)
	if status != 200 {
		t.Fatalf("下单 HTTP=%d resp=%v", status, resp)
	}
	expectCode(t, resp, "0")
	orderNo := dataOf(t, resp)["order_no"].(string)
	_, pay := doRequest(engine, http.MethodPost, "/api/v1/payment/callback", "mock01",
		map[string]interface{}{"order_no": orderNo, "channel_trade_no": tradeNo, "amount": amount, "signature_valid": true}, nil)
	expectCode(t, pay, "0")
	return orderNo
}

func TestAPIHealthIdentityGoodsAndValidation(t *testing.T) {
	engine, _ := newTestEngine("demo-memory")
	status, health := doRequest(engine, http.MethodGet, "/health", "", nil, nil)
	if status != 200 || health["status"] != "ok" {
		t.Fatalf("健康检查失败：%d %v", status, health)
	}
	_, me := doRequest(engine, http.MethodGet, "/api/v1/me", "buyer01", nil, nil)
	expectCode(t, me, "0")
	if dataOf(t, me)["role"] != service.RoleBuyer {
		t.Fatalf("身份解析错误：%v", me)
	}
	_, goods := doRequest(engine, http.MethodGet, "/api/v1/goods", "ops01", nil, nil)
	expectCode(t, goods, "0")
	if dataOf(t, goods)["count"].(float64) != 2 {
		t.Fatalf("演示商品数错误：%v", goods)
	}

	code, noAccount := doRequest(engine, http.MethodGet, "/api/v1/me", "", nil, nil)
	if code != 400 || codeOf(noAccount) != "PARAM_ERROR" {
		t.Fatalf("缺少账号应被拒：%d %v", code, noAccount)
	}
	code, badBody := doRequest(engine, http.MethodPost, "/api/v1/orders", "buyer01", "not-json", nil)
	if code != 400 || codeOf(badBody) != "PARAM_ERROR" {
		t.Fatalf("非法 JSON 应被拒：%d %v", code, badBody)
	}
	_, badEvent := doRequest(engine, http.MethodPost, "/api/v1/late-payment/abc/verify", "cs01", map[string]interface{}{"reason": "核实"}, nil)
	expectCode(t, badEvent, "PARAM_ERROR")
	_, badClock := doRequest(engine, http.MethodPost, "/api/v1/admin/clock", "ops01", map[string]interface{}{"offset_minutes": 9999}, nil)
	expectCode(t, badClock, "PARAM_ERROR")
	_, nonOps := doRequest(engine, http.MethodPost, "/api/v1/admin/clock", "buyer01", map[string]interface{}{"offset_minutes": 1}, nil)
	expectCode(t, nonOps, "M-20")
	_, clock := doRequest(engine, http.MethodGet, "/api/v1/admin/clock", "ops01", nil, nil)
	expectCode(t, clock, "0")

	prodEngine, _ := newTestEngine("mysql-innodb")
	_, prodClock := doRequest(prodEngine, http.MethodPost, "/api/v1/admin/clock", "ops01", map[string]interface{}{"offset_minutes": 1}, nil)
	expectCode(t, prodClock, "PARAM_ERROR")
}

func TestAPIScenarioS1NormalAndS2Stock(t *testing.T) {
	engine, _ := newTestEngine("demo-memory")
	orderNo := createPaidOrder(t, engine, 1, 2, 20000, "S1-PAY")
	_, st := doRequest(engine, http.MethodGet, "/api/v1/orders/"+orderNo+"/status", "buyer01", nil, nil)
	expectCode(t, st, "0")
	if dataOf(t, st)["status"] != service.StatusWaitingShipment {
		t.Fatalf("支付后状态错误：%v", st)
	}
	_, detail := doRequest(engine, http.MethodGet, "/api/v1/orders/"+orderNo, "ops01", nil, nil)
	expectCode(t, detail, "0")
	_, ship := doRequest(engine, http.MethodPost, "/api/v1/orders/"+orderNo+"/shipment", "warehouse01",
		map[string]interface{}{"carrier": "顺丰", "tracking_no": "SF-1"}, nil)
	expectCode(t, ship, "0")
	_, dup := doRequest(engine, http.MethodPost, "/api/v1/orders/"+orderNo+"/shipment", "warehouse01",
		map[string]interface{}{"carrier": "顺丰", "tracking_no": "SF-2"}, nil)
	expectCode(t, dup, "M-19")
	_, denied := doRequest(engine, http.MethodGet, "/api/v1/orders/"+orderNo, "buyer02", nil, nil)
	expectCode(t, denied, "M-20")
	_, tampered := doRequest(engine, http.MethodGet, "/api/v1/orders/"+orderNo, "buyer02", nil,
		map[string]string{"X-User-Id": "1001", "X-Role": "买家"})
	expectCode(t, tampered, "M-20")

	success, reject, firstNo := 0, 0, ""
	for i := 0; i < 20; i++ {
		_, resp := doRequest(engine, http.MethodPost, "/api/v1/orders", "buyer02",
			map[string]interface{}{"goods_id": 1, "quantity": 1}, nil)
		if codeOf(resp) == "0" {
			success++
			if firstNo == "" {
				firstNo = dataOf(t, resp)["order_no"].(string)
			}
		} else {
			reject++
		}
	}
	if success != 3 || reject != 17 {
		t.Fatalf("库存守恒错误：成功=%d 被拒=%d", success, reject)
	}
	_, cancel := doRequest(engine, http.MethodPost, "/api/v1/orders/"+firstNo+"/cancel", "buyer02", nil, nil)
	expectCode(t, cancel, "0")
	_, cancelDup := doRequest(engine, http.MethodPost, "/api/v1/orders/"+firstNo+"/cancel", "buyer02", nil, nil)
	expectCode(t, cancelDup, "M-10")
	_, summary := doRequest(engine, http.MethodGet, "/api/v1/ops/summary", "ops01", nil, nil)
	expectCode(t, summary, "0")
	if _, exists := dataOf(t, summary)["no_duplicate_release_refund"]; !exists {
		t.Fatalf("汇总缺少核查字段：%v", summary)
	}
}

func TestAPIScenarioS3PresaleRefund(t *testing.T) {
	engine, _ := newTestEngine("demo-memory")
	orderNo := createPaidOrder(t, engine, 2, 1, 10000, "S3-PAY")
	_, apply := doRequest(engine, http.MethodPost, "/api/v1/orders/"+orderNo+"/refund/apply", "buyer01",
		map[string]interface{}{"reason": "不想要了"}, nil)
	expectCode(t, apply, "0")
	_, blocked := doRequest(engine, http.MethodPost, "/api/v1/orders/"+orderNo+"/shipment", "warehouse01",
		map[string]interface{}{"carrier": "顺丰", "tracking_no": "SF-3"}, nil)
	expectCode(t, blocked, "M-22")
	_, approve := doRequest(engine, http.MethodPost, "/api/v1/orders/"+orderNo+"/refund/approve", "cs01",
		map[string]interface{}{"remark": "同意整单退款"}, nil)
	expectCode(t, approve, "0")
	callback := map[string]interface{}{
		"order_no": orderNo, "refund_channel_trade_no": "S3-RF", "amount": 10000,
		"signature_valid": true, "success": false,
	}
	_, failed := doRequest(engine, http.MethodPost, "/api/v1/refund/callback", "mock01", callback, nil)
	expectCode(t, failed, "M-08")
	_, retry := doRequest(engine, http.MethodPost, "/api/v1/orders/"+orderNo+"/refund/retry", "cs01",
		map[string]interface{}{"remark": "客服重试"}, nil)
	expectCode(t, retry, "0")
	callback["success"] = true
	_, refunded := doRequest(engine, http.MethodPost, "/api/v1/refund/callback", "mock01", callback, nil)
	expectCode(t, refunded, "0")
	_, repeated := doRequest(engine, http.MethodPost, "/api/v1/refund/callback", "mock01", callback, nil)
	expectCode(t, repeated, "0")
	_, st := doRequest(engine, http.MethodGet, "/api/v1/orders/"+orderNo+"/status", "buyer01", nil, nil)
	if dataOf(t, st)["status"] != service.StatusRefunded {
		t.Fatalf("退款终态错误：%v", st)
	}
	_, reject := doRequest(engine, http.MethodPost, "/api/v1/orders/"+orderNo+"/refund/reject", "cs01",
		map[string]interface{}{"remark": "重复审核"}, nil)
	expectCode(t, reject, "M-05")
}

func TestAPIScenarioS4LatePayment(t *testing.T) {
	engine, _ := newTestEngine("demo-memory")
	_, order := doRequest(engine, http.MethodPost, "/api/v1/orders", "buyer03",
		map[string]interface{}{"goods_id": 2, "quantity": 1}, nil)
	expectCode(t, order, "0")
	orderNo := dataOf(t, order)["order_no"].(string)
	_, clock := doRequest(engine, http.MethodPost, "/api/v1/admin/clock", "ops01",
		map[string]interface{}{"offset_minutes": 11}, nil)
	expectCode(t, clock, "0")
	_, closed := doRequest(engine, http.MethodPost, "/api/v1/admin/orders/close-expired", "ops01",
		map[string]interface{}{"limit": 100}, nil)
	expectCode(t, closed, "0")
	_, late := doRequest(engine, http.MethodPost, "/api/v1/payment/callback", "mock01",
		map[string]interface{}{"order_no": orderNo, "channel_trade_no": "S4-LATE", "amount": 10000, "signature_valid": true}, nil)
	expectCode(t, late, "M-09")
	eventID := int64(dataOf(t, late)["event_id"].(float64))
	if eventID <= 0 {
		t.Fatalf("迟到支付必须返回可核实的异常事件 ID：%v", late)
	}
	_, summary := doRequest(engine, http.MethodGet, "/api/v1/ops/summary", "ops01", nil, nil)
	if dataOf(t, summary)["late_payment_events"].(float64) != 1 {
		t.Fatalf("异常待处理数错误：%v", summary)
	}
	_, verify := doRequest(engine, http.MethodPost, fmt.Sprintf("/api/v1/late-payment/%d/verify", eventID), "cs01",
		map[string]interface{}{"reason": "核实为迟到支付"}, nil)
	expectCode(t, verify, "0")
	_, initiate := doRequest(engine, http.MethodPost, fmt.Sprintf("/api/v1/late-payment/%d/refund/initiate", eventID), "cs01",
		map[string]interface{}{"refund_no": "S4-LR", "reason": "核实后发起退款"}, nil)
	expectCode(t, initiate, "0")
	callback := map[string]interface{}{
		"event_id": eventID, "refund_no": "S4-LR", "amount": 10000,
		"signature_valid": true, "success": false,
	}
	_, failed := doRequest(engine, http.MethodPost, "/api/v1/late-payment/refund/callback", "mock01", callback, nil)
	expectCode(t, failed, "M-08")
	_, retry := doRequest(engine, http.MethodPost, "/api/v1/late-payment/refund/retry", "cs01",
		map[string]interface{}{"event_id": eventID, "refund_no": "S4-LR", "remark": "客服重试"}, nil)
	expectCode(t, retry, "0")
	callback["success"] = true
	_, ok := doRequest(engine, http.MethodPost, "/api/v1/late-payment/refund/callback", "mock01", callback, nil)
	expectCode(t, ok, "0")
	_, st := doRequest(engine, http.MethodGet, "/api/v1/orders/"+orderNo+"/status", "buyer03", nil, nil)
	if dataOf(t, st)["status"] != service.StatusClosed {
		t.Fatalf("迟到支付退款后终态必须保持已关闭：%v", st)
	}
	_, closeAgain := doRequest(engine, http.MethodPost, "/api/v1/admin/orders/close-expired", "ops01", nil, nil)
	expectCode(t, closeAgain, "0")
	if dataOf(t, closeAgain)["closed_count"].(float64) != 0 {
		t.Fatalf("重复关闭不得产生第二笔关闭结果：%v", closeAgain)
	}
}

func TestAPIScenarioS5CompetitionRejectionsAndViewsNil(t *testing.T) {
	engine, _ := newTestEngine("demo-memory")
	orderNo := createPaidOrder(t, engine, 1, 1, 10000, "S5-PAY")
	_, repeat := doRequest(engine, http.MethodPost, "/api/v1/payment/callback", "mock01",
		map[string]interface{}{"order_no": orderNo, "channel_trade_no": "S5-PAY", "amount": 10000, "signature_valid": true}, nil)
	expectCode(t, repeat, "0")
	for _, item := range []struct {
		tradeNo string
		amount  int64
		valid   bool
		want    string
	}{
		{"S5-BAD-SIGN", 10000, false, "M-28"},
		{"S5-BAD-AMT", 9999, true, "M-29"},
	} {
		_, resp := doRequest(engine, http.MethodPost, "/api/v1/payment/callback", "mock01",
			map[string]interface{}{"order_no": orderNo, "channel_trade_no": item.tradeNo, "amount": item.amount, "signature_valid": item.valid}, nil)
		expectCode(t, resp, item.want)
	}
	_, unknown := doRequest(engine, http.MethodPost, "/api/v1/payment/callback", "mock01",
		map[string]interface{}{"order_no": "NOT-EXIST", "channel_trade_no": "S5-UNKNOWN", "amount": 10000, "signature_valid": true}, nil)
	expectCode(t, unknown, "M-30")
	_, apply := doRequest(engine, http.MethodPost, "/api/v1/orders/"+orderNo+"/refund/apply", "buyer01",
		map[string]interface{}{"reason": "并发申请"}, nil)
	expectCode(t, apply, "0")
	_, raceShip := doRequest(engine, http.MethodPost, "/api/v1/orders/"+orderNo+"/shipment", "warehouse01",
		map[string]interface{}{"carrier": "顺丰", "tracking_no": "SF-5"}, nil)
	expectCode(t, raceShip, "M-22")

	if orderView(nil) != nil || paymentView(nil) != nil || summaryView(nil) != nil {
		t.Fatal("nil 视图必须返回 nil")
	}
	if len(goodsViews(nil)) != 0 {
		t.Fatal("空商品列表视图长度必须为 0")
	}
	if !boolOrTrue(nil) || boolOrTrue(func() *bool { v := false; return &v }()) {
		t.Fatal("boolOrTrue 默认值处理错误")
	}
}
