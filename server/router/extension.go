package router

import (
	"github.com/gin-gonic/gin"

	"shop-trade/server/api/v1"
)

// ExtensionRouter 按 GVA 原生方式注册「代码产物补齐」批次新增的三个接口。
// 路径与既有 API-01~API-20 不重叠，全部挂在 /api/v1 下。
type ExtensionRouter struct{}

func (ExtensionRouter) InitExtensionRouter(r *gin.RouterGroup, api *v1.ExtensionApi) {
	// API-21 商品调价入口（运营，V-03）
	r.POST("/admin/goods/:goods_id/price", api.UpdateGoodsPrice)
	// API-22 可控模拟渠道超时通知分支
	r.POST("/payment/timeout", api.HandleChannelTimeout)
	// API-23 库存恢复逐单核查（V-04 / V-07）
	r.GET("/ops/stock-check/:order_no", api.VerifyStockRestoration)
}
