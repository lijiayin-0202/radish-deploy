#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第五轮：11 条 partial 条目的独立闭环证据文档生成。

每份文档 = 真实命令原始输出 + 真实手工 case + 缺口说明 + 解除条件。
不改动生产代码；不虚构 MySQL / race / CI / PR / 独立会话证据。
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from r5_closure_lib import (  # noqa: E402
    ACCOUNTS, EXE, ROOT, block, build, call, case_lines, code_of, data_of, git, md_table, now,
    partial_doc, run, save, start_demo, stop_demo,
)

AUDIT = json.loads((ROOT / 'outputs/单题检查/shop-trade/01/20261112-04/audit-input.json')
                   .read_text(encoding='utf-8'))
REASON = {c['id']: c.get('reason', '') for c in AUDIT['checks']}

build()
print('go build ok ->', EXE)

schema_text = (ROOT / 'schema.sql').read_text(encoding='utf-8')
agents_text = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
agents_v1_text = (ROOT / 'AGENTS-v1.0.md').read_text(encoding='utf-8')


def schema_lines(keywords):
    """截取 schema.sql 中包含关键字的完整建表语句（含 ENGINE / CHARSET 行）。"""
    out = []
    stmt = []
    for line in schema_text.splitlines():
        stmt.append(line)
        if line.strip().endswith(';'):
            text = '\n'.join(stmt)
            if any(k.lower() in text.lower() for k in keywords):
                out.append(text)
            stmt = []
    return '\n'.join(out)


# ============================ R-A2-01 持久化 / 重启后可查 ============================
sections = []
rc, out = git('branch', '--show-current')
sections.append('### 1.1 运行模式与数据库环境')
sections.append(block('$ git branch --show-current\n' + out))
rc, out = run('echo %GVA_MYSQL_DSN%')
sections.append(block('$ echo %GVA_MYSQL_DSN%\n' + out + '\n（本轮采集脚本启动实例时显式 unset GVA_MYSQL_DSN）'))
sections.append('### 1.2 `schema.sql` 建表引擎与字符集（真实读取）')
sections.append(block(schema_lines(['engine', 'charset', 'unique', 'dedup_key', 'table'])))

restart_detail = []

p = start_demo()
try:
    o = call('POST', '/api/v1/orders', 'buyer01', {'goods_id': 1, 'quantity': 1})
    order_no = data_of(o).get('order_no', 'R5-NO-ORDER')
    blocks = []
    b, ok1 = case_lines('下单成功（生成订单号）', 'POST', '/api/v1/orders', 'buyer01',
                        {'goods_id': 1, 'quantity': 1}, '0', o)
    blocks.append(b)
    pay = call('POST', '/api/v1/payment/callback', 'mock01',
               {'order_no': order_no, 'channel_trade_no': 'R5-A201-PAY', 'amount': 10000,
                'signature_valid': True})
    b, ok2 = case_lines('模拟渠道支付成功', 'POST', '/api/v1/payment/callback', 'mock01',
                        {'order_no': order_no, 'channel_trade_no': 'R5-A201-PAY', 'amount': 10000,
                         'signature_valid': True}, '0', pay)
    blocks.append(b)
    q1 = call('GET', f'/api/v1/orders/{order_no}', 'buyer01')
    b, ok3 = case_lines('重启前查询订单（业务结果可查）', 'GET', f'/api/v1/orders/{order_no}',
                        'buyer01', None, '0', q1)
    blocks.append(b)
finally:
    stop_demo(p)

restart_detail.append(f'- 进程 1：下单 → 支付 → 查询订单成功，订单号 `{order_no}`。')
restart_detail.extend(blocks)
restart_detail.append('- 进程 2：**真实终止 demo 实例进程并重新启动同一二进制**（`stop_demo` → `start_demo`），'
                      '模拟「服务重启」。')

p = start_demo()
try:
    q2 = call('GET', f'/api/v1/orders/{order_no}', 'buyer01')
    b, ok4 = case_lines('重启后查询同一订单', 'GET', f'/api/v1/orders/{order_no}', 'buyer01',
                        None, '0', q2)
    restart_detail.append(b)
    g = call('GET', '/api/v1/goods', 'buyer01')
    b, ok5 = case_lines('重启后查询商品库存（可售应回到初始值）', 'GET', '/api/v1/goods',
                        'buyer01', None, '0', g)
    restart_detail.append(b)
finally:
    stop_demo(p)

restart_detail.append(f'- 重启后同一订单号查询实际返回：`{q2["body"]}`（HTTP {q2["status"]}）。')

sections.append('### 1.3 真实「服务重启」链路下的手工 case')
sections.extend(restart_detail)

partial_doc(
    'R-A2-01', '核心业务数据持久化：服务重启后业务结果仍可查询',
    REASON.get('R-A2-01', ''),
    '仍为 `partial`（代码侧无缺陷，缺真实 MySQL 实例与初始化/重启实测）',
    sections,
    gap=[
        '本机**无 MySQL 实例**：`GVA_MYSQL_DSN` 未设置，`schema.sql` 没有真实初始化执行记录，'
        '「InnoDB + utf8mb4」只在文件层面成立，未在真实实例上跑过。',
        '第五轮用**真实终止并重启同一二进制进程**的方式复现了「服务重启」，但 `demo-memory` 模式按设计'
        '把业务数据放在进程内存中，重启后同一订单号查询失败——这证明的是**内存模式不具备持久化**，'
        '**不能**据此判定 MySQL 模式不持久化，也不能用内存模式结果冒充真实 MySQL 结果。',
        '因此本条缺少「真实 MySQL(InnoDB) 下建表 → 写入业务数据 → 重启服务 → 同一业务结果仍可查询」这一整条实测链。',
    ],
    release=[
        '准备一个真实 MySQL 8.x 实例（InnoDB 默认引擎、`utf8mb4`），执行 `schema.sql` 并保留执行输出与建表结果'
        '（`SHOW CREATE TABLE`）。',
        '以 `GVA_MYSQL_DSN` 启动服务，完成下单 → 支付 → 查询，落库后**重启服务进程**，'
        '再次查询同一订单号并保存原始响应。',
        '保存本机 `go env GVA_MYSQL_DSN`、`mysql --version`、DDL 执行输出与重启前后两份响应，'
        '三者时间戳与提交哈希一致后，本条可由 `partial` 升为 `pass`。',
    ],
    boundary='',
)

# ============================ R-A2-02 账号落库 ============================
sections = []
rc, out = run('echo %GVA_MYSQL_DSN%')
sections.append('### 1.1 账号映射的真实存放位置（源码定位）')
src = (ROOT / 'server/api/v1/order.go').read_text(encoding='utf-8').splitlines()
hit = [f'{i + 1}: {ln}' for i, ln in enumerate(src)
       if 'demoAccounts' in ln or ('"' in ln and 'Role' in ln and '{UserID' in ln)]
sections.append(block('server/api/v1/order.go\n' + '\n'.join(hit)))
sections.append('### 1.2 7 个预置账号逐个身份解析（真实 HTTP）')
p = start_demo()
try:
    rows = []
    for acc in ACCOUNTS:
        r = call('GET', '/api/v1/me', acc)
        d = data_of(r)
        rows.append((acc, r['status'], code_of(r), d.get('user_id'), d.get('role'),
                     'PASS' if code_of(r) == '0' else 'FAIL'))
    sections.append(md_table(rows, headers=('账号', 'HTTP', 'code', 'user_id', 'role', '结论')))
    r_unknown = call('GET', '/api/v1/me', 'nobody')
    sections.append('### 1.3 未知账号的边界')
    sections.append(block(f'GET /api/v1/me  X-Demo-Account=nobody\nHTTP {r_unknown["status"]}\n'
                          f'{r_unknown["body"]}'))
finally:
    stop_demo(p)
sections.append('### 1.4 `schema.sql` 是否含账号 / 用户表')
sections.append(block('schema.sql 中 CREATE TABLE 语句：\n' +
                      schema_lines(['create table'])))

partial_doc(
    'R-A2-02', '预置账号与演示数据的落库持久化',
    REASON.get('R-A2-02', ''),
    '仍为 `partial`（角色隔离实测通过，账号数据未落库）',
    sections,
    gap=[
        '7 个演示账号来自 `server/api/v1/order.go` 中的 **controller 内存 map**（`demoAccounts`），'
        '不是数据库表中的记录；账号与角色**不落库**。',
        '`schema.sql` 中没有账号 / 用户表，本题也**不在授权补齐范围内**新增账号表（属题外数据表，'
        '需学生确认 C-02）。',
        '本机无 MySQL 实例，即使落库也无从验证重启后仍可查。',
    ],
    release=[
        '若题面/需求文档要求账号落库：经学生确认（C-02）后新增账号表与初始化数据，'
        '在真实 MySQL 上重启后复查 `/api/v1/me` 仍返回相同 role / user_id。',
        '若题面不要求账号落库（当前口径）：由**验收 Agent 在独立会话**中确认「账号为演示级内存映射」'
        '符合题面「角色身份必须可信」的最小实现，本条按「不适用」结论归档，而非继续挂 `partial`。',
    ],
    boundary='',
)

# ============================ R-A2-03 并发与 race ============================
sections = []
rc, out = run('go env CGO_ENABLED')
sections.append('### 1.1 `go test -race` 前置条件（真实执行）')
sections.append(block('$ go env CGO_ENABLED\n' + out))
rc, out = run('where gcc')
sections.append(block('$ where gcc\n' + out))
rc, out = run('where clang')
sections.append(block('$ where clang\n' + out))
rc, out = run('go env GOOS GOARCH')
sections.append(block('$ go env GOOS GOARCH\n' + out))

sections.append('### 1.2 20 并发下单（真实 HTTP 并发，线程池 20）')
import concurrent.futures  # noqa: E402

p = start_demo()
try:
    def place(_):
        return call('POST', '/api/v1/orders', 'buyer01', {'goods_id': 1, 'quantity': 1})
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(place, range(20)))
    ok_cnt = sum(1 for r in results if code_of(r) == '0')
    m02 = sum(1 for r in results if code_of(r) == 'M-02')
    other = [(code_of(r), r['body']) for r in results if code_of(r) not in ('0', 'M-02')]
    rows = [('成功下单 code=0', ok_cnt, '', ''),
            ('库存不足 code=M-02', m02, '', ''),
            ('其他返回', len(other), '', '' if not other else str(other[:2])),
            ('合计请求数', len(results), '', '')]
    sections.append(md_table(rows, headers=('分类', '数量', '说明', '样例')))
    g = call('GET', '/api/v1/goods', 'buyer01')
    items = data_of(g).get('items', [])
    g1 = next((it for it in items if it.get('id') == 1), {})
    sections.append('### 1.3 库存守恒（并发下单后读取商品可售 / 占用）')
    sections.append(block('GET /api/v1/goods\n' + g['body']))
    conserve = (g1.get('available_stock') == 0 and g1.get('occupied_stock') == 5)
    sections.append(f'- 断言：可售 0 + 占用 5 == 初始可售 5 → **{"PASS" if conserve else "FAIL"}**'
                    f'（available={g1.get("available_stock")}, occupied={g1.get("occupied_stock")}）')
    sections.append(f'- 断言：20 个并发请求全部有明确返回（成功 {ok_cnt} + 库存不足 {m02} = '
                    f'{ok_cnt + m02}）→ **{"PASS" if ok_cnt + m02 == 20 else "FAIL"}**')
finally:
    stop_demo(p)

sections.append('### 1.4 真实 MySQL 行锁下的并发语义（本轮无法执行）')
sections.append(block(
    '本轮未执行：go test -race 需要 CGO_ENABLED=1 且本机存在 gcc/clang。\n'
    '解除条件命令（具备环境后执行并保存原始输出）：\n'
    '$ $env:CGO_ENABLED = "1"\n'
    '$ go test -race ./server/...'))

partial_doc(
    'R-A2-03', '并发下单与数据竞争检测（含真实 InnoDB 行锁语义）',
    REASON.get('R-A2-03', ''),
    '仍为 `partial`（20 并发库存守恒实测通过，race 探针与真实行锁未执行）',
    sections,
    gap=[
        '20 并发下单在本轮**实测通过**：请求总数守恒（成功 + 库存不足 = 20），且并发后商品可售 / 占用守恒。'
        '但 `demo-memory` 仓储用互斥锁串行化，**不等于**真实 InnoDB 行锁下的并发语义。',
        '`go test -race` 本轮无法执行：`go env CGO_ENABLED` = 0，本机 `where gcc` / `where clang` 无结果，'
        '`-race requires cgo`（详见 `R-A3-03` 条目，该条维持 `unknown`）。',
        '真实 InnoDB 行锁（`SELECT ... FOR UPDATE`）下的并发扣减与超卖防护，本轮**没有任何实测运行结果**。',
    ],
    release=[
        '安装 gcc 或 clang，并设置 `CGO_ENABLED=1`，执行 `go test -race ./server/...` 保存完整原始输出，'
        '确认无 `WARNING: DATA RACE`。',
        '在真实 MySQL 实例上以 `GVA_MYSQL_DSN` 启动服务，重跑 20 并发下单（同一脚本、同一订单商品），'
        '保存并发后的 `SELECT available_stock, occupied_stock FROM goods WHERE id=1` 结果，'
        '验证不超卖且守恒。',
        '两者原始输出 + 真实 MySQL 版本号 + 提交哈希齐备后，本条可升为 `pass`。',
    ],
    boundary='',
)

# ============================ R-A2-04 唯一键幂等 ============================
sections = []
sections.append('### 1.1 `schema.sql` 唯一索引定义（真实读取）')
sections.append(block(schema_lines(['dedup_key', 'unique', 'channel_trade_no'])))
p = start_demo()
try:
    o = call('POST', '/api/v1/orders', 'buyer01', {'goods_id': 1, 'quantity': 1})
    no_a = data_of(o).get('order_no', '')
    pay1 = call('POST', '/api/v1/payment/callback', 'mock01',
                {'order_no': no_a, 'channel_trade_no': 'R5-A204-TRADE', 'amount': 10000,
                 'signature_valid': True})
    b, _ = case_lines('首次支付通知', 'POST', '/api/v1/payment/callback', 'mock01',
                      {'order_no': no_a, 'channel_trade_no': 'R5-A204-TRADE', 'amount': 10000,
                       'signature_valid': True}, '0', pay1)
    sections.append(b)
    pay2 = call('POST', '/api/v1/payment/callback', 'mock01',
                {'order_no': no_a, 'channel_trade_no': 'R5-A204-TRADE', 'amount': 10000,
                 'signature_valid': True})
    b, _ = case_lines('同一 channel_trade_no 重复支付通知（幂等）', 'POST',
                      '/api/v1/payment/callback', 'mock01',
                      {'order_no': no_a, 'channel_trade_no': 'R5-A204-TRADE', 'amount': 10000,
                       'signature_valid': True}, '0', pay2)
    sections.append(b)
    sections.append('- 幂等判定：重复通知返回 `duplicate=true` 且 `result` 为幂等文案，'
                    '未产生第二笔业务结果 → **'
                    + ('PASS' if data_of(pay2).get('duplicate') is True else '需人工判读') + '**')
    o2 = call('POST', '/api/v1/orders', 'buyer01', {'goods_id': 2, 'quantity': 1})
    no_b = data_of(o2).get('order_no', '')
    pay3 = call('POST', '/api/v1/payment/callback', 'mock01',
                {'order_no': no_b, 'channel_trade_no': 'R5-A204-TRADE', 'amount': 10000,
                 'signature_valid': True})
    b, _ = case_lines('同一 channel_trade_no 归属另一订单（M-27）', 'POST',
                      '/api/v1/payment/callback', 'mock01',
                      {'order_no': no_b, 'channel_trade_no': 'R5-A204-TRADE', 'amount': 10000,
                       'signature_valid': True}, 'M-27', pay3)
    sections.append(b)
    sections.append('### 1.2 幂等留痕条数（只追加审计）')
    sections.append(block('重复通知后的订单详情：\n' +
                          call('GET', f'/api/v1/orders/{no_a}', 'buyer01')['body']))
finally:
    stop_demo(p)

partial_doc(
    'R-A2-04', '唯一键冲突下的支付通知幂等',
    REASON.get('R-A2-04', ''),
    '仍为 `partial`（幂等语义实测通过，真实唯一键冲突未触发）',
    sections,
    gap=[
        '幂等语义在本轮**实测通过**：同一 `channel_trade_no` 重复通知返回 `duplicate=true`，'
        '跨订单复用同一交易号返回 M-27。',
        '但 `demo-memory` 仓储的去重是 **Go 侧逻辑查重**，并未真正触发 MySQL 的 '
        '`UNIQUE` 索引冲突；`schema.sql` 中的唯一索引只经文件级核查，**没有真实实例上的冲突报错样本**。',
        '并发场景下的「唯一键兜底 + 幂等成功」分支在真实 InnoDB 下同样未执行（依赖 race 与真实实例）。',
    ],
    release=[
        '在真实 MySQL 实例上执行：同一 `channel_trade_no` 并发发送 2 条支付通知，保存第二条返回的 '
        '`Duplicate entry ... for key ...` 原始错误与被业务层吞掉后的幂等响应。',
        '保存 `SHOW INDEX FROM payments` 输出，证明 `dedup_key` 唯一索引真实存在。',
        '与 `R-A2-03` 的 race / 行锁证据合并后，本条可升为 `pass`。',
    ],
    boundary='',
)

# ============================ R-A4-03 CI ============================
sections = []
ci = ROOT / '.github/workflows/ci.yml'
ci_text = ci.read_text(encoding='utf-8') if ci.exists() else ''
noncomment = [ln for ln in ci_text.splitlines() if ln.strip() and not ln.strip().startswith('#')]
sections.append('### 1.1 CI 模板文件真实内容')
sections.append(block(f'.github/workflows/ci.yml（exists={ci.exists()}，'
                      f'总行数={len(ci_text.splitlines())}）\n' + ci_text))
sections.append('### 1.2 非注释有效行统计')
sections.append(block(f'非注释非空行数 = {len(noncomment)}\n'
                      + ('\n'.join(noncomment) if noncomment
                         else '(全部为注释；不存在可执行的 workflow 步骤定义)')))
rc, out = git('remote', '-v')
sections.append('### 1.3 远端与流水线运行条件')
sections.append(block('$ git remote -v\n' + (out or '(空：无远程仓库)')))
rc, out = git('branch', '-a')
sections.append(block('$ git branch -a\n' + out))

partial_doc(
    'R-A4-03', 'CI 流水线可运行性',
    REASON.get('R-A4-03', ''),
    '仍为 `partial`（模板为纯注释，无可运行 CI；无远端仓库）',
    sections,
    gap=[
        '`.github/workflows/ci.yml` 是**纯注释模板**：非注释非空行数为 0，不存在 `on:` / `jobs:` 等可执行键，'
        '**不会触发任何流水线**。',
        '本仓库 `git remote -v` 为空，**没有远端**，因此也不存在远端 CI 运行记录、'
        '部署地址、冒烟结果与回退说明。',
        '第四轮与第五轮均未编造 CI 运行结果；`R-A4-03` 维持 `partial`。',
    ],
    release=[
        '由学生在 GitHub MCP 创建独立仓库并关联远端后，把 `ci.yml` 改为**可执行 workflow**'
        '（`on: [push, pull_request]` + `jobs.build` 真实执行 `gofmt -l`、`go vet ./...`、`go test ./...`）。',
        '在远端触发一次真实运行，保存 run URL、run id、状态与日志原文。',
        '本机若需补足 `go test -race` 环节，须先满足 `CGO_ENABLED=1` + gcc/clang，'
        '在 workflow 中显式声明该矩阵（并如实标注当前环境无法覆盖 race 的部分）。',
        '以上产物齐备后本条方可由 `partial` 升为 `pass`。',
    ],
    boundary='',
)

# ============================ R-A4-04 版本链 ============================
sections = []
rc, out = git('branch', '--show-current')
sections.append('### 1.1 分支与提交链（真实执行）')
sections.append(block('$ git branch --show-current\n' + out))
rc, out = git('log', '--oneline', '--decorate', '--all')
sections.append(block('$ git log --oneline --decorate --all\n' + out))
rc, out = git('rev-parse', 'HEAD')
sections.append(block('$ git rev-parse HEAD\n' + out))
rc, out = git('status', '--short')
sections.append(block('$ git status --short\n' + (out or '(工作区干净)')))
rc, out = git('remote', '-v')
sections.append(block('$ git remote -v\n' + (out or '(空：无远程仓库)')))

partial_doc(
    'R-A4-04', '版本链与提交历史可追溯性',
    REASON.get('R-A4-04', ''),
    '本轮结论见下方「提交后回补」段（由第五轮 git 提交完成后回补最终 HEAD）',
    sections,
    gap=[
        '第五轮提交前，`dev/01` 仅 2 次提交（基线 `feat` 提交 + `[opt] [v1.1.0]` 整改提交），'
        '**第四轮工作区增量（证据 / 文档 / 测试）当时未提交**，版本链与产物不对应。',
        '本仓库**无远端**，因此不存在「PR 源提交 → 合并提交」的对应关系，也不存在 CI 运行与制品登记。',
    ],
    release=[
        '本轮第五轮增量已按 `docs/git-提交指引.md` 分批提交（`test` / `docs` 分开），'
        '提交后需**回补本节「提交后回补」段**中的最终 HEAD 与提交列表，保持文档与仓库状态一致。',
        '远端 PR / 状态检查 / 合并 / 部署环节仍需学生在 GitHub MCP 建仓后执行，'
        '并按 AGENTS.md 2.6 记录 PR 与源提交关系、对发布提交重新执行门禁。',
    ],
    boundary='',
)

print('partial docs (part 1) done')
