# Windows / WSL 运行说明

本页说明如何在 **Windows + WSL2** 中运行 Docker Engine，并通过项目自带的 npm 脚本启动服务。适用于无法或不想使用 Docker Desktop 的环境。

## 前置条件

- Windows 10/11，已启用 WSL2
- 一个 WSL2 Linux 发行版（下文以 `Ubuntu` 为例）
- 发行版内安装 Docker Engine 与 Docker Compose v2
- 当前用户已加入 `docker` 组

检查：

```bash
wsl -l -v
wsl -d Ubuntu -- docker version
wsl -d Ubuntu -- docker compose version
```

## 1. 在 WSL 中安装 Docker Engine

在 WSL 发行版内执行（以 Ubuntu/Debian 为例，具体命令以 Docker 官方文档为准）：

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

重新登录 WSL 后验证：

```bash
docker run --rm hello-world
docker compose version
```

如果系统未启用 systemd，需要按发行版方式启动 Docker daemon，或启用 systemd 后重试。

## 2. 配置 WSL 网络

多数情况下 WSL2 的 NAT 模式即可让 Windows 通过 `localhost` 访问容器端口。若使用 `mirrored` 模式，请确认 Windows 与 WSL 的端口转发行为符合预期。

可选的 `%UserProfile%\.wslconfig` 示例：

```ini
[wsl2]
networkingMode=NAT
```

修改后重启 WSL：

```powershell
wsl --shutdown
```

> WSL 可能输出 `检测到 localhost 代理配置...` 的提示。这是 WSL 的无害警告，不影响容器端口访问。npm 脚本会设置 `WSL_UTF8=1` 避免中文乱码。

## 3. 配置项目

在项目根目录执行：

```bash
npm run deploy
```

如果自动检测失败，在 `.env` 中显式指定：

```ini
DOCKER_MODE=wsl
WSL_DISTRO=Ubuntu
```

`WSL_DISTRO` 必须与 `wsl -l -q` 输出的发行版名称一致。

然后启动：

```bash
npm start
```

停止：

```bash
npm run infra:down
```

## 4. 常见问题

### Docker Hub 访问受限

默认镜像前缀可以通过 `.env` 覆盖：

```ini
POSTGRES_IMAGE=your-registry/postgres:16-alpine
OPENSEARCH_BASE_IMAGE=your-registry/opensearchproject/opensearch:2.19.3
```

IK 插件与词典已包含在仓库的 `deploy/opensearch/` 中，不依赖额外下载。

### 容器端口无法从 Windows 访问

确认 Docker 容器已映射端口：

```bash
wsl -d Ubuntu -- docker compose --env-file .env -p policysearcher ps
```

并检查 `.env` 中的 `POSTGRES_PORT`、`OPENSEARCH_PORT` 是否与 Windows 侧访问的端口一致。

### WSL 每次命令都出现代理警告

这是 WSL 在 NAT 模式下的提示，不是部署错误。可忽略，或根据团队环境统一配置代理。

### 旧版 PowerShell 脚本

`scripts/start-stack.ps1` 和 `scripts/stop-stack.ps1` 是 Windows/WSL 辅助脚本，保留用于兼容；新环境建议使用 `npm run deploy` / `npm start` / `npm run infra:*`。
