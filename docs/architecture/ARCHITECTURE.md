# 系统架构文档

> Architecture Document — EasyTransfer
> 版本：0.1.0 | 最后更新：2026-03-25

---

## 1. 项目目录结构

```
easytransfer/
├── CLAUDE.md                          # AI Agent 入口文件（必读）
├── pyproject.toml                     # Poetry 项目配置
├── README.md                          # 项目说明
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
│       ├── __main__.py                # 程序入口
│       ├── cli.py                     # 命令行界面
│       │
│       ├── core/                      # 核心数据结构和工具
│       │   ├── __init__.py
│       │   ├── models.py              # 所有数据模型（dataclass）
│       │   ├── config.py              # 应用配置
│       │   ├── logging.py             # 日志系统
│       │   └── errors.py              # 自定义异常
│       │
│       ├── discovery/                 # 设备发现与配对
│       │   ├── __init__.py
│       │   ├── mdns.py                # mDNS 广播和发现
│       │   ├── pairing.py             # 配对协议
│       │   └── secure_channel.py      # 安全通道建立
│       │
│       ├── scanner/                   # 环境扫描（源端使用）
│       │   ├── __init__.py
│       │   ├── base.py                # Scanner 基类
│       │   ├── app_scanner.py         # 已安装应用扫描
│       │   ├── config_scanner.py      # 应用配置扫描
│       │   ├── file_scanner.py        # 用户文件扫描
│       │   ├── browser_scanner.py     # 浏览器数据扫描
│       │   ├── dev_env_scanner.py     # 开发环境扫描
│       │   ├── git_ssh_scanner.py     # Git/SSH 配置扫描
│       │   ├── system_scanner.py      # 系统设置扫描
│       │   └── registry.py            # Scanner 注册表（管理所有扫描器）
│       │
│       ├── planner/                   # AI 迁移规划
│       │   ├── __init__.py
│       │   ├── ai_planner.py          # AI Agent 规划器（调用 Claude API）
│       │   ├── rule_planner.py        # 基于规则的备用规划器
│       │   ├── plan_builder.py        # 迁移计划构建器
│       │   └── app_knowledge.py       # 应用知识库（常见应用的迁移经验）
│       │
│       ├── transfer/                  # 数据传输
│       │   ├── __init__.py
│       │   ├── control_channel.py     # gRPC 控制通道
│       │   ├── data_channel.py        # 文件数据通道
│       │   ├── file_packer.py         # 文件打包（小文件合并）
│       │   ├── checksum.py            # 哈希校验
│       │   └── resume.py              # 断点续传状态管理
│       │
│       ├── executor/                  # 迁移执行（目标端使用）
│       │   ├── __init__.py
│       │   ├── engine.py              # 执行引擎（按顺序执行 MigrationItem）
│       │   ├── installers/
│       │   │   ├── __init__.py
│       │   │   ├── winget_installer.py    # winget 安装器
│       │   │   ├── exe_installer.py       # 静默 exe 安装器
│       │   │   └── portable_installer.py  # 绿色软件安装器
│       │   ├── restorers/
│       │   │   ├── __init__.py
│       │   │   ├── file_restorer.py       # 文件恢复
│       │   │   ├── config_restorer.py     # 配置恢复
│       │   │   ├── registry_restorer.py   # 注册表恢复
│       │   │   └── env_restorer.py        # 环境变量恢复
│       │   └── verifier.py            # 结果验证器
│       │
│       ├── report/                    # 迁移报告
│       │   ├── __init__.py
│       │   ├── generator.py           # 报告生成器
│       │   └── templates/             # HTML 报告模板
│       │       └── report.html
│       │
│       └── security/                  # 安全相关
│           ├── __init__.py
│           ├── crypto.py              # 加密/解密工具
│           ├── srp.py                 # SRP 配对协议
│           └── credential_handler.py  # 凭证安全处理
│
├── tests/
│   ├── unit/                          # 单元测试
│   ├── integration/                   # 集成测试
│   └── e2e/                           # 端到端测试
│
├── scripts/
│   ├── setup_test_source.ps1          # 搭建测试源端 VM
│   ├── setup_test_target.ps1          # 搭建测试目标端 VM
│   ├── verify_migration.ps1           # 验证迁移结果
│   └── reset_target.ps1              # 重置目标端 VM
│
└── proto/
    └── easytransfer.proto             # gRPC 协议定义文件
```

---

## 2. 模块依赖关系

```
依赖方向：箭头表示"依赖于"

cli
 ├──→ discovery
 ├──→ scanner ──→ core
 ├──→ planner ──→ core
 │      └──→ AI API (Claude)
 ├──→ transfer ──→ core, security
 ├──→ executor ──→ core, transfer
 └──→ report ──→ core

security ──→ core（基础层，被多个模块依赖）
```

**依赖规则**：
- `core` 是基础层，不依赖任何其他业务模块
- `security` 只依赖 `core`
- 其他模块可以依赖 `core` 和 `security`，但业务模块之间尽量不互相依赖
- `cli` 是顶层协调者，可以依赖所有模块

---

## 3. 关键技术选型

| 需求 | 选型 | 理由 |
|------|------|------|
| 编程语言 | Python 3.11+ | 开发效率高，AI 生态好，Windows 兼容好 |
| 包管理 | Poetry | 现代 Python 项目标准 |
| AI 能力 | Claude API (Anthropic SDK) | 强推理能力，适合复杂决策 |
| Agent 间通信 | gRPC | 强类型、高性能、支持双向流 |
| 设备发现 | zeroconf (Python库) | 成熟的 mDNS 实现 |
| 加密 | cryptography (Python库) | 工业级加密库 |
| 命令行界面 | rich + typer | 美观的 CLI 输出 + 优雅的命令行参数解析 |
| Windows 注册表 | winreg (标准库) | Python 自带，无需额外依赖 |
| 异步 | asyncio | Python 原生异步，适合 IO 密集的迁移任务 |
| 测试 | pytest + pytest-asyncio | Python 测试标准 |
| 文件哈希 | hashlib (标准库) | SHA-256 校验 |

---

## 4. 核心流程的状态机

### 4.1 整体迁移状态

```
                    ┌─────────────┐
                    │    IDLE     │  初始状态
                    └──────┬──────┘
                           │ 启动
                    ┌──────▼──────┐
                    │  DISCOVERING │  发现对端
                    └──────┬──────┘
                           │ 配对成功
                    ┌──────▼──────┐
                    │   SCANNING  │  扫描旧电脑环境
                    └──────┬──────┘
                           │ 扫描完成
                    ┌──────▼──────┐
                    │  PLANNING   │  AI 生成迁移计划
                    └──────┬──────┘
                           │ 用户确认计划
                    ┌──────▼──────┐
                    │  MIGRATING  │  执行迁移
                    └──────┬──────┘
                           │ 迁移完成
                    ┌──────▼──────┐
                    │  COMPLETED  │  生成报告
                    └─────────────┘

任何阶段都可以转到：
  → PAUSED（暂停，可恢复）
  → CANCELLED（取消，可回滚）
  → ERROR（错误，等待用户决策）
```

### 4.2 单个 MigrationItem 的状态

```
PENDING → APPROVED → RUNNING → SUCCESS
                        │
                        ├──→ RETRYING → RUNNING
                        │
                        └──→ FAILED

PENDING → REJECTED → SKIPPED
```

---

## 5. Agent 通信协议概要

源端和目标端 Agent 之间的通信消息类型：

```protobuf
// 核心消息类型（简化版，详见 proto/easytransfer.proto）

// 配对请求
message PairRequest { string pairing_code = 1; }

// 环境画像传输
message ProfileTransfer { EnvironmentProfile profile = 1; }

// 迁移计划传输
message PlanTransfer { MigrationPlan plan = 1; }

// 迁移控制命令
message MigrationCommand {
  enum Type { START, PAUSE, RESUME, CANCEL, SKIP_ITEM }
  Type type = 1;
  string item_id = 2;  // 可选，指定具体项
}

// 进度更新
message ProgressUpdate {
  string item_id = 1;
  string status = 2;
  float percent = 3;
  string message = 4;
}

// 文件传输请求
message FileRequest { string file_path = 1; int64 offset = 2; }
message FileChunk { bytes data = 1; string hash = 2; bool is_last = 3; }
```

---

## 6. 性能考虑

### 6.1 内存管理
- 文件传输使用流式处理，不将整个文件加载到内存
- 大目录扫描使用生成器（generator），避免一次性加载所有文件信息
- 环境画像序列化后通常 < 10MB，可以安全地在内存中操作

### 6.2 并发策略
- 文件扫描：使用 asyncio + ThreadPoolExecutor（因为文件IO是阻塞的）
- 文件传输：支持多文件并行传输（默认 4 个并行流）
- 应用安装：串行执行（避免安装冲突）
- AI API 调用：带超时和重试机制

### 6.3 AI API 使用优化
- 尽量批量发送信息给 AI（不要一个应用一个应用地问）
- 缓存常见应用的迁移策略（减少 API 调用）
- 本地规则处理简单情况，只有复杂决策才调用 AI
