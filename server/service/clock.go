package service

import "time"

// NewOrderServiceWithClock 只注入服务端时间源，用于演示教学时钟与可控的超时关单场景。
// 业务规则（待支付保留 10 分钟、以服务端时间判断）不变；不改动任何既有业务逻辑。
func NewOrderServiceWithClock(repo OrderRepository, now func() time.Time) *OrderService {
	s := NewOrderService(repo)
	if now != nil {
		s.now = now
	}
	return s
}

// ServerTimeForDisplay 只向 controller 暴露当前服务端时间，用于演示时钟核对，不参与业务裁决。
func (s *OrderService) ServerTimeForDisplay() time.Time {
	return s.now()
}
