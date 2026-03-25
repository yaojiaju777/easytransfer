# 里程碑与开发计划

> Milestones & Development Plan — EasyTransfer
> 版本：0.1.0 | 最后更新：2026-03-25

---

## 开发方法论

本项目采用 **Spec-Driven Development（规格驱动开发）** 方法：

1. **先写规格文档**（PRD → Tech Spec → Architecture）← 我们在这里
2. **再写测试**（根据规格写测试用例）
3. **最后写代码**（让代码满足测试和规格）
4. **持续验证**（代码始终与规格文档保持一致）

每个 Milestone 都遵循这个顺序：**规格 → 测试 → 实现 → 验证**

---

## Milestone 总览

```
M0: 项目初始化        ▓▓▓▓▓▓▓▓▓▓ 当前阶段
M1: 基础框架          ░░░░░░░░░░
M2: 环境扫描          ░░░░░░░░░░
M3: 设备发现与通信     ░░░░░░░░░░
M4: AI 迁移规划       ░░░░░░░░░░
M5: 文件传输          ░░░░░░░░░░
M6: 迁移执行          ░░░░░░░░░░
M7: 端到端集成        ░░░░░░░░░░
M8: VM 测试验证       ░░░░░░░░░░
```

---

## M0: 项目初始化（当前）

**目标**：建立项目骨架和文档体系

**产出物**：
- [x] CLAUDE.md — Agent 入口文件
- [x] PRD.md — 产品需求文档
- [x] TECH_SPEC.md — 技术规格文档
- [x] ARCHITECTURE.md — 架构文档
- [x] MILESTONES.md — 本文件
- [ ] DEV_GUIDE.md — 开发规范
- [ ] pyproject.toml — 项目依赖配置
- [ ] 基本目录结构创建
- [ ] Git 仓库初始化

**完成标准**：
- 所有文档完整且一致
- AI Agent 读完文档后能理解项目全貌并开始开发

---

## M1: 基础框架

**目标**：搭建项目基础框架，能运行最简单的命令

**产出物**：
- [ ] Poetry 项目配置完成，所有依赖可安装
- [ ] 核心数据模型定义（core/models.py）
- [ ] 日志系统（core/logging.py）
- [ ] 配置系统（core/config.py）
- [ ] 自定义异常体系（core/errors.py）
- [ ] CLI 骨架（cli.py）—— 能运行 `easytransfer --help`
- [ ] 单元测试框架搭建

**验收命令**：
```bash
poetry install                       # 依赖安装成功
poetry run python -m easytransfer --help   # 显示帮助信息
poetry run pytest tests/unit/        # 单元测试通过
```

**完成标准**：
- `poetry install` 无报错
- `easytransfer --help` 显示版本号和可用命令
- 所有 core 模块的数据模型有对应的单元测试
- 代码覆盖率 > 80%

---

## M2: 环境扫描

**目标**：实现源端的环境扫描功能，能生成完整的环境画像

**产出物**：
- [ ] Scanner 基类和注册机制
- [ ] InstalledAppScanner — 扫描已安装应用
- [ ] AppConfigScanner — 扫描应用配置文件
- [ ] UserFileScanner — 扫描用户文件目录
- [ ] BrowserScanner — 扫描浏览器数据
- [ ] DevEnvScanner — 扫描开发环境
- [ ] GitSshScanner — 扫描 Git/SSH 配置
- [ ] 环境画像序列化/反序列化（JSON）
- [ ] 各扫描器的单元测试

**验收命令**：
```bash
poetry run python -m easytransfer scan         # 执行扫描
poetry run python -m easytransfer scan --output profile.json  # 输出为 JSON
poetry run pytest tests/unit/test_scanner/     # 扫描器测试通过
```

**完成标准**：
- 在测试 VM 上能扫描出所有预装的测试软件
- 扫描结果 JSON 格式正确，包含所有必要字段
- 扫描耗时 < 5 分钟
- 各扫描器有独立的单元测试

**开发子步骤**：

```
M2.1: Scanner 基础设施
  ├─ 定义 BaseScanner 抽象基类
  ├─ 实现 ScannerRegistry（管理所有扫描器）
  ├─ 实现 EnvironmentProfile 的 JSON 序列化
  └─ 编写基础设施的单元测试

M2.2: 应用扫描器（最核心）
  ├─ 从注册表读取已安装程序列表
  ├─ 从 winget 获取可用包信息
  ├─ 匹配已安装应用和 winget ID
  ├─ 识别应用的配置文件位置
  └─ 编写测试

M2.3: 文件和浏览器扫描器
  ├─ 扫描用户目录，按类别分组
  ├─ 计算各目录大小
  ├─ 识别可跳过的目录（缓存、依赖等）
  ├─ 扫描 Chrome/Edge 浏览器 Profile
  └─ 编写测试

M2.4: 开发环境和系统配置扫描器
  ├─ 检测 PATH 中的开发工具
  ├─ 扫描 Git/SSH 配置
  ├─ 扫描环境变量
  ├─ 扫描 Windows Terminal 配置
  └─ 编写测试
```

---

## M3: 设备发现与通信

**目标**：两台电脑能互相发现并建立安全的通信通道

**产出物**：
- [ ] mDNS 广播和发现
- [ ] 配对协议（6位配对码 + SRP）
- [ ] TLS 安全通道
- [ ] gRPC 控制通道（基于 proto 定义）
- [ ] 集成测试

**验收命令**：
```bash
# 在 VM-Source 上运行
poetry run python -m easytransfer serve --role source

# 在 VM-Target 上运行
poetry run python -m easytransfer connect --role target

# 两端成功配对并建立连接
```

**完成标准**：
- 同一局域网（虚拟网络）中两台 VM 能互相发现
- 配对过程安全（不传输明文配对码）
- 通道建立后能双向传输消息
- 通信使用 TLS 加密

---

## M4: AI 迁移规划

**目标**：实现 AI Agent 迁移计划生成功能

**产出物**：
- [ ] AI Planner（调用 Claude API 生成迁移计划）
- [ ] Rule-based Planner（本地备用规划器）
- [ ] 应用知识库（常见应用的迁移经验数据）
- [ ] 迁移计划的 CLI 展示（用户可在终端中审核）
- [ ] 用户交互（确认/修改计划）

**验收命令**：
```bash
# 读取之前生成的环境画像，生成迁移计划
poetry run python -m easytransfer plan --profile profile.json --output plan.json

# 显示迁移计划供用户审核
poetry run python -m easytransfer plan --show plan.json
```

**完成标准**：
- AI 能为测试环境生成合理的迁移计划
- 常见应用（Chrome, VS Code, Python 等）能正确识别安装方式
- 用户可以在 CLI 中审核和修改计划
- 当 AI API 不可用时，能退化到基于规则的规划器

---

## M5: 文件传输

**目标**：实现高效、安全、可靠的文件传输

**产出物**：
- [ ] 数据通道（TCP + TLS 流式传输）
- [ ] 文件打包器（小文件合并传输）
- [ ] SHA-256 校验
- [ ] 断点续传
- [ ] 传输进度显示
- [ ] 带宽控制

**验收命令**：
```bash
# 从源端传输文件到目标端
poetry run python -m easytransfer transfer --plan plan.json
```

**完成标准**：
- 能传输 10GB+ 文件无错误
- 所有文件哈希校验通过
- 支持断点续传（中断后恢复能继续）
- 传输速度达到网络带宽的 80%

---

## M6: 迁移执行

**目标**：在目标端执行迁移计划（安装应用、恢复配置等）

**产出物**：
- [ ] 执行引擎（按顺序和依赖关系执行）
- [ ] Winget 安装器
- [ ] 配置文件恢复器
- [ ] 环境变量恢复器
- [ ] 注册表恢复器
- [ ] 结果验证器
- [ ] 回滚机制

**验收命令**：
```bash
# 在目标端执行迁移计划
poetry run python -m easytransfer execute --plan plan.json
```

**完成标准**：
- winget 可用的应用能自动安装成功
- 配置文件被正确恢复到目标位置
- 环境变量正确设置
- 每个步骤有验证结果
- 失败的步骤能自动回滚

---

## M7: 端到端集成

**目标**：将所有模块串联为完整的一键迁移流程

**产出物**：
- [ ] 完整的 CLI 流程（从扫描到生成报告）
- [ ] 迁移报告生成器（HTML 格式）
- [ ] 迁移状态持久化（支持中断恢复）
- [ ] 错误处理和用户提示完善
- [ ] 集成测试

**验收命令**：
```bash
# 源端：一键开始
poetry run python -m easytransfer source

# 目标端：一键开始
poetry run python -m easytransfer target
```

**完成标准**：
- 完整流程能从头运行到尾
- 每个阶段的过渡自然流畅
- 错误处理覆盖所有已知异常场景
- 生成的迁移报告清晰、有用

---

## M8: VM 测试验证

**目标**：在两台 VM 之间验证完整的迁移功能

**测试场景**：

```
场景 1：开发者环境迁移
  源端预装：VS Code + 插件、Python 3.11、Node.js 18、Git + SSH 密钥
  验证：新电脑上所有工具可用，配置正确

场景 2：办公环境迁移
  源端预装：Chrome（带书签和扩展）、WPS Office、微信
  验证：浏览器数据完整，应用配置恢复

场景 3：大文件迁移
  源端：50GB 混合文件（文档、代码、图片）
  验证：文件完整性 100%，传输速度合理

场景 4：异常恢复
  迁移过程中断开网络 → 重连后继续
  迁移过程中关闭源端 → 重启后恢复

场景 5：部分迁移
  用户只选择迁移开发环境，跳过文件和办公应用
```

**完成标准**：
- 所有测试场景通过
- 迁移报告中无意外的失败项
- 性能达到 PRD 中的要求

---

## 给 AI Agent 的开发指引

### 开发每个 Milestone 时的标准流程

```
1. 阅读该 Milestone 的描述和完成标准
2. 阅读 TECH_SPEC.md 中相关模块的详细设计
3. 先编写测试文件（TDD）
4. 实现代码，让测试通过
5. 运行验收命令，确认功能正常
6. 更新本文件中的进度标记（ [ ] → [x] ）
```

### 代码实现的优先级

```
如果你不确定先实现什么，遵循这个优先级：
  1. 数据模型（models.py）—— 其他一切的基础
  2. 核心扫描功能 —— 产品的第一步
  3. 通信通道 —— 两台电脑的桥梁
  4. AI 规划 —— 产品的智能核心
  5. 文件传输 —— 数据搬运
  6. 执行引擎 —— 在新电脑上重建
  7. 报告和润色 —— 锦上添花
```
