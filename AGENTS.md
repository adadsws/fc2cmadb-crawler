# 项目代理规则

- 本项目需要 Plan 的任务，在 `docs/plans/` 为当前目标保留唯一 Plan；同一目标后续收到的规范、补充规范、需求及其补充、澄清、变更、样例、验收标准和验证记录，直接更新该 Plan，不另建同目标文档。完成后将该 Plan 移至 `docs/finished_plans/`；`docs/lessons/` 仅用于复盘。
- 爬虫和工具生成、复制的结果统一写入 `~outputs/`，不得提交该目录内容。
- 修改 Cookie 文件结构或查找顺序时，必须同步维护 `secrets/**/*.example` 与相应离线测试；任何输出都不得包含 Cookie 正文。
