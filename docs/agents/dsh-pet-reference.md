# dsh-pet 源码参考

用户要求后续改动参考 dsh-pet；接入、状态更新和维护优先对照其源码。先找到对应实现，再说明本项目采用的机制及必要差异。既有需求与状态语义仍以本项目已确认的决策为准。

## 本地快照

- 目录：`references/dsh-pet-indesktop/`，相对本项目根目录。
- 来源：<https://github.com/MerZlin/dsh-pet-indesktop.git>。
- 固定提交：`34d810b1eadd98d00e7cb9b3b51428a45b5bf03e`。
- 保存日期：2026-10-25（Asia/Shanghai）。
- 形式：独立 Git 仓库、浅层历史、detached HEAD；源码、文档、测试和许可证已检出。`assets/`、`resources/` 的媒体素材暂不检出，Git 按需获取。

这是本地阅读副本，由根目录 `.gitignore` 排除，不随宿傩桌宠打包。实现写入本项目，参考副本保持干净。上游新提交不自动覆盖该基线；需要比较新版本时，记录新旧提交和相关差异。

## 按问题定位

| 问题 | 参考路径（相对快照目录） |
| --- | --- |
| 项目功能、安装与发布说明 | `README.md`、`docs/` |
| DSH 插件及状态写入 | `integrations/dsh-pet-bridge/index.js`、`package.json`、`cordis.patch.yml` |
| 状态文件读取、插件安装/刷新/卸载 | `pet/agent_link/__init__.py` |
| 状态归并、等待与结束处理 | `pet/agent_link/dsh_state.py` |
| 桌宠自身更新 | `pet/updater.py`、`pet/update_settings.py`、`update.json` |
| 安装器与卸载清理 | `packaging/dsh-pet.iss`、`pet/uninstall_cleanup.py` |
| 桥接依赖修复工具 | `scripts/fix_bridge_bundle.py` |
| 桌面显示、动作和交互 | `pet/window.py`、`pet/overlay_shell.py`、`pet/overlay_window.py`、`pet/pet_sprite.py`、`pet/sprite_behavior.py`、`pet/physics.py` |
| 对应验证场景 | `tests/`，按模块名和行为检索 |

阅读对应函数和调用方，区分源码事实、设计推论及实机验证。当前快照与 `D:/dsh-pet` 的已装发行物未证实逐字同版；有源码的问题直接读源码，只有发行版差异等必须依赖打包物证据的问题才转向发行物调查。

用户已确认 Q2/Q3 采用参考实现；修改传递或维护逻辑前，阅读[已确认的接入方案](../specs/task-status-connection.md)。与旧候选的对照历史见[源码参考讨论](https://github.com/xyd-0811/skip-pet/issues/35#issuecomment-6398860040)。本项目的真实等待、首次/重连状态、断线与气泡规则分别以[状态决策](https://github.com/xyd-0811/skip-pet/issues/33#issuecomment-6398138655)和[气泡决策](https://github.com/xyd-0811/skip-pet/issues/36#issuecomment-6398491400)为准。

## 校验与恢复

在本项目根目录运行：

```powershell
git -C references/dsh-pet-indesktop rev-parse HEAD
git -C references/dsh-pet-indesktop status --short
```

前者应为上面的固定提交，后者应为空。引用代码时使用该提交的上游永久链接或本地路径及行号。

在新工作区没有本地副本时，使用以下命令重建；先确认目标目录不存在：

```powershell
git init references/dsh-pet-indesktop
git -C references/dsh-pet-indesktop remote add origin https://github.com/MerZlin/dsh-pet-indesktop.git
git -C references/dsh-pet-indesktop fetch --depth=1 --filter=blob:none origin 34d810b1eadd98d00e7cb9b3b51428a45b5bf03e
git -C references/dsh-pet-indesktop sparse-checkout set --no-cone '/*' '!/assets/' '!/resources/'
git -C references/dsh-pet-indesktop checkout --detach 34d810b1eadd98d00e7cb9b3b51428a45b5bf03e
```

需要媒体素材时可在该参考仓库中执行 `git sparse-checkout disable` 获取完整工作树。保留 `LICENSE` 与 `THIRD_PARTY_NOTICES.md`；实际复用代码时按许可证维护署名。
