# Windows 运行与构建

默认交付文件在 `dist/release/`：`Setup.exe`、`sukuna-pet-0.3.0-source.zip`、`build-report.json`、`SHA256SUMS.txt`。目录式程序在 `dist/app/SukunaPet/`。本次候选使用 `--output-root dist/issue-42`，避免覆盖既有 0.2.1 安装包。日常用户只需 Setup.exe；使用说明见 [user-guide.md](user-guide.md)。

## 固定工具链

- Windows 10 1809 及更新版本或 Windows 11 x64，x64 CPython **3.14.4**（本次实际版本）。源码声明支持 3.12+，其他版本的打包未验证。系统范围沿用 [Qt 6.12 官方支持条件](https://doc.qt.io/qt-6/windows.html)。
- `requirements-build.txt` 通过两个递归依赖文件固定完整运行、测试、构建依赖；包括 PyInstaller 6.22.3、hooks 2026.9、setuptools 84.2.1、pip 26.0.1。
- Inno Setup **6.7.3**。从[官方入口](https://jrsoftware.org/isdl.php)下载 [innosetup-6.7.3.exe](https://github.com/jrsoftware/issrc/releases/download/is-6_7_3/innosetup-6.7.3.exe)，检查 Authenticode 签名有效、发布者 Pyrsys B.V.。选择安装到项目 `.scratch/build-tools/InnoSetup`，或使用既有安装中的 ISCC.exe。

## 从独立目录重建

将源码 ZIP 解压到新的可写目录，不需要原仓库、Git 历史、参考程序或原视频。构建依赖从 Python 包索引安装，构建时需要网络或预先准备的 wheelhouse。下列命令在源码根目录的 PowerShell 执行：

Windows 未启用长路径支持时，源码和虚拟环境应使用较短路径（例如 `C:\src\sp`）；PySide6 的 QML 依赖中含很深的文件名，过长的 `.venv` 路径会导致 pip 安装失败。建议将虚拟环境放在较短的独立路径。本轮实际路径和结果见 #28 验证记录。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\pythonw.exe -m sukuna_pet
New-Item -ItemType Directory -Force .scratch/checks | Out-Null
.\.venv\Scripts\python.exe -m mypy src
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.scratch/checks/pytest
.\.venv\Scripts\python.exe tools/build_release.py --iscc 'C:\path\to\Inno Setup 6\ISCC.exe' --output-root dist/issue-42
```

安装项目时使用 `--no-build-isolation`，避免构建隔离临时解析未锁定的 setuptools。PyInstaller 从 `src` 收集代码，从包资源收集 PNG 与 provenance.json；程序、Python DLL、Qt DLL 和插件位于同一个目录包，不依赖目标机 Python。Qt WebEngine/PDF/QML 不进入运行包。包中保留动态 Qt DLL 与上游许可文本。

构建脚本在运行前核对 CPython 3.14.4、全部锁定包版本及三张冻结素材哈希，打包后再次核对包内素材及插件清单中每个文件与本次源码一致。插件版本、逐文件哈希、依赖文件哈希与素材来源写入报告。PyInstaller 明确读取本次源码目录的素材和桥插件，避免旧 editable 安装漏打新资源。使用说明及验收范围随安装提供。构建脚本为 PyInstaller 使用仅含当前解释器目录及 Windows System32 的 PATH，防止从其他开发工具误收集同名 DLL。Qt 使用目标 Windows 自带 ICU，不能把其他工具的 ICU 拷贝进 `_internal`。默认输出相对于源码根目录；显式相对 `--output-root` 相对于调用目录。

`build_release.py` 会覆盖选定输出根目录下的 `app/SukunaPet`、`build/pyinstaller` 和同名交付文件；请勿将用户资料放入构建目录。源码 ZIP 显式包含 src、tests、tools、packaging、docs、词表及依赖配置，不收集 `.scratch`、`.venv`、Git 数据、原视频、参考安装目录或主机配置。源码 ZIP 是当前文件快照；报告中的 Git SHA 仅为基点，不能据此断言 ZIP 与该提交完全相同。重新运行会更新 SHA-256 清单；不承诺二进制按位可重现。

## 安装与卸载验收

在独立、无 Python 的干净 Windows 10/11 x64 虚拟机或物理机，仅复制 Setup.exe：

1. 双击安装，检查当前用户安装路径；从完成页、开始菜单和可选桌面快捷方式分别启动。
2. 无设置首次启动为点击跳动，依次点击观察阶段停留、视线 2 停留、下一点击眨眼、连点接续。
3. 切换持续跳动，点击仍可互动；切回点击模式观察阶段收尾。保存持续模式后退出，重启确认恢复；再保存点击模式，重启复核。
4. 在其他应用上复核透明处穿透、可见处拖动、拖动不触发点击、置顶、工作区四边及右键退出；真实多屏/不同 DPI 可用时逐屏补验。
5. 退出，从“已安装的应用”或开始菜单卸载入口卸载，检查安装文件、开始菜单及桌面快捷方式被移除，记录保留的模式和大小偏好。
6. 保存 Windows 版本、屏幕/DPI、安装路径、开始菜单与卸载条目、进程路径、操作记录和截图；区分新 venv、独立源码目录、本机安装和干净 Windows，不能互相代替。

本次实测结论与限制见 [#28 验证记录](verification/issue-28/README.md)。
