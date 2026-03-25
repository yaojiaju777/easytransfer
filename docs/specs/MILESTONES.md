# 里程碑与开发计划

> Milestones & Development Plan — EasyTransfer
> 版本：0.2.0 | 最后更新：2026-03-25

---

## 开发方法论

**Spec-Driven Development（规格驱动开发）**：
1. 先写规格文档 ← 我们在这里
2. 再写测试
3. 最后写代码
4. 持续验证

---

## Milestone 总览

```
M0: 项目初始化与规格文档    ▓▓▓▓▓▓▓▓▓▓ 当前阶段
M1: 基础框架 + MCP 骨架    ░░░░░░░░░░
M2: 环境扫描               ░░░░░░░░░░
M3: 迁移分析与规划          ░░░░░░░░░░
M4: 打包与加密              ░░░░░░░░░░
M5: 恢复执行引擎            ░░░░░░░░░░
M6: 端到端集成              ░░░░░░░░░░
M7: 单文件恢复器构建        ░░░░░░░░░░
M8: VM 测试验证             ░░░░░░░░░░
```

---

## M0: 项目初始化（当前）

**目标**：建立项目骨架和完整的规格文档体系

**产出物**：
- [x] CLAUDE.md — Agent 入口文件
- [x] PRD.md — 产品需求文档（v0.2 — 技能包定位）
- [x] TECH_SPEC.md — 技术规格文档（v0.2 — MCP Server 架构）
- [x] ARCHITECTURE.md — 架构文档（v0.2）
- [x] MILESTONES.md — 本文件
- [x] DEV_GUIDE.md — 开发规范
- [x] pyproject.toml — 项目依赖配置
- [x] 基本目录结构创建
- [x] Git 仓库初始化
- [ ] 更新 CLAUDE.md 反映新产品定位

**完成标准**：
- AI Agent 读完文档后能理解项目全貌并开始开发

---

## M1: 基础框架 + MCP 骨架

**目标**：搭建项目基础框架，MCP Server 能启动，CLI 能运行

**产出物**：
- [ ] 核心数据模型（core/models.py）— 所有 dataclass 定义
- [ ] 自定义异常体系（core/errors.py）
- [ ] 日志系统（core/logging.py）
- [ ] 配置系统（core/config.py）
- [ ] MCP Server 骨架（mcp/server.py）— 能启动，6 个工具注册但返回 mock 数据
- [ ] CLI 骨架（cli.py）— `easytransfer --help` 能运行
- [ ] 单元测试框架搭建

**验收命令**：
```bash
poetry install
poetry run python -m easytransfer --help         # CLI 显示帮助
poetry run python -m easytransfer.mcp_server      # MCP Server 启动
poetry run pytest tests/unit/                     # 测试通过
```

**完成标准**：
- MCP Server 能启动并响应工具列表请求
- 所有数据模型有单元测试
- CLI 显示版本号和命令列表

**开发子步骤**：
```
M1.1: core/ 模块
  ├─ models.py — 定义 EnvironmentProfile, AppInfo, MigrationPackageInfo 等
  ├─ errors.py — EasyTransferError 及各子类
  ├─ logging.py — 基于 Python logging + rich 的日志
  ├─ config.py — 配置文件读取
  └─ 编写单元测试

M1.2: MCP Server 骨架
  ├─ mcp/server.py — MCP Server 初始化和启动
  ├─ mcp/tools.py — 6 个工具的定义（参数、描述、返回类型）
  ├─ 每个工具暂时返回 mock 数据
  └─ 编写测试

M1.3: CLI 骨架
  ├─ cli.py — 使用 typer 定义命令
  ├─ 命令：scan, package, restore, verify
  └─ 每个命令暂时打印提示信息
```

---

## M2: 环境扫描

**目标**：实现源端环境扫描，能生成完整的环境画像

**产出物**：
- [ ] Scanner 基类和注册机制（scanner/base.py, scanner/registry.py）
- [ ] InstalledAppScanner — 从注册表和 winget 扫描已安装应用
- [ ] AppConfigScanner — 识别应用配置文件位置
- [ ] UserFileScanner — 扫描用户文件目录
- [ ] BrowserScanner — 扫描 Chrome/Edge 浏览器数据
- [ ] DevEnvScanner — 扫描开发环境
- [ ] GitSshScanner — 扫描 Git/SSH 配置
- [ ] MCP 工具 scan_environment 连接到真实扫描逻辑
- [ ] CLI 命令 `easytransfer scan` 连接到真实扫描逻辑

**验收命令**：
```bash
# 在测试 VM 上运行扫描
poetry run python -m easytransfer scan
poetry run python -m easytransfer scan --output profile.json
# 验证 JSON 输出包含所有预装软件
poetry run pytest tests/unit/test_scanner/
```

**完成标准**：
- 能识别 VM 上所有预装的测试软件
- 输出的 JSON 格式正确
- 扫描耗时 < 5 分钟
- 各扫描器有独立单元测试

**开发子步骤**：
```
M2.1: Scanner 基础设施
  ├─ base.py — BaseScanner 抽象基类
  ├─ registry.py — ScannerRegistry 管理所有扫描器
  └─ 测试

M2.2: 应用扫描（核心）
  ├─ app_scanner.py — 注册表读取 + winget 匹配
  ├─ config_scanner.py — 识别各应用的配置文件
  └─ 测试

M2.3: 文件和浏览器扫描
  ├─ file_scanner.py — 用户目录扫描
  ├─ browser_scanner.py — Chrome/Edge Profile
  └─ 测试

M2.4: 开发环境和系统扫描
  ├─ dev_env_scanner.py — 运行时检测
  ├─ git_ssh_scanner.py — Git/SSH 配置
  └─ 测试
```

---

## M3: 迁移分析与规划

**目标**：实现对环境画像的智能分析，生成迁移建议

**产出物**：
- [ ] 环境分析器（planner/analyzer.py）
- [ ] 应用知识库（planner/app_knowledge.py）— 常见应用的迁移策略
- [ ] 安装计划构建器（planner/plan_builder.py）
- [ ] MCP 工具 analyze_migration 连接到真实逻辑

**验收命令**：
```bash
poetry run python -m easytransfer analyze --profile profile.json
poetry run pytest tests/unit/test_planner/
```

**完成标准**：
- 能正确判断哪些应用可以通过 winget 自动安装
- 应用知识库覆盖至少 50 个常见应用
- 生成的分析报告清晰、有用

---

## M4: 打包与加密

**目标**：实现迁移包的打包、加密和上传

**产出物**：
- [ ] 打包器（packager/packer.py）— 生成 .etpkg 文件
- [ ] 清单文件处理（packager/manifest.py）
- [ ] 加密（security/crypto.py）— AES-256-GCM
- [ ] 密钥派生（security/key_derivation.py）— 迁移码 → 密钥
- [ ] 上传（transfer/uploader.py）— 上传到中转服务器
- [ ] MCP 工具 create_migration_package 连接到真实逻辑

**验收命令**：
```bash
poetry run python -m easytransfer package --profile profile.json
# 输出迁移码和包大小
poetry run pytest tests/unit/test_packager/
poetry run pytest tests/unit/test_security/
```

**完成标准**：
- 能将扫描结果打包为 .etpkg 文件
- 加密后的包无法在没有迁移码的情况下解密
- 打包过程跳过 node_modules 等不需要的目录
- 有加密/解密的单元测试

---

## M5: 恢复执行引擎

**目标**：在目标端实现迁移包的解密、解包和恢复

**产出物**：
- [ ] 解包器（packager/unpacker.py）
- [ ] 下载器（transfer/downloader.py）— 从中转服务器下载
- [ ] 执行引擎（executor/engine.py）
- [ ] Winget 安装器（executor/installers/winget_installer.py）
- [ ] 配置恢复器（executor/restorers/config_restorer.py）
- [ ] 文件恢复器（executor/restorers/file_restorer.py）
- [ ] 环境变量恢复器（executor/restorers/env_restorer.py）
- [ ] 验证器（executor/verifier.py）
- [ ] MCP 工具 restore_from_package 和 verify_migration 连接到真实逻辑

**验收命令**：
```bash
poetry run python -m easytransfer restore --code 123456
poetry run pytest tests/unit/test_executor/
```

**完成标准**：
- 能从迁移码下载并解密迁移包
- winget 可用的应用能自动安装
- 配置文件被正确恢复到目标位置
- 每个步骤有验证结果

---

## M6: 端到端集成

**目标**：将所有模块串联为完整流程

**产出物**：
- [ ] MCP Server 完整流程可用（6 个工具全部连接真实逻辑）
- [ ] CLI 完整流程可用
- [ ] 迁移报告生成器（report/generator.py）
- [ ] 回滚功能（MCP 工具 rollback_migration）
- [ ] 迁移状态持久化
- [ ] 集成测试

**验收命令**：
```bash
# CLI 完整流程
poetry run python -m easytransfer scan --output profile.json
poetry run python -m easytransfer package --profile profile.json
# 记下迁移码，在另一台 VM 上：
poetry run python -m easytransfer restore --code XXXXXX
poetry run python -m easytransfer verify

# MCP 模式：启动 server，Agent 调用工具
poetry run python -m easytransfer.mcp_server
```

**完成标准**：
- 完整流程能从头运行到尾
- 迁移报告清晰、有用
- 错误处理覆盖所有已知场景

---

## M7: 单文件恢复器构建

**目标**：构建可独立运行的单文件恢复器 .exe

**产出物**：
- [ ] 恢复器入口（restorer/main.py）
- [ ] 简单 CLI 界面（restorer/ui.py）
- [ ] PyInstaller 打包配置（restorer/build.py）
- [ ] 构建脚本（scripts/build_restorer.ps1）

**验收命令**：
```bash
# 构建恢复器
poetry run python restorer/build.py
# 产出 dist/EasyTransfer-Restorer.exe (<50MB)
# 在新 VM 上运行
./EasyTransfer-Restorer.exe --code XXXXXX
```

**完成标准**：
- 生成的 .exe < 50MB
- 无需 Python 环境即可运行
- 输入迁移码后能完成恢复

---

## M8: VM 测试验证

**目标**：在两台 VM 之间验证完整功能

**测试场景**：
```
场景 1：开发者环境迁移
  源端预装：VS Code + 插件、Python 3.11、Node.js 18、Git + SSH
  验证：新电脑上所有工具可用，配置正确

场景 2：办公环境迁移
  源端预装：Chrome + 书签 + 扩展、WPS Office
  验证：浏览器数据完整

场景 3：大文件迁移
  源端：10GB 混合文件
  验证：文件完整性 100%

场景 4：单文件恢复器
  新 VM 上无 Python、无 Agent，仅用恢复器 .exe
  验证：能正确恢复
```

**完成标准**：
- 所有测试场景通过
- 性能达到 PRD 要求

---

## 给 AI Agent 的开发指引

### 每个 Milestone 的标准流程

```
1. 阅读该 Milestone 的描述和完成标准
2. 阅读 TECH_SPEC.md 中相关模块的详细设计
3. 先编写测试（TDD）
4. 实现代码，让测试通过
5. 运行验收命令确认功能正常
6. 更新本文件中的进度标记（ [ ] → [x] ）
```

### 代码实现优先级

```
1. core/models.py — 一切的基础
2. mcp/ — 技能包的入口
3. scanner/ — 产品的第一步
4. planner/ — 智能分析
5. packager/ + security/ — 打包加密
6. executor/ — 恢复执行
7. transfer/ — 云端传输
8. report/ — 报告润色
9. restorer/ — 独立恢复器
```
