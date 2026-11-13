# 覆盖率与质量门禁报告

> 项目：shop-trade（题目 01）　版本：dev/01 @ `def0977`（交付版本 v1.8.0）
> 执行时间：2026-11-13　执行方式：`python -X utf8 evidence/quality_gate.py`（真实执行）
> 原始输出：`evidence/quality_gate_output.txt`、`evidence/coverage-gate.out`、`evidence/coverage-gate-func.txt`
> 版本化快照：`evidence/coverage/`（原始 profile、逐函数表、门禁判定与清单，均带版本与提交哈希标注）

## 一、门禁命令与真实结果

| 门禁项 | 命令 | 真实输出 | 结论 |
| --- | --- | --- | --- |
| 格式检查 | `gofmt -l .` | 无任何文件输出，`[exit=0]` | 通过 |
| 静态检查 | `go vet ./...` | 无告警输出，`[exit=0]` | 通过 |
| 编译 | `go build ./...` | `[exit=0]` | 通过 |
| 单元测试 | `go test -count=1 ./...` | 6 个包全部 `ok`，`[exit=0]` | 通过 |
| 覆盖率生成 | `go test -count=1 -coverpkg=./... -coverprofile=coverage-gate.out ./...` | `[exit=0]` | 通过 |
| 竞态检测 | `CGO_ENABLED=1 go test -race ./... -count=1`（WSL Ubuntu + gcc 15.2.0） | 6 个包全部 `ok`，`race_exit=0`，无 `WARNING: DATA RACE` | 通过 |

单元测试真实输出：

```
$ go test -count=1 ./...
ok  	shop-trade	0.990s
ok  	shop-trade/server/api/v1	2.130s
?   	shop-trade/server/global	[no test files]
ok  	shop-trade/server/initialize	0.966s
ok  	shop-trade/server/model	0.406s
ok  	shop-trade/server/router	1.080s
ok  	shop-trade/server/service	1.488s
[exit=0]
```

## 二、覆盖率结果（-coverpkg=./... 口径，按语句数加权）

| 包 | 覆盖率 | 已覆盖/总语句 |
| --- | --- | --- |
| `shop-trade/server/service`（核心业务包） | **98.5%** | 1161 / 1179 |
| `shop-trade/server/api/v1`（接入层） | **99.1%** | 323 / 326 |
| `shop-trade/server/router` | 100.0% | 24 / 24 |
| `shop-trade/server/model` | 100.0% | 3 / 3 |
| `shop-trade/server/initialize` | 90.0% | 27 / 30 |
| `shop-trade`（main 入口） | 64.1% | 25 / 39 |
| **整体** | **97.6%** | **1563 / 1601** |

说明：

- 整体语句覆盖率 97.6%，核心业务包 `server/service` 98.5%，均高于 85% 门禁；
- `server/api/v1` 接入层由 82.2%（268/326）提升到 99.1%（323/326），来源为 `server/api/v1/api_branch_coverage_test.go` 补齐的「身份拒绝 / 请求体非法 / 未知订单 / 未知异常事件 / 越权 / 错误兜底」六类分支；
- `server/global` 无业务语句，仅常量定义，故显示 `[no test files]`；
- 未排除任何自编生产代码；覆盖率原始文件为 `evidence/coverage-gate.out`，逐函数明细为 `evidence/coverage-gate-func.txt`，版本化快照见 `evidence/coverage/`。

## 三、配套的接口级与集成级验证

| 验证 | 脚本 | 真实结果 |
| --- | --- | --- |
| 接口入参与异常分支巡检 | `python -X utf8 evidence/api_validation_probe.py` | 57 条非法入参探针，0 条 HTTP 500、0 条 INTERNAL_ERROR、0 条非 JSON 响应，全部异常分支被显式兜住（`evidence/api_validation_probe.txt`） |
| 业务错误码逐条穷举 | `python -X utf8 scripts/error_code_enumeration.py` | M-01~M-30 共 30 个错误码，27 个被真实业务流程触发（52 条用例全部命中，0 条未命中），剩余 M-07 / M-16 / M-21 经源码核对为仅在 `types.go` 定义、无任何分支引用的文案常量，如实登记不推测（`evidence/error_code_enumeration.txt` / `.json`） |
| 真实 MySQL 持久化与并发 | `python -X utf8 evidence/mysql_app_persistence.py` | 8/8 断言通过；含「应用重启后同一订单仍可查询」「20 并发不超卖、库存守恒」 |
| 唯一键冲突复现 | `evidence/mysql_verify.sh unique` | 三类唯一约束均实测触发 ERROR 1062 |
| Apipost 用例集合重建 | `python -X utf8 scripts/regen_apipost.py` | 按定稿接口清单重建 5 组场景 / 48 个用例，状态保持「未运行」，不产生任何伪造运行结果 |

## 四、结论

- 质量门禁（格式、静态检查、编译、单元测试、竞态检测）全部通过，无失败用例、无数据竞争；
- 覆盖率整体 97.6%、核心业务包 98.5%、接入层 99.1%，满足「整体 ≥85%、各核心业务包 ≥85%」的要求；
- 本报告所有数字均来自上述原始输出文件，可用 `evidence/quality_gate.py`、`scripts/coverage_gate.py`、`scripts/error_code_enumeration.py`、`evidence/api_validation_probe.py` 重新复现。