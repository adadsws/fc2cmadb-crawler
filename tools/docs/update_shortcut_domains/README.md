# 修复快捷方式域名

[中文](README.md) | [English](README_EN.md)

批量更新文件夹内 `.url` 网页快捷方式中的 FC2 域名。

## 功能

- 递归查找 `.url` 文件，只处理域名包含 `fc2` 的链接。
- 默认改为 `fc2cmadb.com`，也可输入其他目标域名；链接的路径和参数保留。
- 修改前预览；可按最近批次撤销多次修改。

## 1. 准备环境

安装 Python 3，在终端运行 `python --version` 确认命令可用。此工具不需要安装爬虫依赖。

## 2. 安装工具

此工具随 [主项目](../../../README.md) 提供。下载或克隆项目后，在项目根目录打开终端；无需额外安装 Python 包。

## 3. 使用工具

运行 `python -m tools.update_shortcut_domains`，或双击 `tools/run_update_shortcut_domains.bat`。选择目标域名，输入存放快捷方式的文件夹，查看预览后确认。也可直接运行：

```powershell
python -m tools.update_shortcut_domains "文件夹" "目标域名"
```

主菜单选 `3` 可按最近处理顺序查看可撤销的文件夹；输入编号选一批，预览该批全部文件并确认，完成后可继续选择。处理完成后可继续输入下一个文件夹；数字菜单回车默认选择 `1`，`b` 返回主菜单，`q` 退出。
