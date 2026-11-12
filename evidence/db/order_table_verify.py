#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""订单表 order_no 唯一索引 & 数据持久化验证（真实 MySQL/InnoDB 实例执行）。

对应文档：docs/db/order_table_verify.md
输出：evidence/db/order_table_verify_raw.txt（UTF-8）
用法：python -X utf8 evidence/db/order_table_verify.py
"""
import pathlib
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = ROOT / 'evidence/db/order_table_verify_raw.txt'
WSL = ['wsl', '-d', 'Ubuntu', '-u', 'root', '--']
LINES = []

INSERT = ("INSERT INTO `order`(order_no, buyer_id, goods_id, goods_no, goods_name, quantity, "
          "unit_price, total_amount, status, expires_at)\n"
          "VALUES ('ORD001', 1, 1, 'G001', '测试商品', 1, 9900, 9900, 'pending', '2026-12-31 23:59:59');")


def log(text=''):
    LINES.append(text)
    print(text)


def sql(statement, db='shop_trade', label=None):
    proc = subprocess.run(WSL + ['mysql', '-uroot', db], input=statement, capture_output=True,
                          text=True, encoding='utf-8', errors='replace')
    if label:
        log('----- %s -----' % label)
        log('$ mysql -uroot %s' % db)
    out = (proc.stdout or '') + (proc.stderr or '')
    log(out.rstrip())
    log('[exit=%d]' % proc.returncode)
    return proc.returncode, out


def main():
    log('===== 订单表 order_no 唯一索引 & 数据持久化验证（真实 MySQL/InnoDB）=====')
    log('时间：%s' % time.strftime('%Y-%m-%d %H:%M:%S'))
    log('')
    log('===== 步骤 0：环境与订单表约束 =====')
    sql('SELECT VERSION() AS mysql_version, @@default_storage_engine AS default_engine, '
        '@@character_set_server AS charset_server;', db='', label='版本与默认引擎')
    sql("SELECT CONSTRAINT_NAME, TABLE_NAME, CONSTRAINT_TYPE FROM information_schema.TABLE_CONSTRAINTS "
        "WHERE TABLE_SCHEMA='shop_trade' AND TABLE_NAME='order';", label='订单表约束')
    log('')
    log('===== 步骤 1：首次插入订单（插入成功）=====')
    sql("DELETE FROM `order` WHERE order_no IN ('ORD001','ORD001-TX');", label='清理历史验证数据')
    sql(INSERT, label='首次插入')
    sql("SELECT id, order_no, buyer_id, goods_id, goods_no, goods_name, quantity, unit_price, "
        "total_amount, status, expires_at FROM `order` WHERE order_no='ORD001';", label='插入结果校验')
    log('')
    log('===== 步骤 2：重复插入相同 order_no（唯一索引拦截）=====')
    sql(INSERT, label='重复插入')
    log('')
    log('===== 步骤 3：唯一索引定义核对 =====')
    sql("SHOW INDEX FROM `order` WHERE Key_name='uk_order_order_no';", label='SHOW INDEX')
    log('')
    log('===== 步骤 4：事务回滚后不落盘 =====')
    sql("START TRANSACTION;\n"
        "INSERT INTO `order`(order_no, buyer_id, goods_id, goods_no, goods_name, quantity, unit_price, "
        "total_amount, status, expires_at)\n"
        "VALUES ('ORD001-TX', 1, 1, 'G001', '测试商品', 1, 9900, 9900, 'pending', '2026-12-31 23:59:59');\n"
        "SELECT COUNT(*) AS rows_in_transaction FROM `order` WHERE order_no='ORD001-TX';\n"
        "ROLLBACK;\n"
        "SELECT COUNT(*) AS rows_after_rollback FROM `order` WHERE order_no='ORD001-TX';", label='事务回滚')
    log('')
    log('===== 步骤 5：数据库重启后数据持久化校验 =====')
    r = subprocess.run(WSL + ['bash', '-c', 'service mysql restart'], capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    log('$ service mysql restart')
    log((r.stdout or '') + (r.stderr or ''))
    for _ in range(30):
        time.sleep(1)
        ping = subprocess.run(WSL + ['mysqladmin', '-uroot', 'ping'], capture_output=True, text=True,
                              encoding='utf-8', errors='replace')
        if 'alive' in (ping.stdout or ''):
            log('$ mysqladmin ping -> %s' % (ping.stdout or '').strip())
            break
    sql("SELECT id, order_no, buyer_id, goods_no, quantity, unit_price, total_amount, status, "
        "expires_at, created_at FROM `order` WHERE order_no='ORD001';", label='重启后仍可查询')
    log('')
    log('===== 步骤 6：清理验证数据 =====')
    sql("DELETE FROM `order` WHERE order_no IN ('ORD001','ORD001-TX');", label='删除验证数据')
    sql("SELECT COUNT(*) AS rows_after_cleanup FROM `order` WHERE order_no IN ('ORD001','ORD001-TX');",
        label='清理后校验')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text('\n'.join(LINES) + '\n', encoding='utf-8')
    print('written: %s' % OUT)


if __name__ == '__main__':
    main()