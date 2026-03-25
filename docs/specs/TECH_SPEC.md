# 技术规格文档（Tech Spec）

> Technical Specification — EasyTransfer
> 版本：0.1.0 | 最后更新：2026-03-25

---

## 1. 系统总览

EasyTransfer 由两个对称的 Agent 程序组成，分别运行在旧电脑（源端）和新电脑（目标端）。两个 Agent 通过局域网通信，协作完成迁移任务。

```
┌─────────────────────┐          ┌─────────────────────┐
│    源端（旧电脑）      │          │    目标端（新电脑）    │
│                     │          │                     │
│  ┌───────────────┐  │  gRPC +  │  ┌───────────────┐  │
│  │  EasyTransfer  │←─┼──TLS────┼─→│  EasyTransfer  │  │
│  │  Source Agent  │  │         │  │  Target Agent  │  │
│  └───────┬───────┘  │         │  └───────┬───────┘  │
│          │          │         │          │          │
│  ┌───────▼───────┐  │         │  ┌───────▼───────┐  │
│  │  Scanner 模块  │  │  文件流   │  │  Executor 模块 │  │
│  │  Collector 模块 │←─┼─────────┼─→│  Installer 模块│  │
│  │  Packager 模块  │  │         │  │  Verifier 模块 │  │
│  └───────────────┘  │         │  └───────────────┘  │
└─────────────────────┘          └─────────────────────┘
```

---

## 2. 模块详细设计

### 2.1 设备发现与配对模块（Discovery）

**职责**：让同一局域网内的两台电脑互相发现并建立安全连接。

**技术方案**：

```
发现阶段：
  - 使用 mDNS（Multicast DNS）在局域网广播自己的存在
  - 服务名称：_easytransfer._tcp.local
  - 广播内容：设备名称、角色（source/target）、版本号

配对阶段：
  1. Target 端发现 Source 端后，显示 6 位配对码
  2. 用户在 Source 端输入相同的配对码
  3. 两端使用 SRP（Secure Remote Password）协议验证配对码
  4. 配对成功后，使用 TLS 1.3 建立加密通道
  5. 后续所有通信走此加密通道

备选方案（无法 mDNS 时）：
  - 用户手动输入对方的 IP 地址
```

**关键接口**：

```python
class DiscoveryService:
    async def start_broadcasting(self, role: str) -> None:
        """开始在局域网广播自己的存在"""

    async def discover_peers(self) -> list[PeerInfo]:
        """发现局域网内的其他 EasyTransfer 实例"""

    async def pair_with_peer(self, peer: PeerInfo, pairing_code: str) -> SecureChannel:
        """与指定 peer 进行配对，返回加密通道"""
```

---

### 2.2 环境扫描模块（Scanner）

**职责**：扫描旧电脑的完整软件环境，生成结构化的环境画像。

**设计理念**：采用插件式架构，每种扫描任务是一个独立的 Scanner 插件，方便扩展。

```python
# 扫描器基类
class BaseScanner:
    name: str                    # 扫描器名称
    description: str             # 描述（给 AI Agent 看的）
    priority: int                # 优先级（P0/P1/P2）

    async def scan(self) -> ScanResult:
        """执行扫描，返回结构化结果"""
        raise NotImplementedError

    async def estimate_size(self) -> int:
        """估算此项迁移需要传输的数据量（字节）"""
        raise NotImplementedError
```

**已规划的扫描器列表**：

| 扫描器 | 类名 | 数据来源 | 优先级 |
|--------|------|---------|--------|
| 已安装应用 | InstalledAppScanner | 注册表 + winget + Program Files | P0 |
| 应用配置 | AppConfigScanner | AppData/各应用配置目录 | P0 |
| 用户文件 | UserFileScanner | 用户目录（Documents/Desktop/Downloads等） | P0 |
| 浏览器数据 | BrowserScanner | Chrome/Edge/Firefox 的 Profile 目录 | P0 |
| 开发环境 | DevEnvScanner | PATH 中的运行时、包管理器 | P0 |
| Git/SSH | GitSshScanner | ~/.gitconfig, ~/.ssh/ | P0 |
| 系统设置 | SystemSettingsScanner | 注册表、系统API | P1 |
| 网络配置 | NetworkConfigScanner | netsh 输出、VPN 配置 | P1 |
| 终端配置 | TerminalConfigScanner | Windows Terminal settings.json, PS profile | P1 |
| 字体 | FontScanner | C:\Windows\Fonts（用户安装的） | P2 |
| 计划任务 | ScheduledTaskScanner | schtasks 输出 | P2 |

**环境画像数据结构**：

```python
@dataclass
class EnvironmentProfile:
    """一台电脑的完整环境画像"""
    scan_time: datetime
    system_info: SystemInfo            # OS 版本、架构、计算机名等
    installed_apps: list[AppInfo]      # 已安装应用列表
    app_configs: list[ConfigInfo]      # 应用配置信息
    user_files: list[FileGroup]        # 用户文件（按类别分组）
    browser_profiles: list[BrowserProfile]  # 浏览器数据
    dev_environments: list[DevEnvInfo]      # 开发环境
    credentials: list[CredentialInfo]       # 凭证信息（仅元数据，不含实际密码）
    system_settings: dict                   # 系统配置
    network_config: NetworkConfig           # 网络配置
    total_size_bytes: int                   # 总数据量

@dataclass
class AppInfo:
    """单个应用的信息"""
    name: str                          # 应用名称
    version: str                       # 版本号
    publisher: str                     # 发布者
    install_path: str                  # 安装路径
    install_source: str                # 安装来源（winget/msi/exe/portable/store）
    winget_id: str | None              # winget 包 ID（如果可用）
    config_paths: list[str]            # 配置文件路径列表
    data_paths: list[str]              # 数据文件路径列表
    size_bytes: int                    # 占用空间
    last_used: datetime | None         # 最后使用时间
    can_auto_install: bool             # 是否支持自动安装
    install_command: str | None        # 自动安装命令（如果支持）
    notes: str                         # AI Agent 的备注（如兼容性说明）
```

---

### 2.3 AI 迁移规划模块（Planner）

**职责**：基于环境画像，利用 AI Agent 生成智能迁移计划。

**这是产品的核心智能所在。** 传统迁移工具只能机械复制，而我们的 Planner 能"理解"用户的环境并做出合理决策。

**AI Agent 在此模块的职责**：

```
输入：源端环境画像（EnvironmentProfile）+ 目标端系统信息（SystemInfo）

AI Agent 需要做出的决策：
  1. 每个应用的最佳安装方式是什么？
     - 优先 winget → 其次静默安装 → 最后给出手动指引
  2. 哪些应用建议不迁移？（过旧、已弃用、临时安装的）
  3. 应用配置如何迁移？（直接复制 vs 需要转换 vs 建议使用云同步）
  4. 文件迁移策略：哪些文件跳过？（node_modules, .venv, __pycache__ 等）
  5. 凭证迁移的安全建议
  6. 识别潜在的兼容性问题

输出：MigrationPlan（用户可审核的迁移计划）
```

**迁移计划数据结构**：

```python
@dataclass
class MigrationPlan:
    """AI Agent 生成的迁移计划"""
    plan_id: str
    created_at: datetime
    source_profile: EnvironmentProfile
    target_system_info: SystemInfo

    # 迁移项列表，按执行顺序排列
    items: list[MigrationItem]

    # 需要用户决策的问题
    user_decisions: list[UserDecision]

    # 预估信息
    estimated_transfer_size: int       # 预估传输数据量
    estimated_duration_minutes: int    # 预估耗时
    estimated_steps: int               # 总步骤数

@dataclass
class MigrationItem:
    """单个迁移项"""
    id: str
    category: str                      # app_install / config_restore / file_transfer / credential / system_setting
    name: str                          # 显示名称
    description: str                   # 描述（给用户看的）
    priority: int                      # 执行优先级
    status: str                        # pending / approved / rejected / running / success / failed / skipped
    action: MigrationAction            # 具体执行动作
    rollback_action: MigrationAction | None  # 回滚动作
    dependencies: list[str]            # 依赖的其他 MigrationItem ID
    risk_level: str                    # low / medium / high
    requires_confirmation: bool        # 是否需要用户逐项确认
    ai_notes: str                      # AI Agent 的说明

@dataclass
class MigrationAction:
    """迁移动作（具体要执行的操作）"""
    action_type: str                   # winget_install / file_copy / config_restore / registry_write / command_run
    params: dict                       # 动作参数
    verify_command: str | None         # 验证命令（执行后检查是否成功）
```

---

### 2.4 数据传输模块（Transfer）

**职责**：在源端和目标端之间安全、高效地传输数据。

**传输协议设计**：

```
传输层架构：

  ┌─────────────────────────────────────┐
  │         应用层（迁移逻辑）            │
  ├─────────────────────────────────────┤
  │         控制通道（gRPC + TLS）        │  ← 命令、状态同步、小数据
  ├─────────────────────────────────────┤
  │         数据通道（TCP + TLS）         │  ← 大文件流式传输
  ├─────────────────────────────────────┤
  │         加密层（TLS 1.3）            │
  ├─────────────────────────────────────┤
  │         传输层（TCP）                │
  └─────────────────────────────────────┘
```

**关键设计决策**：

1. **控制通道和数据通道分离**
   - 控制通道：用 gRPC，传输命令、状态、迁移计划等结构化数据
   - 数据通道：用原始 TCP 流，传输文件内容（避免 gRPC 的消息大小限制）

2. **文件传输策略**
   ```
   小文件（< 1MB）：打包成 tar.gz 批量传输
   大文件（≥ 1MB）：单独传输，支持断点续传
   所有文件：传输前计算 SHA-256，传输后校验
   ```

3. **断点续传**
   ```
   传输状态文件：~/.easytransfer/transfer_state.json
   记录每个文件的传输进度（已传输字节数）
   中断后恢复时，从上次位置继续
   ```

---

### 2.5 执行引擎模块（Executor）

**职责**：在目标端按照迁移计划执行具体操作。

**执行流程**：

```
For each MigrationItem in plan (按优先级和依赖关系排序):
  1. 检查依赖项是否已完成
  2. 如果 requires_confirmation，等待用户确认
  3. 记录当前状态（用于回滚）
  4. 执行 action
  5. 执行 verify_command 验证结果
  6. 如果失败：
     a. AI Agent 分析失败原因
     b. 如果能自动修复：尝试修复后重试（最多 2 次）
     c. 如果不能修复：标记为 failed，记录原因，继续下一项
  7. 更新状态
  8. 报告进度
```

**执行器类型**：

```python
class WingetInstaller:
    """使用 winget 安装应用"""
    async def install(self, winget_id: str, version: str = None) -> InstallResult:
        # winget install --id {winget_id} --version {version} --accept-source-agreements --accept-package-agreements
        pass

class FileRestorer:
    """将文件恢复到目标位置"""
    async def restore(self, source_path: str, target_path: str) -> RestoreResult:
        # 复制文件，保留权限和时间戳
        pass

class ConfigRestorer:
    """恢复应用配置文件"""
    async def restore(self, config_info: ConfigInfo) -> RestoreResult:
        # 将配置文件复制到正确位置
        # 如果目标位置已有配置，备份后覆盖
        pass

class RegistryWriter:
    """写入注册表项"""
    async def write(self, key: str, value_name: str, value: any) -> WriteResult:
        # 写入前备份原值（用于回滚）
        pass

class CommandRunner:
    """执行任意命令"""
    async def run(self, command: str, timeout: int = 300) -> RunResult:
        # 用于执行自定义安装脚本等
        pass
```

---

### 2.6 验证模块（Verifier）

**职责**：验证每个迁移步骤的执行结果。

```python
class MigrationVerifier:
    """迁移结果验证器"""

    async def verify_app_installed(self, app_name: str) -> bool:
        """检查应用是否已安装（通过注册表/winget list）"""

    async def verify_file_integrity(self, file_path: str, expected_hash: str) -> bool:
        """校验文件 SHA-256 哈希值"""

    async def verify_config_applied(self, config_info: ConfigInfo) -> bool:
        """检查配置文件是否存在且内容正确"""

    async def verify_env_variable(self, name: str, expected_value: str) -> bool:
        """检查环境变量是否正确设置"""
```

---

## 3. 数据流

```
完整的数据流：

源端                              目标端
 │                                 │
 │  1. 扫描环境                      │
 ├──────────────┐                  │
 │  Scanner 模块  │                  │
 ├──────────────┘                  │
 │                                 │
 │  2. 生成环境画像                    │
 │  EnvironmentProfile              │
 │                                 │
 │  3. 发送画像给目标端   ────────────→ │
 │                                 │  4. 目标端收集自身 SystemInfo
 │                                 │
 │                                 │  5. AI Agent 生成迁移计划
 │                                 │     (在目标端运行，因为需要知道目标环境)
 │                                 │
 │  6. 迁移计划发回给源端  ←──────────  │
 │                                 │
 │  7. 两端都显示计划给用户审核          │
 │     用户确认后...                  │
 │                                 │
 │  8. 源端开始打包数据  ────────────→ │  9. 目标端接收并执行
 │     按 MigrationItem 逐项进行      │     安装应用 → 恢复配置 → 复制文件
 │                                 │
 │                                 │  10. 验证每一步
 │                                 │
 │  11. 迁移完成，生成报告             │
```

---

## 4. 安全设计

### 4.1 通信安全

```
配对过程：
  1. 用户在目标端看到 6 位配对码
  2. 在源端输入配对码
  3. 使用 SRP 协议验证（配对码不在网络上传输）
  4. 建立 TLS 1.3 通道（使用临时生成的证书）
  5. 两端显示通道指纹让用户确认（防中间人）

数据传输：
  - 所有数据通过 TLS 1.3 加密通道传输
  - 凭证类数据额外使用 AES-256-GCM 加密
  - 加密密钥从配对码派生（PBKDF2）
```

### 4.2 凭证处理

```
处理原则：
  1. 凭证在源端加密，密文传输，在目标端解密
  2. 中间过程不存储任何明文凭证到磁盘
  3. 迁移完成后，内存中的凭证数据立即清零
  4. SSH 私钥等高敏感数据需要用户逐项确认
  5. 浏览器密码建议使用浏览器自带的同步功能，而非直接迁移密码数据库
```

---

## 5. 错误处理策略

| 错误类型 | 处理方式 | 用户感知 |
|---------|---------|---------|
| 网络中断 | 自动重连（30秒超时），恢复传输 | "网络中断，正在重连..." |
| 应用安装失败 | 记录错误，尝试备用安装方式，继续其他项 | 报告中标注该应用需手动安装 |
| 文件传输校验失败 | 自动重传该文件（最多3次） | 用户无感知 |
| 目标磁盘空间不足 | 暂停迁移，提示用户释放空间或跳过大文件 | 弹出空间不足提示 |
| 权限不足 | 提示用户以管理员身份运行 | "需要管理员权限，请重新启动" |
| AI API 调用失败 | 使用本地备用规则生成基础迁移计划 | "智能规划暂不可用，使用基础模式" |

---

## 6. 本地开发与测试环境

### 6.1 虚拟机测试环境

```
推荐配置：

宿主机要求：
  - 16GB+ 内存（给两台 VM 各分配 4GB）
  - 100GB+ 可用磁盘空间
  - 支持 Hyper-V 或 VMware

VM-Source（旧电脑模拟）：
  - Windows 11 Pro
  - 4GB 内存 / 60GB 磁盘
  - 预装测试软件套装（见 scripts/setup_test_source.ps1）
  - 内部网络连接

VM-Target（新电脑模拟）：
  - Windows 11 Pro（全新安装）
  - 4GB 内存 / 60GB 磁盘
  - 仅默认软件
  - 内部网络连接（与 Source 同一虚拟网络）
```

### 6.2 测试数据准备脚本

项目中应包含以下自动化脚本：

```
scripts/
  setup_test_source.ps1    — 在 VM-Source 中安装一批测试软件和配置
  setup_test_target.ps1    — 确保 VM-Target 是干净状态
  verify_migration.ps1     — 迁移后自动验证结果是否正确
  reset_target.ps1         — 重置 VM-Target 到初始状态（利用快照）
```

### 6.3 自动化测试策略

```
单元测试（tests/unit/）：
  - 每个 Scanner 插件的测试
  - 每个 Executor 的测试
  - 数据结构的序列化/反序列化测试
  - 加密/解密测试

集成测试（tests/integration/）：
  - 源端扫描 → 生成画像 → 序列化 → 反序列化 → 验证完整性
  - 完整迁移流程（在 CI 环境中使用 mock）

端到端测试（tests/e2e/）：
  - 在两台 VM 之间执行完整迁移
  - 验证迁移结果
  - 需要手动或半自动触发（因为需要 VM 环境）
```
