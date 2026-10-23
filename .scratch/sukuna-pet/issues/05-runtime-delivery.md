# 第一版采用怎样的独立运行与交付方案

Id: 05
Parent: ../map.md
Labels: wayfinder:grilling
Type: grilling
Mode: HITL
Status: open
Assignee:
Blocked by: 01, 02, 06, 07

## Question

在参考应用、素材及双宿主接口约束明确后，选择独立项目的窗口绘制、动画与宿主适配方式，确认源码运行及 Windows 交付形态，以及能证明不依赖原目录、双宿主联动及点击拖动退出均有效的验收方式。

## Context

先由代理给出有证据的建议和取舍，用户只需确认影响使用的交付选择，不要求用户替代理回答技术事实。不能因为参考应用采用 PySide6 就直接把它作为用户已确认的技术决定。后续交付不得依赖 `D:\dsh-pet` 中的私有路径或其已安装环境。

## Comments

- 2026-10-23：规划阶段创建，尚未认领。
