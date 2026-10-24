# 宿傩桌宠

原生 Windows 透明半身角色，首次启动静止，点击一次推进一个视线阶段并停留。
当前实现对应 [#13](https://github.com/xyd-0811/skip-pet/issues/13)，使用已认可原型的重绘素材与固定 3× 眼动，身体不摆动。

## 从源码运行

在 Windows x64、Python 3.12 或更新版本中执行；本次实际验证环境是 Python 3.14.4。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\pythonw.exe -m sukuna_pet
```

单击角色依次进入视线 1、2、3、0，每次结束保持。视线 2 不自行眨眼；下一次单独点击进入视线 3 时眨眼，240ms 完成，闭合 120ms 时直接换位。连点覆盖前方目标，从当前位置衔接。右键选择“退出”。提供基本拖动，拖动后不推进阶段。

素材已随 Python 包提供，运行不需要 `.scratch`、参考程序、原型网页、原视频或联网。
这一步交付源码运行入口；持续模式与记忆、完整原生拖动/透明处输入穿透、多屏可见区域和 Setup.exe 分别在 #14–#17 中交付。

## 维护与验证

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m mypy src
.\.venv\Scripts\python.exe -m pytest tests/test_playback.py -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tools/visual_check.py --show
```

`PetApplication.click()`、`advance(elapsed_ms)` 与只读 `view` 是父规格已确认的应用级测试边界。
`view` 提供源图坐标下两眼中心、眼皮闭合程度及阶段/停留状态；Qt 仅将真实时间和输入接入此边界。绘制不决定播放时序。

行为基准来自原型提交 `9eef9e2418d536fe6a5b71235841ae98da64329c`。
测试夹具直接执行该提交中的原始 `StageRules`、`next`、`tick`、`paintSprite` 生成，覆盖普通周期、动作中改目标、闭眼/睁眼中点击、跨周期快速点击及再次眨眼。夹具以 1ms 虚拟绘制步长采样，眼中心比较容许 0.2 个源像素的采样差异；断言不重写轨迹公式。
如本地保留了该历史 Git 对象，可用 Node.js 重新生成夹具：`node tools/capture_prototype_traces.mjs`。日常运行及测试不需要 Node.js 或该 Git 对象。

素材来源及 SHA-256 见 `src/sukuna_pet/assets/provenance.json`；原生观察与背景检查见 [#13 验证记录](docs/verification/issue-13/README.md)。
