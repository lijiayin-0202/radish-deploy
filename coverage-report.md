# 覆盖率报告（开发会话草案，非第 1 轮正式证据）

| 项 | 内容 |
| --- | --- |
| 执行时间 | 2026-11-12 |
| 分支 | `dev/01`（未提交、未推送） |
| 命令 1 | `go test -coverprofile=coverage.out ./server/service/... -count=1` |
| 命令 2 | `go tool cover -func=coverage.out` |
| 命令 3 | `go test -coverpkg=./... -coverprofile=coverage-all.out ./... -count=1` |
| 命令 4 | `go tool cover -func=coverage-all.out` |
| 原始文件 | `coverage.out`、`coverage-all.out` |
| 逐函数原始输出 | 由 `scripts/run-race.ps1` 生成 `coverage-report-raw.txt`、`coverage-all-report-raw.txt` |

## 实测数值

| 口径 | 语句覆盖率 | 门禁 ≥85% |
| --- | --- | --- |
| `server/service`（核心业务包） | **85.3%** | 达标（草案口径） |
| `-coverpkg=./...`（全部自编生产代码） | **85.2%** | 达标（草案口径） |

> 上述数值来自本轮真实执行的 `go test`，但所用夹具是内存仓储 + `sqlmock`，不是真实 MySQL(InnoDB)。
> 正式第 1 轮覆盖率须由测试 Agent 在独立会话、真实数据库环境重新执行并保存原始输出。

## 自编生产代码是否被排除

| 文件 | 是否纳入统计 | 说明 |
| --- | --- | --- |
| `server/service/order_service.go` | 是 | 全部业务逻辑，未排除 |
| `server/service/gorm_repository.go` | 是 | 自编数据库访问代码，`gorm_repository_test.go` 用 `sqlmock` 覆盖，未排除 |
| `server/service/types.go` | 是 | 常量、`BizError`、`fail` 等，未排除 |
| `server/api/v1/health.go` | 是（`-coverpkg=./...`） | 最小健康检查骨架，无业务；当前 0% |
| `server/global/global.go` | 是 | 仅模型基类与 `GVA_DB` 声明，无可执行语句 |
| `server/model/model.go` | 是（`-coverpkg=./...`） | 仅结构体与 `TableName`，当前 0% |

## 覆盖要点

- 库存：20 并发抢 5 件不超卖、库存守恒、取消/关闭各释放一次、重复关闭不多释放、售前退款仅恢复一次、迟到支付退款不二次恢复。
- 状态机：8 状态 4 终态、10 分钟服务端时间、终态迟到支付不改状态、退款审核中/处理中暂停发货、已发货不受理售前退款。
- 幂等：重复支付通知、重复退款通知、渠道交易号跨订单冲突、dedup 唯一键冲突映射 `M-27`/`M-10`。
- 并发裁决：退款申请与发货并发只形成一种合法结果；条件更新 `RowsAffected=0` 只追加重复操作留痕。
- 权限：越权查询/取消/审核/发货/重试均拒绝并留痕。
- 数据访问：`SELECT ... FOR UPDATE` 行锁、`available_stock >= ?`、`occupied_stock >= ?`、`stock_restored = 0` 条件更新、`payment` 只追加无 UPDATE/DELETE、`effective IS NOT NULL` 汇总口径。

## 未达标 / 待补项（交测试 Agent）

1. `go test -race` 本机未启动（见 `race-output.txt`），门禁未通过。
2. `server/api/v1/health.go`、`server/model/model.go` 无专门单测，虽被纳入统计但覆盖率为 0%。
3. 部分 `if err != nil` 技术错误分支、并发下 `RowsAffected=0` 的真实数据库路径，须在真实 MySQL(InnoDB) 环境补测。
4. 草案不得冒充 PR 门禁证据；三轮验证顺序仍为：第 1 轮单测 + race → 第 2 轮 Apipost → 第 3 轮浏览器页面验收。
