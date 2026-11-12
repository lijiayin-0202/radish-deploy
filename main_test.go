package main

// 竞态检测说明：go test ./... -race 需要 CGO_ENABLED=1 与可用 C 编译器。
// PowerShell：$env:CGO_ENABLED = "1"; go test ./... -race -count=1
// bash：CGO_ENABLED=1 go test ./... -race -count=1

import (
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	"github.com/gin-gonic/gin"
)

func TestEnvOr(t *testing.T) {
	const key = "SHOP_TRADE_TEST_KEY"
	defer os.Unsetenv(key)
	os.Unsetenv(key)
	if got := envOr(key, "fallback"); got != "fallback" {
		t.Fatalf("未设置时应返回默认值，实际 %s", got)
	}
	os.Setenv(key, "value")
	if got := envOr(key, "fallback"); got != "value" {
		t.Fatalf("已设置时应返回环境变量，实际 %s", got)
	}
}

func TestBuildServerDemoMode(t *testing.T) {
	gin.SetMode(gin.TestMode)
	oldDSN, hadDSN := os.LookupEnv("GVA_MYSQL_DSN")
	oldAddr, hadAddr := os.LookupEnv("GVA_ADDR")
	defer func() {
		if hadDSN {
			os.Setenv("GVA_MYSQL_DSN", oldDSN)
		} else {
			os.Unsetenv("GVA_MYSQL_DSN")
		}
		if hadAddr {
			os.Setenv("GVA_ADDR", oldAddr)
		} else {
			os.Unsetenv("GVA_ADDR")
		}
	}()
	os.Unsetenv("GVA_MYSQL_DSN")
	os.Setenv("GVA_ADDR", ":18099")

	engine, addr, mode, err := buildServer()
	if err != nil {
		t.Fatal(err)
	}
	if engine == nil || addr != ":18099" || mode != "demo-memory" {
		t.Fatalf("演示模式初始化错误：addr=%s mode=%s", addr, mode)
	}
	w := httptest.NewRecorder()
	engine.ServeHTTP(w, httptest.NewRequest(http.MethodGet, "/health", nil))
	if w.Code != http.StatusOK {
		t.Fatalf("健康检查返回 %d", w.Code)
	}
}

func TestBuildServerRejectsInvalidDSN(t *testing.T) {
	oldDSN, hadDSN := os.LookupEnv("GVA_MYSQL_DSN")
	defer func() {
		if hadDSN {
			os.Setenv("GVA_MYSQL_DSN", oldDSN)
		} else {
			os.Unsetenv("GVA_MYSQL_DSN")
		}
	}()
	os.Setenv("GVA_MYSQL_DSN", "not-a-dsn")
	if _, _, _, err := buildServer(); err == nil {
		t.Fatal("非法 DSN 必须导致初始化失败")
	}
}
