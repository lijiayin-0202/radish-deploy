package v1

// 竞态检测说明：go test ./... -race 需要 CGO_ENABLED=1 与可用 C 编译器。
// 本文件用 httptest 覆盖 API-21~API-23 的成功与拒绝分支，复用既有 doRequest 辅助函数。

import (
	"context"
	"fmt"
	"testing"

	"github.com/gin-gonic/gin"
	"net/http"

	"shop-trade/server/model"
	"shop-trade/server/service"
)

func newExtensionTestEngine() (*gin.Engine, service.OrderRepository) {
	gin.SetMode(gin.TestMode)
	repo := service.NewDemoOrderRepository()
	ext := service.NewExtensionService(repo.(service.ExtensionRepository), nil)
	api := NewExtensionApi(ext)
	engine := gin.New()
	group := engine.Group("/api/v1")
	group.POST("/admin/goods/:goods_id/price", api.UpdateGoodsPrice)
	group.POST("/payment/timeout", api.HandleChannelTimeout)
	group.GET("/ops/stock-check/:order_no", api.VerifyStockRestoration)
	// 覆盖路径参数为空时的 PARAM_ERROR 分支。
	group.GET("/ops/stock-check-empty", api.VerifyStockRestoration)
	return engine, repo
}

func seedExtOrder(t *testing.T, repo service.OrderRepository, orderNo string) {
	t.Helper()
	err := repo.CreateOrder(context.Background(), &model.Order{
		OrderNo: orderNo, BuyerID: 1001, GoodsID: 1, GoodsNo: "GOODS-ACT-001",
		Quantity: 1, UnitPrice: 10000, TotalAmount: 10000,
		Status: service.StatusPendingPayment, RefundKind: service.RefundKindNone,
	})
	if err != nil {
		t.Fatalf("准备订单失败：%v", err)
	}
}

func TestExtensionApiUpdateGoodsPrice(t *testing.T) {
	engine, _ := newExtensionTestEngine()
	body := map[string]interface{}{"unit_price": 12000, "reason": "活动价格调整"}

	status, resp := doRequest(engine, http.MethodPost, "/api/v1/admin/goods/1/price", "ops01", body, nil)
	if status != http.StatusOK {
		t.Fatalf("HTTP 状态应为 200，实际 %d", status)
	}
	expectCode(t, resp, "0")
	data := dataOf(t, resp)
	if fmt.Sprint(data["new_unit_price"]) != "12000" || fmt.Sprint(data["old_unit_price"]) != "10000" {
		t.Fatalf("调价前后金额不正确：%v", data)
	}
	if data["hint"] != "已有订单的下单时商品与价格不受本次调价 / 上下架影响" {
		t.Fatalf("必须回传 M-12 提示：%v", data)
	}
	if fmt.Sprint(data["audit_event_id"]) != "1" {
		t.Fatalf("必须回传只追加审计事件 ID：%v", data)
	}

	_, resp = doRequest(engine, http.MethodPost, "/api/v1/admin/goods/1/price", "buyer01", body, nil)
	expectCode(t, resp, "M-20")
	_, resp = doRequest(engine, http.MethodPost, "/api/v1/admin/goods/1/price", "", body, nil)
	expectCode(t, resp, "PARAM_ERROR")
	_, resp = doRequest(engine, http.MethodPost, "/api/v1/admin/goods/abc/price", "ops01", body, nil)
	expectCode(t, resp, "PARAM_ERROR")
	_, resp = doRequest(engine, http.MethodPost, "/api/v1/admin/goods/999/price", "ops01", body, nil)
	expectCode(t, resp, "PARAM_ERROR")
	_, resp = doRequest(engine, http.MethodPost, "/api/v1/admin/goods/1/price", "ops01",
		map[string]interface{}{"unit_price": 0}, nil)
	expectCode(t, resp, "PARAM_ERROR")
	_, resp = doRequest(engine, http.MethodPost, "/api/v1/admin/goods/1/price", "ops01", nil, nil)
	expectCode(t, resp, "PARAM_ERROR")
}

func TestExtensionApiChannelTimeout(t *testing.T) {
	engine, repo := newExtensionTestEngine()
	seedExtOrder(t, repo, "ORD-TIMEOUT")
	body := map[string]interface{}{
		"order_no": "ORD-TIMEOUT", "channel_trade_no": "TO-1", "reason": "模拟渠道通知超时",
	}

	status, resp := doRequest(engine, http.MethodPost, "/api/v1/payment/timeout", "mock01", body, nil)
	if status != http.StatusOK {
		t.Fatalf("HTTP 状态应为 200，实际 %d", status)
	}
	expectCode(t, resp, "0")
	data := dataOf(t, resp)
	if data["order_status_unchanged"] != true || data["order_status"] != service.StatusPendingPayment || data["duplicate"] != false {
		t.Fatalf("超时通知不得改状态：%v", data)
	}

	_, resp = doRequest(engine, http.MethodPost, "/api/v1/payment/timeout", "ops01", body, nil)
	expectCode(t, resp, "0")
	if dataOf(t, resp)["duplicate"] != true {
		t.Fatalf("重复通知应幂等：%v", resp)
	}

	unknown := map[string]interface{}{"order_no": "NO-SUCH-ORDER", "channel_trade_no": "TO-2"}
	_, resp = doRequest(engine, http.MethodPost, "/api/v1/payment/timeout", "mock01", unknown, nil)
	expectCode(t, resp, "M-30")

	_, resp = doRequest(engine, http.MethodPost, "/api/v1/payment/timeout", "buyer01", body, nil)
	expectCode(t, resp, "M-20")
	_, resp = doRequest(engine, http.MethodPost, "/api/v1/payment/timeout", "mock01",
		map[string]interface{}{"order_no": ""}, nil)
	expectCode(t, resp, "PARAM_ERROR")
	_, resp = doRequest(engine, http.MethodPost, "/api/v1/payment/timeout", "mock01", nil, nil)
	expectCode(t, resp, "PARAM_ERROR")
	_, resp = doRequest(engine, http.MethodPost, "/api/v1/payment/timeout", "", body, nil)
	expectCode(t, resp, "PARAM_ERROR")
}

func TestExtensionApiVerifyStockRestoration(t *testing.T) {
	engine, repo := newExtensionTestEngine()
	seedExtOrder(t, repo, "ORD-CHECK")

	for _, account := range []string{"ops01", "cs01"} {
		status, resp := doRequest(engine, http.MethodGet, "/api/v1/ops/stock-check/ORD-CHECK", account, nil, nil)
		if status != http.StatusOK {
			t.Fatalf("HTTP 状态应为 200，实际 %d", status)
		}
		expectCode(t, resp, "0")
		data := dataOf(t, resp)
		if data["consistent"] != true || fmt.Sprint(data["unit_price_snapshot"]) != "10000" ||
			fmt.Sprint(data["available_stock"]) != "5" {
			t.Fatalf("逐单核查应带出金额快照与库存：%v", data)
		}
	}

	_, resp := doRequest(engine, http.MethodGet, "/api/v1/ops/stock-check/NO-SUCH-ORDER", "ops01", nil, nil)
	expectCode(t, resp, "PARAM_ERROR")
	_, resp = doRequest(engine, http.MethodGet, "/api/v1/ops/stock-check/ORD-CHECK", "buyer01", nil, nil)
	expectCode(t, resp, "M-20")
	_, resp = doRequest(engine, http.MethodGet, "/api/v1/ops/stock-check-empty", "ops01", nil, nil)
	expectCode(t, resp, "PARAM_ERROR")
	_, resp = doRequest(engine, http.MethodGet, "/api/v1/ops/stock-check/ORD-CHECK", "", nil, nil)
	expectCode(t, resp, "PARAM_ERROR")
}
