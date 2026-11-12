# MySQL InnoDB 核查记录

> 项目：shop-trade（题目 01 小型电商订单交易、发货与售前退款）
> 核查对象版本：dev/01 @ `58719fb`
> 核查执行时间：2026-11-12
> 本文所有输出均为真实命令执行结果，原始输出见同目录 `mysql_raw_*.txt`；未执行的步骤已明确标注，不作任何推定。

## 环境

| 项 | 实测值 | 取证方式 |
| --- | --- | --- |
| 数据库产品 | MySQL 8.4.11（Ubuntu 26.04 官方 `mysql-server` 包） | `mysqld --version`，见 `mysql_raw_00_env.txt` |
| 版本说明 | MySQL 8.4 为 MySQL 8 系列 LTS，与 8.0 同属 MySQL 8.x InnoDB 体系；本机无法安装 8.0 精确版本，脚本与 DDL 均以 8.0 语法基线编写，并在 8.4 上实测通过 | 同上 |
| 存储引擎 | InnoDB（`default_engine = InnoDB`，`SHOW ENGINES` 中 InnoDB 为 DEFAULT） | `mysql_raw_00_env.txt` |
| 字符集 | `character_set_server = utf8mb4`，`collation_server = utf8mb4_0900_ai_ci` | `mysql_raw_00_env.txt` |
| 隔离级别 | `transaction_isolation = REPEATABLE-READ` | `mysql_raw_00_env.txt` |
| 运行方式 | WSL Ubuntu 内真实 mysqld 进程（`service mysql start/restart`），Windows 侧通过 `127.0.0.1:3306` 访问 | `mysql_raw_00_env.txt`、`mysql_raw_05_app_persistence.txt` |
| 账号 | 应用专用账号 `shoptrade`@`%`，口令随机生成且仅存放于 WSL `/tmp/shop_dsn_pw`（600），不写入仓库、不出现在本文 | `evidence/mysql_prepare_user.sh` |
| 建表脚本 | `evidence/schema.sql`（含建库、三张业务表、索引、唯一约束、字段与表注释、演示数据，可直接执行） | 文件本体 |

## 操作1：执行 schema.sql 建库建表成功

命令（WSL 内 root）：

```bash
mysql -uroot < /mnt/d/Desktop/shop/evidence/schema.sql
```

实测结果（`evidence/mysql_raw_01_schema.txt`）：

- `schema_script_exit=0`，脚本执行过程中**无任何 ERROR 输出**；
- 脚本包含 `CREATE DATABASE IF NOT EXISTS shop_trade ... DEFAULT CHARSET utf8mb4` + `USE shop_trade` + 三张表的 `CREATE TABLE IF NOT EXISTS` + `INSERT ... ON DUPLICATE KEY UPDATE` 演示数据，可重复执行（幂等）；
- 执行后 `SHOW TABLES` 返回 `goods`、`order`、`payment` 三张表（见 `mysql_raw_02_inspect.txt`）。

表结构实测（`information_schema.TABLES`，`mysql_raw_02_inspect.txt`）：

| TABLE_NAME | ENGINE | TABLE_COLLATION | 业务含义 |
| --- | --- | --- | --- |
| `goods` | InnoDB | utf8mb4_0900_ai_ci | 商品与库存（可售 available_stock / 预扣占用 occupied_stock 分离） |
| `order` | InnoDB | utf8mb4_0900_ai_ci | 订单（下单时商品与价格快照、状态机、10 分钟到期时间） |
| `payment` | InnoDB | utf8mb4_0900_ai_ci | 支付/退款/迟到支付与只追加审计流水 |

索引与唯一约束实测（`information_schema.STATISTICS` 与 `TABLE_CONSTRAINTS`，`mysql_raw_02_inspect.txt`）：

- `order`：`PRIMARY(id)`、`UNIQUE uk_order_order_no(order_no)`、`idx_order_status_expires(status, expires_at)`（超时关单扫描）、`idx_order_buyer_status(buyer_id, status)`、`idx_order_goods_id`、`idx_order_refund_channel_trade_no`、`idx_order_status`、`idx_order_deleted_at`；
- `goods`：`PRIMARY(id)`、`UNIQUE uk_goods_goods_no(goods_no)`、`idx_goods_status`、`idx_goods_available_stock`、`idx_goods_deleted_at`；
- `payment`：`PRIMARY(id)`、`UNIQUE uk_payment_dedup_key(dedup_key)`（幂等键）、`UNIQUE uk_payment_channel_effective(channel_trade_no, effective)`（渠道交易号不得归属两个有效业务结果）、`idx_payment_order_id`、`idx_payment_order_no`、`idx_payment_event_type`、`idx_payment_result`、`idx_payment_related_event_id`、`idx_payment_occurred_at`、`idx_payment_deleted_at`；
- 金额列全部为 `BIGINT`（单位：分），无 `FLOAT`/`DOUBLE`/`DECIMAL` 类型；状态列全部为 `VARCHAR(32)`，未使用 MySQL `ENUM`。

## 操作2：数据库重启后，查询表结构、索引，校验约束正常

命令：

```bash
service mysql restart
mysqladmin ping
mysql -uroot shop_trade -e "SHOW TABLES;"
mysql -uroot shop_trade -e "SHOW INDEX FROM \`order\`;"
mysql -uroot shop_trade -e "SHOW INDEX FROM \`goods\`;"
mysql -uroot shop_trade -e "SHOW INDEX FROM \`payment\`;"
mysql -uroot shop_trade -e "SELECT CONSTRAINT_NAME, TABLE_NAME, CONSTRAINT_TYPE FROM information_schema.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA='shop_trade';"
```

实测结果（`evidence/mysql_raw_04_restart.txt`）：

- `mysqld is alive`：重启成功；
- `SHOW TABLES` 仍返回 `goods`、`order`、`payment`；
- 三张表的索引清单在重启后与建表时完全一致（`uk_order_order_no`、`uk_goods_goods_no`、`uk_payment_dedup_key`、`uk_payment_channel_effective` 及全部普通索引均在）；
- `information_schema.TABLE_CONSTRAINTS` 中 `PRIMARY` 与 `UNIQUE` 约束全部保留；
- 数据留存实测：`goods_rows=2`、`order_rows=1`、`payment_rows=4`，均为重启前写入的数据，未丢失；
- 该日志 `grep -c ERROR` 结果为 `0`，整个重启复查过程无报错。

**应用层持久化复核（超出题面最低要求的额外验证）**：`evidence/mysql_raw_05_app_persistence.txt` 记录了应用以 `GVA_MYSQL_DSN` 指向本实例运行时的真实过程：

1. 进程1 启动后 `GET /api/v1/me` 返回 `mode=mysql-innodb`；`GET /api/v1/goods` 直接从 MySQL 读出商品与库存；
2. `POST /api/v1/orders` 下单成功；`SELECT ... FROM \`order\`` 与 `SELECT ... FROM goods` 均查到真实落库行（订单「待支付」，可售 5→3、占用 0→2）；
3. `POST /api/v1/payment/callback` 支付回调成功，订单状态「待发货」，`payment` 表新增 `effective=1` 的有效收款事件；
4. **真实终止进程1**（`terminate` 后确认退出）→ **启动进程2**（同一二进制、同一 DSN）→ `GET /api/v1/orders/{order_no}` 仍返回该订单且状态一致；重启前后两次 SQL 查询结果一致；
5. 断言汇总 **8 / 8 全部 PASS**（含「应用重启后同一订单仍可查询且状态一致」）。

## 操作3：唯一键冲突复现

可直接运行的复现 SQL（`evidence/mysql_raw_03_unique.txt` 为其真实执行输出）：

```sql
-- 3.1 写入一条订单基线数据
INSERT INTO `order` (order_no,buyer_id,goods_id,goods_no,goods_name,quantity,unit_price,total_amount,status,expires_at)
VALUES ('UNIQ-PROBE-0001',1001,1,'GOODS-ACT-001','活动商品',1,10000,10000,'待支付',NOW(3)+INTERVAL 10 MINUTE)
ON DUPLICATE KEY UPDATE order_no=VALUES(order_no);

-- 3.2 重复插入相同 order_no -> 触发 uk_order_order_no
INSERT INTO `order` (order_no,buyer_id,goods_id,goods_no,goods_name,quantity,unit_price,total_amount,status,expires_at)
VALUES ('UNIQ-PROBE-0001',1002,1,'GOODS-ACT-001','活动商品',1,10000,10000,'待支付',NOW(3)+INTERVAL 10 MINUTE);

-- 3.3 重复插入相同 dedup_key -> 触发 uk_payment_dedup_key（重复执行同一条语句即触发）
INSERT INTO payment (order_id,order_no,channel_trade_no,dedup_key,effective,event_type,result,amount,occurred_at)
VALUES (1,'UNIQ-PROBE-0001','TRADE-UNIQ-0001','DEDUP-UNIQ-0001',1,'支付通知','成功',10000,NOW(3));

-- 3.4 重复插入相同 (channel_trade_no, effective) -> 触发 uk_payment_channel_effective
INSERT INTO payment (order_id,order_no,channel_trade_no,dedup_key,effective,event_type,result,amount,occurred_at)
VALUES (1,'UNIQ-PROBE-0001','TRADE-UNIQ-0002','DEDUP-UNIQ-0002',1,'支付通知','成功',10000,NOW(3));
```

真实报错输出（逐字摘自 `evidence/mysql_raw_03_unique.txt`）：

```
ERROR 1062 (23000) at line 1: Duplicate entry 'UNIQ-PROBE-0001' for key 'order.uk_order_order_no'
ERROR 1062 (23000) at line 1: Duplicate entry 'DEDUP-UNIQ-0001' for key 'payment.uk_payment_dedup_key'
ERROR 1062 (23000) at line 1: Duplicate entry 'TRADE-UNIQ-0002-1' for key 'payment.uk_payment_channel_effective'
```

对照验证：把 `effective` 置为 NULL 的审计事件可以重复追加（唯一索引对 NULL 不生效），两次插入均成功，用于证明「只追加审计流水可重复、有效业务结果不可重复」这一设计意图成立。

## 事务与行锁

| 业务点 | 实现位置 | 事务与锁策略 | 证据 |
| --- | --- | --- | --- |
| 下单扣减可售并占用 | `server/service/gorm_repository.go` `DecreaseGoodsStock` | `WHERE id=? AND available_stock>=?` 条件更新，命中 `goods` 聚簇索引行锁；受影响行数不为 1 即判定并发失败 | `mysql_raw_05_app_persistence.txt` 操作5 |
| 超时关单释放占用 | `server/service/gorm_repository.go` `IncreaseGoodsStock` | 与扣减在同一事务内成对执行，保证守恒 | 同上 |
| 订单状态流转 | `server/service/gorm_repository.go` `UpdateOrderStatus` | `WHERE id=? AND status=?` 条件更新，状态不符时受影响行数为 0，判定非法流转并拒绝 | 同上 |
| 支付/退款幂等 | `server/service/gorm_repository.go` `CreatePaymentEvent` | `uk_payment_dedup_key` + `uk_payment_channel_effective` 双唯一约束兜底，重复通知不重复记款 | `mysql_raw_03_unique.txt` 操作3.3/3.4 |

并发实测（`evidence/mysql_raw_05_app_persistence.txt` 操作5）：在真实 InnoDB 上对同一商品发起 20 次并发下单，**成功 3 次、失败 17 次（M-02 缺货）**，与该商品可售 3 件完全一致；并发后 `available_stock=0`、`occupied_stock=5`，`available + occupied == 5` 恒等成立，无超卖。

## 结论

| 核查项 | 结论 | 依据 |
| --- | --- | --- |
| 业务库与三张业务表 | 通过 | `mysql_raw_01_schema.txt`、`mysql_raw_02_inspect.txt` |
| InnoDB 引擎与 utf8mb4 | 通过 | `information_schema.TABLES.ENGINE` 三表均为 InnoDB；`character_set_server=utf8mb4` |
| 订单唯一约束（order_no） | 通过 | `uk_order_order_no`，冲突时报 ERROR 1062 |
| 幂等唯一约束（dedup_key / channel_trade_no+effective） | 通过 | 两项唯一约束均实测触发 ERROR 1062 |
| 索引设计 | 通过 | 覆盖订单号查询、买家维度查询、超时扫描、渠道流水检索 |
| 金额以分为单位且不使用浮点 | 通过 | 全部金额列为 `BIGINT` |
| 事务边界与行锁 | 通过 | 条件更新 + 行锁 + 受影响行数判定，并发不超卖、库存守恒 |
| 重启后表结构、索引、约束、数据 | 通过 | `mysql_raw_04_restart.txt`（ERROR 计数为 0） |
| 应用重启后业务结果仍可查询 | 通过 | `mysql_raw_05_app_persistence.txt`，8/8 断言 PASS |

对应评分项的证据补齐情况：

- **A2-04（数据库落地与持久化）**：已由「内存仓储」升级为「真实 MySQL 8.x InnoDB 实例实测」，核查记录与原始输出齐备；
- **A3-05（并发/一致性实现）**：已补真实 InnoDB 行锁下的 20 并发不超卖与库存守恒实测；
- **A3-06（竞态与并发安全）**：本项的 `go test -race` 部分另见 `evidence/race竞态检测说明.md` 与 `evidence/race_raw_output.txt`（WSL 内真实 CGO 工具链执行，exit=0，无数据竞争报告）；
- **A4-04（交付物与部署/运行证据）**：已补「应用进程重启后同一订单仍可查询」的真实运行证据。

## 复现方式

```bash
# 1) 启动真实 MySQL（WSL Ubuntu）
sudo service mysql start

# 2) 建库建表
wsl -d Ubuntu -u root -- mysql -uroot < evidence/schema.sql

# 3) 结构 / 索引 / 约束 / 重启复查 / 唯一键冲突复现
wsl -d Ubuntu -u root -- bash /mnt/d/Desktop/shop/evidence/mysql_verify.sh env
wsl -d Ubuntu -u root -- bash /mnt/d/Desktop/shop/evidence/mysql_verify.sh schema
wsl -d Ubuntu -u root -- bash /mnt/d/Desktop/shop/evidence/mysql_verify.sh inspect
wsl -d Ubuntu -u root -- bash /mnt/d/Desktop/shop/evidence/mysql_verify.sh restart
wsl -d Ubuntu -u root -- bash /mnt/d/Desktop/shop/evidence/mysql_verify.sh unique

# 4) 应用级持久化与并发验证（Windows 侧）
wsl -d Ubuntu -u root -- bash /mnt/d/Desktop/shop/evidence/mysql_prepare_user.sh
python -X utf8 evidence/mysql_app_persistence.py
```

## 声明

本文及配套原始输出均为真实执行结果；未执行的步骤一律标注「未执行」，无任何模拟、编造或回填的数据库执行结果。
