## lug-vpn-web —— WireGuard 管理面板

文档语言：[English](README.md) / **中文**

本仓库提供一个基于 Flask 的 Web 界面，用于管理 WireGuard VPN 客户端。它包含自动化配置生成器和基于 SSE 的同步守护程序，用于管理 WireGuard 对等节点（Peers）。

---

## 组件

- **`web`**：Flask 应用程序，用于用户管理和 WireGuard 对等节点配置。
- **`mysql`**：数据库，用于存储用户数据和 WireGuard 对等节点信息。
- **`caddy`**：边缘反向代理，用于提供 HTTPS 支持并分发 Web 界面。

---

## 部署要求

- **Docker Engine + Docker Compose v2**
- 宿主机（或单独的数据面主机）已安装 **WireGuard**。
- **Python 3.10+**（如果在宿主机上运行同步守护程序）。

如果宿主机是 **arm64** 架构，可能需要在 `.env` 中设置 `DOCKER_PLATFORM=linux/amd64` 以强制使用模拟运行。

---

## 配置（`.env`）

复制示例文件并修改：

```bash
cp .env.example .env
```

### 核心设置

- **`SECRET_KEY`**：Flask 会话密钥（建议使用长随机字符串）。
- **`MYSQL_ROOT_PASSWORD`**、**`MYSQL_PASSWORD`**：数据库凭据。
- **`SERVER_NAME`**：除非确实需要，否则建议**留空**。如果设置了该值，它必须与请求的 **Host** 头一致。

### WireGuard 设置 (`WG_*`)

- **`WG_SERVER_ENDPOINT`**：WireGuard 服务器的公网地址和端口（例如 `vpn.example.org:51820`）。
- **`WG_SERVER_PRIVATE_KEY`**：服务器的 WireGuard 私钥（Base64 编码的 Curve25519）。
- **`WG_LISTEN_PORT`**：WireGuard 服务器监听的端口（默认：`51820`）。
- **`WG_SERVER_INTERFACE_IP`**：WireGuard 接口的内部 IP（默认：`10.100.0.1/16`）。
- **`WG_ADDRESS_POOL`**：客户端 IP 的 CIDR 范围（默认：`10.100.0.0/16`）。
- **`WG_DNS`**：提供给客户端的 DNS 服务器（默认：`1.1.1.1`）。
- **`WG_ALLOWED_IPS`**：通过 VPN 路由的 IP 范围（默认：`0.0.0.0/0, ::/0`）。
- **`SSE_TOKEN`**：同步守护程序的共享密钥。

---

## 部署步骤

### 1）准备 DNS 与 Caddy

修改 `Caddyfile` 为你的域名与联系人邮箱。将域名的 **A/AAAA** 记录指向该主机。

### 2）启动服务

运行 Web 界面和数据库：

```bash
docker compose --profile core --profile dev up -d --build
```

### 3）WireGuard 同步

Web 界面负责生成 WireGuard 配置。要将这些配置同步到宿主机上的实际 WireGuard 接口，请使用 `wg_client_daemon.py` 脚本：

```bash
# 在运行 WireGuard 的宿主机上
export SSE_TOKEN="your-secure-token"
export WG_API_URL="https://your-domain.com"
python3 scripts/wg_client_daemon.py --wg-dev wg0 --wg-config /etc/wireguard/wg0.conf
```

该守护程序通过 SSE 监听更新，并使用 `wg-quick` 自动重载 WireGuard 接口。

---

## 运维操作

### 启动 / 停止
```bash
docker compose --profile core --profile dev up -d
docker compose --profile core --profile dev down
```

### 查看日志
```bash
docker compose logs -f web
```

---

## 故障排查

### 反向代理后 Web 返回 404
检查 `.env` 中的 `SERVER_NAME`。如果设置了该值但与请求 Host 不一致，Flask 会返回 404。建议留空。

### 无效的 WireGuard 私钥
如果 `WG_SERVER_PRIVATE_KEY` 缺失或无效，`web` 服务将无法启动。请使用 `wg genkey` 生成有效的密钥。

### arm64 主机：出现 “no matching manifest for linux/arm64”
在 `.env` 设置 `DOCKER_PLATFORM=linux/amd64` 强制使用模拟运行。

---

## 开发

安装 [uv](https://docs.astral.sh/uv/) 并运行：

```bash
uv sync                      # 安装依赖
uv run pytest tests/ -v      # 运行测试
uv run python run.py         # 启动开发服务器（需要 MySQL）
```



