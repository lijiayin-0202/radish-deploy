# 测试报告（整改后 · 开发会话草稿，不是第 1 轮正式证据）

| 项 | 内容 |
| --- | --- |
| 项目 | `shop-trade` 题目 01 小型电商订单交易、发货与售前退款 |
| 技术栈 | GVA 单体 + Gin + GORM + MySQL(InnoDB) |
| 分支 | `dev/01`（本地首次提交已建立有效 HEAD；无远端，未推送 `main`） |
| 会话角色 | 开发 Agent（本文件为**开发草稿**；正式第 1 轮报告须由独立测试 Agent 会话重写） |
| 执行时间 | 2026-11-12 |

> **声明边界**：本文件只能支持「开发草稿完成」声明，不能支持「门禁验收通过」声明。详见 `docs/完成声明边界.md`。

## 1. 【草稿覆盖率】与【真实环境覆盖率】的严格区分

| 口径 | 定义 | 本次数值 | 是否可作为正式验收证据 |
| --- | --- | --- | --- |
| **草稿覆盖率** | 本机开发会话执行 `go test`，仓储为 `sqlmock` 或演示内存仓储；`CGO_ENABLED=0`，未连真实 MySQL(InnoDB)，未跑 race | 核心业务包 `server/service` **87.7%**；`-coverpkg ./...` 整体 **86.0%** | **否**。仅用于开发自检，证明测试代码本身能跑通、未排除自编 DAO/HTTP 代码 |
| **真实环境覆盖率** | 独立测试 Agent 会话，在 `CGO_ENABLED=1` + gcc/clang + 真实 MySQL(InnoDB) 测试库 + 可控模拟渠道 + 绑定最终提交哈希的环境重新执行全部命令 | **尚未产生** | 是，但必须附原始输出、退出码、`coverage.out`、`race-output-raw.txt` 与版本对应关系 |
| **禁止混淆** | 不得把草稿数值写成「验收覆盖率 ≥85% 已通过」，不得用内存仓储的并发结果替代 InnoDB 行锁证据，不得把 `go test -race` 未启动写成通过 | — | 违反即为编造证据 |

草稿数值虽然 ≥85%，但**不解除 PR 门禁**；门禁以真实环境证据为准。

## 2. 可直接执行的测试命令

```powershell
# 进入项目根目录
cd d:/Desktop/shop

# ① 格式与静态检查
gofmt -l .
go vet ./...

# ② 单元测试（草稿口径）
go test ./... -count=1

# ③ 覆盖率（核心业务包 + 全量自编生产代码两种口径）
#    注意：本机 Windows PowerShell 下 "-flag=xxx.out" 会被错误分词，
#    覆盖率参数一律使用空格形式，已实测可正常生成 coverage 文件。
go test -coverprofile coverage.out ./server/service/... -count=1
go tool cover -func coverage.out
go test -coverpkg ./... -coverprofile coverage-all.out ./... -count=1
go tool cover -func coverage-all.out

# ④ 竞态检测：环境开启 CGO 后可直接执行
#    -race 需要 CGO_ENABLED=1 与可用 C 编译器（gcc/clang）
$env:CGO_ENABLED = "1"
go test ./... -race -count=1
go test ./... -race -coverprofile coverage-race.out -count=1
```

```bash
# Linux / macOS 或 WSL 等价命令
CGO_ENABLED=1 go test ./... -race -count=1
```

一键脚本：`scripts/run-race.ps1`（会先检查 `CGO_ENABLED`，不满足时如实记录阻塞而不伪造通过结论）。
所有单元测试文件头部均标注了 `-race` 需要 `CGO_ENABLED=1` 与上述开启命令。

## 3. 实际执行的命令与结果（2026-11-12，本机）

| 命令 | 结果 |
| --- | --- |
| `gofmt -l .` | 无输出，exit=0 |
| `go vet ./...` | exit=0，无输出 |
| `go build ./...` | exit=0 |
| `go build -o <二进制> .` | exit=0，产出可执行二进制（15,395,328 字节） |
| **`go run main.go`（直接启动）** | exit 正常；`GET /health` → `{"mode":"demo-memory","status":"ok"}`；`GET /api/v1/me`（`X-Demo-Account: buyer01`）→ `{"code":"0","message":"ok","data":{...}}`；原始输出 `evidence/go-run-main-output.txt`、启动日志 `evidence/go-run-stderr.txt`、Gin 路由注册输出 `evidence/go-run-stdout.txt` |
| `go test ./... -count=1` | 7 个包全部 ok，exit=0（含 `main`、`api/v1`、`router`、`initialize`、`model`） |
| `go test -coverprofile coverage.out ./server/service/... -count=1` | ok，**87.7%**（草稿口径） |
| `go test -coverpkg ./... -coverprofile coverage-all.out ./... -count=1` | ok，`go tool cover -func coverage-all.out` → total **86.0%**（草稿口径） |
| `go test ./server/service/... -race -count=1` | **未启动**：`CGO_ENABLED=0` → `-race requires cgo; enable cgo by setting CGO_ENABLED=1`，exit=2（见 `race-output.txt` 与 `evidence/final-verification-output.txt`） |
| `apipost-collection.json` JSON 解析 | `json_ok`，5 组场景，`source_interface_list = docs/interface-list.md v1.0` |
| `scripts/demo-five-scenarios.ps1` | 默认端口已对齐定稿 `8080`；五组场景 HTTP 接口全部可从头到尾调用，关键 `M-09/M-08/M-22/M-19/M-10/M-28/M-29/M-30` 拒绝原因正确；原始输出 `evidence/demo-five-scenarios-output.txt`（开发草稿演示，非第 2 轮证据） |

完整原始输出：`evidence/final-verification-output.txt`（含 exit code 与 race 失败原文）；中间产物 `evidence/verification-output.txt`、`evidence/verification-coverage-output.txt` 保留了 PowerShell 参数分词失败的第一次尝试与修正后重跑结果，未删除失败记录。

## 4. 单元测试清单

| 文件 | 主要用例 |
| --- | --- |
| `server/service/order_service_test.go` | 下单校验、支付幂等/验签/金额/未知订单、取消与超时关单、退款失败重试成功、退款发货竞争、迟到支付不二次恢复、20 并发抢 5 件 |
| `server/service/order_service_branches_test.go` | 退款回调全分支、迟到支付核实/发起/回调/重试、运营汇总 9 个仓储错误分支、dedup 冲突映射、重复操作拒绝 |
| `server/service/gorm_repository_test.go` | `sqlmock` 覆盖 25 个仓储方法：事务、行锁 SQL、库存条件更新、只追加审计、聚合口径、错误传播 |
| `server/service/memory_repository_test.go` | 演示仓储基线、幂等冲突、`applyOrderFields`/`timeField` 分支、聚合与过期列表；夹具已提升为生产文件 `demo_repository.go` |
| `server/api/v1/order_api_test.go` | `httptest` 覆盖全部 controller：身份验证、商品、下单/支付/状态/发货、售前退款、迟到支付、并发竞争、越权、参数错误、视图 nil 分支 |
| `server/router/order_router_test.go` | 核对 21 条必需路由全部注册 |
| `server/initialize/router_test.go` | 全局路由与健康检查、演示时钟偏移、非法 DSN 错误分支 |
| `server/model/model_test.go` | `goods` / `order` / `payment` 表名 |
| `main_test.go` | `envOr`、演示模式构建、非法 DSN 初始化失败 |

## 5. 发现与修正记录（开发 Agent 自检，非测试 Agent 缺陷闭环）

| 编号 | 现象 | 修正 | 复测 |
| --- | --- | --- | --- |
| D-01 | `go vet` 恒假断言 `suspect and` | 改为校验并发裁决只产生一种合法状态 | `go vet ./...` 无输出 |
| D-02 | 重复取消/发货返回 nil，调用方看不到 M-10/M-19 | 新增 `duplicateRejectPayment`，渠道回调重复仍幂等成功 | 相关用例通过 |
| D-03 | 仓储 0% 覆盖、整体仅 59.6% | 新增 `sqlmock` 与分支测试，未排除自编代码 | 87.7% / 86.0% |
| D-04 | `go.mod` 缺 `go-sqlmock`、`gorm.io/driver/mysql` | 补依赖 | 编译通过 |
| D-05 | 整改新增 controller/router/main 导致整体覆盖率一度降到 66.4% | 新增 5 个包的单元测试，并补 controller 响应视图 | 整体回到 86.0% |
| D-06 | 迟到支付 `M-09` 响应未携带异常事件 ID，客服无法核实 | `writeErr` 支持携带同事务提交的审计记录，响应 `data.event_id` | `TestAPIScenarioS4LatePayment` 通过 |
| D-07 | 本机 Windows PowerShell 把 `-coverprofile=coverage.out`、`-func=coverage.out` 错误分词，产生 `no required module provides package .out` 与 `too many arguments` | 覆盖率参数改用空格形式 `-coverprofile coverage.out` / `-func coverage.out` / `-coverpkg ./...`，并把可直接执行命令写入第 2 节 | 87.7% / 86.0% 重跑成功，原始输出已保留 |
| D-08 | 五组场景脚本默认 `18080` 与定稿接口清单 `8080` 不一致 | 脚本默认值与注释改为 `8080`，保留 `-BaseUrl` 覆盖能力；BOM 校验通过 | 五组场景 HTTP 演示全部通过 |

## 6. 五组场景覆盖与证据状态

| 场景 | 开发草稿覆盖 | 正式证据状态 |
| --- | --- | --- |
| `TST-S1` 活动正常成交 | 单测 + HTTP 演示（下单→支付→状态→发货→重复发货 M-19→汇总） | 待测试 Agent 执行第 2 轮 |
| `TST-S2` 缺货与弃单 | 20 次抢单/库存守恒单测 + HTTP 演示（成功 3、被拒 17、取消释放一次） | 待真实 MySQL(InnoDB) 20 并发 + race |
| `TST-S3` 售前退款 | 首次渠道失败、重试、成功、仅恢复一次 + HTTP 演示 | 待测试 Agent 执行 |
| `TST-S4` 迟到支付 | 终态不变、异常登记、核实、退款、不二次恢复 + HTTP 演示（演示时钟 +11 分钟） | 待测试 Agent 执行 |
| `TST-S5` 操作竞争 | 退款发货竞争、重复支付/退款通知、越权与改编号无效 + HTTP 演示 | 待 `go test -race` 正式证据 |

## 7. 阻塞项与交接

1. **race 门禁条件已就绪，但本机未通过**：`CGO_ENABLED=0` 且无 gcc/clang；命令、脚本与注释均已给出，需在开启 CGO 的环境执行 `go test ./... -race` 并保存 `race-output-raw.txt`。在此之前第 1 轮门禁仍为未通过。
2. 无真实 MySQL(InnoDB) 测试库：草稿覆盖率与内存仓储并发结果不得替代正式持久化/行锁证据。
3. 接口清单已定稿为 `docs/interface-list.md` v1.0，`api/v1` 与路由已实现，Apipost 48 用例已基于定稿重建；但** Apipost 未运行**，无 `apipost-run-export.json`。
4. 三轮验证顺序不可跳过：第 1 轮单测 + race → 第 2 轮 Apipost → 第 3 轮浏览器页面验收（验收 Agent 独立会话）。
5. `feat` / `fix` 提交前须完成 meegle 编号核验并保留原始输出，见 `evidence/交付证据说明.md`；本机 `meegle` 不可用，当前未核验。
6. 开发、测试、验收三方会话导出与结构化事件清单尚未建立，见 `evidence/会话导出说明.md`、`evidence/事件清单说明.md`。

## 8. 证据位置

`coverage.out`、`coverage-all.out`、`coverage-report.md`、`gofmt-vet-output.txt`、`race-output.txt`、`scripts/run-race.ps1`、`scripts/demo-five-scenarios.ps1`、`evidence/final-verification-output.txt`、`evidence/go-run-main-output.txt`、`evidence/go-run-stdout.txt`、`evidence/go-run-stderr.txt`、`evidence/demo-five-scenarios-output.txt`、`evidence/verification-output.txt`、`evidence/verification-coverage-output.txt`、`apipost-run-summary.md`、`skill-usage.md`、`docs/完成声明边界.md`、`docs/git-提交指引.md`、`evidence/交付证据说明.md`。
