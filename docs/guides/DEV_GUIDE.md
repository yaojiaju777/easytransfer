# 开发规范

> Development Guide — EasyTransfer
> 版本：0.1.0 | 最后更新：2026-03-25

---

## 1. 环境设置

### 1.1 前置要求

```
- Python 3.11+
- Poetry（Python 包管理器）
- Git
- Windows 10/11（开发和运行环境）
```

### 1.2 项目初始化

```bash
# 克隆项目
git clone <repo-url>
cd easytransfer

# 安装依赖
poetry install

# 激活虚拟环境
poetry shell

# 验证安装
python -m easytransfer --help
```

---

## 2. 编码规范

### 2.1 Python 代码风格

- 遵循 PEP 8
- 使用 Type Hints（类型注解）—— 所有函数必须有参数和返回值类型注解
- 使用 dataclass 定义数据模型
- 使用 async/await 处理异步操作
- 最大行宽：100 字符

### 2.2 命名规范

```python
# 模块名：小写下划线
app_scanner.py

# 类名：PascalCase
class InstalledAppScanner:

# 函数/方法：小写下划线
async def scan_installed_apps():

# 常量：大写下划线
MAX_RETRY_COUNT = 3

# 私有方法/属性：单下划线前缀
def _parse_registry_entry():
```

### 2.3 文档字符串

每个公共类和方法都必须有 docstring：

```python
class InstalledAppScanner(BaseScanner):
    """扫描 Windows 系统中已安装的应用程序。

    通过以下来源识别已安装应用：
    1. Windows 注册表（Uninstall 键）
    2. winget 包列表
    3. Program Files 目录扫描

    Attributes:
        include_system_apps: 是否包含系统应用（默认 False）
    """

    async def scan(self) -> ScanResult:
        """执行应用扫描。

        Returns:
            ScanResult: 包含已识别应用列表的扫描结果

        Raises:
            ScanError: 当注册表访问失败时
        """
```

### 2.4 错误处理

```python
# 使用自定义异常，不要裸 raise Exception
from easytransfer.core.errors import ScanError, TransferError, InstallError

# 每个模块有自己的异常类
class ScanError(EasyTransferError):
    """扫描过程中的错误"""

class TransferError(EasyTransferError):
    """数据传输过程中的错误"""

# 捕获异常时要具体，不要 bare except
try:
    result = await scanner.scan()
except RegistryAccessError as e:
    logger.error(f"注册表访问失败: {e}")
    # 降级处理...
except ScanError as e:
    logger.error(f"扫描失败: {e}")
    raise
```

### 2.5 日志规范

```python
from easytransfer.core.logging import get_logger

logger = get_logger(__name__)

# 日志级别使用指南：
logger.debug("扫描注册表键: %s", key_path)       # 调试信息，开发时用
logger.info("发现 %d 个已安装应用", count)         # 关键流程节点
logger.warning("应用 %s 无法确定安装来源", name)   # 非致命问题
logger.error("注册表访问失败: %s", error)          # 错误，但可恢复
logger.critical("安全通道建立失败，终止迁移")       # 致命错误

# 日志中不要包含敏感信息（密码、密钥内容等）
# ❌ 错误
logger.info("SSH 密钥内容: %s", key_content)
# ✅ 正确
logger.info("发现 SSH 密钥: %s", key_path)
```

---

## 3. 测试规范

### 3.1 测试组织

```
tests/
├── unit/                      # 单元测试（不需要外部依赖）
│   ├── test_models.py         # 数据模型测试
│   ├── test_scanner/
│   │   ├── test_app_scanner.py
│   │   ├── test_browser_scanner.py
│   │   └── ...
│   ├── test_planner/
│   ├── test_executor/
│   └── test_security/
│
├── integration/               # 集成测试（需要本机环境）
│   ├── test_scan_and_plan.py  # 扫描→规划 流程
│   └── test_transfer.py       # 本机内传输测试
│
├── e2e/                       # 端到端测试（需要两台 VM）
│   └── test_full_migration.py
│
├── fixtures/                  # 测试数据
│   ├── sample_profile.json    # 样例环境画像
│   ├── sample_plan.json       # 样例迁移计划
│   └── mock_registry/         # 模拟注册表数据
│
└── conftest.py                # pytest 共享 fixtures
```

### 3.2 测试编写原则

```python
# 每个测试函数只测一件事
# 测试名要清晰表达"测什么"和"期望什么"

class TestInstalledAppScanner:
    """InstalledAppScanner 的单元测试"""

    async def test_scan_finds_apps_from_registry(self, mock_registry):
        """测试：能从注册表中发现已安装应用"""
        scanner = InstalledAppScanner()
        result = await scanner.scan()
        assert len(result.apps) > 0
        assert any(app.name == "Google Chrome" for app in result.apps)

    async def test_scan_matches_winget_id(self, mock_registry, mock_winget):
        """测试：能将注册表应用与 winget ID 匹配"""
        scanner = InstalledAppScanner()
        result = await scanner.scan()
        chrome = next(app for app in result.apps if app.name == "Google Chrome")
        assert chrome.winget_id == "Google.Chrome"

    async def test_scan_handles_corrupted_registry(self, corrupted_registry):
        """测试：注册表损坏时能优雅处理而非崩溃"""
        scanner = InstalledAppScanner()
        result = await scanner.scan()  # 不应抛出异常
        assert result is not None
```

### 3.3 Mock 策略

```python
# 对外部依赖使用 Mock，确保单元测试不依赖真实环境
# 需要 Mock 的外部依赖：
#   - Windows 注册表 → 使用内存中的模拟数据
#   - 文件系统 → 使用临时目录
#   - winget 命令 → 使用预录制的输出
#   - Claude API → 使用预定义的响应
#   - 网络通信 → 使用 loopback

# 集成测试可以使用真实的本地环境
# 端到端测试使用真实的 VM 环境
```

---

## 4. Git 工作流

### 4.1 分支策略

```
main          — 稳定版本，所有测试通过
develop       — 开发主线
feature/xxx   — 功能开发分支
fix/xxx       — Bug 修复分支
```

### 4.2 Commit 消息格式

```
<type>(<scope>): <description>

类型（type）：
  feat     — 新功能
  fix      — Bug 修复
  docs     — 文档更新
  refactor — 代码重构
  test     — 测试相关
  chore    — 构建、配置等杂项

范围（scope）：
  core, scanner, planner, transfer, executor, discovery, cli, security

示例：
  feat(scanner): 实现 InstalledAppScanner 注册表扫描
  fix(transfer): 修复大文件断点续传偏移量计算错误
  test(scanner): 添加 BrowserScanner Chrome 书签解析测试
  docs: 更新 MILESTONES.md M2 进度
```

---

## 5. 安全开发规范

### 5.1 敏感数据处理

```python
# ❌ 绝对禁止
password = "my_password"              # 硬编码密码
logger.info(f"密码是: {password}")     # 日志中记录密码
open("credentials.txt", "w").write(key)  # 明文写入凭证

# ✅ 正确做法
encrypted = crypto.encrypt(sensitive_data, key)  # 加密后再存储
logger.info("凭证已加密处理")                     # 只记录操作，不记录内容
```

### 5.2 外部命令执行

```python
# ❌ 危险：字符串拼接命令（注入风险）
os.system(f"winget install {user_input}")

# ✅ 安全：使用参数列表
subprocess.run(["winget", "install", "--id", validated_id], check=True)
```

---

## 6. 依赖管理

### 6.1 核心依赖列表

```toml
[tool.poetry.dependencies]
python = "^3.11"
anthropic = "^0.40.0"        # Claude API SDK
grpcio = "^1.60.0"           # gRPC 通信
grpcio-tools = "^1.60.0"     # gRPC 代码生成
zeroconf = "^0.130.0"        # mDNS 设备发现
cryptography = "^42.0.0"     # 加密
rich = "^13.7.0"             # 美观的终端输出
typer = "^0.9.0"             # CLI 框架
pydantic = "^2.5.0"          # 数据验证（可选，与 dataclass 互补）

[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"
pytest-asyncio = "^0.23.0"
pytest-cov = "^4.1.0"        # 覆盖率
ruff = "^0.2.0"              # 代码检查和格式化
```

### 6.2 添加依赖的原则

- 优先使用 Python 标准库
- 新增第三方依赖需要说明理由
- 避免引入不维护的库
- Windows 兼容性是硬性要求
