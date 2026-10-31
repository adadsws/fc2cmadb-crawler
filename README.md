# FC2 PPV Data Crawler

[中文](README.md) | [English](README_EN.md)

抓取 `fc2cmadb.com` 的演员作品信息，按作品创建文件夹。另附四个可单独使用的工具。

[介绍视频（哔哩哔哩）](https://www.bilibili.com/video/BV11zzfBMEWu)

请不要滥用本脚本。如本项目侵犯版权，请联系删除。

## 功能

- 抓取指定演员的所有影片，支持分页。
- 按 `fc2-ppv-{ID} {制作商}-{影片名}` 创建文件夹。
- 演员快捷方式保持原有命名格式，包含演员 ID 和第一页最新番号，例如 `id_10436 - latest_1035965.url`。
- 文件夹名过长时自动截断并以 `+++` 标记。
- 抓取结束后校验影片数量，数量一致才提示成功。
- 演员目录只创建一个演员页 `.url` 快捷方式；作品目录不创建网页快捷方式。

## 1. 准备环境

在 Windows 上安装 [Python 3](https://www.python.org/downloads/windows/) 和 [Google Chrome](https://www.google.com/chrome/)。安装 Python 后重新打开命令提示符或 PowerShell，运行以下命令确认 Python 与 pip 可用：

```powershell
python --version
python -m pip --version
```

若 `python` 无法识别，请按 [Python 的 Windows 安装说明](https://docs.python.org/3/using/windows.html) 检查安装与命令配置。

## 2. 安装爬虫

已安装 Git 时，在终端运行：

```bash
git clone https://github.com/adadsws/fc2cmadb-crawler.git
cd fc2cmadb-crawler
python -m pip install -r requirements.txt
```

没有 Git 时，可从 [项目页面](https://github.com/adadsws/fc2cmadb-crawler) 下载 ZIP 并解压；在解压后的项目目录运行 `python -m pip install -r requirements.txt`。

## 3. 运行爬虫

运行 `python -m fc2cmadb_crawler.main`，或双击 `run_fc2cmadb_crawler.bat`。首次运行会打开专用 Chrome；请在该窗口登录 `fc2cmadb.com`，再按终端提示继续。后续运行会尽量复用登录状态。

登录状态保存在 `%LOCALAPPDATA%\fc2cmadb-crawler\chrome-profile`。关闭命令行不会关闭该 Chrome；需要结束浏览器会话时，请手动关闭窗口。

登录准备完成后选择输入方式：

- `1`：演员 ID 模式，输入纯数字演员 ID。
- `2`：FC2 番号模式，只输入数字，不带 `FC2-PPV-` 前缀。
- `q`：从模式菜单或编号输入处退出。

一次任务完成后继续停留在当前模式，可直接输入下一个编号；输入 `b` 返回模式菜单，输入 `q` 退出。提示中的编号只是示例，回车不会自动抓取。

生成的演员与作品目录位于项目 `~outputs/`。FC2 详情页无法确定唯一演员时，程序会提示重新输入。遇到站点安全验证，请在打开的 Chrome 中完成验证。

## 工具

以下工具均可单独使用；其中工具 4 用于更新本项目的作品文件夹名称。

| 编号 | 工具 | 用途 | 入口 | 环境配置 |
|---|---|---|---|---|
| 1 | [复制非视频文件](tools/docs/copy_nonvids/README.md) | 保留目录结构复制非视频文件。 | `python -m tools.copy_nonvids` 或 `tools/run_copy_nonvids.bat` | Python 3 |
| 2 | [重命名视频](tools/docs/rename_vids/README.md) | 按媒体信息重命名视频及目录。 | `tools/rename_videos_by_media_info.bat` | Windows PowerShell、FFprobe |
| 3 | [修复快捷方式域名](tools/docs/update_shortcut_domains/README.md) | 更新 `.url` 中的 FC2 域名。 | `python -m tools.update_shortcut_domains` 或 `tools/run_update_shortcut_domains.bat` | Python 3 |
| 4 | [更新 FC2 文件夹名称](tools/docs/update_fc2_folder_names/README.md) | 按站点资料更新作品文件夹名称。 | `python -m tools.update_fc2_folder_names` 或 `tools/run_update_fc2_folder_names.bat` | Python 3、`requests`、`beautifulsoup4` |
