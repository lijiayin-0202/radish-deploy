package router

// 竞态检测说明：go test ./... -race 需要 CGO_ENABLED=1 与可用 C 编译器。

import (
	"testing"

	"github.com/gin-gonic/gin"

	"shop-trade/server/api/v1"
	"shop-trade/server/service"
)

func TestInitExtensionRouterRegistersThreeEndpoints(t *testing.T) {
	gin.SetMode(gin.TestMode)
	repo := service.NewDemoOrderRepository().(service.ExtensionRepository)
	api := v1.NewExtensionApi(service.NewExtensionService(repo, nil))
	engine := gin.New()
	ExtensionRouter{}.InitExtensionRouter(engine.Group("/api/v1"), api)

	registered := map[string]bool{}
	for _, r := range engine.Routes() {
		registered[r.Method+" "+r.Path] = true
	}
	required := []string{
		"POST /api/v1/admin/goods/:goods_id/price",
		"POST /api/v1/payment/timeout",
		"GET /api/v1/ops/stock-check/:order_no",
	}
	for _, path := range required {
		if !registered[path] {
			t.Fatalf("缺少扩展路由 %s；已注册：%v", path, registered)
		}
	}
	if len(engine.Routes()) != len(required) {
		t.Fatalf("扩展路由数量应为 %d，实际 %d", len(required), len(engine.Routes()))
	}
}
