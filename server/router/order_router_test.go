package router

// 竞态检测说明：go test ./... -race 需要 CGO_ENABLED=1 与可用 C 编译器。
// PowerShell：$env:CGO_ENABLED = "1"; go test ./... -race -count=1
// bash：CGO_ENABLED=1 go test ./... -race -count=1

import (
	"testing"

	"github.com/gin-gonic/gin"

	"shop-trade/server/api/v1"
	"shop-trade/server/model"
	"shop-trade/server/service"
)

type routerTestClock struct{}

func (routerTestClock) OffsetMinutes() int   { return 0 }
func (routerTestClock) SetOffsetMinutes(int) {}

func TestInitOrderRouterRegistersAllRequiredEndpoints(t *testing.T) {
	gin.SetMode(gin.TestMode)
	svc := service.NewOrderService(service.NewDemoOrderRepository())
	api := v1.NewOrderApi(svc, func() ([]model.Goods, error) { return service.DemoGoods(), nil }, routerTestClock{}, "demo-memory")
	engine := gin.New()
	OrderRouter{}.InitOrderRouter(engine.Group("/api/v1"), api)

	registered := map[string]bool{}
	for _, r := range engine.Routes() {
		registered[r.Method+" "+r.Path] = true
	}
	required := []string{
		"POST /api/v1/orders",
		"GET /api/v1/orders/:order_no",
		"GET /api/v1/orders/:order_no/status",
		"POST /api/v1/orders/:order_no/cancel",
		"POST /api/v1/payment/callback",
		"POST /api/v1/admin/orders/close-expired",
		"POST /api/v1/orders/:order_no/refund/apply",
		"POST /api/v1/orders/:order_no/refund/reject",
		"POST /api/v1/orders/:order_no/refund/approve",
		"POST /api/v1/orders/:order_no/refund/retry",
		"POST /api/v1/refund/callback",
		"POST /api/v1/orders/:order_no/shipment",
		"POST /api/v1/late-payment/:event_id/verify",
		"POST /api/v1/late-payment/:event_id/refund/initiate",
		"POST /api/v1/late-payment/refund/callback",
		"POST /api/v1/late-payment/refund/retry",
		"GET /api/v1/ops/summary",
		"GET /api/v1/goods",
		"GET /api/v1/me",
		"GET /api/v1/admin/clock",
		"POST /api/v1/admin/clock",
	}
	for _, r := range required {
		if !registered[r] {
			t.Fatalf("缺少必需路由：%s", r)
		}
	}
}
