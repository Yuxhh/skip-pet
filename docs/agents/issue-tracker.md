# Issue tracker: GitHub

任务和规格存放在 xyd-0811/skip-pet 的 GitHub Issues，使用 gh CLI 操作。
在仓库目录中运行命令，由 git remote 确定目标仓库。

## 常用操作

- 发布任务：gh issue create --title "..." --body-file <文件路径>
- 读取任务：gh issue view <编号> --comments，并检查其标签。
- 查询任务：gh issue list，按状态和标签筛选。
- 追加讨论：gh issue comment <编号> --body-file <文件路径>
- 更新标签：gh issue edit <编号> --add-label / --remove-label
- 关闭任务：gh issue close <编号>

多行正文先保存到临时文件，再通过 --body-file 提交。
分诊标签见 triage-labels.md。

## Pull requests as a triage surface

PRs as a request surface: no.

## Wayfinding operations

- Map：使用一个带 wayfinder:map 标签的 issue 保存规划地图。
- Child：每个子任务单独建 issue，使用 wayfinder:<type> 标签；
  优先关联为 sub-issue，不支持时在地图中维护任务列表，
  并在子任务正文顶部注明 Part of #<map>。
- Blocking：优先使用 GitHub 原生 issue dependencies；
  不支持时在正文顶部记录 Blocked by: #<编号>。
- Frontier：按地图顺序选择尚未关闭、无人认领且阻塞项均已关闭的子任务。
- Claim：开始处理前，将任务分配给当前开发者。
- Resolve：评论记录结论、关闭任务，再向地图追加结论摘要和链接。

## 现有本地规划

已有 .scratch/sukuna-pet/ 文件保留为当前规划记录。
引用这些文件的任务继续读取对应文件；后续新任务默认发布到 GitHub。
迁移已有任务时，维护本地路径与 GitHub 编号的对应关系。
