# 系统架构文档

> Architecture Document — EasyTransfer
> 版本：0.2.0 | 最后更新：2026-03-25

---

## 1. 项目目录结构

```
easytransfer/
├── CLAUDE.md                          # AI Agent 开发入口文件
├── pyproject.toml                     # Poetry 项目配置
│
├── docs/
│   ├── specs/
│   │   ├── PRD.md                     # 产品需求文档
│   │   ├── TECH_SPEC.md               # 技术规格文档
│   │   └── MILESTONES.md              # 里程碑计划
│   ├── architecture/
│   │   └── ARCHITECTURE.md            # 本文件
│   └── guides/
│       └── DEV_GUIDE.md               # 开发规范
│
├── src/
│   └── easytransfer/
│       ├── __init__.py
│       ├── __main__.py                # 程序入口（CLI 模式）
│       ├── cli.py                     # 命令行界面
│       ├── mcp_server.py              # MCP Server 入口（技能模式）
│       │
│       ├── core/                      # 核心数据结构和工具
│       │   ├── __init__.py
│       │   ├── models.py              # 所有数据模型（dataclass）
│       │   ├── config.py              # 应用配置
│       │   ├── logging.py             # 日志系统
│       │   └── errors.py              # 自定义异常
│       │
│       ├── mcp/                       # MCP 协议层
│       │   ├── __init__.py
│       │   ├── server.py              # MCP Server 实现
│       │   └── tools.py               # MCP Tool 定义（6 个工具）
│       │
│       ├── scanner/                   # 环境扫描
│       │   ├── __init__.py
│       │   ├── base.py                # Scanner 基类
│       │   ├── app_scanner.py         # 已安装应用扫描
│       │   ├── config_scanner.py      # 应用配置扫描
│       │   ├── file_scanner.py        # 用户文件扫描
│       │   ├── browser_scanner.py     # 浏览器数据扫描
│       │   ├── dev_env_scanner.py     # 开发环境扫描
│       │   ├── git_ssh_scanner.py     # Git/SSH 配置扫描
│       │   ├── system_scanner.py      # 系统设置扫描
│       │   └── registry.py            # Scanner 注册表
│       │
│       ├── planner/                   # 迁移分析与规划
│       │   ├── __init__.py
│       │   ├── analyzer.py            # 环境分析器
│       │   ├── plan_builder.py        # 安装计划构建器
│       │   └── app_knowledge.py       # 应用知识库
│       │
│       ├── packager/                  # 迁移包打包
│       │   ├── __init__.py
│       │   ├── packer.py              # 打包器
│       │   ├── unpacker.py            # 解包器
│       │   └── manifest.py            # 清单文件处理
│       │
│       ├── transfer/                  # 数据传输（云端中转）
│       │   ├── __init__.py
│       │   ├── uploader.py            # 上传到中转服务器
│       │   ├── downloader.py          # 从中转服务器下载
│       │   ├── checksum.py            # 哈希校验
│       │   └── resume.py              # 断点续传
│       │
│       ├── executor/                  # 迁移执行（目标端）
│       │   ├── __init__.py
│       │   ├── engine.py              # 执行引擎
│       │   ├── installers/
│       │   │   ├── __init__.py
│       │   │   ├── winget_installer.py
│       │   │   ├── exe_installer.py
│       │   │   └── portable_installer.py
│       │   ├── restorers/
│       │   │   ├── __init__.py
│       │   │   ├── file_restorer.py
│       │   │   ├── config_restorer.py
│       │   │   └── env_restorer.py
│       │   └── verifier.py            # 结果验证器
│       │
│       ├── report/                    # 迁移报告
│       │   ├── __init__.py
│       │   └── generator.py           # 报告生成器
│       │
│       └── security/                  # 安全
│           ├── __init__.py
│           ├── crypto.py              # AES-256-GCM 加密/解密
│           ├── key_derivation.py      # 从迁移码派生密钥（PBKDF2）
│           └── credential_handler.py  # 凭证安全处理
│
├── restorer/                          # 单文件恢复器（独立构建）
│   ├── main.py                        # 恢复器入口
│   ├── ui.py                          # 简单 CLI 界面
│   └── build.py                       # PyInstaller 打包脚本
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
│
├── scripts/
│   ├── setup_test_source.ps1          # 搭建测试源端 VM
│   ├── verify_migration.ps1           # 验证迁移结果
│   └── build_restorer.ps1             # 构建单文件恢复器
│
└── proto/                             # 预留：未来局域网直连的协议定义
    └── easytransfer.proto
```

---

## 2. 模块依赖关系

```
                    ┌─────────────┐
                    │   mcp/      │  MCP 协议层（Agent 调用入口）
                    │   cli.py    │  CLI 入口
                    └──────┬──────┘
                           │ 调用
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ scanner/ │    │ packager/│    │ executor/│
    └─────┬────┘    └─────┬────┘    └─────┬────┘
          │               │               │
          ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ planner/ │    │transfer/ │    │ report/  │
    └─────┬────┘    └─────┬────┘    └─────┬────┘
          │               │               │
          └───────────────┼───────────────┘
                          ▼
                   ┌──────────────┐
                   │   core/      │  数据模型、配置、日志、异常
                   ├──────────────┤
                   │  security/   │  加密、密钥派生
                   └──────────────┘
```

**依赖规则**：
- `core` 和 `security` 是基础层，不依赖任何业务模块
- 业务模块之间尽量不互相依赖
- `mcp/` 和 `cli.py` 是顶层入口，可以调用所有业务模块

---

## 3. 关键技术选型

| 需求 | 选型 | 理由 |
|------|------|------|
| 编程语言 | Python 3.11+ | 开发效率高，AI/MCP 生态好 |
| 包管理 | Poetry | 现代 Python 项目标准 |
| MCP 框架 | mcp (Python SDK) | Anthropic 官方 MCP SDK |
| 加密 | cryptography | 工业级加密库 |
| CLI 界面 | rich + typer | 美观的终端输出 |
| Windows 注册表 | winreg (标准库) | 无需额外依赖 |
| 异步 | asyncio | IO 密集任务的最佳选择 |
| 测试 | pytest + pytest-asyncio | Python 测试标准 |
| 打包恢复器 | PyInstaller | 生成单文件 .exe |
| 文件哈希 | hashlib (标准库) | SHA-256 校验 |

---

## 4. 数据流

### 4.1 迁移码模式（MVP）

```
旧电脑                                                 新电脑

[1] Agent 调用 scan_environment
         │
         ▼
    扫描所有 Scanner
         │
         ▼
    生成 EnvironmentProfile (JSON)
         │
[2] Agent 调用 analyze_migration
         │
         ▼
    分析并展示给用户
    用户确认迁移选项
         │
[3] Agent 调用 create_migration_package
         │
         ▼
    收集文件和配置
    生成 install_plan.json
    打包为 tar.gz
    生成迁移码 → 派生密钥 → AES-256 加密
    上传到中转服务器
         │
         ▼
    返回迁移码给用户
    用户将迁移码告诉新电脑
                                              [4] 输入迁移码
                                                   │
                                                   ▼
                                              下载加密迁移包
                                              迁移码 → 派生密钥 → 解密
                                                   │
                                                   ▼
                                              读取 install_plan.json
                                              执行恢复：
                                                - winget install 应用
                                                - 复制配置文件
                                                - 复制用户文件
                                                - 设置环境变量
                                                   │
                                              [5] 验证每个步骤
                                                   │
                                                   ▼
                                              生成迁移结果报告
```

### 4.2 核心状态机

```
IDLE → SCANNING → ANALYZED → PACKAGING → PACKAGED
                                            │
                    ┌───────────────────────┘
                    ▼  （切换到新电脑）
                DOWNLOADING → RESTORING → VERIFYING → COMPLETED
                                 │
                                 ├→ PARTIALLY_COMPLETED（部分失败）
                                 └→ FAILED（严重错误）
```

---

## 5. 性能考虑

### 5.1 扫描性能
- 文件系统扫描使用 `os.scandir()`（比 `os.listdir()` 快）
- 大目录扫描使用生成器，避免一次性加载
- 多个 Scanner 可以并行执行

### 5.2 打包性能
- 使用流式压缩，不将整个包加载到内存
- 跳过不需要的目录（node_modules, .venv, __pycache__ 等）
- 小文件合并后压缩效率更高

### 5.3 传输性能
- 大文件分块上传/下载（每块 10MB）
- 支持断点续传
- 并行上传多个块

### 5.4 恢复性能
- 多个不冲突的应用可以并行安装（默认串行，因为 winget 有锁）
- 文件恢复和应用安装可以并行
- 配置恢复在对应应用安装完成后立即执行
