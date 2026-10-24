# #17 Windows 安装版交付与验收

日期：2026-10-24（Asia/Shanghai）。规格：[交付票 #17](https://github.com/xyd-0811/skip-pet/issues/17)、父规格 #12；审查基点由用户确认：`a3f03c45047560164f8f77af9deedc1cc31581aa`。原工作区规划、词表和其他历史记录保留，未纳入本票提交。

## 交付

- `dist/release/Setup.exe`：PyInstaller 6.22.3 目录包 + Inno Setup 6.7.3，Windows 10 1809+/11 x64，当前用户安装，不提权、不配置宿主、不增加开机启动。
- `dist/app/SukunaPet/SukunaPet.exe`：完整目录包的主入口；不可离开 `_internal` 单独移动。
- `dist/release/sukuna-pet-0.1.0-source.zip`：完整运行源码、包内素材与 provenance、测试及夹具、工具、构建配置、锁定依赖、使用/构建/验证说明。没有原视频、参考程序或 `.scratch`。
- `build-report.json` 记录工具链、Python/Windows、包版本、逐个运行文件 SHA-256；`SHA256SUMS.txt` 对安装器、源码 ZIP 与报告校验。工作树源码快照不冒充纯提交导出。

构建命令和上游工具入口见 [build.md](../../build.md)，用户操作见 [user-guide.md](../../user-guide.md)。项目生产交互源码未改动，沿用 #13–#16；本票没有宿主适配器、桥接或任务联动。

## 自动化与构建环境

在本机新建 `.scratch/issue17-build-env`，从锁定依赖安装并构建，而非沿用原 `.venv`。Windows 11 家庭版中文版 x64，10.0.26200，CPython 3.14.4、PySide6/Qt 6.12.0。模式单文件 22 项、桌面单文件 11 项、源码及构建工具共 7 文件 mypy 检查通过，pip check 通过。完整套件和最终双轴审查记录见 [review.md](review.md)。本次无应用行为变更，不新增内部测试接口；使用父规格与 #16 已确认的测试边界。

构建最初发现并修复了仅冻结包出现的 QtCore DLL 导入错误：原 PATH 中 Poppler 的 `icuuc.dll` 被 PyInstaller 误收集，其导出符号与 Windows ICU 不同。现限制构建进程 PATH，重新干净构建；修复后安装进程实际加载系统 ICU。没有修改 Poppler、参考程序、原视频或系统配置。

Inno 下载文件签名为有效 Pyrsys B.V.，SHA-256 为 `9c73c3bae7ed48d44112a0f48e66742c00090bdb5bef71d9d3c056c66e97b732`；编译器由安装脚本的预处理版本检查固定到 6.7.3。上游开放许可文本与 CPython/发行包许可随安装提供。

独立源码检查：将源码 ZIP 解压到 `.scratch/issue17-source-checkout/sukuna-pet-source`，没有 `.git`、原视频或参考程序。首次在该深目录内建 `.venv` 时，pip 因 Windows 长路径限制失败，未记为通过；随后使用较短的 `.scratch/i17e` 新虚拟环境成功安装相同锁定依赖、安装该解压源码，pip check 通过。独立目录构建结果在完成后追加；新 venv 与新源码目录均在同一台已有 Python 的主机上，不能充当干净 Windows。

## 实际安装后的 Windows 程序

安装与卸载调用均是交付 Setup.exe / 其生成的 unins000.exe，不是源码模拟。安装使用 Inno 的 `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /TASKS=desktopicon`；没有跳过任何必需运行文件。安装日志保留在工作区 `.scratch/issue17-verification`。

- 安装返回 0，默认路径 `%LOCALAPPDATA%\Programs\SukunaPet`。
- HKCU 正常卸载条目：`{04B576E4-248B-4D31-978B-86783245D204}_is1`，DisplayVersion 0.1.0，UninstallString 指向安装目录的 `unins000.exe`。
- 开始菜单包含“宿傩桌宠”和“卸载宿傩桌宠”，并实际创建桌面快捷方式。
- 修复后从开始菜单快捷方式启动成功；真实系统鼠标右键显示两种模式与退出，首次勾选点击跳动。选择持续跳动，设置文件仅含 `{"mode":"always"}`，点击后持续模式仍勾选。
- 从真实右键菜单退出，进程消失；从桌面快捷方式重启，菜单恢复持续跳动。切回点击跳动成功。截图是安装目录程序的真实窗口，非源码窗口或历史原型。
- [installed-modules.json](installed-modules.json) 记录运行中的 Python、Qt、shiboken 均来自安装目录；ICU 来自 Windows System32。程序未加载项目 `.venv` 或参考程序运行库。
- 第一版试装已调用正常 unins000.exe 卸载，返回 0；最终包的卸载清理结果在完成后追加。

![安装版启动](installed-startup.jpg)
![首次点击模式菜单](installed-click-menu.jpg)
![持续模式菜单](installed-always-menu.jpg)
![桌面快捷方式重启恢复持续模式](restored-always-menu.jpg)

静态截图和菜单操作不能证明 3× 插值、240ms 眨眼或所有逐帧阶段收尾；精确交互契约由原型轨迹驱动的应用级测试覆盖。真实桌面自动化拖动两次因目标位置被判断为 ChatGPT 窗口而拒绝，未作为执行成功的拖动证据。用户已选择手动复核四边拖动、点击与退出，结果待其反馈；期间代理不发送桌面输入。

## 验收矩阵

| 验证层/条件 | 结论 |
| --- | --- |
| 自动化应用行为与 Qt 几何 | 沿用已确认边界；完整套件见 review.md |
| 新 venv 固定依赖、PyInstaller 目录包与安装器编译 | 通过 |
| 本机实际安装、卸载条目、开始菜单及桌面入口 | 通过 |
| 本机实际安装版两种模式选择、持续模式保存/重启、菜单退出 | 通过 |
| 本机安装版四边拖动、释放不推进与拖后点击 | 等待用户手动结果；自动化拖动被拒绝 |
| 本机安装版跨应用透明穿透与置顶 | 待复验；不以 #15 的源码进程证据替代 |
| 本机安装版全部阶段逐帧原生观感 | 待完整复验；自动行为测试与静态截图不替代 |
| 真实多屏/混合 DPI/其他任务栏布局 | 未验证；本机仅单屏 100%，沿用 #16 设备限制 |
| 独立源码目录、新 venv 的运行与重建 | 依赖安装通过；构建结果待追加 |
| 无 Python/无参考程序/无原视频的干净 Windows 安装到卸载 | **未验证**：本机无 Sandbox/VM；用户已明确先交付并记录待验收 |

干净环境与硬件补验步骤见 [build.md](../../build.md)。未完成项目保持未验证，#17 不因安装器已生成就宣称全部验收完成。
