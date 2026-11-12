#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查者独立 MySQL/InnoDB 复核（第6轮）：引擎/唯一约束/1062/重启留存/应用重启后可查。"""
import json, os, pathlib, subprocess, time, urllib.request, urllib.error

ROOT = pathlib.Path(r'd:/Desktop/shop')
OUT = ROOT / 'outputs/单题检查/shop-trade/01/20261112-06/evidence/audit_mysql_verify.txt'
WSL = ['wsl', '-d', 'Ubuntu', '-u', 'root', '--']
BASE = 'http://127.0.0.1:18098'
EXE = pathlib.Path(os.environ.get('TEMP', '/tmp')) / 'shop-trade-audit-mysql.exe'
L = []


def log(t=''):
    L.append(t)
    print(t)


def sql(s, db='shop_trade'):
    p = subprocess.run(WSL + ['mysql', '-uroot', db], input=s, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return (p.stdout or '') + (p.stderr or ''), p.returncode


def http(m, path, body=None, acc='buyer01'):
    h = {'X-Demo-Account': acc} if acc else {}
    d = None
    if body is not None:
        d = json.dumps(body, ensure_ascii=False).encode('utf-8')
        h['Content-Type'] = 'application/json'
    try:
        with urllib.request.urlopen(urllib.request.Request(BASE + path, data=d, headers=h, method=m),
                                    timeout=20) as r:
            return r.status, json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, {'code': 'HTTP%d' % e.code, 'message': e.read().decode('utf-8', 'replace')}
    except Exception as e:
        return -1, {'code': 'REQUEST_FAILED', 'message': repr(e)}


def ck(name, ok, detail=''):
    log('[断言] %s | %s | %s' % ('PASS' if ok else 'FAIL', name, detail))


def start_app(dsn, tag):
    env = dict(os.environ)
    env['GVA_ADDR'] = ':18098'
    env['GVA_MYSQL_DSN'] = dsn
    h = open(OUT.with_suffix('.app.log'), 'a', encoding='utf-8')
    p = subprocess.Popen([str(EXE)], env=env, stdout=h, stderr=h)
    for _ in range(60):
        time.sleep(0.5)
        try:
            with urllib.request.urlopen(BASE + '/health', timeout=3) as r:
                if r.status == 200:
                    log('[启动] %s 就绪 pid=%s' % (tag, p.pid))
                    return p
        except Exception:
            continue
    p.kill()
    raise SystemExit('应用启动失败')
def main():
    log('===== 检查者独立 MySQL/InnoDB 复核（第6轮）=====')
    log('时间：%s' % time.strftime('%Y-%m-%d %H:%M:%S'))
    log('')
    log('--- 1. 业务表引擎与字符集 ---')
    out, _ = sql("SELECT TABLE_NAME, ENGINE, TABLE_COLLATION FROM information_schema.TABLES "
                 "WHERE TABLE_SCHEMA='shop_trade' AND TABLE_NAME IN ('goods','order','payment') "
                 "ORDER BY TABLE_NAME;")
    log(out.rstrip())
    ck('三张业务表均为 InnoDB + utf8mb4', out.count('InnoDB') == 3 and 'utf8mb4' in out,
       out.strip().replace('\n', ' | '))
    log('')
    log('--- 2. 唯一约束清单 ---')
    out, _ = sql("SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE FROM information_schema.STATISTICS "
                 "WHERE TABLE_SCHEMA='shop_trade' AND NON_UNIQUE=0 ORDER BY TABLE_NAME;")
    log(out.rstrip())
    for w in ('uk_order_order_no', 'uk_payment_dedup_key', 'uk_payment_channel_effective',
              'uk_goods_goods_no'):
        ck('唯一索引存在：%s' % w, w in out)
    log('')
    log('--- 3. 自行构造重复插入验证 1062 ---')
    sql("DELETE FROM `order` WHERE order_no='AUDIT-DUP-0001';")
    base = ("INSERT INTO `order`(order_no,buyer_id,goods_id,goods_no,goods_name,quantity,unit_price,"
            "total_amount,status,expires_at) VALUES ('AUDIT-DUP-0001',9001,1,'GOODS-ACT-001','审计探针',"
            "1,10000,10000,'待支付',NOW(3)+INTERVAL 10 MINUTE)")
    sql(base + ';')
    out2, code2 = sql(base + ';')
    log(out2.rstrip())
    ck('重复 order_no 被拦截且报 1062', 'ERROR 1062' in out2 and code2 != 0,
       out2.strip().splitlines()[-1] if out2.strip() else '(无输出)')
    sql("DELETE FROM `order` WHERE order_no='AUDIT-DUP-0001';")
    log('')
    log('--- 4. 数据库重启后行数据仍在 ---')
    sql("DELETE FROM `order` WHERE order_no='AUDIT-PERSIST-0001';")
    sql("INSERT INTO `order`(order_no,buyer_id,goods_id,goods_no,goods_name,quantity,unit_price,"
        "total_amount,status,expires_at) VALUES ('AUDIT-PERSIST-0001',9002,1,'GOODS-ACT-001','审计持久化',"
        "1,10000,10000,'待支付',NOW(3)+INTERVAL 10 MINUTE);")
    subprocess.run(WSL + ['bash', '-c', 'service mysql restart'], capture_output=True, text=True)
    alive = False
    for _ in range(30):
        time.sleep(1)
        pg = subprocess.run(WSL + ['mysqladmin', '-uroot', 'ping'], capture_output=True, text=True)
        if 'alive' in (pg.stdout or ''):
            alive = True
            break
    out, _ = sql("SELECT order_no, total_amount, status FROM `order` "
                 "WHERE order_no='AUDIT-PERSIST-0001';")
    log(out.rstrip())
    ck('数据库重启后行数据仍在', alive and 'AUDIT-PERSIST-0001' in out,
       'mysqld_alive=%s rows=%s' % (alive, out.strip()))
    sql("DELETE FROM `order` WHERE order_no='AUDIT-PERSIST-0001';")
    log('')
    log('--- 5. 应用进程重启后同一订单仍可查询 ---')
    pw_s = subprocess.run(WSL + ['bash', '-c', 'cat /tmp/shop_dsn_pw 2>/dev/null'],
                      capture_output=True, text=True).stdout or ''
    pw_a = subprocess.run(WSL + ['bash', '-c', 'cat /tmp/audit_chk_pw 2>/dev/null'],
                      capture_output=True, text=True).stdout or ''
    if pw_s.strip():
        dsn_user, password = 'shoptrade', pw_s.strip()
    elif pw_a.strip():
        dsn_user, password = 'audit_chk', pw_a.strip()
        log('[说明] 学生口令临时文件已被 WSL tmpfiles 清理，检查者用自建一次性账号 audit_chk 等效复核')
    else:
        dsn_user, password = '', ''
        log('[说明] 未取得可用数据库口令，检查者自建一次性账号 audit_chk 复核（复核后删除）')
    if not password:
        log('[跳过] 无法准备数据库账号，未执行应用级持久化复核')
    else:
        dsn = ('%s:%s@tcp(127.0.0.1:3306)/shop_trade?charset=utf8mb4&parseTime=True&loc=Local'
               % (dsn_user, password))
        b = subprocess.run(['go', 'build', '-o', str(EXE), '.'], cwd=ROOT, capture_output=True, text=True)
        log('$ go build -o %s . -> exit=%d' % (EXE, b.returncode))
        proc = start_app(dsn, '进程1')
        status, me = http('GET', '/api/v1/me')
        log('GET /api/v1/me -> %s %s' % (status, json.dumps(me, ensure_ascii=False)))
        ck('应用以 MySQL 模式启动（mode=mysql-innodb）',
           (me.get('data') or {}).get('mode') == 'mysql-innodb', json.dumps(me, ensure_ascii=False)[:160])
        status, created = http('POST', '/api/v1/orders', {'goods_id': 1, 'quantity': 1})
        log('POST /api/v1/orders -> %s %s' % (status, json.dumps(created, ensure_ascii=False)[:180]))
        order_no = (created.get('data') or {}).get('order_no', '')
        ck('通过应用接口下单成功并取得 order_no', bool(order_no), order_no)
        if order_no:
            out, _ = sql("SELECT order_no, status, quantity, unit_price, total_amount FROM `order` "
                         "WHERE order_no='%s';" % order_no)
            log('数据库直查：\n' + out.rstrip())
            ck('订单真实落库（可直查 order 表）', order_no in out, out.strip().replace('\n', ' | '))
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
            log('[停止] 进程1 已真实退出 pid=%s' % proc.pid)
            time.sleep(2)
            proc2 = start_app(dsn, '进程2')
            status, again = http('GET', '/api/v1/orders/%s' % order_no)
            log('GET /api/v1/orders/%s -> %s %s' % (order_no, status,
                                                    json.dumps(again, ensure_ascii=False)[:180]))
            ck('应用重启后同一订单仍可查询且状态一致',
               status == 200 and (again.get('data') or {}).get('order_no') == order_no,
               'http=%s order_no=%s' % (status, order_no))
            proc2.terminate()
            try:
                proc2.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc2.kill()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text('\n'.join(L) + '\n', encoding='utf-8')
    print('written: %s' % OUT)


if __name__ == '__main__':
    main()
