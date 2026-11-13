# shop-trade —— 小型电商订单交易、发货与售前退款（题目 01）

Go + Gin + GORM + MySQL(InnoDB) 实现的小型电商单商品订单系统：一单一种商品、金额以「分」为单位的整数、
待支付 10 分钟超时关闭、支付通知鉴权与幂等、迟到支付异常登记、售前整单退款审核与渠道失败重试、
发货登记一次、退款与发货互斥裁决、角色权限隔离、运营核查汇总与只追加审计流水。

## 技术栈与运行环境

| 项 | 说明 |
| --- | --- |
| 语言 / 框架 | Go 1.22、Gin v1.10、GORM v1.25 |
| 数据库 | MySQL 8.4 / InnoDB / utf8mb4（可选；不配置时进入 demo-memory 演示模式） |
| 外部依赖 | 仅可控 HTTP 模拟支付渠道（`scripts/mock_channel_service.py`），无真实第三方接入 |
| 静态页面 | `resource/static/` 下 9 个零构建视图（V01~V08 + index） |

## 目录结构

```
main.go                       入口：按 GVA 风格装配 initialize，装配逻辑与 main 分离便于测试
server/
  api/v1/                     controller：参数绑定、身份解析、响应封装
  initialize/                 路由注册、MySQL 初始化、演示时钟
  model/                      GORM 模型（goods / order / payment）
  router/                     路由表
  service/                    业务规则、状态机、权限校验、两种仓储实现
resource/static/              9 个原型视图
schema.sql                    建表 + 演示数据（InnoDB、utf8mb4、唯一键）
scripts/                      模拟渠道、证据采集脚本、质量门禁脚本
docs/                         接口契约、假设清单、建库与提交说明
evidence/                     各轮验证原始输出
.agent/                       题集随附的工作流约束集
AGENTS.md                     项目级 Agent 约束（三角色职责、提交规范、质量门禁、禁止项）
```

## 快速开始（demo-memory 演示模式）

不配置数据库即可运行，数据不持久化，适合五组场景演示。

```powershell
go build -o shop-trade.exe .
$env:GVA_ADDR = ':8080'
.\shop-trade.exe
# 健康检查：http://127.0.0.1:8080/health
# 页面入口：http://127.0.0.1:8080/
```

## MySQL(InnoDB) 模式

```powershell
# 1) 建库并执行建表与演示数据
mysql -uroot -e "CREATE DATABASE IF NOT EXISTS shop_trade DEFAULT CHARACTER SET utf8mb4;"
mysql -uroot shop_trade < schema.sql

# 2) 准备应用账号（口令请本地设置，勿写入仓库）
#    MySQL 8 默认 root 使用 auth_socket，建议单独建应用账号并只授予 shop_trade 权限

# 3) 以 DSN 启动（未设置 GVA_MYSQL_DSN 时回落到 demo-memory）
$env:GVA_MYSQL_DSN = 'shoptrade:<口令>@tcp(127.0.0.1:3306)/shop_trade?charset=utf8mb4&parseTime=True&loc=Local'
$env:GVA_ADDR = ':8080'
.\shop-trade.exe
```

启动日志中的 `mode=` 会标明当前是 `demo-memory` 还是 `mysql-innodb`。

## 演示账号

身份只由请求头 `X-Demo-Account` 解析，请求里的 `X-Role` / `X-User-Id` 一律忽略，改编号不能越权。

| 账号 | 角色 | 可用操作 |
| --- | --- | --- |
| `buyer01` ~ `buyer03` | 买家 | 下单、查询、取消、申请售前退款 |
| `ops01` | 运营 | 商品列表与调价、核查汇总 |
| `warehouse01` | 仓库 | 登记发货 |
| `cs01` | 客服 | 退款审核（同意/拒绝/重试）、迟到支付核实与退款 |
| `mock01` | 模拟渠道 | 支付通知与退款回调 |

## 五组场景入口

| 场景 | 关键接口 |
| --- | --- |
| S1 活动正常成交 | `POST /api/v1/orders` → `POST /api/v1/payment/callback` → `POST /api/v1/orders/{no}/shipment` |
| S2 缺货与弃单 | 并发下单返回 `M-02`；`POST /api/v1/admin/clock` 推进时钟后 `POST /api/v1/admin/orders/close-expired` |
| S3 售前退款 | `POST /api/v1/orders/{no}/refund/apply` → `approve` / `retry` → `POST /api/v1/refund/callback` |
| S4 迟到支付 | 支付回调返回 `M-09` → `POST /api/v1/late-payment/{event_id}/verify` → `refund/initiate` |
| S5 操作竞争 | 退款申请与发货登记并发；重复支付/退款通知幂等；越权访问返回 `M-20` |

接口全量契约见 `docs/interface-list.md`（含全量边界矩阵）。

## 质量门禁与流水线

生效的流水线定义在 `.github/workflows/ci.yml`，两个门禁作业与本地脚本一一对应，可原样复跑：

```powershell
# 覆盖率阈值门禁：整体 ≥85%，核心业务包 server/service ≥85%，不达标退出码非零
go test -count=1 -coverpkg=./... -coverprofile=coverage.out ./...
python scripts/coverage_gate.py --profile coverage.out --overall 85 --pkg server/service:85

# 基础部署门禁：构建制品 → 登记版本 → 启动 → 健康检查 → 业务冒烟 → 回退准备校验
python scripts/deploy_gate.py --addr 127.0.0.1:18080 --out dist
```

`scripts/coverage_gate.py` 的解析口径与 `go tool cover -func` 一致（mode:set profile 按代码块去重后取最大命中次数）。

## 验证脚本清单

| 脚本 | 作用 |
| --- | --- |
| `evidence/db/inno_ship_refund_race.py` | 真实 InnoDB 行锁下「退款申请 vs 登记发货」互斥裁决复现，含行锁阻塞探针；复现步骤见 `evidence/db/inno_ship_refund_race.md` |
| `evidence/db/order_table_verify.py`、`ticket_table_verify.py` | 唯一索引、事务回滚原子性与持久化验证 |
| `scripts/r4_evidence_suite.py`、`r5_*.py` | 各轮接口与边界证据采集 |
| `scripts/check_commit_message.py` | 提交消息格式校验（对照 `commit-convention.md`） |

## 其他文档

- `题目01-…-需求文档.md` / `…-原型设计文档.md` / `…-任务规划文档.md`：需求、原型与任务规划（v1.0 / v1.0 / v1.1）
- `AGENTS.md`：项目级 Agent 约束；`AGENTS-v1.0.md` 为历史版本
- `commit-convention.md`：提交消息规范
- `docs/dev-assumptions.md`：假设清单
- `outputs/单题检查/`：历轮单题检查报告、评分明细与证据
