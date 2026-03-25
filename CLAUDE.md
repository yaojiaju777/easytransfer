# CLAUDE.md — AI Agent 开发指引

> 本文件是 AI Agent（Claude Code 及其他 AI 开发工具）的入口文件。
> 在开始任何开发工作之前，必须先阅读本文件和它引用的文档。

## 项目名称

**EasyTransfer** — AI Agent 电脑换机技能包

## 项目一句话描述

一个以 MCP Server 形式运行的 AI Agent 技能包（Skill），让用户的 AI 助手（如 OpenClaw、Claude Desktop 等）获得"帮用户完成 Windows 电脑迁移"的能力。用户只需要说一句话，Agent 就能扫描旧电脑环境、打包迁移数据、在新电脑上自动恢复一切。

## 产品形态

- **主要形态**：MCP Server（AI Agent 的技能包）
- **辅助形态**：单文件恢复器 .exe（新电脑无 Agent 时使用）
- **也支持**：独立 CLI 工具（不依赖 Agent 也能用）

## 文档阅读顺序

开始开发前，请按以下顺序阅读文档：

1. `docs/specs/PRD.md` — 产品需求文档（理解"做什么"和"为什么做"）
2. `docs/specs/TECH_SPEC.md` — 技术规格文档（理解"怎么做"）
3. `docs/architecture/ARCHITECTURE.md` — 系统架构文档（理解整体结构）
4. `docs/specs/MILESTONES.md` — 里程碑与开发计划（理解开发节奏）
5. `docs/guides/DEV_GUIDE.md` — 开发规范（编码时遵守的规则）

## 当前开发阶段

**M0 — 项目初始化与规格文档（已完成）**

下一步：**M1 — 基础框架 + MCP 骨架**

## 核心原则（Agent 必须遵守）

1. **用户确认优先**：涉及删除、覆盖、修改用户数据的操作，必须先获得用户确认
2. **安全第一**：所有凭证和密码必须加密处理，永远不明文传输或存储
3. **可回滚**：每个迁移步骤都必须支持回滚
4. **渐进式**：先扫描 → 再分析 → 用户确认 → 才执行
5. **透明**：每一步操作都要有清晰的日志和进度反馈
6. **优雅降级**：单个步骤失败不应阻止其他步骤执行

## 技术栈

- **语言**：Python 3.11+
- **MCP 框架**：mcp (Python SDK)
- **加密**：cryptography (AES-256-GCM)
- **CLI**：typer + rich
- **包管理**：Poetry
- **测试**：pytest + pytest-asyncio
- **目标平台**：Windows 10/11
- **打包**：PyInstaller（单文件恢复器）

## 快速命令

```bash
# 安装依赖
poetry install

# 运行测试
poetry run pytest

# CLI 模式
poetry run python -m easytransfer scan              # 扫描环境
poetry run python -m easytransfer package            # 打包迁移数据
poetry run python -m easytransfer restore --code XX  # 恢复

# MCP Server 模式（供 Agent 调用）
poetry run python -m easytransfer.mcp_server

# 构建单文件恢复器
poetry run python restorer/build.py
```
