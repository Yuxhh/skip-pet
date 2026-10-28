# Domain Docs

## 布局

本仓库采用 single-context：

- 根目录 GLOSSARY.md：统一领域术语。
- docs/adr/：记录已确认的架构决策。

## 阅读规则

探索项目之前，阅读 GLOSSARY.md，以及 docs/adr/ 中与当前任务相关的决策。
如果将来出现 GLOSSARY-MAP.md，按其中指引阅读相关上下文的词表。

缺失的文档直接跳过；术语或决策明确后，由 domain-modeling 按需创建。

## 使用规则

任务标题、设计建议、代码和测试中的领域概念沿用词表定义。
发现术语缺口时，记录供 domain-modeling 澄清。
提出与现有 ADR 冲突的方案时，明确指出冲突及重新讨论的理由。
