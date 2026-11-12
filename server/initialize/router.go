package initialize

import (
	"github.com/gin-gonic/gin"

	"shop-trade/server/api/v1"
	"shop-trade/server/router"
	"shop-trade/server/service"
)

// Routers 按 GVA 原生方式创建 Gin 引擎、注册全局中间件与全部业务路由。
// /health 保持为健康检查入口；业务路由统一挂在 /api/v1 下。
func Routers(svc *service.OrderService, goodsLister v1.GoodsLister, clock *DemoClock, mode string) *gin.Engine {
	engine := gin.New()
	engine.Use(gin.Logger(), gin.Recovery())
	engine.Use(func(c *gin.Context) {
		c.Set("mode", mode)
		c.Next()
	})

	engine.GET("/health", v1.Health)

	group := engine.Group("/api/v1")
	api := v1.NewOrderApi(svc, goodsLister, clock, mode)
	router.OrderRouter{}.InitOrderRouter(group, api)

	return engine
}
