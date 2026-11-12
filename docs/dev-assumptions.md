# shop-trade 本轮开发新增假设记录

| 编号 | 假设 | 授权来源 | 影响范围 | 备注 |
| --- | --- | --- | --- | --- |
| A-DEV-01 | Go module 名使用 `shop-trade` | 本轮问答「授权最小骨架」 | `go.mod`、所有 Go import | 工作区原无 `go.mod`，此为本轮新增假设 |
| A-DEV-02 | 创建最小 GVA 风格目录 `server/global/`、`server/model/`、`server/service/`、`server/api/v1/` | 本轮问答「授权最小骨架」 | 骨架文件 | 仅创建最小声明，不修改既有 GVA 底层框架代码；`global` 只放 `GVA_MODEL` 与 `GVA_DB` |
| A-DEV-03 | GVA 模型基类命名为 `global.GVA_MODEL`，全局 DB 句柄命名为 `global.GVA_DB` | 本轮问答「授权最小骨架」 | `server/global/global.go`、model/service | 原仓库无具体标识符，此为本轮新增假设 |
| A-DEV-04 | 本轮仅建 `goods`、`order`、`payment` 三张业务表 | 用户在任务 2 明确指定 | `schema.sql`、`model.go` | 为满足「审计流水只追加、异常记录不消失、支付/退款流水可查」，`payment` 表同时承载支付通知处理结果、异常支付待处理、退款回调与审计事件；不新增购物车、订单项、售后、部分退款表 |
| A-DEV-05 | `payment.dedup_key` 与 `(channel_trade_no, effective)` 共同承担有效渠道交易号唯一约束 | 根据需求 R-15/R-16 与幂等要求推导 | `schema.sql`、service | 有效记款/退款记录写入非空 `effective` 与唯一 `dedup_key`；重复通知/拒绝/审计事件写入 `effective = NULL`，只追加、不修改、不删除 |
| A-DEV-06 | 接口清单不存在，按本轮 service 方法推导为「待确认接口清单草案」 | 本轮问答「授权按 service 推导」 | `docs/interface-list-draft.md`、Apipost 用例草案 | 不生成 API/Router 代码；接口路径、请求体、响应体均为新增假设，须由学生后续定稿 |
| A-DEV-07 | 当前会话生成的单元测试与 Apipost 用例仅为草案 | 本轮问答「授权草案」 | `server/service/*_test.go`、`apipost-*` | 明确不得作为正式三轮验证证据；正式第 1/2/3 轮证据须由独立测试 Agent / 验收 Agent 会话产出 |
| A-DEV-08 | 本地无 Go/GVA 真实骨架、无真实 MySQL(InnoDB) 测试库、无可控 HTTP 模拟渠道服务实例 | 环境核查 + 用户授权草案 | 单测与 Apipost 草案 | 单元测试用内存仓储与 sqlmock 覆盖逻辑/SQL 语句；并发超卖草案不作为正式并发证据，正式验证须使用 MySQL(InnoDB) 事务 + 行锁 |
| A-DEV-09 | 本机 `CGO_ENABLED=0` 且无 `gcc` | `go env` / `gcc --version` 实际输出 | `scripts/run-race.ps1`、`race-output.txt` | `go test -race` 命令已生成并尝试执行，但本机无法产出正式 race 证据；测试 Agent 需在具备 CGO/C 编译器与 MySQL 的环境重跑 |
| A-DEV-10 | `AGENTS.md` v1.0 的 Q-01 旧数据库技术栈与 `.agent` MySQL 冲突 | 本轮问答「授权修复并初始化」 | `AGENTS.md`、`AGENTS-v1.0.md` | 以 `.agent` 的 MySQL(InnoDB) 为准同步修正 Q-01；v1.0 原文已备份；本轮不提交、不推送、不改 main |
| A-DEV-11 | 工作区原非 Git 仓库，本轮初始化本地 Git 并创建 `dev/01` 分支 | 本轮问答「授权修复并初始化」 | `.git/HEAD` | 不提交、不推送、不创建远端；提交前仍须完成 meegle 编号核验 |
| A-DEV-12 | 演示教学时钟保持默认 10 分钟服务端时间 | 需求文档 C-08 | `OrderService.timeout` | 未缩短；若测试/演示需缩短，必须另行记录并注明测试与线上演示规则一致 |
| A-DEV-13 | 重复通知与重复人工操作采用不同返回口径 | 题面规则 3、7、8 与原型 M-10/M-19/M-25 推导 | `order_service.go` 的 `noopPayment` / `duplicateRejectPayment` | 渠道回调重复以 nil error 幂等成功响应（避免模拟渠道持续重推）；人为重复取消/发货/核实/发起以 `BizError` 返回 M-10/M-19 并仍提交只追加审计 |
| A-DEV-14 | 草案覆盖率按「不排除自编生产代码」两种口径统计 | `.agent/05`、`AGENTS.md` Q-02 | `coverage.out`、`coverage-all.out`、`coverage-report.md` | `go test -coverprofile` 得 service 85.3%；`go test -coverpkg=./...` 得整体 85.2%；`gorm_repository.go` 由 `sqlmock` 覆盖，未排除自编数据库访问代码；数值仅为草案，正式门禁须测试 Agent 在真实 MySQL 环境重跑 |
| A-DEV-15 | Apipost 集合为自定义用例草案结构，不是官方导出格式 | 本轮问答「授权草案」 | `apipost-collection.json` | 字段为可读草案结构；导入前须按实际 Apipost 导出格式转换，并在接口清单经学生确认后定稿；未生成 `apipost-run-export.json` |
| A-DEV-16 | `go.mod` 补齐 `go-sqlmock` 与 `gorm.io/driver/mysql` | 草案单测编译所需 | `go.mod`、`go.sum` | 二者为测试/驱动依赖，不引入题外组件；`go mod tidy` 曾移除未引用依赖，本轮重新补齐 |

> 本记录只说明本轮开发必需的新增假设，不覆盖题面、需求文档、原型文档、任务规划文档及 `.agent` 规则。所有题外功能（购物车、一单多商品、部分退款、售后退货、真实支付/物流）均未实现。
