# README 介绍视频链接设计

## 目标

在 README 顶部简介区域增加项目介绍视频入口，方便用户在阅读功能和安装
说明前直接观看演示。

## 文案与位置

在项目用途说明后、免责声明前加入：

```markdown
[介绍视频（哔哩哔哩）](https://www.bilibili.com/video/BV11zzfBMEWu)
```

不新增章节标题、缩略图、徽章或额外说明，保持 README 顶部简洁。

## 验证

- README 只出现一次视频 BV 号 `BV11zzfBMEWu`。
- 链接文本为“介绍视频（哔哩哔哩）”。
- 链接位于项目用途说明与免责声明之间。
- 不改变 README 的其他内容。
- 修改后创建本地 commit，并通过 `output/github-export/` 脱敏导出仓库
  fast-forward push 远程 `main`。
- 任务完成后将 `docs/superpowers/` 中的已完成规格和计划全部移入
  `~archived/superpowers-plans/`，不得 push。
