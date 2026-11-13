# InnoDB 行锁下「退款申请 vs 登记发货」互斥裁决复现

本文件对应第 6 轮单题检查登记的 `ISS-A1-13-SHIP-RACE`：退款与发货的互斥裁决此前只在
demo-memory 的进程内互斥锁下被验证过，缺少「同一断言在真实 InnoDB 行锁下复现」的证据。
本轮补齐该证据。

## 复现步骤（Windows PowerShell，不使用 WSL）

前置条件：

- 本机 MySQL 8.4.11 正在运行并监听 `127.0.0.1:3306`，库 `shop_trade` 已按 `schema.sql` 建表
  （三张业务表均为 InnoDB / utf8mb4）；
- 有一个对 `shop_trade` 有读写权限的账号（脚本通过环境变量读取，不写入仓库）；
- Go 工具链可用（脚本自行 `go build` 拉起独立实例）。

```powershell
# 1) 指定账号（口令留空表示空口令；如有口令请填入，勿写入仓库）
$env:MYSQL_USER = 'audit_chk'
$env:MYSQL_PASSWORD = ''

# 2) 执行复现脚本（自动构建并以 mysql-innodb 模式拉起独立实例，端口 18099）
python -X utf8 evidence/db/inno_ship_refund_race.py --rounds 5

# 3) 退出码 0 表示全部断言通过；原始输出同时写入
#    evidence/db/inno_ship_refund_race_raw.txt
#    evidence/db/inno_ship_refund_race_raw.json
```

可选参数：`--host`、`--port`、`--db`、`--user`、`--password`、`--app-port`、`--rounds`、
`--lock-wait-seconds`（行锁阻塞探针的持锁观察时长，默认 4 秒）。

## 脚本做了什么

### 阶段 A：并发裁决复现

对同一笔「已支付待发货」的订单，并发发起两个请求：

| 角色 | 接口 | 请求体 |
| --- | --- | --- |
| 买家 `buyer01` | `POST /api/v1/orders/{order_no}/refund/apply` | `{"reason": "..."}` |
| 仓库 `warehouse01` | `POST /api/v1/orders/{order_no}/shipment` | `{"carrier": "...", "tracking_no": "..."}` |

每轮断言：

1. 只形成一种合法结果——要么 `refund=0 且 ship=M-22`（退款胜出，发货被拒），
   要么 `ship=0 且 refund ∈ {M-05, M-10, M-11}`（发货胜出，退款被拒）；
2. 数据库 `order` 表的 `status` 与胜方一致，且终态唯一（`已发货` 或 `退款审核中`）；
3. `goods` 表满足 `available_stock + occupied_stock` 恒定（库存守恒，不超卖）；
4. `payment` 表中该订单的终态类审计事件不超过一条（不重复发货、不重复退款）。

### 阶段 B：行锁阻塞探针（决定性证据）

阶段 A 只能证明「结果唯一」，仍不能排除是进程内互斥锁在起作用。阶段 B 给出决定性证据：

1. 用**外部事务 T0** 对该订单行执行 `SELECT ... FOR UPDATE` 并保持不提交——这是纯粹的
   数据库行锁，进程内的任何互斥锁都无法阻止它；
2. 此时发起应用侧退款请求，观察 4 秒——请求**未返回**，说明请求确实阻塞在 InnoDB 行锁上
   （应用侧 `LockOrder` 走的正是 `SELECT ... FOR UPDATE`）；
3. T0 回滚释放行锁后，请求**立即成功**返回 `code=0`，订单状态变为 `退款审核中`。

由「外部事务持锁 → 应用请求被阻塞 → 释放锁 → 立即成功」这一组现象可判定：
并发裁决发生在 InnoDB 行锁层，而非仅靠进程内互斥。

> 说明：读取 `information_schema.innodb_trx` 需要 `PROCESS` 权限，当前账号不具备，
> 因此脚本无法直接打印 `trx_state=LOCK WAIT`。脚本对此做了显式说明，
> 并以「阻塞时长 + 释放锁后立即成功」作为等价证据，不掩盖该限制。

### 阶段 C：表级一致性汇总与清理

删除本脚本创建的订单与审计流水，并把 `goods` 表的 `available_stock` / `occupied_stock`
按测试前的原值完整还原。脚本在阶段开始时记录原始基线，并在可售不足时临时补足，
结束时统一还原，保证可重复执行且不污染演示数据。

## 本轮执行结果

- 执行时间：2026-11-12 22:44（真实 MySQL 8.4.11，账号 `audit_chk`，`shop_trade` 库）；
- 应用启动模式：`mode=mysql-innodb`（见 `evidence/db/inno_ship_refund_race.app.log`）；
- 断言结果：**37 条全部 PASS，0 条 FAIL**，退出码 0；
- 5 轮并发裁决中，3 轮由退款胜出（`ship=M-22`）、2 轮由发货胜出（`refund=M-11`），
  两种合法结果都真实出现，说明裁决来自真实竞争而非固定偏向；
- 原始输出：`evidence/db/inno_ship_refund_race_raw.txt`（应用日志同目录 `.app.log`）。

## 与脚本当前版本的差异说明

上述原始输出产生于 2026-11-12 22:44。其后脚本仅修正了一处**日志显示**语句
（阶段 B 打印被锁定订单行时改为直接读取游标，避免辅助函数已取尽结果导致打印 `None`），
断言集合、判定逻辑与结论均未改变；重跑应得到同样的 37 条断言全部 PASS。
2026-11-13 复核时本机 MySQL 实例已停止监听（且检查者命令范围不含 WSL），故未当日重跑，
该差异在此显式记录，不做隐去。
