package service

// 竞态检测说明：go test ./... -race 需要 CGO_ENABLED=1 与可用 C 编译器。
// 本文件用 sqlmock 覆盖新增的三个 GORM 仓储方法，不排除自编数据库访问代码。

import (
	"context"
	"errors"
	"testing"

	"github.com/DATA-DOG/go-sqlmock"
)

func TestGormExtensionRepositoryMethods(t *testing.T) {
	e := newMockEnv(t)
	defer e.close(t)
	ctx := context.Background()

	e.mock.ExpectExec("UPDATE").WillReturnResult(sqlmock.NewResult(0, 1))
	if err := e.repo.UpdateGoodsPrice(ctx, 1, 12000); err != nil {
		t.Fatalf("调价更新应成功：%v", err)
	}

	e.mock.ExpectQuery("SELECT").WillReturnRows(goodsRows())
	goods, err := e.repo.ListGoods(ctx)
	if err != nil || len(goods) != 1 || goods[0].GoodsNo != "GOODS-ACT-001" || goods[0].UnitPrice != 10000 {
		t.Fatalf("商品列表不正确：err=%v goods=%+v", err, goods)
	}

	e.mock.ExpectQuery("SELECT").WillReturnRows(paymentRows())
	payments, err := e.repo.ListPaymentsByOrderNo(ctx, "NO-1")
	if err != nil || len(payments) != 1 || payments[0].OrderNo != "NO-1" || payments[0].EventType != EventPaymentSuccess {
		t.Fatalf("逐单流水不正确：err=%v rows=%+v", err, payments)
	}
	if len(e.sqlLog) < 3 {
		t.Fatalf("应产生三条真实 SQL：%v", e.sqlLog)
	}
}

func TestGormExtensionRepositoryErrors(t *testing.T) {
	e := newMockEnv(t)
	defer e.close(t)
	ctx := context.Background()

	e.mock.ExpectExec("UPDATE").WillReturnError(errors.New("update goods failed"))
	if err := e.repo.UpdateGoodsPrice(ctx, 1, 12000); err == nil || err.Error() != "update goods failed" {
		t.Fatalf("期望更新错误，实际 %v", err)
	}
	e.mock.ExpectQuery("SELECT").WillReturnError(errors.New("list goods failed"))
	if _, err := e.repo.ListGoods(ctx); err == nil || err.Error() != "list goods failed" {
		t.Fatalf("期望商品查询错误，实际 %v", err)
	}
	e.mock.ExpectQuery("SELECT").WillReturnError(errors.New("list payments failed"))
	if _, err := e.repo.ListPaymentsByOrderNo(ctx, "NO-1"); err == nil || err.Error() != "list payments failed" {
		t.Fatalf("期望流水查询错误，实际 %v", err)
	}
}
