package initialize

// 竞态检测说明：go test ./... -race 需要 CGO_ENABLED=1 与可用 C 编译器。
// PowerShell：$env:CGO_ENABLED = "1"; go test ./... -race -count=1
// bash：CGO_ENABLED=1 go test ./... -race -count=1

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"

	"shop-trade/server/model"
	"shop-trade/server/service"
)

func TestRoutersHealthAndBusinessRoutes(t *testing.T) {
	gin.SetMode(gin.TestMode)
	clock := NewDemoClock(0)
	svc := service.NewOrderServiceWithClock(service.NewDemoOrderRepository(), clock.Now)
	goodsLister := func() ([]model.Goods, error) { return service.DemoGoods(), nil }
	engine := Routers(svc, goodsLister, clock, "demo-memory")

	foundHealth, foundOrders := false, false
	for _, r := range engine.Routes() {
		if r.Method == http.MethodGet && r.Path == "/health" {
			foundHealth = true
		}
		if r.Method == http.MethodPost && r.Path == "/api/v1/orders" {
			foundOrders = true
		}
	}
	if !foundHealth || !foundOrders {
		t.Fatalf("全局路由注册不完整：health=%v orders=%v", foundHealth, foundOrders)
	}

	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	engine.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("/health 返回 %d", w.Code)
	}
	if w.Body.String() == "" || !containsText(w.Body.String(), `"mode":"demo-memory"`) {
		t.Fatalf("/health 未返回运行模式：%s", w.Body.String())
	}
}

func containsText(body, sub string) bool {
	for i := 0; i+len(sub) <= len(body); i++ {
		if body[i:i+len(sub)] == sub {
			return true
		}
	}
	return false
}

func TestDemoClockOffset(t *testing.T) {
	clock := NewDemoClock(0)
	before := clock.Now()
	clock.SetOffsetMinutes(11)
	if clock.OffsetMinutes() != 11 {
		t.Fatal("演示时钟偏移未生效")
	}
	if !clock.Now().After(before.Add(10 * time.Minute)) {
		t.Fatal("演示时钟未按偏移量推进服务端时间")
	}
	clock.SetOffsetMinutes(0)
	if clock.OffsetMinutes() != 0 {
		t.Fatal("演示时钟未复位")
	}
}

func TestGormMysqlRejectsInvalidDSN(t *testing.T) {
	if _, err := GormMysql("not-a-dsn"); err == nil {
		t.Fatal("非法 DSN 必须返回错误")
	}
}
