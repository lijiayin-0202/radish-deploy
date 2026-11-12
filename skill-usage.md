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

## 6. Skill 检查 → 修正 → 复检闭环（`K-04`）

| 阶段 | 真实情况 |
| --- | --- |
| 检查发现问题 | `student-project-audit` 的 `E-017/E-018` 与检查报告 `B3`：3 个自编 Skill 结构完整且真实调用，但 `skill-usage.md` 缺六项说明、缺验收检查 Skill、缺「发现问题 → 修正 → 复检」闭环记录 |
| 学生指导修正 | 用户于整改指令中明确要求「补全 `skill-usage.md` 六类说明」；本文件即修正产物 |
| 复检 | **尚未由验收 Agent 独立会话完成**。本轮开发会话只做到文件补齐，不自行判定闭环通过；复检须读取本题面条款、本文件与对应提交哈希后给出逐项结论 |
| 未编造声明 | 不把「文件已补齐」写成 `K-04` 闭环已通过；不把未触发过的 Skill 列为已使用 |

## 7. 当前仍存在的 Skill 相关缺口（如实登记）

1. `.agent/06` `K-02` 要求「至少两个自编 Skill：业务专项 Skill + **验收检查 Skill**」；当前 3 个自编 Skill 均为生成/测试类，**尚无验收检查 Skill**。是否新增属 C-08，须学生确认后以 `docs` 单独提交，不得完工后补造调用记录。
2. `K-04` 闭环缺独立验收会话的复检结论。
3. 三个自编 Skill 的 `SKILL.md` 修改需学生确认（C-08）并保留历史版本；本轮未修改 `SKILL.md`。
4. 所有 Skill 的正式运行证据（真实 MySQL + `CGO_ENABLED=1` 的 race、Apipost 运行导出、第 3 轮页面验收）均待独立测试/验收 Agent 会话。

## 8. 证据位置

`.codebuddy/skills/*/SKILL.md`、`docs/dev-assumptions.md`、`docs/interface-list.md`、`test-report.md`、`race-output.txt`、`coverage-report.md`、`apipost-run-summary.md`、`outputs/单题检查/shop-trade/01/20261112-01/检查报告.md`、`docs/完成声明边界.md`。
