#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工单表 ticket_no 唯一索引 & 数据持久化验证（真实 MySQL/InnoDB 实例执行）。

对应文档：docs/db/ticket_table_verify.md
建表脚本：evidence/db/ticket_schema.sql
输出：evidence/db/ticket_table_verify_raw.txt（UTF-8）
用法：python -X utf8 evidence/db/ticket_table_verify.py
"""
import pathlib
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = ROOT / 'evidence/db/ticket_table_verify_raw.txt'
DDL = ROOT / 'evidence/db/ticket_schema.sql'
WSL = ['wsl', '-d', 'Ubuntu', '-u', 'root', '--']
LINES = []

INSERT = ("INSERT INTO `ticket`(ticket_no, user_id, content, status, created_at)\n"
          "VALUES ('TK001', 1, '订单 ORD001 未收到货，请协助核查', 'pending', NOW(3));")


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
    log('===== 工单表 ticket_no 唯一索引 & 数据持久化验证（真实 MySQL/InnoDB）=====')
    log('时间：%s' % time.strftime('%Y-%m-%d %H:%M:%S'))
    log('')
    log('===== 步骤 0：执行建表脚本与环境核对 =====')
    ddl = subprocess.run(WSL + ['bash', '-c', 'mysql -uroot shop_trade < /mnt/d/Desktop/shop/evidence/db/ticket_schema.sql'],
                         capture_output=True, text=True, encoding='utf-8', errors='replace')
    log('$ mysql -uroot shop_trade < evidence/db/ticket_schema.sql')
    log(((ddl.stdout or '') + (ddl.stderr or '')).rstrip())
    log('[exit=%d]' % ddl.returncode)
    sql('SELECT VERSION() AS mysql_version, @@default_storage_engine AS default_engine, '
        '@@character_set_server AS charset_server;', db='', label='版本与默认引擎')
    sql("SELECT TABLE_NAME, ENGINE, TABLE_COLLATION FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA='shop_trade' AND TABLE_NAME='ticket';", label='ticket 表引擎与字符集')
    sql("SELECT CONSTRAINT_NAME, TABLE_NAME, CONSTRAINT_TYPE FROM information_schema.TABLE_CONSTRAINTS "
        "WHERE TABLE_SCHEMA='shop_trade' AND TABLE_NAME='ticket';", label='ticket 表约束')
    log('')
    log('===== 步骤 1：首次插入工单（插入成功）=====')
    sql("DELETE FROM `ticket` WHERE ticket_no IN ('TK001','TK001-TX');", label='清理历史验证数据')
    sql(INSERT, label='首次插入')
    sql("SELECT id, ticket_no, user_id, content, status, created_at FROM `ticket` WHERE ticket_no='TK001';",
        label='插入结果校验')
    log('')
    log('===== 步骤 2：重复插入相同 ticket_no（唯一索引拦截）=====')
    sql(INSERT, label='重复插入')
    log('')
    log('===== 步骤 3：唯一索引定义核对 =====')
    sql("SHOW INDEX FROM `ticket` WHERE Key_name='uk_ticket_ticket_no';", label='SHOW INDEX')
    log('')
    log('===== 步骤 4：事务回滚后不落盘 =====')
    sql("START TRANSACTION;\n"
        "INSERT INTO `ticket`(ticket_no, user_id, content, status, created_at)\n"
        "VALUES ('TK001-TX', 1, '事务回滚验证工单', 'processing', NOW(3));\n"
        "SELECT COUNT(*) AS rows_in_transaction FROM `ticket` WHERE ticket_no='TK001-TX';\n"
        "ROLLBACK;\n"
        "SELECT COUNT(*) AS rows_after_rollback FROM `ticket` WHERE ticket_no='TK001-TX';", label='事务回滚')
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
    sql("SELECT id, ticket_no, user_id, content, status, created_at FROM `ticket` WHERE ticket_no='TK001';",
        label='重启后仍可查询')
    sql("SHOW INDEX FROM `ticket` WHERE Key_name='uk_ticket_ticket_no';", label='重启后索引仍在')
    log('')
    log('===== 步骤 6：清理验证数据 =====')
    sql("DELETE FROM `ticket` WHERE ticket_no IN ('TK001','TK001-TX');", label='删除验证数据')
    sql("SELECT COUNT(*) AS rows_after_cleanup FROM `ticket` WHERE ticket_no IN ('TK001','TK001-TX');",
        label='清理后校验')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text('\n'.join(LINES) + '\n', encoding='utf-8')
    print('written: %s' % OUT)


if __name__ == '__main__':
    main()