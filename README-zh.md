## lug-vpn-web —— 部署文档（Docker Compose）

文档语言：[English](README.md) / **中文**

本仓库提供一个 Flask Web 管理端，以及运行一套「基于 RADIUS 认证的 VPN/HTTPS 代理」所需的基础设施服务。全部组件通过 **`docker compose`** 按 **profiles** 部署与管理。

---

## 组件与 Profiles

### `core`（控制面）

- **`caddy`**：Web UI 的边缘反向代理（监听 **:80/:443**），配置文件为 `Caddyfile`
- **`web`**：Flask 应用（本仓库），容器内端口 **5000**（映射到 `${WEB_PORT}`）
- **`mysql`**：`mysql:5.7`（存储应用数据与 RADIUS 数据）
- **`freeradius`**：`ghcr.io/ustclug/docker-freeradius:nightly`（宿主机发布 UDP **1812/1813/3799**）

### `vpn`（数据面）

- **`ocserv`**：OpenConnect 服务端（使用 `network_mode: host`）

### `proxy`（数据面）

- **`light-server`**：HTTPS 代理（使用 `network_mode: host`）

### `acme`（工具）

- **`acme-sh`**：容器化 `acme.sh`，用于为 `ocserv` / `light-server` 申请与安装证书

### `acme-test`（可选）

- **`pebble`**：ACME 测试服务器（用于 CI/开发验证；生产部署不需要）

---

## 部署要求

- **Docker Engine + Docker Compose v2**（`docker compose ...`）
- **需要宿主机支持 host networking**（profiles `vpn` / `proxy`：`ocserv`、`light-server`）
- 本项目按 **Linux 的 host networking 语义**设计

如果宿主机是 **arm64**，某些镜像可能只有 **amd64** 版本；此时在 `.env` 中设置 `DOCKER_PLATFORM=linux/amd64` 以强制使用模拟运行。

---

## 配置（`.env`）

复制示例文件并修改：

```bash
cp .env.example .env
```

最低必须设置：

- **`SECRET_KEY`**：Flask 会话密钥（建议长随机字符串）
- **`MYSQL_ROOT_PASSWORD`**
- **`RADIUS_KEY` / `RADIUS_SECRET`**：FreeRADIUS 与客户端必须一致

数据目录：

- **`DATA_ROOT`**：宿主机上用于挂载持久化数据的根目录（默认 `/srv/docker`）

Flask Host 校验（重要）：

- **`SERVER_NAME`**：除非确实需要，否则建议留空。若设置了该值，它必须与请求的 **Host** 头一致，否则 Flask 会返回 **404**（常见于反向代理场景）。

---

## 部署方式一：单机（All-in-one）

最简单的拓扑：在同一台机器上运行 `core` + `vpn` + `proxy`。

### 1）准备 DNS 与 Caddy

修改 `Caddyfile` 为你的域名与联系人邮箱。仓库内默认配置会将流量转发到 `web:5000`：

```text
internet.zlix.tech {
	tls internet@ustc.global
	reverse_proxy web:5000
}
```

将域名的 **A/AAAA** 记录指向该主机。Caddy 会自动申请与续期证书。

### 2）启动整套服务

```bash
docker compose --profile core --profile vpn --profile proxy up -d --build
```

### 3）常用端口/入口

- **Web UI（直连 Flask）**：`http://<host>:${WEB_PORT:-5000}`
- **Web UI（经 Caddy）**：`https://<your-domain>`（宿主机 80/443）
- **RADIUS（控制面）**：UDP `${RADIUS_AUTH_PORT:-1812}` / `${RADIUS_ACCT_PORT:-1813}`（可选 CoA `${RADIUS_COA_PORT:-3799}`）
- **ocserv**：TCP/UDP `${OCSERV_TCP_PORT:-13806}` / `${OCSERV_UDP_PORT:-13806}`（host networking）
- **light-server**：HTTPS 代理端口（默认 **29980**，host networking）

---

## 部署方式二：控制面 / 数据面分离（推荐）

将“有状态 + 管理能力”的组件集中部署，并在数据面主机上只跑 VPN/代理。

### 控制面主机

启动 Web + DB + RADIUS：

```bash
docker compose --profile core up -d --build
```

确保数据面主机可以访问控制面以下端口：

- **RADIUS UDP**：`${RADIUS_AUTH_PORT:-1812}`、`${RADIUS_ACCT_PORT:-1813}`（可选 `${RADIUS_COA_PORT:-3799}`）
- **Web**：如需公网访问 Web UI，则开放 80/443（Caddy）

### 数据面主机（可多台）

在每台数据面主机上：

1）复制 `.env.example` 为 `.env`
2）设置：
   - `RADIUS_SERVER=<CONTROL_PLANE_IP_OR_DNS>`
   - `RADIUS_KEY` / `RADIUS_SECRET` 与控制面一致
3）只启动数据面服务：

```bash
docker compose --profile vpn --profile proxy up -d
```

---

## `ocserv` / `light-server` 证书（acme.sh）

这两个服务通过挂载目录读取证书：

- **ocserv**
  - `${DATA_ROOT}/ocserv/pki/public/server.crt`
  - `${DATA_ROOT}/ocserv/pki/private/server.key`
- **light-server**
  - `${DATA_ROOT}/light/ssl/server.crt`
  - `${DATA_ROOT}/light/ssl/server.key`

仓库提供 **`acme-sh` 容器**（profile `acme`）来完成申请、安装证书，无需在宿主机安装 certbot。

### 一次性：注册 ACME 账号

在 `.env` 中设置 `ACME_EMAIL`，然后执行：

```bash
docker compose --profile acme run --rm acme-sh --register-account -m "$ACME_EMAIL"
```

### 申请 + 安装（推荐：DNS-01）

由于 `caddy` 已占用 **:80/:443**，通常 DNS-01 更简单。

```bash
# 1) 申请（按你的 DNS 服务商替换 --dns <plugin> 与相应凭据）
docker compose --profile acme run --rm acme-sh \
  --issue --dns <your_dns_plugin> \
  -d vpn.zlix.tech -d light.zlix.tech

# 2) 安装：ocserv
docker compose --profile acme run --rm acme-sh \
  --install-cert -d vpn.zlix.tech \
  --fullchain-file /target/ocserv-pki/public/server.crt \
  --key-file /target/ocserv-pki/private/server.key

chmod 400 "${DATA_ROOT}/ocserv/pki/private/server.key"
chmod 444 "${DATA_ROOT}/ocserv/pki/public/server.crt"
docker compose --profile vpn restart ocserv

# 3) 安装：light-server
docker compose --profile acme run --rm acme-sh \
  --install-cert -d light.zlix.tech \
  --fullchain-file /target/light-ssl/server.crt \
  --key-file /target/light-ssl/server.key

chmod 400 "${DATA_ROOT}/light/ssl/server.key"
chmod 444 "${DATA_ROOT}/light/ssl/server.crt"
docker compose --profile proxy restart light-server
```

### 续期自动化

使用 cron/systemd timer 定期执行：

```bash
docker compose --profile acme run --rm acme-sh --cron
```

续期成功后，重启 `ocserv` / `light-server` 以加载新证书。

---

## FreeRADIUS 数据库初始化（MySQL Schema）

`ghcr.io/ustclug/docker-freeradius:nightly` 可以在启动阶段通过 **pre-run** 脚本初始化数据库表结构：

- **触发时机**：仅在该容器 **首次启动**时（内部标志 `HAVE_INITIALIZED=false`）
- **条件**：
  - `FREERADIUS_INIT_DATABASE_ENABLE != false`
  - `FREERADIUS_MYSQL_ADMIN_USERNAME` 非空
- **行为**：使用 MySQL 管理员账号导入 `/srv/tables.sql` 与 `/srv/user.sql`

若需要重新执行初始化，请 **重建** `freeradius` 容器（SQL 文件使用 `IF NOT EXISTS`，重复导入通常是安全的）。

---

## 运维

### 启动 / 停止

```bash
docker compose --profile core up -d --build
docker compose --profile core down
```

### 升级镜像

```bash
docker compose --profile core --profile vpn --profile proxy pull
docker compose --profile core --profile vpn --profile proxy up -d
```

### 查看日志

```bash
docker compose logs -f --tail=200 web
docker compose logs -f --tail=200 freeradius
```

### 备份（推荐）

建议备份你使用到的 `${DATA_ROOT}` 下目录，尤其是：

- `${DATA_ROOT}/mysql/data`
- `${DATA_ROOT}/ocserv/pki`
- `${DATA_ROOT}/light/ssl`
- `${DATA_ROOT}/acme.sh`

---

## 故障排查

### 反向代理后 Web 一直 404

检查 `.env` 中的 `SERVER_NAME`。如果设置了该值但与请求 Host 不一致，Flask 会返回 404。建议默认留空。

### `network_mode: host` 不可用

profiles `vpn` / `proxy` 依赖 **Linux 风格 host networking**。

### arm64：出现 “no matching manifest for linux/arm64”

在 `.env` 设置 `DOCKER_PLATFORM=linux/amd64` 强制使用模拟运行。

### `config/default.py` 在哪里？

它会在 `web` 容器启动时由 `docker-startup.sh` 动态生成。非 Docker 场景可参考 `config/example.py` 手动创建。


