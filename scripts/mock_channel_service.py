#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""可控模拟支付渠道服务（独立进程，题面共同要求第 5 条）。

只做 HTTP 通知转发与可重复的响应留痕，不含业务状态机、不落库、不改动订单状态。
主服务仍是唯一的业务裁决方；本服务不是真实第三方支付接入。

用法：python scripts/mock_channel_service.py --port 18085 --target http://127.0.0.1:18084
"""
import argparse
import datetime
import json
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROUTES = {
    '/health': None,
    '/notify/payment': '/api/v1/payment/callback',
    '/notify/refund': '/api/v1/refund/callback',
    '/notify/late-refund': '/api/v1/late-payment/refund/callback',
    '/notify/timeout': '/api/v1/payment/timeout',
}

STATE = {'target': 'http://127.0.0.1:8080'}


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, payload):
        raw = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == '/health':
            self._send(200, {'status': 'ok', 'service': 'mock-channel',
                             'target': STATE['target'], 'time': datetime.datetime.now().astimezone().isoformat()})
        else:
            self._send(404, {'code': 'NOT_FOUND', 'message': '未知模拟渠道端点'})

    def do_POST(self):
        if self.path == '/health':
            self._send(405, {'code': 'METHOD_NOT_ALLOWED'})
            return
        upstream = ROUTES.get(self.path)
        if upstream is None:
            self._send(404, {'code': 'NOT_FOUND', 'message': '未知模拟渠道端点'})
            return
        length = int(self.headers.get('Content-Length', '0'))
        try:
            body = json.loads(self.rfile.read(length) or b'{}')
        except ValueError as exc:
            self._send(400, {'code': 'BAD_JSON', 'message': str(exc)})
            return
        account = self.headers.get('X-Demo-Account', 'mock01')
        req = urllib.request.Request(
            STATE['target'] + upstream,
            data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'X-Demo-Account': account},
            method='POST')
        try:
            with urllib.request.urlopen(req, timeout=8) as r:
                status, raw = r.status, r.read().decode('utf-8', 'replace')
        except urllib.error.HTTPError as e:
            status, raw = e.code, e.read().decode('utf-8', 'replace')
        except Exception as exc:                 # noqa: BLE001
            self._send(502, {'code': 'UPSTREAM_ERROR', 'message': str(exc)})
            return
        try:
            parsed = json.loads(raw)
        except ValueError:
            parsed = None
        self._send(200, {
            'mock_service': 'mock-channel (independent process)',
            'endpoint': self.path,
            'upstream': upstream,
            'upstream_status': status,
            'forwarded_body': body,
            'upstream_response': parsed if parsed is not None else raw,
            'time': datetime.datetime.now().astimezone().isoformat(),
        })

    def log_message(self, fmt, *args):
        pass


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--port', type=int, default=18085)
    ap.add_argument('--target', default='http://127.0.0.1:8080')
    args = ap.parse_args()
    STATE['target'] = args.target.rstrip('/')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'mock-channel listening 127.0.0.1:{args.port} -> {STATE["target"]}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
