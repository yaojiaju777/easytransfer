# CLAUDE.md — AI Agent 开发指引

> 本文件是 AI Agent（Claude Code 及其他 AI 开发工具）的入口文件。
> 在开始任何开发工作之前，必须先阅读本文件和它引用的文档。

## 项目名称

**EasyTransfer** — Windows 电脑一键换机工具

## 项目一句话描述

一个基于 AI Agent 的 Windows 电脑迁移工具，能够智能扫描旧电脑上的应用、配置、文件和凭证，并在新电脑上自动重建完整的工作环境。

## 文档阅读顺序

开始开发前，请按以下顺序阅读文档：

1. `docs/specs/PRD.md` — 产品需求文档（理解"做什么"和"为什么做"）
2. `docs/specs/TECH_SPEC.md` — 技术规格文档（理解"怎么做"）
3. `docs/architecture/ARCHITECTURE.md` — 系统架构文档（理解整体结构）
4. `docs/specs/MILESTONES.md` — 里程碑与开发计划（理解开发节奏）
5. `docs/guides/DEV_GUIDE.md` — 开发规范（编码时遵守的规则）

## 当前开发阶段

**Phase 0 — 项目初始化与规划（当前）**

下一步：Phase 1 — 基础框架搭建

## 核心原则（Agent 必须遵守）

1. **用户确认优先**：任何涉及删除、覆盖、修改用户数据的操作，必须先获得用户确认
2. **安全第一**：所有凭证和密码必须加密传输和存储，永远不明文存储
3. **可回滚**：每个迁移步骤都必须支持回滚
4. **渐进式**：先生成迁移计划让用户审核，确认后才执行
5. **透明**：迁移过程中的每一步操作都要有清晰的日志和进度反馈

## 技术栈

- **语言**：Python 3.11+
- **AI 框架**：Claude Agent SDK（用于 Agent 智能决策）
- **网络通信**：gRPC（Agent 间通信）+ WebSocket（实时状态同步）
- **包管理**：Poetry
- **测试**：pytest
- **目标平台**：Windows 10/11

## 快速命令

```bash
# 安装依赖
poetry install

# 运行测试
poetry run pytest

# 启动源端 Agent（旧电脑）
poetry run python -m easytransfer.source

# 启动目标端 Agent（新电脑）
poetry run python -m easytransfer.target
```
