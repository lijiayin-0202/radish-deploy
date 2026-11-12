package main

import (
	"log"
	"os"
	"strconv"

	"github.com/gin-gonic/gin"

	"shop-trade/server/api/v1"
	"shop-trade/server/initialize"
	"shop-trade/server/model"
	"shop-trade/server/service"
)

func envOr(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}

// buildServer 完成 GVA 风格初始化并返回已注册的 Gin 引擎；与 main 分离便于单元测试覆盖。
func buildServer() (*gin.Engine, string, string, error) {
	addr := envOr("GVA_ADDR", ":8080")
	dsn := os.Getenv("GVA_MYSQL_DSN")
	offset := 0
	if parsed, err := strconv.Atoi(envOr("DEMO_CLOCK_OFFSET_MINUTES", "0")); err == nil {
		offset = parsed
	}
	clock := initialize.NewDemoClock(offset)

	var repo service.OrderRepository
	var goodsLister v1.GoodsLister
	mode := "demo-memory"

	if dsn != "" {
		db, err := initialize.GormMysql(dsn)
		if err != nil {
			return nil, "", "", err
		}
		repo = service.NewGormOrderRepository(db)
		goodsLister = func() ([]model.Goods, error) {
			var goods []model.Goods
			err := db.Find(&goods).Error
			return goods, err
		}
		mode = "mysql-innodb"
	} else {
		// 未配置 DSN 时启用演示模式：可直接启动并演示五组场景，但数据不持久化。
		// 正式验收须配置 GVA_MYSQL_DSN 走 InnoDB 事务 + 行锁，并用 schema.sql 初始化。
		repo = service.NewDemoOrderRepository()
		goodsLister = func() ([]model.Goods, error) {
			return service.DemoGoods(), nil
		}
	}

	svc := service.NewOrderServiceWithClock(repo, clock.Now)
	engine := initialize.Routers(svc, goodsLister, clock, mode)
	return engine, addr, mode, nil
}

func main() {
	engine, addr, mode, err := buildServer()
	if err != nil {
		log.Fatalf("服务初始化失败：%v", err)
	}
	log.Printf("shop-trade 启动 addr=%s mode=%s 健康检查=GET /health", addr, mode)
	if err := engine.Run(addr); err != nil {
		log.Fatalf("服务启动失败：%v", err)
	}
}
