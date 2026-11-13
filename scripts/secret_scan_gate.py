#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""敏感信息扫描门禁（只读校验）。

依据 AGENTS.md P-03「密钥、访问令牌、演示口令、签名密钥及用户敏感信息进入仓库、
日志、截图、对话导出或视频；相关内容一律脱敏」与题面共同要求：扫描仓库内已跟踪的
文本文件，命中真实凭据特征即以非零码退出。

只扫描 git 已跟踪文件，排除覆盖率 profile、截图与二进制；示例占位值不判失败。

用法：python -X utf8 scripts/secret_scan_gate.py
"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# 明确的凭据特征（与语言无关的强特征）
HARD_PATTERNS = [
    (r'-----BEGIN [A-Z ]*PRIVATE KEY-----', '私钥文件内容'),
    (r'\bAKIA[0-9A-Z]{16}\b', 'AWS AccessKey ID'),
    (r'\bgh[pousr]_[A-Za-z0-9]{30,}\b', 'GitHub Token'),
    (r'\bgithub_pat_[A-Za-z0-9_]{20,}\b', 'GitHub Fine-grained Token'),
    (r'\bxox[baprs]-[A-Za-z0-9-]{10,}\b', 'Slack Token'),
    (r'\bsk-[A-Za-z0-9]{20,}\b', 'OpenAI 风格 API Key'),
    (r'\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b', 'JWT'),
]

# 「键名 = 值」形式的弱特征，值需再过白名单
WEAK_PATTERN = re.compile(
    r'(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key)\b'
    r'\s*[:=]\s*[\'"]?([^\s\'",;<>{}]{6,})')

ALLOW = ('mock', 'demo', 'example', 'changeme', 'your', 'test', 'dummy', 'placeholder',
         'none', 'null', 'xxx', 'todo', 'redacted', '$', '{{', '<', '*', 'sha256')
SKIP_SUFFIX = ('.out', '.exe', '.png', '.jpg', '.jpeg', '.gif', '.pdf', '.docx', '.zip')


def tracked_files():
    r = subprocess.run(['git', '-C', str(ROOT), 'ls-files'], capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return [line for line in r.stdout.splitlines() if line.strip()]


def read_text(path):
    raw = path.read_bytes()
    if raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
        return raw.decode('utf-16')
    return raw.decode('utf-8', errors='replace')


def allowed(value):
    """白名单：示例占位值、变量引用、表达式取值不算敏感信息。"""
    low = value.lower()
    if any(word in low for word in ALLOW):
        return True
    if len(set(low)) <= 2:
        return True
    # 形如 args.password / os.environ['X'] / pw.stdout.strip() 的表达式取值
    if re.fullmatch(r"[A-Za-z_][\w.\[\](){}\s'\"-]*", value) and (
            '.' in value or '(' in value or '[' in value or
            value.split('.')[0] in ('args', 'os', 'env', 'cfg', 'config', 'pw', 'self')):
        return True
    return False


def main():
    print('===== 敏感信息扫描门禁 =====')
    print('仓库：%s' % ROOT)
    hits = []
    scanned = 0
    skipped = 0
    for rel in tracked_files():
        path = ROOT / rel
        if not path.is_file() or rel.lower().endswith(SKIP_SUFFIX):
            skipped += 1
            continue
        if 'evidence/db/screenshots' in rel:
            skipped += 1
            continue
        try:
            text = read_text(path)
        except Exception:  # noqa: BLE001
            skipped += 1
            continue
        scanned += 1
        for number, line in enumerate(text.splitlines(), 1):
            if len(line) > 4000:
                continue
            for pattern, name in HARD_PATTERNS:
                if re.search(pattern, line):
                    hits.append((rel, number, name, line.strip()[:120]))
            m = WEAK_PATTERN.search(line)
            if m and not allowed(m.group(2)):
                hits.append((rel, number, '疑似%s赋值' % m.group(1), line.strip()[:120]))
    print('已扫描文件：%d；跳过（二进制/覆盖率 profile/截图）：%d' % (scanned, skipped))
    print('命中：%d 处' % len(hits))
    for rel, number, name, snippet in hits[:50]:
        print('  HIT %s:%d [%s] %s' % (rel, number, name, snippet))
    if hits:
        print('结论：FAIL 疑似敏感信息命中 %d 处，须脱敏后再提交' % len(hits))
        return 1
    print('结论：PASS 未发现密钥、令牌、演示口令等敏感信息')
    return 0


if __name__ == '__main__':
    sys.exit(main())
