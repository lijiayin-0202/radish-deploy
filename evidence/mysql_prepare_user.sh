#!/usr/bin/env bash
# 准备「真实 MySQL 应用级验证」所需的本地账号。
# 口令随机生成，只保存在 WSL 的 /tmp/shop_dsn_pw（权限 600），不写入仓库、不回显。
# 用法：wsl -d Ubuntu -u root -- bash /mnt/d/Desktop/shop/evidence/mysql_prepare_user.sh
set -eu
PW="$(head -c 24 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 16)"
mysql -uroot <<SQL
CREATE USER IF NOT EXISTS 'shoptrade'@'%' IDENTIFIED BY '${PW}';
ALTER USER 'shoptrade'@'%' IDENTIFIED BY '${PW}';
GRANT ALL PRIVILEGES ON shop_trade.* TO 'shoptrade'@'%';
FLUSH PRIVILEGES;
SQL
printf '%s' "${PW}" > /tmp/shop_dsn_pw
chmod 600 /tmp/shop_dsn_pw
echo "app user prepared:"
mysql -uroot -e "SELECT user, host FROM mysql.user WHERE user='shoptrade';"
echo "password file: /tmp/shop_dsn_pw (mode 600, value not echoed)"
