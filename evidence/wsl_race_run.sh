#!/usr/bin/env bash
set -u
cd /mnt/d/Desktop/shop || exit 1
export CGO_ENABLED=1
export GOPROXY=https://goproxy.cn,direct
export GOFLAGS=-mod=mod
echo "== toolchain =="
go version
gcc --version | head -1
echo "CGO_ENABLED=${CGO_ENABLED}"
echo "GOPROXY=${GOPROXY}"
echo "== go test -race ./... -count=1 =="
go test -race ./... -count=1 2>&1
echo "race_exit=$?"
