package model

// 竞态检测说明：go test ./... -race 需要 CGO_ENABLED=1 与可用 C 编译器。
// PowerShell：$env:CGO_ENABLED = "1"; go test ./... -race -count=1
// bash：CGO_ENABLED=1 go test ./... -race -count=1

import "testing"

func TestTableNames(t *testing.T) {
	if (Goods{}).TableName() != "goods" {
		t.Fatal("goods 表名错误")
	}
	if (Order{}).TableName() != "order" {
		t.Fatal("order 表名错误（MySQL 保留字由 GORM 反引号转义）")
	}
	if (Payment{}).TableName() != "payment" {
		t.Fatal("payment 表名错误")
	}
}
