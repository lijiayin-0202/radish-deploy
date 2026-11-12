package global

import (
	"time"

	"gorm.io/gorm"
)

// GVA_MODEL 是用户授权创建的最小 GVA 风格模型基类。
// 注意：本文件属于新增最小骨架声明，不含业务逻辑；不修改任何既有 GVA 底层框架代码。
type GVA_MODEL struct {
	ID        uint           `gorm:"primarykey;column:id"`
	CreatedAt time.Time      `gorm:"column:created_at;type:datetime(3);not null"`
	UpdatedAt time.Time      `gorm:"column:updated_at;type:datetime(3);not null"`
	DeletedAt gorm.DeletedAt `gorm:"column:deleted_at;type:datetime(3);index"`
}

// GVA_DB 是最小 GVA 风格全局 DB 句柄假设。
// 实际连接由既有 GVA initialize 层注入；本轮不实现、不修改底层初始化代码。
var GVA_DB *gorm.DB
