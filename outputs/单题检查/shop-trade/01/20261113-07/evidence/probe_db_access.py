#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""探测本机 MySQL 账号权限与 shop_trade 库表现状（Windows 直连，不使用 WSL）。"""
import pymysql

QUERIES = [
    'SELECT CURRENT_USER(), VERSION()',
    'SHOW GRANTS FOR CURRENT_USER()',
    "SELECT table_name, engine, table_collation FROM information_schema.tables "
    "WHERE table_schema='shop_trade' ORDER BY table_name",
    "SELECT user, host, plugin FROM mysql.user ORDER BY user",
    "SELECT COUNT(*) FROM shop_trade.goods",
    "SELECT COUNT(*) FROM shop_trade.`order`",
    "SELECT COUNT(*) FROM shop_trade.payment",
]


def main():
    c = pymysql.connect(host='127.0.0.1', port=3306, user='audit_chk', password='',
                         connect_timeout=5, autocommit=True)
    cur = c.cursor()
    for q in QUERIES:
        try:
            cur.execute(q)
            print('--', q)
            for r in cur.fetchall():
                print('   ', r)
        except Exception as e:
            print('--', q, 'ERR', str(e)[:160])
    c.close()


if __name__ == '__main__':
    main()
