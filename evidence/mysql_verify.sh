#!/usr/bin/env bash
# MySQL InnoDB 真实核查脚本（shop-trade · 题目 01）
# 在 WSL Ubuntu 内以 root 执行；输出为真实命令输出，供 evidence/mysql核查记录.md 引用。
# 用法：wsl -d Ubuntu -u root -- bash /mnt/d/Desktop/shop/evidence/mysql_verify.sh <stage>
# stage: env | schema | inspect | restart | unique | cleanup
set -u
STAGE="${1:-env}"
DB="shop_trade"
SCHEMA="/mnt/d/Desktop/shop/evidence/schema.sql"

say() { echo "$*"; }

sql() {
  say ""
  say "--------------------------------------------------------------"
  say "\$ mysql -uroot ${2:+$2} -e \"$1\""
  say "--------------------------------------------------------------"
  mysql -uroot ${2:+$2} -e "$1" 2>&1
}

run() {
  say ""
  say "--------------------------------------------------------------"
  say "\$ $*"
  say "--------------------------------------------------------------"
  "$@" 2>&1
}

wait_up() {
  for _ in $(seq 1 40); do
    mysqladmin ping >/dev/null 2>&1 && return 0
    sleep 1
  done
  return 1
}

case "$STAGE" in
  env)
    say "===== 阶段 0：实例与版本 ====="
    run /usr/sbin/mysqld --version
    say "\$ service mysql start"
    service mysql start 2>&1 | tail -2
    wait_up
    say "\$ mysqladmin ping"
    mysqladmin ping 2>&1
    sql "SELECT VERSION() AS version, @@default_storage_engine AS default_engine, @@character_set_server AS charset_server, @@collation_server AS collation_server;"
    sql "SHOW ENGINES;"
    sql "SHOW VARIABLES WHERE Variable_name IN ('bind_address','port','innodb_version','lower_case_table_names','transaction_isolation','innodb_lock_wait_timeout');"
    ;;

  schema)
    say "===== 阶段 1：执行 evidence/schema.sql 建库建表 ====="
    say "\$ mysql -uroot < ${SCHEMA}"
    mysql -uroot < "$SCHEMA" 2>&1
    say "schema_script_exit=$?"
    ;;

  inspect)
    say "===== 阶段 2：库表结构、索引与约束核查 ====="
    sql "SHOW DATABASES LIKE '${DB}';"
    sql "SHOW TABLES;" "${DB}"
    sql "SELECT TABLE_NAME, ENGINE, TABLE_COLLATION, TABLE_COMMENT FROM information_schema.TABLES WHERE TABLE_SCHEMA='${DB}' ORDER BY TABLE_NAME;"
    sql "SHOW CREATE TABLE \`goods\`\G" "${DB}"
    sql "SHOW CREATE TABLE \`order\`\G" "${DB}"
    sql "SHOW CREATE TABLE \`payment\`\G" "${DB}"
    sql "SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, SEQ_IN_INDEX, COLUMN_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA='${DB}' ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;"
    sql "SELECT CONSTRAINT_NAME, TABLE_NAME, CONSTRAINT_TYPE FROM information_schema.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA='${DB}' ORDER BY TABLE_NAME, CONSTRAINT_NAME;"
    sql "SELECT goods_no, name, unit_price, available_stock, occupied_stock, status FROM goods ORDER BY id;" "${DB}"
    ;;

  restart)
    say "===== 阶段 3：数据库重启后复查 ====="
    say "\$ service mysql restart"
    service mysql restart 2>&1 | tail -2
    wait_up
    say "\$ mysqladmin ping"
    mysqladmin ping 2>&1
    sql "SELECT VERSION() AS version, @@port AS port, @@innodb_version AS innodb_version;"
    sql "SHOW TABLES;" "${DB}"
    sql "SHOW INDEX FROM \`order\`;" "${DB}"
    sql "SHOW INDEX FROM \`goods\`;" "${DB}"
    sql "SHOW INDEX FROM \`payment\`;" "${DB}"
    sql "SELECT CONSTRAINT_NAME, TABLE_NAME, CONSTRAINT_TYPE FROM information_schema.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA='${DB}' ORDER BY TABLE_NAME;"
    sql "SELECT COUNT(*) AS goods_rows FROM goods;" "${DB}"
    sql "SELECT COUNT(*) AS order_rows FROM \`order\`;" "${DB}"
    sql "SELECT COUNT(*) AS payment_rows FROM payment;" "${DB}"
    ;;

  unique)
    say "===== 阶段 4：唯一键冲突复现 ====="
    say "--- 4.1 写入订单基线数据 ---"
    sql "INSERT INTO \`order\` (order_no,buyer_id,goods_id,goods_no,goods_name,quantity,unit_price,total_amount,status,expires_at) VALUES ('UNIQ-PROBE-0001',1001,1,'GOODS-ACT-001','活动商品',1,10000,10000,'待支付',NOW(3)+INTERVAL 10 MINUTE) ON DUPLICATE KEY UPDATE order_no=VALUES(order_no);" "${DB}"
    say "--- 4.2 重复插入相同 order_no：预期 uk_order_order_no 唯一约束报错 ---"
    sql "INSERT INTO \`order\` (order_no,buyer_id,goods_id,goods_no,goods_name,quantity,unit_price,total_amount,status,expires_at) VALUES ('UNIQ-PROBE-0001',1002,1,'GOODS-ACT-001','活动商品',1,10000,10000,'待支付',NOW(3)+INTERVAL 10 MINUTE);" "${DB}"
    say "--- 4.3 重复插入相同 dedup_key：预期 uk_payment_dedup_key 唯一约束报错 ---"
    sql "INSERT INTO payment (order_id,order_no,channel_trade_no,dedup_key,effective,event_type,result,amount,occurred_at) VALUES (1,'UNIQ-PROBE-0001','TRADE-UNIQ-0001','DEDUP-UNIQ-0001',1,'支付通知','成功',10000,NOW(3));" "${DB}"
    sql "INSERT INTO payment (order_id,order_no,channel_trade_no,dedup_key,effective,event_type,result,amount,occurred_at) VALUES (1,'UNIQ-PROBE-0001','TRADE-UNIQ-0001','DEDUP-UNIQ-0001',1,'支付通知','成功',10000,NOW(3));" "${DB}"
    say "--- 4.4 重复插入相同 (channel_trade_no, effective)：预期 uk_payment_channel_effective 唯一约束报错 ---"
    sql "INSERT INTO payment (order_id,order_no,channel_trade_no,dedup_key,effective,event_type,result,amount,occurred_at) VALUES (1,'UNIQ-PROBE-0001','TRADE-UNIQ-0002','DEDUP-UNIQ-0002',1,'支付通知','成功',10000,NOW(3));" "${DB}"
    sql "INSERT INTO payment (order_id,order_no,channel_trade_no,dedup_key,effective,event_type,result,amount,occurred_at) VALUES (1,'UNIQ-PROBE-0001','TRADE-UNIQ-0002','DEDUP-UNIQ-0003',1,'支付通知','成功',10000,NOW(3));" "${DB}"
    say "--- 4.5 effective 为 NULL 的审计事件允许重复追加（唯一索引对 NULL 不生效）---"
    sql "INSERT INTO payment (order_id,order_no,channel_trade_no,dedup_key,effective,event_type,result,amount,failure_reason,occurred_at) VALUES (1,'UNIQ-PROBE-0001','TRADE-UNIQ-0001',NULL,NULL,'支付通知','重复通知幂等',0,'重复支付通知已幂等处理，未重复记款',NOW(3));" "${DB}"
    sql "INSERT INTO payment (order_id,order_no,channel_trade_no,dedup_key,effective,event_type,result,amount,failure_reason,occurred_at) VALUES (1,'UNIQ-PROBE-0001','TRADE-UNIQ-0001',NULL,NULL,'支付通知','重复通知幂等',0,'重复支付通知已幂等处理，未重复记款',NOW(3));" "${DB}"
    sql "SELECT id, order_no, channel_trade_no, dedup_key, effective, event_type, result, amount FROM payment ORDER BY id;" "${DB}"
    ;;

  cleanup)
    say "===== 阶段 5：清理唯一键复现产生的探测数据 ====="
    sql "DELETE FROM payment WHERE order_no='UNIQ-PROBE-0001';" "${DB}"
    sql "DELETE FROM \`order\` WHERE order_no='UNIQ-PROBE-0001';" "${DB}"
    sql "SELECT COUNT(*) AS order_rows FROM \`order\`;" "${DB}"
    sql "SELECT COUNT(*) AS payment_rows FROM payment;" "${DB}"
    ;;
esac
