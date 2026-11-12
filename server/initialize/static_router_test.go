package initialize

// 竞态检测说明：go test ./... -race 需要 CGO_ENABLED=1 与可用 C 编译器。
// 静态资源路径相对项目根目录，单测只核对路由注册，不读取页面文件内容。

import (
	"testing"

	"github.com/gin-gonic/gin"

	"shop-trade/server/model"
	"shop-trade/server/service"
)

func TestRoutersStaticAndOptionalExtensionRoutes(t *testing.T) {
	gin.SetMode(gin.TestMode)
	clock := NewDemoClock(0)
	repo := service.NewDemoOrderRepository()
	svc := service.NewOrderServiceWithClock(repo, clock.Now)
	goodsLister := func() ([]model.Goods, error) { return service.DemoGoods(), nil }
	ext := service.NewExtensionService(repo.(service.ExtensionRepository), clock.Now)

	withExt := Routers(svc, goodsLister, clock, "demo-memory", ext)
	registered := map[string]bool{}
	for _, r := range withExt.Routes() {
		registered[r.Method+" "+r.Path] = true
	}
	for _, path := range []string{
		"GET /health",
		"GET /",
		"GET /static/*filepath",
		"POST /api/v1/admin/goods/:goods_id/price",
		"POST /api/v1/payment/timeout",
		"GET /api/v1/ops/stock-check/:order_no",
		"POST /api/v1/orders",
	} {
		if !registered[path] {
			t.Fatalf("传入扩展服务后缺少路由 %s；已注册：%v", path, registered)
		}
	}

	withoutExt := Routers(svc, goodsLister, clock, "demo-memory")
	for _, r := range withoutExt.Routes() {
		if r.Path == "/api/v1/payment/timeout" || r.Path == "/api/v1/admin/goods/:goods_id/price" {
			t.Fatalf("不传扩展服务时不应注册扩展路由：%s", r.Path)
		}
	}
	if !hasRoute(withoutExt, "GET", "/health") || !hasRoute(withoutExt, "GET", "/") {
		t.Fatal("健康检查与静态首页在两种模式下都应保留")
	}
}

func hasRoute(engine *gin.Engine, method, path string) bool {
	for _, r := range engine.Routes() {
		if r.Method == method && r.Path == path {
			return true
		}
	}
	return false
}
