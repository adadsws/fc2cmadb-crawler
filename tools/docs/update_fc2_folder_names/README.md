# 更新 FC2 文件夹名称

[中文](README.md) | [English](README_EN.md)

按 `fc2cmadb.com` 的最新资料更新现有 FC2 作品文件夹名称。

## 功能

- 递归查找名称含 `fc2-ppv-<数字>` 的文件夹，获取最新制作人与标题。
- 保留原名称中制作人前的所有文字，按主程序规则整理其余部分；文件夹内的文件不变。
- 修改前预览；遇到目标重名或无法确认名称边界时跳过；可撤销最近的多批修改。

## 1. 准备环境

安装 Python 3，并确认可访问 `fc2cmadb.com`。在终端运行 `python --version` 检查环境。

## 2. 安装工具

此工具随 [主项目](../../../README.md) 提供。下载或克隆项目后，在项目根目录安装此工具需要的包：

```powershell
python -m pip install requests beautifulsoup4
```

## 3. 使用工具

运行 `python -m tools.update_fc2_folder_names`，或双击 `tools/run_update_fc2_folder_names.bat`。输入要扫描的根目录，查看预览后确认。可先只预览：

```powershell
python -m tools.update_fc2_folder_names "根目录" --dry-run
```

预览会列出所有待改目录的原名和目标名。主菜单选 `2` 可按最近处理顺序查看可撤销的文件夹；输入编号选一批，确认该批还原预览后可继续选择。完成后可继续输入下一个根目录；数字菜单回车默认选择 `1`，`b` 返回主菜单，`q` 退出。
