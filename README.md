# FC2 PPV Data Crawler

用于抓取 `fc2cmadb.com` 演员影片信息，并按作品自动创建文件夹和 `.url` 快捷方式。

[介绍视频（哔哩哔哩）](https://www.bilibili.com/video/BV11zzfBMEWu)

请不要滥用本脚本。如本项目侵犯版权，请联系删除。

## 功能

- 抓取指定演员的所有影片，支持分页。
- 按 `fc2-ppv-{ID} {制作商}-{影片名}` 创建文件夹。
- 文件夹名过长时自动截断并以 `+++` 标记。
- 抓取结束后校验影片数量，数量一致才提示成功。
- 附带非媒体文件复制工具和快捷方式域名修复工具。

## 安装

需要 Python 3.x 和 Chrome。

```bash
git clone https://github.com/adadsws/fc2ppvdb-crawler.git
cd fc2ppvdb-crawler
pip install -r requirements.txt
```

## 登录

首次启动时，程序会打开独立的 Chrome 窗口。请在该窗口中手动登录 `fc2cmadb.com`，完成后回到终端按 Enter。登录状态会保存在用户本机的独立 Chrome profile 中，后续启动自动复用；只有站点确认会话已失效时才需要再次登录。

profile 默认位于 Windows 的 `%LOCALAPPDATA%\fc2cmadb-crawler\chrome-profile`，不在项目目录内，也不会提交到 Git。请勿删除该目录，除非希望清除登录状态。

## 运行爬虫

默认演员 ID 在 `fc2cmadb_crawler/config.py`：

```python
DEFAULT_ACTRESS_ID = 6061
```

启动：

```bash
python -m fc2cmadb_crawler.main
```

Windows 可双击：

```text
run_fc2cmadb_crawler.bat
```

启动后直接输入演员 ID；直接回车使用配置文件默认 ID。完成一个演员后会回到输入提示，可继续输入下一个演员 ID，输入 `q` 退出。

## 工具

复制除视频、图片外的文件，保留目录结构：

```bash
python -m tools.copy_non_media_files
python -m tools.copy_non_media_files "D:\source_folder" "D:\target_folder"
```

Windows 可双击 `tools/run_copy_non_media_files.bat`。

批量把 `.url` 中域名包含 `fc2` 的链接改为 `fc2cmadb.com`：

```bash
python -m tools.update_shortcut_domains
python -m tools.update_shortcut_domains "D:\shortcut_folder"
```

Windows 可双击 `tools/run_update_shortcut_domains.bat`。

## 目录结构

```text
fc2ppvdb-crawler/
├── AGENTS.md
├── AGENT_CONTEXT.md
├── fc2cmadb_crawler/
│   ├── config.py
│   ├── crawler.py
│   ├── main.py
│   └── __init__.py
├── run_fc2cmadb_crawler.bat
├── tools/
│   ├── copy_non_media_files.py
│   ├── update_shortcut_domains.py
│   ├── run_copy_non_media_files.bat
│   └── run_update_shortcut_domains.bat
├── requirements.txt
├── CHANGELOG.md
├── ~outputs/                  # 生成输出，不提交
├── recommend_20260629/
└── tests/                     # 离线自动化测试
```

生成的演员目录默认写入 `~outputs/`。技术架构、开发流程和已知问题见 [AGENT_CONTEXT.md](AGENT_CONTEXT.md)。
