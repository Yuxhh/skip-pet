# #53：作者验收通过，正式交付

2026-10-27（Asia/Shanghai），作者在本聊天明确回复“通过了”。正式交付为 `dist/accepted-0.4.0/release/`：与当前实际安装的 #55 构建逐文件一致，包含 #54 菜单顺序和 #55 托盘更新。Setup SHA-256 为 `df997dcaef3f675024840245b88bc6c56976a0d0a6289b719baaf507931b36fe`，人设版本 `sukuna-2026-10-27-v1`。原始 Setup、源码 ZIP 与报告均未重新构建。

最终结论见 [验收记录](acceptance.md)、[作者确认及产物哈希](acceptance.json)、[最终安装与交付审计](accepted-installation-audit.json)和[最终安装版冻结检查](accepted-runtime.json)。186 个运行文件、源码 22 个模块、许可及交付校验和均已核对。后续构建的补充验证见 [#54](../issue-54/README.md)、[#55](../issue-55/README.md)。这些后续改动不混入本票验收收尾提交。

下方是较早 #53 候选的构建时记录，其待人工状态及 a4e1216f… 哈希已被本节取代。保留未验硬件与环境限制；不宣称完成原有限制之外的验证。没有公开发布或创建 Release。

---

# #53：0.4.0 安装候选与作者试聊交接

2026-10-27（Asia/Shanghai）。候选已构建、本机安装并验证；作者真实语气验收待进行，#53 保持开放并转 ready-for-human。规格为 [#53](https://github.com/xyd-0811/skip-pet/issues/53)、[#48 完整确认](https://github.com/xyd-0811/skip-pet/issues/48#issuecomment-6434830497)、[#46 作者决议](https://github.com/xyd-0811/skip-pet/issues/46#issuecomment-6432965439)。#52 已关闭。

## 固定候选

- 安装器：`dist/issue-53/release/Setup.exe`，版本 **0.4.0**。
- Setup SHA-256：`a4e1216f113d7cabdf72a5aeee1eda1fdf6d4346cffa985dec47870b720b84b8`。
- 人设：**sukuna-2026-10-27-v1**；固定 deepseek-flash，关闭思考。
- 同目录提供对应源码 ZIP、build-report.json、SHA256SUMS.txt、candidate.json、试聊验收.md。未公开发布或创建 GitHub Release。
- 运行代码基点：`485e66580580ecfc7ade702a561dea00cb2a8b1d`。源码快照额外保留工作区已有 task_bubble.py，文本内容在归一换行后与已验收 0.3.0 源码 ZIP 相同；此改动不属于本票提交。源码 ZIP 与报告中的模块哈希是重建依据，不声称 ZIP 是单一 Git 提交。其余用户原有改动未混入候选快照或本票提交。
- 最初候选发现从右下角角色打开聊天时窗口越界，已修复聊天/设置初始工作区定位，并重建、重装、重验。旧候选保留在本机 .scratch，不供作者验收。

## 本机安装与冻结运行

环境：Windows 11 x64 build 26200；单显示器 1920×1080；CPython 3.14.4、PySide6 6.12.0、PyInstaller 6.22.3、Inno Setup 6.7.3。沿用锁定依赖。来源核对固定 dsh-pet `34d810b1eadd98d00e7cb9b3b51428a45b5bf03e`，参考工作树保持干净。

对照上游 `pet/chat/models.py::SecretStore` 的后端可用性及失败反馈、`packaging/dsh-pet.iss` 的当前用户安装与升级机制，以及 `pet/updater.py` 的大小/摘要校验。本项目继续使用当前用户 Credential Manager 适配器和完整 Inno 安装包，增加本机冻结验证入口及交付哈希；未引入上游更新下载器、默认人设或个人数据。

[安装结果](installation.json)与[升级前记录](install-before.json)：0.3.0 → 0.4.0 的真实安装器退出 0，默认安装目录为 `%LOCALAPPDATA%\Programs\SukunaPet`；修正窗口位置后再次安装退出 0。偏好文件前后 SHA-256 都为 `7c5efffcd1318410abd3aae3d3c3de5ebf51a1ab3377d1bae5053998f23655ea`。原 `dist/release/Setup.exe` 保持历史哈希 `35b37f84dfd86df7f020b3fe2de6238f1d6d30eef14e30a1f4b83370953d9ba9`。

[安装版冻结验证](installed-runtime.json)：真实安装目录的 EXE 从 Windows 目录启动，退出码 0；windows 平台、frozen=true。使用 `skip-pet/installation-check/<随机 ID>` 合成凭据，不访问产品凭据目标；Windows 实际保存、第二个冻结进程读取、删除均通过。真实适配器拒绝超过 2560 字节的值后，仅内存降级提示/释放通过；没有关闭 Windows 凭据服务或修改系统策略，因此不能冒称验证了所有系统后端不可用分支。

合成会话及原样人设快照经第二个冻结进程恢复；generating 恢复为 incomplete。聊天重复激活复用窗口，关闭不退出桌宠，设置复用、模式/大小变更、未知字段和 dsh_bridge 字段保留通过。Windows CA 已载入，_ssl.pyd 随包；本检查没有请求真实计费服务，也没有测 HTTPS 端到端链路。

[默认数据目录元数据](default-data-metadata.json)：正常安装版首次打开聊天后，在 `%LOCALAPPDATA%\skip-pet\sukuna-pet\chat\sessions` 实际生成 schema 1 的空会话，消息数 0、人设版本正确；重启后列表恢复同一空会话。未记录聊天正文。合成的完整会话/未完成重启验证使用隔离目录，与默认目录证据分别记录。

实际 UI 操作确认右键入口、完整可见的首次聊天/设置窗口及“关于”版本/署名。截图：[聊天](installed-chat.png)、[AI 设置](installed-settings-ai.png)、[关于](installed-about.png)。冻结检查另覆盖重复开关；不把 Qt 自动操作当作所有真实硬件与驱动的验证。

## 对照 #48 的验收矩阵

| 类别 | 证据与实际结论 |
| --- | --- |
| 视觉 | [#52 三档原生截图与布局验证](../issue-52/README.md)，本票追加上述实际安装截图及初始窗口定位修复；单屏通过，真实混合 DPI 切屏未测 |
| 流式 | [#49](../issue-49/README.md)、[#50](../issue-50/README.md)、[#51](../issue-51/README.md)及本票完整回归覆盖首字等待、SSE/UTF-8、结束、取消与迟到事件；使用回环服务，非真实服务商 |
| 记录与上下文 | #49/#50 的隔离、删除不复活、40 条/24,000 字符、原子写盘、损坏/版本保护；本票冻结二进程恢复与默认目录空会话证据通过 |
| 重试 | #49–#51 及本票完整回归覆盖替换未完成回复、问题不重复、无自动重发；真实计费未测 |
| 人设 | 作者原文/补充规则/新旧快照自动验证，22 个冻结模块与源码逐个一致；不等于语气通过 |
| 设置凭据 | #51 行为回归，本票真实 Credential Manager 跨进程读写/删除及内存降级、偏好升级、设置窗口操作通过；企业策略故障未实测 |
| 接口异常 | #49/#51 及本票回环测试覆盖固定模型/关闭思考、鉴权/余额/限流/繁忙/传输分类与主动测试；真实余额及服务体验待作者 |
| 既有桌宠 | 完整回归覆盖三模式、阶段推进/回弹、缩放贴边、气泡和桥接维护；本机正常启动通过；真实多屏与完整宿主矩阵沿用 #42 边界 |
| 作者实测 | **待作者**：按[三组试聊步骤](../../chat-acceptance.md)，自备 Key 亲自评价；代理未发送计费请求，未代作通过结论 |
| 打包 | Setup 实际升级/启动、186 个安装文件摘要、源码模块一致、MIT 全文、TLS 模块/CA、独立源码重建通过；干净无 Python Windows 未测 |

[交付审计](delivery-audit.json)与[脚本](audit_delivery.py)核对哈希清单、186 个安装运行文件、源码中的全部 22 个冻结模块、dsh-pet MIT 全文与 SSL 模块。路径/Key 模式扫描未命中运行记录、开发凭据或参考程序资料；模式扫描不能证明不存在所有可能的秘密。源码归档采用显式目录白名单，不收集个人配置、参考安装目录、.scratch、.venv 或 Git 数据。

## 自动化、重建与审查

用户确认测试边界为 tools/build_release.py 的构建命令和产物校验。版本不一致的新回归先失败（DID NOT RAISE），补上版本核对后通过；原有“关于”版本断言同步到 0.4.0。初始完整回归 367 passed；安装发现窗口定位问题后，最终源码重新执行完整回归，结果为 **367 passed，300.60 秒**，见 [pytest.txt](pytest.txt)/[JUnit](pytest.xml)。严格类型检查见 [mypy.txt](mypy.txt)，24 个文件通过。

从候选源码 ZIP 解压到新的独立目录，使用锁定构建环境实际重跑 PyInstaller 和 Inno Setup，生成第二套 Setup 成功。重建包仅用于可重建性验证，不替换所验候选，不承诺二进制按位一致。交付 ZIP 后续仅补入本票验证资料；运行代码、tests、tools、packaging 和依赖文件与成功重建输入逐字节相同，由 final-source-consistency.json 记录。无需参考程序、原视频或仓库历史。

[双轴审查](review.md)：Standards 0 项发现；Spec 0 项发现。两路已补审窗口位置修复。完整原生视觉范围沿用 #52，本票不是重复执行全部硬件现场矩阵。

## 作者下一步及收尾条件

本机已安装最终候选，右键“桌宠设置 → AI 对话”配置自己的 Key，再新建聊天依次输入问候、限时复习求助、接着追问。主动测试及发送/重试可能计费，不要分享 Key。反馈 Setup 哈希、脱敏输入与实际回复，以及明确通过或差异。

作者未给明确结论前保持 #53 开放、ready-for-human。通过后转 ready-for-agent，补记录脱敏结论并核对所验 Setup 哈希，再交付收口；不重新编译同名候选。若不通过，记录差异、修复并重新验收。当前不能声明正式交付完成。
