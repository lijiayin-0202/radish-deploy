package initialize

import (
	"gorm.io/driver/mysql"
	"gorm.io/gorm"

	"shop-trade/server/global"
)

// GormMysql 按 GVA 原生方式初始化全局 DB 句柄。
// DSN 只从环境变量 GVA_MYSQL_DSN 读取，不写入仓库、日志或文档。
// 建表口径为 ENGINE=InnoDB / utf8mb4，见 schema.sql；本函数不执行任何 DDL。
func GormMysql(dsn string) (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(dsn), &gorm.Config{})
	if err != nil {
		return nil, err
	}
	global.GVA_DB = db
	return db, nil
}
