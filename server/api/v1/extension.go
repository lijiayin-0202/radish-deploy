package v1

import (
	"errors"
	"strconv"
	"strings"

	"github.com/gin-gonic/gin"

	"shop-trade/server/service"
)

// 竞态检测说明：go test -race 需要 CGO_ENABLED=1 与 gcc/clang，详见 test-report.md。
// 本 controller 只做参数绑定、身份解析与响应封装，业务逻辑全部在 service.ExtensionService。
// 不复用/不改动 OrderApi 与既有 20 个接口。

// ExtensionApi 承载 API-21~API-23 三个补齐接口。
type ExtensionApi struct {
	ext *service.ExtensionService
}

func NewExtensionApi(ext *service.ExtensionService) *ExtensionApi {
	return &ExtensionApi{ext: ext}
}

type priceRequest struct {
	UnitPrice int64  `json:"unit_price"`
	Reason    string `json:"reason"`
}

// extensionActor 与 OrderApi.actor 使用同一份服务端预置账号映射，
// X-Role / X-User-Id 一律忽略，改请求用户编号不能越权。
func extensionActor(c *gin.Context) (service.Actor, bool) {
	account := strings.TrimSpace(c.GetHeader("X-Demo-Account"))
	actor, exists := demoAccounts[account]
	if !exists {
		paramError(c, "缺少或未知 X-Demo-Account；身份由服务端预置账号解析，X-Role / X-User-Id 不作为身份依据")
		return service.Actor{}, false
	}
	return actor, true
}

// UpdateGoodsPrice 对应 API-21：运营商品调价入口（原型 V-03 / M-12）。
func (a *ExtensionApi) UpdateGoodsPrice(c *gin.Context) {
	actor, valid := extensionActor(c)
	if !valid {
		return
	}
	goodsID, err := strconv.ParseUint(strings.TrimSpace(c.Param("goods_id")), 10, 64)
	if err != nil || goodsID == 0 {
		paramError(c, "goods_id 必须是正整数")
		return
	}
	var req priceRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		paramError(c, "请求体必须是合法 JSON")
		return
	}
	if req.UnitPrice <= 0 {
		paramError(c, "unit_price 必须是正整数分")
		return
	}
	res, err := a.ext.UpdateGoodsPrice(c.Request.Context(), actor, goodsID, req.UnitPrice, strings.TrimSpace(req.Reason))
	if err != nil {
		writeExtensionErr(c, err)
		return
	}
	ok(c, res)
}

// HandleChannelTimeout 对应 API-22：可控模拟渠道超时通知分支。
func (a *ExtensionApi) HandleChannelTimeout(c *gin.Context) {
	actor, valid := extensionActor(c)
	if !valid {
		return
	}
	var notice service.ChannelTimeoutNotice
	if err := c.ShouldBindJSON(&notice); err != nil {
		paramError(c, "请求体必须是合法 JSON")
		return
	}
	notice.OrderNo = strings.TrimSpace(notice.OrderNo)
	notice.ChannelTradeNo = strings.TrimSpace(notice.ChannelTradeNo)
	notice.Reason = strings.TrimSpace(notice.Reason)
	if notice.OrderNo == "" || notice.ChannelTradeNo == "" {
		paramError(c, "order_no 与 channel_trade_no 均不能为空")
		return
	}
	res, err := a.ext.HandleChannelTimeout(c.Request.Context(), actor, notice)
	if err != nil {
		writeExtensionErr(c, err)
		return
	}
	ok(c, res)
}

// VerifyStockRestoration 对应 API-23：按订单号逐单核查库存恢复。
func (a *ExtensionApi) VerifyStockRestoration(c *gin.Context) {
	actor, valid := extensionActor(c)
	if !valid {
		return
	}
	orderNo := strings.TrimSpace(c.Param("order_no"))
	if orderNo == "" {
		paramError(c, "order_no 不能为空")
		return
	}
	res, err := a.ext.VerifyStockRestoration(c.Request.Context(), actor, orderNo)
	if err != nil {
		writeExtensionErr(c, err)
		return
	}
	ok(c, res)
}

// writeExtensionErr 把资源类错误转成 PARAM_ERROR；业务拒绝沿用既有 M-xx 响应。
func writeExtensionErr(c *gin.Context, err error) {
	switch {
	case errors.Is(err, service.ErrGoodsNotFound):
		paramError(c, "商品不存在或已下架，不能调价 / 核查")
	case errors.Is(err, service.ErrOrderNotFound):
		paramError(c, "订单不存在，不能逐单核查")
	case errors.Is(err, service.ErrInvalidPrice):
		paramError(c, "unit_price 必须是正整数分")
	default:
		writeErr(c, err)
	}
}
