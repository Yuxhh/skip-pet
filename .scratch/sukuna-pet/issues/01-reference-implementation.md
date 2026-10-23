# 原桌宠有哪些已证实的实现线索可以参考

Id: 01
Parent: ../map.md
Labels: wayfinder:research
Type: research
Mode: AFK
Status: resolved
Assignee: inspect_reference
Blocked by: none

## Question

只读核实 `D:\dsh-pet` 的技术栈、点击动画资源组织及源码可读范围。哪些结论有文件证据，哪些点击压缩或弹跳参数仍不能确认？独立项目应参考到什么程度？

## Context

仅分析随包文件，不运行桌宠或安装包，不写入参考目录。研究资料存于当前项目。明确区分事实、结构推断和未验证行为。

## Comments

- 2026-10-23：初步文件调查已完成；登记认领后复核证据并记录最终结论。上下文指针为本票及后续 Answer。

## Answer

### 已证实的文件事实

- `D:/dsh-pet/app/dsh-pet-standalone-webm-chat.exe` 与安装包是发行物。`D:/dsh-pet/app/_internal/python311.dll`、`PySide6/`、`cv2/`、`imageio_ffmpeg/` 随包存在，支持将参考实现归为 Python 3.11 / Qt 技术栈；未执行二进制确认其运行时调用。目录结构符合 PyInstaller onedir 的常见布局，但此项属于结构推断。
- 点击动画原视频位于 [点击回应-开心跃动.webm](D:/dsh-pet/app/_internal/assets/characters/shenshen/videos/click/点击回应-开心跃动.webm)，复核大小为 538,110 bytes。
- 对应 [meta.json](D:/dsh-pet/app/_internal/assets/characters/shenshen/frameseq/click/点击回应-开心跃动.g86dcb0c3dd7b/meta.json) 明确记录 `fps: 24.0`、`frames: 241`、`source: 点击回应-开心跃动.webm`、`encoder: libwebp lossy q70 (bgra straight, unblend-white-v5)`，以及源文件声明哈希 `86dcb0c3dd7b651de9c107e927d57a5c4224599101706dbdcc782fa48bcd0ad7`。哈希是元数据声明，本次未另行计算匹配。
- 同目录可见 `f_0001.webp` 至 `f_0241.webp`，已复核首尾文件存在；它展示了“视频素材及其预解码 WebP 帧序列”的资源组织方式。24 fps / 241 帧对应约 10.04 秒的素材长度，不能据此视作一次弹跳的时长。
- [manifest.json](D:/dsh-pet/app/_internal/assets/characters/shenshen/videos/manifest.json) 含 `body_box: [212,60,428,330]` 和 `head_box: [185,60,436,195]`。这些是随包配置值，实际命中测试是否使用、如何使用未确认。
- 递归查看 `D:/dsh-pet/app/_internal/pet/` 后，仅发现聊天 QSS、菜单模板及人设 JSON，未发现点击处理、窗口绘制或弹跳算法的可读 Python 源码。整个目录中的其他 Python 文件主要属于第三方依赖；此结论限定于本次提供的发行目录，不代表上游没有源码。
- 可用视频解码程序为 `D:/dsh-pet/app/_internal/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe`。本票仅核对路径，未执行它。
- [LICENSE](D:/dsh-pet/app/_internal/LICENSE) 提供项目 MIT 声明；[THIRD_PARTY_NOTICES.md](D:/dsh-pet/app/_internal/THIRD_PARTY_NOTICES.md) 明确第三方软件和资产各有许可，不能据项目许可证直接认定全部素材可复制。

### 未确认的机制

未找到可读的鼠标事件处理入口，未进行反编译或运行时观察。因此尚不能确定用户提及的点击收缩弹跳是窗口位移、绘制缩放、预制动画，还是它们的组合；也不能确认压缩比例、起跳高度、缓动曲线、点击与拖拽判定、连点重置及播放完成后的状态切换。文件名 `click` 与“开心跃动”只用于定位资源，不当作运行行为证据。

已读取 reverse-engineer-anything 技能；本会话无 REA MCP 工具且无现成 `rea` CLI。本次证据全部来自普通文件清单和文本读取，不含 REA Evidence 或运行时验证；未安装分析工具。

### 对独立项目的结论

独立项目可以参考“角色素材按状态分类、视频预解码为透明帧序列、集中记录帧率”的组织方法。无需依赖或修改原程序，更不应把其 241 帧点击素材当作宿傩的一次弹跳。本项目按用户提供的视频确定静止形象和单个跳跃周期：idle 静止，每次点击播放一个周期，连续点击立即重新起跳；具体周期边界与时序以视频研究票为准。原程序算法未确认不会阻塞这一实现路径；只有未来明确需要复用原算法时，才另行研究上游源码或打包代码。

### 研究记录

- 2026-10-23 23:01（Asia/Shanghai）：inspect_reference 完成只读复核并将本票标为 resolved。未执行桌宠或安装包，未写入 `D:/dsh-pet`，未创建或切换分支，未提交。
