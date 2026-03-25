# 技术规格文档（Tech Spec）

> Technical Specification — EasyTransfer
> 版本：0.2.0 | 最后更新：2026-03-25

---

## 1. 系统总览

### 1.1 产品形态

EasyTransfer 以两种形态存在：

```
形态 1：MCP Server（主要形态）
  → 作为 AI Agent 的技能包运行
  → Agent 通过 MCP 协议调用我们的工具
  → 用户通过自然语言与 Agent 交互

形态 2：单文件恢复器（辅助形态）
  → 一个独立的 .exe 文件（<50MB）
  → 用于新电脑上无 Agent 时快速恢复
  → 输入迁移码即可自动恢复
  → 恢复完成后可选安装 Agent + 技能
```

### 1.2 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    用户的 AI Agent                           │
│              (OpenClaw / Claude Desktop / etc.)              │
│                                                             │
│  用户说："帮我准备换机"                                        │
│  Agent："好的，我来调用 EasyTransfer..."                       │
└──────────────────────┬──────────────────────────────────────┘
                       │ MCP 协议
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              EasyTransfer MCP Server                         │
│                                                             │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌──────────┐      │
│  │  scan     │ │ analyze  │ │  package  │ │ restore  │ ...  │
│  │  _environ │ │ _migra   │ │  _migra   │ │ _from    │      │
│  │  ment     │ │ tion     │ │  tion     │ │ _package │      │
│  └─────┬─────┘ └─────┬────┘ └─────┬─────┘ └────┬─────┘      │
│        │             │            │             │            │
│  ┌─────▼─────────────▼────────────▼─────────────▼─────┐      │
│  │              Core Engine                            │      │
│  │  Scanner │ Planner │ Packager │ Executor │ Verifier │      │
│  └─────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 两种迁移流程

```
流程 A：迁移码模式（MVP，推荐）

  旧电脑                         云端/U盘                    新电脑
  ┌──────────┐                 ┌─────────┐              ┌──────────────┐
  │ Agent +   │  加密迁移包     │ 临时存储  │  迁移码下载   │ 单文件恢复器  │
  │ EasyTrans │ ──────────────→│ (加密的)  │─────────────→│ 或 Agent +   │
  │ fer 技能   │                │          │              │ EasyTransfer │
  └──────────┘                 └─────────┘              └──────────────┘
      ↑                                                       ↑
  用户说一句话                                            输入 6 位迁移码

流程 B：局域网直连模式（未来增强）

  旧电脑                                              新电脑
  ┌──────────┐         局域网 P2P                  ┌──────────┐
  │ Agent +   │ ←────── 加密直连 ──────────────→    │ Agent +   │
  │ EasyTrans │                                    │ EasyTrans │
  │ fer 技能   │                                    │ fer 技能   │
  └──────────┘                                     └──────────┘
```

---

## 2. MCP Server 设计

### 2.1 MCP 工具定义

这是我们暴露给 Agent 的工具接口，也是产品的"API"：

```python
# MCP Tool 1: scan_environment
@mcp_tool(
    name="scan_environment",
    description="扫描当前 Windows 电脑的完整软件环境，包括已安装应用、"
                "用户文件、浏览器数据、开发环境、系统配置等。"
                "返回结构化的环境画像。通常需要 1-5 分钟。"
)
async def scan_environment(
    scope: str = "full",         # "full" | "apps_only" | "files_only" | "dev_only"
    include_file_sizes: bool = True,
    skip_system_apps: bool = True,
) -> EnvironmentProfile:
    """扫描环境并返回画像"""
    pass


# MCP Tool 2: analyze_migration
@mcp_tool(
    name="analyze_migration",
    description="分析环境画像，返回人类可读的迁移报告。"
                "告诉用户有多少应用可以自动迁移、多少需要手动处理、"
                "总数据量是多少等。这个工具很快，几秒钟就能完成。"
)
async def analyze_migration(
    profile_path: str,           # 环境画像 JSON 文件路径
) -> MigrationAnalysis:
    """分析并生成迁移报告"""
    pass


# MCP Tool 3: create_migration_package
@mcp_tool(
    name="create_migration_package",
    description="根据用户确认的迁移选项，将需要迁移的数据打包为加密的迁移包。"
                "生成一个 6 位迁移码，用于在新电脑上恢复。"
                "耗时取决于数据量。"
)
async def create_migration_package(
    profile_path: str,           # 环境画像 JSON 文件路径
    include_apps: list[str] | None = None,    # 要迁移的应用列表（None=全部）
    include_files: bool = True,
    include_browser: bool = True,
    include_dev_env: bool = True,
    include_credentials: bool = False,         # 默认不迁移凭证，需用户明确同意
    output_mode: str = "cloud",  # "cloud"（上传到中转服务器）| "local"（保存到本地/U盘）
    output_path: str | None = None,  # output_mode="local" 时，保存路径
) -> MigrationPackageInfo:
    """打包迁移数据"""
    pass


# MCP Tool 4: restore_from_package
@mcp_tool(
    name="restore_from_package",
    description="从迁移包恢复环境到当前电脑。可以通过迁移码从云端下载，"
                "或从本地文件恢复。会自动安装应用、恢复配置、传输文件。"
                "过程中会报告进度。"
)
async def restore_from_package(
    migration_code: str | None = None,   # 6 位迁移码（云端模式）
    package_path: str | None = None,     # 本地迁移包路径
    auto_install_apps: bool = True,
    restore_files: bool = True,
    restore_configs: bool = True,
) -> MigrationResult:
    """从迁移包恢复"""
    pass


# MCP Tool 5: verify_migration
@mcp_tool(
    name="verify_migration",
    description="验证迁移结果。检查应用是否安装成功、配置是否生效、"
                "文件是否完整。返回详细的验证报告。"
)
async def verify_migration(
    migration_id: str,           # 迁移记录 ID
) -> VerificationReport:
    """验证迁移结果"""
    pass


# MCP Tool 6: rollback_migration
@mcp_tool(
    name="rollback_migration",
    description="回滚指定的迁移操作。可以回滚单个应用安装或全部迁移。"
)
async def rollback_migration(
    migration_id: str,
    item_ids: list[str] | None = None,  # None = 回滚全部
) -> RollbackResult:
    """回滚迁移"""
    pass
```

### 2.2 MCP Server 启动方式

```python
# 作为 MCP Server 运行
# 用户的 Agent 通过以下方式启动我们的技能：

# 方式 1：npx（推荐，无需预装 Python）
# npx easytransfer-mcp

# 方式 2：pip 安装后运行
# pip install easytransfer
# python -m easytransfer.mcp_server

# 方式 3：Agent 平台的技能商店一键安装
# （未来，当技能商店成熟后）
```

### 2.3 MCP 配置文件

用户在 Agent 配置中添加我们的技能：

```json
{
  "mcpServers": {
    "easytransfer": {
      "command": "npx",
      "args": ["easytransfer-mcp"],
      "env": {
        "EASYTRANSFER_LICENSE": "用户的许可证密钥（付费后获得）"
      }
    }
  }
}
```

---

## 3. 核心模块设计

### 3.1 环境扫描模块（Scanner）

**设计理念**：插件式架构，每种扫描任务是一个独立的 Scanner 插件。

```python
class BaseScanner:
    """扫描器基类"""
    name: str
    description: str
    priority: int                # P0/P1/P2

    async def scan(self) -> ScanResult:
        raise NotImplementedError

    async def estimate_size(self) -> int:
        """估算迁移数据量（字节）"""
        raise NotImplementedError
```

**扫描器列表**：

| 扫描器 | 类名 | 数据来源 | 优先级 |
|--------|------|---------|--------|
| 已安装应用 | InstalledAppScanner | 注册表 + winget + Program Files | P0 |
| 应用配置 | AppConfigScanner | AppData/各应用配置目录 | P0 |
| 用户文件 | UserFileScanner | 用户目录 | P0 |
| 浏览器数据 | BrowserScanner | Chrome/Edge/Firefox Profile | P0 |
| 开发环境 | DevEnvScanner | PATH 中的运行时 | P0 |
| Git/SSH | GitSshScanner | ~/.gitconfig, ~/.ssh/ | P0 |
| 系统设置 | SystemSettingsScanner | 注册表、系统API | P1 |
| 网络配置 | NetworkConfigScanner | netsh、VPN 配置 | P1 |
| 终端配置 | TerminalConfigScanner | Windows Terminal, PS profile | P1 |
| 字体 | FontScanner | 用户安装的字体 | P2 |
| 计划任务 | ScheduledTaskScanner | schtasks | P2 |

### 3.2 核心数据模型

```python
@dataclass
class EnvironmentProfile:
    """一台电脑的完整环境画像"""
    profile_id: str                     # 唯一标识
    scan_time: datetime
    system_info: SystemInfo
    installed_apps: list[AppInfo]
    app_configs: list[ConfigInfo]
    user_files: list[FileGroup]
    browser_profiles: list[BrowserProfile]
    dev_environments: list[DevEnvInfo]
    credentials: list[CredentialInfo]   # 仅元数据
    system_settings: dict
    total_size_bytes: int

@dataclass
class AppInfo:
    """单个应用的信息"""
    name: str
    version: str
    publisher: str
    install_path: str
    install_source: str                 # winget/msi/exe/portable/store
    winget_id: str | None
    config_paths: list[str]
    data_paths: list[str]
    size_bytes: int
    last_used: datetime | None
    can_auto_install: bool
    install_command: str | None
    notes: str

@dataclass
class MigrationPackageInfo:
    """迁移包信息"""
    package_id: str
    migration_code: str                 # 6 位迁移码
    package_size_bytes: int
    item_count: int
    storage_mode: str                   # cloud / local
    storage_path: str                   # 云端 URL 或本地路径
    expires_at: datetime                # 过期时间（24小时）
    encryption_info: str                # 加密方式说明

@dataclass
class MigrationResult:
    """迁移执行结果"""
    migration_id: str
    started_at: datetime
    completed_at: datetime
    total_items: int
    success_count: int
    failed_count: int
    skipped_count: int
    items: list[MigrationItemResult]
    manual_actions: list[str]           # 需要用户手动处理的事项
```

### 3.3 迁移包格式

```
迁移包结构（.etpkg 文件，本质上是加密的 tar.gz）：

migration_package.etpkg
├── manifest.json              # 迁移清单（包含所有元数据）
├── apps/                      # 应用配置数据
│   ├── vscode/
│   │   ├── settings.json
│   │   ├── keybindings.json
│   │   └── extensions.json    # 扩展列表（不含扩展本身，到目标端重新安装）
│   ├── chrome/
│   │   ├── bookmarks.json
│   │   ├── extensions.json
│   │   └── local_state
│   └── ...
├── files/                     # 用户文件
│   ├── documents/
│   ├── desktop/
│   └── ...
├── dev/                       # 开发环境配置
│   ├── gitconfig
│   ├── ssh/                   # 加密的 SSH 密钥
│   ├── pip_packages.txt       # pip freeze 输出
│   ├── npm_global.txt         # npm list -g 输出
│   └── ...
├── system/                    # 系统配置
│   ├── env_variables.json
│   ├── hosts
│   ├── terminal_settings.json
│   └── ...
└── install_plan.json          # 自动生成的安装计划
                               # （在目标端恢复时，Executor 按此执行）
```

### 3.4 打包与加密

```python
class MigrationPackager:
    """迁移包打包器"""

    async def create_package(
        self,
        profile: EnvironmentProfile,
        options: PackageOptions,
    ) -> MigrationPackageInfo:
        """
        打包流程：
        1. 根据用户选项筛选迁移项
        2. 收集所有需要迁移的文件和配置
        3. 生成 install_plan.json（目标端的安装指令）
        4. 打包为 tar.gz
        5. 生成随机迁移码（6 位数字）
        6. 从迁移码派生加密密钥（PBKDF2）
        7. 用 AES-256-GCM 加密整个包
        8. 上传到中转服务器 或 保存到本地
        """
        pass
```

### 3.5 恢复执行引擎

```python
class MigrationExecutor:
    """在目标端执行恢复"""

    async def restore(self, package_path: str, key: bytes) -> MigrationResult:
        """
        恢复流程：
        1. 解密迁移包
        2. 读取 manifest.json 和 install_plan.json
        3. 按顺序执行：
           a. 安装应用（优先 winget，其次其他方式）
           b. 恢复应用配置（复制到正确位置）
           c. 恢复用户文件
           d. 恢复系统配置（环境变量等）
           e. 恢复开发环境（安装运行时 + 全局包）
        4. 每步执行后验证
        5. 生成迁移结果报告
        """
        pass
```

---

## 4. 单文件恢复器设计

**用途**：新电脑上什么都没有时，用这个小工具恢复。

```
技术方案：
  - 使用 PyInstaller 打包为单个 .exe（<50MB）
  - 内含精简版 EasyTransfer（只有 restore + verify 功能）
  - 自带 Python 运行时（无需用户安装 Python）

功能：
  - 输入 6 位迁移码
  - 从云端下载迁移包
  - 解密并执行恢复
  - 显示进度和结果
  - 可选：恢复完成后安装完整版 Agent + EasyTransfer 技能

界面：
  - 简单的命令行界面（用 rich 美化）
  - 未来可以加 GUI（用 PySide6 或 webview）
```

---

## 5. 安全设计

### 5.1 加密方案

```
迁移码 → PBKDF2(migration_code, salt, iterations=600000) → 256-bit Key
Key → AES-256-GCM 加密迁移包

特点：
  - 迁移码只有用户知道（不传输给服务器）
  - 服务器存储的是加密后的数据，无法解密
  - 即使服务器被入侵，攻击者也无法获取用户数据
  - 迁移码 24 小时后失效，过期的迁移包自动删除
```

### 5.2 凭证特殊处理

```
SSH 密钥、GPG 密钥等高敏感数据：
  1. 在迁移包内使用独立的二次加密
  2. 恢复时需要用户额外确认
  3. 恢复后立即从临时目录删除中间文件
  4. 日志中绝不记录凭证内容
```

### 5.3 云端中转服务器

```
中转服务器职责：
  - 临时存储加密的迁移包
  - 根据迁移码分发迁移包
  - 24 小时后自动删除

中转服务器不能做的：
  - 不解密任何数据
  - 不记录用户信息
  - 不分析迁移内容
```

---

## 6. 错误处理策略

| 错误类型 | 处理方式 | Agent 应如何告知用户 |
|---------|---------|-------------------|
| 扫描某个应用失败 | 跳过该应用，记录错误 | "有 2 个应用无法识别，已跳过" |
| 打包时磁盘空间不足 | 提示用户释放空间或选择更少迁移项 | "磁盘空间不足，建议先迁移应用配置，文件稍后用U盘拷贝" |
| 上传中断 | 自动重试 3 次，支持断点续传 | "上传中断，正在重试..." |
| 迁移码错误 | 返回错误，让用户重新输入 | "迁移码不正确，请确认 6 位数字" |
| 迁移码过期 | 需要在旧电脑上重新生成 | "迁移码已过期，请在旧电脑上重新打包" |
| 应用安装失败 | 记录失败原因，继续其他项 | "Chrome 安装成功，但 Photoshop 需要手动安装" |
| 恢复时磁盘不足 | 暂停，提示用户 | "新电脑磁盘空间不足，已安装 30 个应用，还剩 8 个待安装" |

---

## 7. 本地开发与测试环境

### 7.1 虚拟机测试环境

```
VM-Source（旧电脑模拟）：
  - Windows 11 Pro
  - 4GB 内存 / 60GB 磁盘
  - 预装测试软件套装
  - 可选安装 Agent

VM-Target（新电脑模拟）：
  - Windows 11 Pro 全新安装
  - 4GB 内存 / 60GB 磁盘
  - 仅默认软件（模拟开箱状态）
```

### 7.2 测试策略

```
单元测试：
  - 各 Scanner 的扫描逻辑
  - 打包和解包逻辑
  - 加密和解密
  - 各 Executor 的安装/恢复逻辑

集成测试：
  - 扫描 → 打包 → 解包 → 恢复 全流程（单机内）
  - MCP Server 启动和工具调用

端到端测试：
  - 两台 VM 之间的完整迁移流程
```
