package initialize

import (
	"github.com/gin-gonic/gin"

	"shop-trade/server/api/v1"
	"shop-trade/server/router"
	"shop-trade/server/service"
)

// Routers 按 GVA 原生方式创建 Gin 引擎、注册全局中间件与全部业务路由。
// /health 保持为健康检查入口；业务路由统一挂在 /api/v1 下。
// exts 为可选扩展服务：不传时行为与整改前完全一致，既有单元测试与五组场景不受影响。
func Routers(svc *service.OrderService, goodsLister v1.GoodsLister, clock *DemoClock, mode string, exts ...*service.ExtensionService) *gin.Engine {
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
	if len(exts) > 0 && exts[0] != nil {
		router.ExtensionRouter{}.InitExtensionRouter(group, v1.NewExtensionApi(exts[0]))
	}

	// GVA 静态资源：V-01~V-08 简易演示页面，纯 HTML + 原生 JS，不引入 Vue 或前端构建。
	engine.Static("/static", "resource/static")
	engine.GET("/", func(c *gin.Context) {
		c.File("resource/static/index.html")
	})

	return engine
}
