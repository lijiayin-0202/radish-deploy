package v1

// 竞态检测说明：go test ./... -race 需要 CGO_ENABLED=1 与可用 C 编译器。
// 本文件只补接入层的拒绝与异常分支覆盖，不改动任何生产代码：
//   1) 每个接口的「缺少或未知 X-Demo-Account」分支；
//   2) 每个带请求体接口的「请求体不是合法 JSON」分支；
//   3) service 层的未知订单 / 未知异常事件 / 角色不允许分支；
//   4) writeErr / writeExtensionErr 的技术错误兜底与可选 data 载荷分支。

import (
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"

	"shop-trade/server/model"
	"shop-trade/server/service"
)

// apiCase 描述一次接口调用的最小要素。
type apiCase struct {
	name    string
	method  string
	path    string
	account string
	body    interface{}
}

// allAPICases 覆盖 server/router/order.go 注册的全部业务接口。
func allAPICases() []apiCase {
	return []apiCase{
		{"me", http.MethodGet, "/api/v1/me", "buyer01", nil},
		{"goods", http.MethodGet, "/api/v1/goods", "ops01", nil},
		{"create-order", http.MethodPost, "/api/v1/orders", "buyer01",
			map[string]interface{}{"goods_id": 1, "quantity": 1}},
		{"get-order", http.MethodGet, "/api/v1/orders/ORD-BRANCH", "buyer01", nil},
		{"get-order-status", http.MethodGet, "/api/v1/orders/ORD-BRANCH/status", "buyer01", nil},
		{"cancel-order", http.MethodPost, "/api/v1/orders/ORD-BRANCH/cancel", "buyer01", nil},
		{"payment-callback", http.MethodPost, "/api/v1/payment/callback", "mock01",
			map[string]interface{}{"order_no": "ORD-BRANCH", "channel_trade_no": "BRANCH-PAY",
				"amount": 10000, "signature_valid": true}},
		{"close-expired", http.MethodPost, "/api/v1/admin/orders/close-expired", "ops01",
			map[string]interface{}{"limit": 10}},
		{"refund-apply", http.MethodPost, "/api/v1/orders/ORD-BRANCH/refund/apply", "buyer01",
			map[string]interface{}{"reason": "不想要了"}},
		{"refund-reject", http.MethodPost, "/api/v1/orders/ORD-BRANCH/refund/reject", "cs01",
			map[string]interface{}{"remark": "不同意退款"}},
		{"refund-approve", http.MethodPost, "/api/v1/orders/ORD-BRANCH/refund/approve", "cs01",
			map[string]interface{}{"remark": "同意整单退款"}},
		{"refund-retry", http.MethodPost, "/api/v1/orders/ORD-BRANCH/refund/retry", "cs01",
			map[string]interface{}{"remark": "客服重试"}},
		{"refund-callback", http.MethodPost, "/api/v1/refund/callback", "mock01",
			map[string]interface{}{"order_no": "ORD-BRANCH", "refund_channel_trade_no": "BRANCH-RF",
				"amount": 10000, "signature_valid": true, "success": true}},
		{"shipment", http.MethodPost, "/api/v1/orders/ORD-BRANCH/shipment", "warehouse01",
			map[string]interface{}{"carrier": "顺丰", "tracking_no": "SF-BRANCH"}},
		{"late-verify", http.MethodPost, "/api/v1/late-payment/1/verify", "cs01",
			map[string]interface{}{"reason": "核实为迟到支付"}},
		{"late-initiate", http.MethodPost, "/api/v1/late-payment/1/refund/initiate", "cs01",
			map[string]interface{}{"refund_no": "BRANCH-LR", "reason": "核实后发起退款"}},
		{"late-callback", http.MethodPost, "/api/v1/late-payment/refund/callback", "mock01",
			map[string]interface{}{"event_id": 1, "refund_no": "BRANCH-LR", "amount": 10000,
				"signature_valid": true, "success": true}},
		{"late-retry", http.MethodPost, "/api/v1/late-payment/refund/retry", "cs01",
			map[string]interface{}{"event_id": 1, "refund_no": "BRANCH-LR", "remark": "客服重试"}},
		{"ops-summary", http.MethodGet, "/api/v1/ops/summary", "ops01", nil},
		{"get-clock", http.MethodGet, "/api/v1/admin/clock", "ops01", nil},
		{"set-clock", http.MethodPost, "/api/v1/admin/clock", "ops01",
			map[string]interface{}{"offset_minutes": 5}},
	}
}

// TestAPIBranchAllEndpointsRejectUnknownAccount 覆盖身份解析失败分支：
// 身份只由服务端预置账号解析，缺少或未知账号一律 PARAM_ERROR，不得落到业务逻辑。
func TestAPIBranchAllEndpointsRejectUnknownAccount(t *testing.T) {
	engine, _ := newTestEngine("demo-memory")
	for _, c := range allAPICases() {
		for _, account := range []string{"", "unknown-account"} {
			status, resp := doRequest(engine, c.method, c.path, account, c.body, nil)
			if status != http.StatusBadRequest || codeOf(resp) != "PARAM_ERROR" {
				t.Fatalf("%s 账号=%q 应被 PARAM_ERROR 拒绝，实际 HTTP=%d resp=%v",
					c.name, account, status, resp)
			}
		}
	}
}

// TestAPIBranchAllBodyEndpointsRejectInvalidJSON 覆盖请求体绑定失败分支。
func TestAPIBranchAllBodyEndpointsRejectInvalidJSON(t *testing.T) {
	engine, _ := newTestEngine("demo-memory")
	for _, c := range allAPICases() {
		if c.body == nil {
			continue
		}
		status, resp := doRequest(engine, c.method, c.path, c.account, "not-an-object", nil)
		if status != http.StatusBadRequest || codeOf(resp) != "PARAM_ERROR" {
			t.Fatalf("%s 非法请求体应被 PARAM_ERROR 拒绝，实际 HTTP=%d resp=%v",
				c.name, status, resp)
		}
	}
}

// TestAPIBranchUnknownOrderAndEventPaths 覆盖 service 层的未知订单与未知异常事件分支。
func TestAPIBranchUnknownOrderAndEventPaths(t *testing.T) {
	engine, _ := newTestEngine("demo-memory")

	unknownOrder := []apiCase{
		{"get-order", http.MethodGet, "/api/v1/orders/NO-SUCH-ORDER", "buyer01", nil},
		{"get-order-status", http.MethodGet, "/api/v1/orders/NO-SUCH-ORDER/status", "buyer01", nil},
		{"cancel-order", http.MethodPost, "/api/v1/orders/NO-SUCH-ORDER/cancel", "buyer01", nil},
		{"refund-apply", http.MethodPost, "/api/v1/orders/NO-SUCH-ORDER/refund/apply", "buyer01",
			map[string]interface{}{"reason": "不想要了"}},
		{"refund-reject", http.MethodPost, "/api/v1/orders/NO-SUCH-ORDER/refund/reject", "cs01",
			map[string]interface{}{"remark": "不同意"}},
		{"refund-approve", http.MethodPost, "/api/v1/orders/NO-SUCH-ORDER/refund/approve", "cs01",
			map[string]interface{}{"remark": "同意"}},
		{"refund-retry", http.MethodPost, "/api/v1/orders/NO-SUCH-ORDER/refund/retry", "cs01",
			map[string]interface{}{"remark": "重试"}},
		{"shipment", http.MethodPost, "/api/v1/orders/NO-SUCH-ORDER/shipment", "warehouse01",
			map[string]interface{}{"carrier": "顺丰", "tracking_no": "SF-NONE"}},
	}
	for _, c := range unknownOrder {
		status, resp := doRequest(engine, c.method, c.path, c.account, c.body, nil)
		if status != http.StatusOK || codeOf(resp) != "M-30" {
			t.Fatalf("%s 未知订单应返回 M-30，实际 HTTP=%d resp=%v", c.name, status, resp)
		}
	}

	unknownEvent := []apiCase{
		{"late-verify", http.MethodPost, "/api/v1/late-payment/999/verify", "cs01",
			map[string]interface{}{"reason": "核实"}},
		{"late-initiate", http.MethodPost, "/api/v1/late-payment/999/refund/initiate", "cs01",
			map[string]interface{}{"refund_no": "BR-NONE-LR", "reason": "发起"}},
		{"late-retry", http.MethodPost, "/api/v1/late-payment/refund/retry", "cs01",
			map[string]interface{}{"event_id": 999, "refund_no": "BR-NONE-LR", "remark": "重试"}},
	}
	for _, c := range unknownEvent {
		status, resp := doRequest(engine, c.method, c.path, c.account, c.body, nil)
		if status != http.StatusOK || codeOf(resp) != "M-14" {
			t.Fatalf("%s 未知异常事件应返回 M-14，实际 HTTP=%d resp=%v", c.name, status, resp)
		}
	}

	// 角色不允许：运营汇总与超时关单只允许运营角色。
	for _, c := range []apiCase{
		{"ops-summary", http.MethodGet, "/api/v1/ops/summary", "buyer01", nil},
		{"close-expired", http.MethodPost, "/api/v1/admin/orders/close-expired", "buyer01",
			map[string]interface{}{"limit": 10}},
	} {
		status, resp := doRequest(engine, c.method, c.path, c.account, c.body, nil)
		if status != http.StatusOK || codeOf(resp) != "M-20" {
			t.Fatalf("%s 越权应返回 M-20，实际 HTTP=%d resp=%v", c.name, status, resp)
		}
	}

	// 退款通知缺少渠道交易号：同一渠道交易号归属校验分支。
	status, resp := doRequest(engine, http.MethodPost, "/api/v1/refund/callback", "mock01",
		map[string]interface{}{"order_no": "ORD-BRANCH", "amount": 10000, "signature_valid": true, "success": true}, nil)
	if status != http.StatusOK || codeOf(resp) != "M-27" {
		t.Fatalf("退款通知缺渠道交易号应返回 M-27，实际 HTTP=%d resp=%v", status, resp)
	}
}

// TestAPIBranchErrorMappingHelpers 覆盖错误映射兜底分支：
// 非业务异常不得把内部细节泄露给客户端，统一返回 INTERNAL_ERROR 与 500。
func TestAPIBranchErrorMappingHelpers(t *testing.T) {
	gin.SetMode(gin.TestMode)

	recorder := httptest.NewRecorder()
	ctx, _ := gin.CreateTestContext(recorder)
	writeErr(ctx, errors.New("unexpected internal failure"))
	if recorder.Code != http.StatusInternalServerError {
		t.Fatalf("技术错误应返回 500，实际 %d", recorder.Code)
	}
	var payload map[string]interface{}
	if err := json.Unmarshal(recorder.Body.Bytes(), &payload); err != nil {
		t.Fatalf("响应必须是合法 JSON：%v", err)
	}
	if payload["code"] != "INTERNAL_ERROR" {
		t.Fatalf("技术错误应返回 INTERNAL_ERROR，实际 %v", payload)
	}

	recorder = httptest.NewRecorder()
	ctx, _ = gin.CreateTestContext(recorder)
	writeErr(ctx, &service.BizError{Code: "M-10", Message: "重复操作被拒绝"})
	if recorder.Code != http.StatusOK {
		t.Fatalf("业务拒绝应返回 200，实际 %d", recorder.Code)
	}
	payload = map[string]interface{}{}
	_ = json.Unmarshal(recorder.Body.Bytes(), &payload)
	if payload["code"] != "M-10" || payload["data"] != nil {
		t.Fatalf("业务拒绝响应形状不正确：%v", payload)
	}

	recorder = httptest.NewRecorder()
	ctx, _ = gin.CreateTestContext(recorder)
	writeErr(ctx, &service.BizError{Code: "M-09", Message: "迟到支付"},
		map[string]interface{}{"event_id": 7})
	if recorder.Code != http.StatusOK {
		t.Fatalf("带 data 的业务拒绝应返回 200，实际 %d", recorder.Code)
	}
	payload = map[string]interface{}{}
	_ = json.Unmarshal(recorder.Body.Bytes(), &payload)
	data, ok := payload["data"].(map[string]interface{})
	if !ok || data["event_id"] == nil {
		t.Fatalf("必须携带同事务内已提交的审计事件 ID：%v", payload)
	}

	recorder = httptest.NewRecorder()
	ctx, _ = gin.CreateTestContext(recorder)
	writeExtensionErr(ctx, errors.New("unexpected internal failure"))
	if recorder.Code != http.StatusInternalServerError {
		t.Fatalf("扩展错误兜底应返回 500，实际 %d", recorder.Code)
	}
}

// TestAPIBranchGoodsListerFailure 覆盖商品列表读取失败的兜底分支。
func TestAPIBranchGoodsListerFailure(t *testing.T) {
	gin.SetMode(gin.TestMode)
	clock := &testClock{}
	svc := service.NewOrderServiceWithClock(service.NewDemoOrderRepository(), clock.Now)
	api := NewOrderApi(svc, func() ([]model.Goods, error) {
		return nil, errors.New("goods lister failed")
	}, clock, "demo-memory")
	engine := gin.New()
	engine.GET("/api/v1/goods", api.ListGoods)

	status, resp := doRequest(engine, http.MethodGet, "/api/v1/goods", "ops01", nil, nil)
	if status != http.StatusInternalServerError || codeOf(resp) != "INTERNAL_ERROR" {
		t.Fatalf("商品列表读取失败应返回 500/INTERNAL_ERROR，实际 HTTP=%d resp=%v", status, resp)
	}
}
