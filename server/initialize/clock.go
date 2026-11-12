package initialize

import (
	"sync"
	"time"
)

// DemoClock 是演示教学时钟：只允许整体平移服务端时间，不缩短业务规则中的 10 分钟。
// 测试与线上演示规则一致；偏移量为 0 时即真实服务端时间。
type DemoClock struct {
	mu            sync.RWMutex
	offsetMinutes int
}

func NewDemoClock(offsetMinutes int) *DemoClock {
	return &DemoClock{offsetMinutes: offsetMinutes}
}

func (c *DemoClock) Now() time.Time {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return time.Now().Add(time.Duration(c.offsetMinutes) * time.Minute)
}

func (c *DemoClock) OffsetMinutes() int {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.offsetMinutes
}

func (c *DemoClock) SetOffsetMinutes(minutes int) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.offsetMinutes = minutes
}
