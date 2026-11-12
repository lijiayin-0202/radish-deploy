package v1

import "github.com/gin-gonic/gin"

// Health 保留 /health 健康检查接口，同时返回当前运行模式便于交付核查。
func Health(c *gin.Context) {
	mode := c.GetString("mode")
	if mode == "" {
		mode = "unknown"
	}
	c.JSON(200, gin.H{"status": "ok", "mode": mode})
}
