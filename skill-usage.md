# Skill 使用记录与六类说明（shop-trade 题目 01）

| 项 | 内容 |
| --- | --- |
| 项目 | `shop-trade` 题目 01 小型电商订单交易、发货与售前退款 |
| 分支 | `dev/01`（本地首次提交，无远端） |
| 依据 | 原始题面共同要求第 3/8/9 节、任务规划文档 `SKILL-01~03`、`DOC-03`、`.agent/06-workflow-devflow.md` 第 7 章 `K-01~K-05`、根目录 `AGENTS.md` |
| 文件性质 | 开发 Agent 会话记录；**只记录真实调用，不把草案写成正式验证证据** |
| 记录时间 | 2026-11-12 |

> 六类说明＝**技能用途 / 触发条件 / 输入 / 输出产物 / 验收检查点 / 禁用场景**。下表按 `.agent/06` 的 `K-03` 与任务规划 `SKILL-03` 逐项填写来源版本、使用位置、原因、过程、实际帮助、证据及局限。
> 本文件不代替三轮验证证据，不构成「验收通过」声明，边界见 `docs/完成声明边界.md`。

## 1. 自编 Skill ① `gva-model-generate`

| 项 | 内容 |
| --- | --- |
| 名称 / 来源 / 版本 | `gva-model-generate`／本项目自编／v1.0（`.codebuddy/skills/gva-model-generate/SKILL.md`） |
| 使用位置与原因 | `DB-01/DB-02` 阶段需要题目 01 三张业务表的 GORM 模型与 DDL；用于把 `ENGINE=InnoDB`、`utf8mb4`、整数「分」、单商品订单、审计只追加固化到结构定义 |
| **① 技能用途** | 只产出 `server/model/model.go` 与 `schema.sql`；为 `server/service/` 事务代码提供可持久化数据结构；不写业务规则 |
| **② 触发条件** | 用户要求生成/核对 GVA GORM 模型、建表 SQL、`model.go`、`schema.sql`；或要求核对模型是否满足题目 01 边界与 MySQL(InnoDB) 口径 |
| **③ 输入** | 原始题面、需求文档 v1.0、原型文档 v1.0、任务规划 v1.1、`.agent/01~06`、`AGENTS.md`、经学生确认的表清单/字段口径/版本号与编号、`dev/01` 对应代码版本 |
| **④ 输出产物** | `schema.sql`（`goods`、`` `order` ``、`payment`，`ENGINE=InnoDB DEFAULT CHARSET=utf8mb4`，`uk_payment_dedup_key`、`uk_payment_channel_effective`、`idx_order_status_expires`）；`server/model/model.go`（`Goods`/`Order`/`Payment`，`func (Order) TableName() string { return "order" }`） |
| **⑤ 验收检查点** | 建表引擎与字符集正确；金额为整数分；`order` 保留字加反引号；渠道交易号幂等唯一键存在；状态/商品/买家/库存更新条件命中索引；无购物车、多商品一单、部分退款表；无 PostgreSQL/PG 残留；模型标签与 SQL 一致 |
| **⑥ 禁用场景** | 生成 service 业务代码、接口定义、Apipost 用例、单测、页面、部署脚本；生成题外业务表；修改 GVA 脚手架底层目录；改写测试/验收 Agent 交付物；技术栈换成 Kratos / Kafka / pgvector / PostgreSQL |
| 实际帮助 / 局限 | 帮助：一次性固定三表口径并避免旧数据库方言混入。**局限**：只产出结构，不证明持久化与行锁在实际 MySQL 上行为正确；本机未连真实 MySQL(InnoDB)，正式证据待测试 Agent |

## 2. 自编 Skill ② `unit-test-race`

| 项 | 内容 |
| --- | --- |
| 名称 / 来源 / 版本 | `unit-test-race`／本项目自编／v1.0（`.codebuddy/skills/unit-test-race/SKILL.md`） |
| 使用位置与原因 | `TST-01~08`、`TST-S1~S5` 第 1 轮；需要库存扣减、订单状态流转、退款幂等与并发验证的可重复用例 |
| **① 技能用途** | 生成 `server/service/` 的 `_test.go`、20 并发抢单验证、`gofmt`/`go vet`/覆盖率原始输出与 `go test -race` 脚本；校验库存守恒、终态不可逆、迟到支付不恢复订单 |
| **② 触发条件** | 用户要求 service 层单测、并发验证、`-race` 原始输出、覆盖率 ≥85% 门禁，或要求执行第 1 轮验证 |
| **③ 输入** | 上游四份文档与 `.agent/01~06`、`AGENTS.md`、`server/service/` 对应版本源码、`model.go`、`schema.sql`、接口清单、测试计划、提交哈希与缺陷清单、**已配置的真实 MySQL(InnoDB) 测试库**与可控模拟渠道 |
| **④ 输出产物** | `server/service/order_service_test.go`、`order_service_branches_test.go`、`gorm_repository_test.go`、`memory_repository_test.go`；整改后另含 `server/api/v1/order_api_test.go`、`server/router/order_router_test.go`、`server/initialize/router_test.go`、`server/model/model_test.go`、`main_test.go`；`scripts/run-race.ps1`、`coverage.out`、`coverage-all.out`、`coverage-report.md`、`gofmt-vet-output.txt`、`race-output.txt`、`test-report.md` |
| **⑤ 验收检查点** | 整体与核心业务包覆盖率分别 ≥85%；`go test -race` 在 `CGO_ENABLED=1` 环境无数据竞争报告；`gofmt -l .` 无输出；`go vet ./...` exit=0；五组场景各有独立测试与原始输出；未删除失败 case、未弱化断言、未排除自编 DAO/HTTP 代码 |
| **⑥ 禁用场景** | 生成 `model.go`/`schema.sql`/业务接口/Apipost 用例/页面；执行第 2、3 轮；用内存仓储或 `sqlmock` 结果冒充真实 InnoDB 行锁与 race 证据；把 `CGO_ENABLED=0` 环境下未启动的 race 写成通过；替开发 Agent 修生产代码 |
| 实际帮助 / 局限 | 帮助：服务包 87.7%、`-coverpkg=./...` 整体 86.0%（**草稿口径**），并暴露了仓储 0% 覆盖与重复操作拒绝问题。**局限**：本机 `CGO_ENABLED=0`、无 gcc/clang，`go test -race` 未启动；覆盖率来自 `sqlmock` + 演示内存仓储，不是第 1 轮正式证据 |

## 3. 自编 Skill ③ `apipost-case-gen`

| 项 | 内容 |
| --- | --- |
| 名称 / 来源 / 版本 | `apipost-case-gen`／本项目自编／v1.0（`.codebuddy/skills/apipost-case-gen/SKILL.md`） |
| 使用位置与原因 | 第 2 轮接口自动化准备；需把 `docs/interface-list.md` v1.0（定稿）的 `API-01~API-20` 映射为五组场景用例 |
| **① 技能用途** | 生成 Apipost 用例集合、用例清单、断言矩阵与运行摘要；覆盖 `TST-S1~S5`、正常/异常路径、20 并发抢单、重复通知、迟到支付、退款发货竞争与越权 |
| **② 触发条件** | 用户要求基于**已确认/已定稿**的接口清单生成 Apipost 用例、断言或运行导出；且第 1 轮门禁已通过 |
| **③ 输入** | 上游四份文档与 `.agent/01~06`、`AGENTS.md`、**定稿接口清单**（路径/方法/请求/响应/鉴权/角色/`M-xx`）、`dev/01` 提交哈希、第 1 轮通过记录、可控模拟渠道入口与演示数据基线 |
| **④ 输出产物** | `apipost-collection.json`（5 场景 / 48 用例，来源标记 `docs/interface-list.md` v1.0）、`apipost-case-list.md`、`apipost-assertion-matrix.md`、`apipost-run-summary.md`；重建脚本 `scripts/regen_apipost.py` |
| **⑤ 验收检查点** | 用例全部来源定稿清单而非 `interface-list-draft.md`；每个 `M-xx` 有断言；五组场景端到端链路完整；headers 统一 `X-Demo-Account`；Apipost 真实运行并导出 `apipost-run-export.json`、有通过/失败数与运行标识 |
| **⑥ 禁用场景** | 接口清单未定稿时编造路径与响应；生成 `model.go`/SQL/service/单测；执行第 1、3 轮；把未运行的集合写成「第 2 轮通过」；把可控模拟渠道宣称为真实第三方接入 |
| 实际帮助 / 局限 | 帮助：整改后已基于定稿清单重建 48 用例，消除「用例依据未定稿草案」问题。**局限**：集合为自拟 JSON、需在 Apipost 按实际导出格式转换；**未运行**，无 `apipost-run-export.json`，且第 1 轮 race 未通过，按三轮顺序不得开始第 2 轮 |

## 3.1 自编 Skill ④ `acceptance-check`（补齐 `K-02` 验收检查缺口）

| 项 | 内容 |
| --- | --- |
| 名称 / 来源 / 版本 | `acceptance-check`／本项目自编／v1.0（`.codebuddy/skills/acceptance-check/SKILL.md`） |
| 使用位置与原因 | 第二轮门禁复核报告 `R-B3-01` 判定「3 个自编 Skill 均为生成/测试类，尚无验收检查 Skill」；用户整改指令明确要求新增本 Skill，补齐 `.agent/06` `K-02` 的缺口 |
| **① 技能用途** | 依据原始题面、`AC-01~AC-25`、五组场景、`M-01~M-30`、`V-01~V-08` **只读核对最终交付版本**；核对三轮验证证据、PR 门禁与版本对应；把未通过项分为代码/产物缺陷、环境/权限缺失、过程证据缺失三类 |
| **② 触发条件** | 用户要求验收、逐项核对题面、PR 前门禁核验、`ACC-01~05`、区分代码缺陷与环境限制；或拿到检查报告需要复核整改是否落地 |
| **③ 输入** | 原始题面与三份上游文档、`AGENTS.md` 与 `.agent/01~06`、`commit-convention.md`、对应版本代码与 `git rev-parse HEAD`、接口清单定稿、测试 Agent 全部证据、开发交付清单、Skill 与 AI 过程记录、PR/部署/视频凭据、已知环境约束清单 |
| **④ 输出产物** | 逐项核查矩阵（编号/核查项/依据/实际证据/结论/归属分类/缺口与复验条件）、版本对应链表、三类问题汇总表、未运行/未访问/未播放清单、PR 门禁核验清单与证据索引；写入 `outputs/单题检查/.../` 由验收 Agent 独立会话引用 |
| **⑤ 验收检查点** | 每个适用必做项都有「通过/不通过」结论、证据位置与版本对应；`gofmt`/`go vet`/`go build`/单测/覆盖率/可运行入口/五组场景有原始输出与退出码；环境缺失与代码缺陷严格分离；`-race requires cgo`、无 MySQL、无 meegle 权限不得写成代码错误或写成通过；未运行/未访问/未播放项全部列出；无任何伪造的测试、覆盖率、PR、CI、部署或视频记录 |
| **⑥ 禁用场景** | 生成 `model.go`/SQL/service/单测/Apipost 用例/页面/部署脚本；修改生产或测试代码、替开发/测试 Agent 修复缺陷；执行或伪造 race、真实 MySQL、meegle 核验、CI/CD、部署与视频证据；无原始输出时给出「验收通过/可合并/已上线」结论；把说明文档当成会话导出或验收报告本体 |
| 实际帮助 / 局限 | 帮助：提供题面级只读核查与三类问题分类口径，避免把环境阻塞误判为代码缺陷。**局限**：本轮为文件级交付并按其检查清单做了整改产物自检，**未通过工具加载、未由验收 Agent 独立会话执行**；不冒充原过程调用，也不替代三轮验证 |

## 4. 插件 / 内置 Skill（非自编，不计入 `K-02` 计数）

| Skill | 来源 | 实际触发与用途 | 输出 / 局限 |
| --- | --- | --- | --- |
| `skill-creator`、`writing-skills` | 插件市场 | 创建 `.codebuddy/skills` 目录与 3 个自编 Skill，约束 YAML 元数据与章节结构 | 3 份 `SKILL.md`；只负责技能编写，不产出业务代码 |
| `student-project-audit` | 插件市场 | 用户「帮我检查」时按题面/rubric/checklist 审计单题产出物 | `outputs/单题检查/shop-trade/01/20261112-01/` 下检查报告、两份 CSV、`score.json`（3.23/10，不合格）与证据索引；该报告是本轮整改的输入 |
| `brainstorming`、`test-driven-development`、`verification-before-completion` | 插件市场 | 一次性开发任务前识别前置阻塞、约束测试先行与完成前核验 | `docs/dev-assumptions.md`、`A-DEV-01~16`、验证原始输出；未替代独立测试 Agent |

## 5. 实际调用记录（只列真实发生）

| 时间 | Skill | 调用目的与使用位置 | 产出位置 | 证据状态 |
| --- | --- | --- | --- | --- |
| 2026-11-12 | `skill-creator` / `writing-skills` | 初始化 3 个自编 Skill 目录 | `.codebuddy/skills/*/SKILL.md` | 已生成 |
| 2026-11-12 | `gva-model-generate` | 生成 MySQL(InnoDB) DDL 与 GVA GORM model | `schema.sql`、`server/model/model.go` | 已调用；正式持久化证据待真实 MySQL |
| 2026-11-12 | `unit-test-race` | 生成 service 单测、分支测试、`sqlmock` 仓储测试、race 脚本、覆盖率草案 | `server/service/*_test.go`、`scripts/run-race.ps1`、`coverage*.out`、`test-report.md` | 草案；`-race` 未启动 |
| 2026-11-12 | `apipost-case-gen`（第一次） | 基于 `interface-list-draft.md` 草案生成用例 | `apipost-*` | 草案，已被定稿版本取代 |
| 2026-11-12 | `brainstorming` / `test-driven-development` / `verification-before-completion` | 识别前置阻塞并约束完成前验证 | `docs/dev-assumptions.md`、核查输出 | 已加载执行 |
| 2026-11-12 | `student-project-audit` | 单题检查，输出评分与缺陷清单 | `outputs/单题检查/shop-trade/01/20261112-01/` | 已执行，3.23/10 不合格 |
| 2026-11-12 | `unit-test-race`（整改重新加载） | 补齐 controller/router/main 单测、CGO 与 race 命令注释、覆盖率口径区分 | `main_test.go`、`server/api/v1/order_api_test.go`、`test-report.md` | 草稿 87.7% / 86.0%；非正式证据 |
| 2026-11-12 | `apipost-case-gen`（整改重新加载） | 基于 `docs/interface-list.md` v1.0 定稿重建 48 用例 | `scripts/regen_apipost.py`、`apipost-collection.json` 等 | 已重建；**未运行 Apipost** |
| 2026-11-12 | `student-project-audit`（第二轮） | 对整改后 `dev/01` 做第二轮门禁复核，识别代码缺陷与环境缺失项 | `outputs/单题检查/shop-trade/01/20261112-02/` | 已执行，5.38/10 不合格；本轮整改输入 |
| 2026-11-12 | `acceptance-check`（本轮新增） | 依据第二轮报告 `R-B3-01` 补齐验收检查 Skill；整改验证阶段按其检查清单只读复核新增产物与原有接口 | `.codebuddy/skills/acceptance-check/SKILL.md`、本文件第 3.1 节、`docs/代码产物补齐说明.md` | 文件级交付与清单核对；**未通过工具加载、未由验收 Agent 独立会话执行**，不冒充原过程调用 |

## 6. Skill 检查 → 修正 → 复检闭环（`K-04`）

| 阶段 | 真实情况 |
| --- | --- |
| 检查发现问题 | 第一轮 `student-project-audit` 的 `E-017/E-018` 与检查报告 `B3`：`skill-usage.md` 缺六项说明、缺验收检查 Skill、缺闭环记录；第二轮报告 `R-B3-01` 再次判定「尚无验收检查 Skill」 |
| 学生指导修正 | 用户第一轮整改指令要求「补全 `skill-usage.md` 六类说明」；第二轮整改指令要求「新增【验收检查Skill】，放到 skills 目录，在 skill-usage.md 补充 6 类说明」（C-08 授权）；本文件与第 3.1 节即修正产物 |
| 复检 | **尚未由验收 Agent 独立会话完成**。本轮只在开发会话按 `acceptance-check` 检查清单做了产物自检，不自行判定闭环通过；复检须读取题面条款、本文件与对应提交哈希后给出逐项结论 |
| 未编造声明 | 不把「文件已补齐」写成 `K-04` 闭环已通过；不把未通过工具加载、未在独立会话触发的 Skill 写成已正式调用 |

## 7. 当前仍存在的 Skill 相关缺口（如实登记）

1. `.agent/06` `K-02` 要求的「验收检查 Skill」已由本轮新增的 `acceptance-check` v1.0 补齐（用户整改指令明确授权，属 C-08）；**但缺独立验收 Agent 会话中的真实触发与复检记录**，文件级交付不等于过程证据，不得完工后补造调用记录。
2. `K-04` 闭环仍缺独立验收会话的复检结论。
3. Skill 变更须学生确认并保留历史版本：本轮新增 1 份 `SKILL.md`（`acceptance-check`），未改动原有 3 份 `SKILL.md`；`skill-usage.md` 的变更随本轮整改一并记录。
4. 所有 Skill 的正式运行证据（真实 MySQL + `CGO_ENABLED=1` 的 race、Apipost 运行导出、第 3 轮页面验收）均待独立测试/验收 Agent 会话，属环境/过程证据，不伪造。

## 8. 证据位置

`.codebuddy/skills/*/SKILL.md`、`.codebuddy/skills/acceptance-check/SKILL.md`、`docs/dev-assumptions.md`、`docs/interface-list.md`、`docs/代码产物补齐说明.md`、`test-report.md`、`race-output.txt`、`coverage-report.md`、`apipost-run-summary.md`、`outputs/单题检查/shop-trade/01/20261112-01/检查报告.md`、`outputs/单题检查/shop-trade/01/20261112-02/检查报告.md`、`outputs/单题检查/shop-trade/01/20261112-03/检查报告.md`、`docs/完成声明边界.md`。

## 9. 第四轮证据闭环：逐 Skill 真实调用记录 / 失败样例 / 边界样例

> 本节补齐第 7 节「不只是六类说明」的闭环缺口。**文件级冒烟核查不等于工具加载记录**；
> 本机仍无 `CGO_ENABLED=1` 的 race、真实 MySQL、meegle、远端 CI、独立测试/验收会话、视频与 `events.jsonl`，
> 相关项维持「待补证 / 不可补」，不因本节补齐而改判通过。单条证据见 `evidence/smoke/SKILL-*.txt`。

### 9.1 `gva-model-generate`

| 项 | 内容 |
| --- | --- |
| 真实调用记录 | 一次性开发任务生成 `schema.sql` 三表与 `server/model/model.go`；第三轮复核以 `schema.sql` / `model.go` 核对 InnoDB、utf8mb4 与保留字反引号（E3-025）；第四轮文件级冒烟 `evidence/smoke/SKILL-gva-model-generate.txt` 10 项全 PASS |
| 失败样例 | 初版 `refund_channel_trade_no` 误设为 `uniqueIndex`，空交易号会互相冲突；已改为普通 index，幂等由 `dedup_key` 承担（第一轮整改 D-xx 已复测）。PostgreSQL→MySQL(InnoDB) 的技术栈偏差亦经 `.agent/` 增量修正 |
| 边界样例 | `order` 为 MySQL 保留字须反引号；金额 `bigint` 分不得用浮点；`uk_payment_dedup_key` 与 `uk_payment_channel_effective` 的唯一键口径；`idx_order_status_expires` 必须命中索引，否则条件更新升级表锁引发超卖 |
| 局限 | 生成的是表结构，不产业务代码；真实 MySQL 实例下建表与重启后查询证据属环境缺失 |

### 9.2 `unit-test-race`

| 项 | 内容 |
| --- | --- |
| 真实调用记录 | 生成 service/api/router/initialize/model/main 单测与 `scripts/run-race.ps1`；第一轮整改重新加载补齐 controller/router/main 测试；第四轮新增 `server/service/r4_edge_test.go` 边界 case，`go test -cover ./server/service/...` 由 88.9% → **90.3%**、整体 `-coverpkg ./...` **88.2%**，命令输出见第四轮 `evidence/核查命令与输出.txt` |
| 失败样例 | 第四轮真实复跑 `go test ./server/service/... -race -count=1` 输出 `go: -race requires cgo; enable cgo by setting CGO_ENABLED=1`，`exit=2`；`CGO_ENABLED=0`、`gcc/clang=NOT_FOUND`。按 rubric 41 行记 `unknown`，**不写成已通过、也不写成数据竞争报告** |
| 边界样例 | 第四轮新增：审计写入失败注入（`r4ErrCreateRepo`）、事务内 `LockGoods`/`DecreaseGoodsStock`/`CreateOrder`/`CreatePayment` 技术错误、`falseStock` 条件更新未命中、`unit_price=0/-1/MinInt64`、`quantity=0/3/-1`、越权与空身份、逐单核查 3 次恢复事件计数 |
| 局限 | 仍为开发会话内单测，基于内存仓储与 sqlmock；不冒充独立测试 Agent 会话、不冒充真实 InnoDB 行锁与 race 证据 |

### 9.3 `apipost-case-gen`

| 项 | 内容 |
| --- | --- |
| 真实调用记录 | 首次基于 `interface-list-draft.md` 草案生成用例（已废弃）；整改期以 `docs/interface-list.md` v1.0 定稿重建 5 场景 48 用例与 `apipost-assertion-matrix.md`；第四轮按附录 A 逐接口契约核对用例字段，`evidence/smoke/SKILL-apipost-case-gen.txt` 10 项全 PASS |
| 失败样例 | 首次引用草案路径与 `mock_channel_base_url` / `/trigger` 变量被第三轮复核判为不一致，已删除；`apipost-run-summary.md` 至今自述「未运行，无通过/失败数」，**不得写成第 2 轮通过** |
| 边界样例 | 附录 A 的 `API-01~23` 空/超长/越权/负数入参示例；第四轮 `evidence/manual/` 30 条真实异常响应可直接作为断言输入（其中 5 条 `DIFF` 为边界行为差异登记，不弱化断言） |
| 局限 | Apipost 真实运行导出、运行标识与通过/失败数仍属过程证据缺失，不伪造 |

### 9.4 `acceptance-check`

| 项 | 内容 |
| --- | --- |
| 真实调用记录 | 第三批新增 `SKILL.md`；第三轮复核按其检查清单只读核对新增产物；第四轮按「三类问题分类」口径锁定环境/过程证据缺失项，并生成 `evidence/html-check/` 8 份页面断言与 38 条单用例冒烟；文件级冒烟 `evidence/smoke/SKILL-acceptance-check.txt` 全 PASS |
| 失败样例 | `skill-usage.md` 第 7 节如实登记：未通过工具加载、未由验收 Agent 独立会话执行；本轮仍不满足 `K-04` 独立复检闭环。第三/四轮报告均不把开发会话自检写成验收结论 |
| 边界样例 | 环境阻塞（`-race requires cgo`、无 DSN、meegle=NOT_FOUND）判「待补证」不判代码缺陷；说明文档不得冒充会话导出/验收报告本体；HTTP 200 不得冒充第 3 轮浏览器截图验收 |
| 局限 | 只做只读核查，不修代码、不出「验收通过」结论；独立验收会话属不可补过程证据 |

### 9.5 内置 `student-project-audit`（不计入 `K-02`）

| 项 | 内容 |
| --- | --- |
| 真实调用记录 | 第一、二、三、四轮检查报告分别由 `use_skill` 加载并用 `score_audit.py` 计分；第四轮真实输出见本批次 `score.json` 与 `evidence/核查命令与输出.txt` |
| 失败样例 | PowerShell 5.1 以默认编码读取无 BOM 的 UTF-8 `score.json` 触发 `ConvertFrom-Json` 解析告警；改用 `python -c` 以 UTF-8 读取后校验成功（属读取方式问题，非 `score.json` 内容错误）。第四轮证据采集脚本初版 `.ps1` 同样因中文编码解析失败，改用 Python 重写后成功 |
| 边界样例 | 42 原子项稳定矩阵（`max_points` 各类合计 A1 3.00 / A2 1.80 / A3 1.70 / A4 1.50 / B1 0.60 / B2 0.80 / B3 0.30 / B4 0.30）；门禁封顶 7.90 只统一执行一次；`unknown` 系数 0 但仍触发门禁；最终分 ≥8.00 才合格 |
| 局限 | 计分脚本只校验计分，不判断业务真实性；不得手改分数或把环境阻塞当成已证实违规 |

### 9.6 闭环边界（不冒充）

- 本节补齐的是**文件级冒烟、真实调用记录索引、真实失败样例与边界样例**；`skill-usage.md` 第 6/7 节登记的独立验收会话复检、Apipost 运行导出、真实 race/MySQL/CI/视频证据**仍未闭合**。
- 本节不新增、不改写任何历史会话记录，不生成 `events.jsonl`，不把第四轮开发会话自检冒充独立测试/验收 Agent 会话。

---

## 10. 第五轮证据闭环：11 条 partial 的独立核查 + 覆盖率边界补齐

> 本节登记**第五轮（证据闭环轮次）**新增的 Skill 复用与产物。第五轮**未改动任何生产代码**，
> 只新增测试与证据文档；本节同样**不冒充**独立测试/验收 Agent 会话、真实 MySQL、race 探针、CI / PR / 部署记录。

### 10.1 本轮产物总览

| 项 | 内容 | 证据位置 |
| --- | --- | --- |
| 核查对象 | 第四轮 `audit-input.json` 中 **11 条 `partial`** 条目逐条独立闭环 | `evidence/partial-closure/`（11 份，每份含真实命令输出 + 真实手工 case + 缺口说明 + 解除条件） |
| 边界补齐 | 新增 service 包边界单测 2 个文件，覆盖未覆盖的错误分支、条件更新未命中、锁商品为空、库存守卫未命中、唯一键冲突、迟到支付旁路全链路 | `server/service/r5_edge_test.go`、`server/service/r5_edge2_test.go` |
| 覆盖率 | service 包 **98.5%**（目标 ≥92%）；整体 `-coverpkg ./...` **94.2%**（第四轮 88.2% → 本轮 94.2%） | `evidence/第五轮证据清单.md`、覆盖率原始文件 |
| 第二批异常 | 5 类 **28 条**业务状态级 / 库存守恒级手工样本（第一批为参数级 30 条） | `evidence/manual-round2/`（下单 7 / 退款 5 / 调价 6 / 超时通知 5 / 库存核查 5） |
| 页面契约 | 8 页新增 **A8~A12** 契约级断言（接口契约一致性 / 按钮绑定 / 失败原因编号 / 角色一致性 / 写操作口径），A1~A7 沿用第四轮 | `evidence/html-check/V01-*.md` ~ `V08-*.md` |
| 文档闭环 | `docs/interface-list.md` 新增**附录 B 全量接口 × 边界维度矩阵**；`docs/git-提交指引.md` 新增 2.4 节 | 本仓库 `docs/` |
| 采集脚本 | 4 个可重跑脚本 + 1 个公共库 | `scripts/r5_closure_lib.py`、`scripts/r5_partial_closure.py`、`scripts/r5_partial_closure2.py`、`scripts/r5_manual2.py`、`scripts/r5_htmlcheck_enhance.py` |

### 10.2 逐 Skill 的第五轮复用

| Skill | 第五轮是否复用 | 复用方式与真实结果 | 局限 |
| --- | --- | --- | --- |
| `gva-model-generate` | 是（**文件级复核**，未重新生成表结构） | 逐条读取 `schema.sql` 的 `CREATE TABLE` 语句，确认 `ENGINE=InnoDB`、`DEFAULT CHARSET=utf8mb4`、`uk_payment_dedup_key`、`uk_payment_channel_effective` 等唯一键真实存在；结果写入 `evidence/partial-closure/R-A2-01.md` 与 `R-A2-04.md` | **未在真实 MySQL 实例执行 DDL**；文件级复核不能替代实例级建表证据 |
| `unit-test-race` | 是（本轮主要复用对象） | 新增 `r5_edge_test.go` / `r5_edge2_test.go` 覆盖 service 包 0 执行语句的错误分支与边界分支；`go test ./...` 七包全 ok；`go test -cover ./server/service/...` = **98.5%**；`go tool cover -func` overall = **94.2%**；`gofmt -l .` 为空；`go vet ./...` 通过 | **`go test -race` 本轮仍无法执行**：`go env CGO_ENABLED` = 0，`where gcc` / `where clang` 无结果，`-race requires cgo`（exit=2）；本轮不冒充 race 探针输出 |
| `apipost-case-gen` | 是（**契约反哺**） | 以 `docs/interface-list.md` 附录 B 的 23 接口 × 5 维度矩阵反推用例边界，形成第二批 28 条可执行边界样本与 `evidence/manual-round2/` | **Apipost 正式运行导出仍缺失**；`apipost-run-summary.md` 继续自述未运行，不写成第 2 轮通过 |
| `acceptance-check` | 是（**只读核查口径**） | 11 条 partial 逐条按「环境/过程证据缺失 → 不判代码缺陷」分类，逐份给出真实核查动作、缺口说明与**可核查的解除条件**；不修代码、不出「验收通过」结论 | 仍是**开发会话内自检**，不等于独立验收 Agent 会话复检；`K-04` 独立复检闭环未闭合 |
| 内置 `student-project-audit` | 否（本轮未重跑计分） | 第五轮不改动 `audit-input.json` 的 42 原子项判定，也不改分 | 第四轮计分结果 **7.27/10 不合格**（门禁封顶 7.90）；本轮产物是**补证**，不是重新评分 |

### 10.3 本轮真实的失败样例（不修饰）

| 样例 | 真实表现 | 处理方式 |
| --- | --- | --- |
| `noopPayment` 幂等留痕语义误判 | 初版断言按「返回业务错误 M-25 / M-10」编写，真实行为是**成功返回** `(payment, nil)`，M-25 / M-10 只作为留痕 `code` / `remark` | **修正断言为留痕语义**（如 `ResultRepeatPaymentNoop`），不改动生产代码、不弱化断言、不删除用例 |
| 常量误用 | 迟到退款回调重复成功通知实际返回 `ResultRepeatRefundNoop`，初版写成 `ResultRepeatPaymentNoop` | 改为正确常量，断言重跑通过 |
| `gofmt` 未格式化 | 两个新测试文件初次 `gofmt -l` 报未格式化 | 执行 `gofmt -w`，重跑 `gofmt -l .` 输出为空 |
| 单文件过大 | 初版 `r5_edge_test.go` 约 1000 行，单次写入超限 | 拆分为同包两个文件（`r5_edge_test.go` / `r5_edge2_test.go`），内容不重不漏 |
| A8 首轮判 FAIL | 首版 A8 只在页面 HTML 内查找接口路径，遗漏 `Shop.loadGoods()` 引入的 `app.js` 路径，导致 V01/V03/V04/V05 误判 FAIL | 断言口径修正为「页面 + 公共脚本 `app.js`」，并在文档中写明该口径；**未降低断言强度**（接口契约表一侧始终严格校验） |
| A10 首轮判 FAIL | V07 静态页实际不含 M-17（M-17 由 API-23 的 `conclusion` 返回，不在页面文案中） | 按**页面真实内容**修正必现编号为 M-08 / M-24，不改页面源码 |

### 10.4 第五轮闭环边界（仍不冒充）

- 11 条 `partial` **均未升级为 `pass`**：每条的缺口都源于**真实 MySQL 实例、`CGO_ENABLED=1` 的 race 探针、独立测试/验收会话、`events.jsonl`、远端 CI / PR / 部署**等环境或过程证据缺失，**不是代码缺陷**；解除条件已逐条写入 `evidence/partial-closure/`。
- 本轮**未**建立独立测试 Agent 会话与独立验收 Agent 会话，**未**产出 `events.jsonl`，**未**运行 Apipost，**未**触发 CI，**未**生成浏览器截图或视频。
- 本轮覆盖率数字来自 `go test -cover` 的**真实执行输出**；`-coverpkg ./...` 的 overall 行与逐函数明细均已留存，**未**手工编辑、未排除自编生产代码凑覆盖率。
- 本轮**未改动生产代码**：新增文件仅为 `server/service/r5_edge_test.go`、`server/service/r5_edge2_test.go`、`scripts/r5_*.py` 与 `evidence/` 文档。

