"""EasyTransfer 迁移规划模块。

分析环境画像，匹配应用知识库，生成迁移计划。

主要组件：
- app_knowledge: 常见 Windows 应用知识库（winget ID、配置路径、迁移策略）
- analyzer: 分析 EnvironmentProfile，生成 MigrationAnalysis
- plan_builder: 构建结构化的迁移执行计划
"""
