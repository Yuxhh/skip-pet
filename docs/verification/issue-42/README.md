# 正式安装版与实机验收：前置检查

2026-10-26（Asia/Shanghai）。对应 [正式安装版与实机验收 #42](https://github.com/xyd-0811/skip-pet/issues/42)。这是尚未完成的验收准备记录。

## 实际硬件

通过既有 `tools/verify_screens_native.py --output .scratch/issue42-preflight/screens` 只读枚举，Qt 平台为真实 `windows`。环境详情见 [environment.json](environment.json)。当前仅连接 G24H1 一台屏幕，1920×1080、工作区 1920×1032、DPR 1.0、逻辑 DPI 96。

当前环境不能提供真实多屏、负坐标屏、混合 DPI 和屏幕连接变化的完整验收证据。这些场景保持未通过；单屏枚举不接受任何交互场景，也不等于气泡或正式安装版验证。

## 构建环境

日常 `.venv` 缺少构建依赖 altgraph，随后复用此前发行的独立锁定环境 `.scratch/i28e`，未改动日常环境。该环境运行当前 `tools.build_release.check_inputs()` 成功，CPython 3.14.4、全部锁定依赖和冻结素材哈希均通过；`pip check` 无损坏依赖。Inno Setup 6.7.3 的 ISCC.exe 签名 Valid，发布者 Pyrsys B.V.。

依赖文件 SHA-256：

| 文件 | SHA-256 |
| --- | --- |
| requirements.txt | e3d0fc3556cbae7c96df3a22627a9f8f26c0f93fe3048ed8c720880cc344d03e |
| requirements-dev.txt | 931821290bf9d86046e441dbbc1ac1eb1f3f4b064d593fad0cd7665165cf3ea7 |
| requirements-build.txt | 752f27cdf6ba316735c31787f37a183f53525ff39d2e17f1c48a66179b1f7353 |

## 未完成

完整等待、执行归属及宿主现态恢复由 #41 承接，目前仍缺接口契约。此次没有生成或发布新的 Setup，也没有覆盖旧版交付文件。构建工具可用不代表新发行通过；完整宿主场景、安装升级卸载、独立运行及硬件验收均须分别留证。
