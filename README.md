# FC2 PPV Data Crawler

[中文](README.md) | [English](README_EN.md)

用于抓取 `fc2cmadb.com` 演员影片信息，并按作品自动创建文件夹。每个演员目录只创建一个演员页 `.url` 快捷方式，作品目录不创建网页快捷方式。

[介绍视频（哔哩哔哩）](https://www.bilibili.com/video/BV11zzfBMEWu)

请不要滥用本脚本。如本项目侵犯版权，请联系删除。

## 功能

- 抓取指定演员的所有影片，支持分页。
- 按 `fc2-ppv-{ID} {制作商}-{影片名}` 创建文件夹。
- 演员快捷方式保持原有命名格式，包含演员 ID 和第一页最新番号，例如 `id_10436 - latest_1035965.url`。
- 文件夹名过长时自动截断并以 `+++` 标记。
- 抓取结束后校验影片数量，数量一致才提示成功。
- 附带非媒体文件复制工具和快捷方式域名修复工具。

## 安装

需要 Python 3.x 和 Chrome。

```bash
git clone https://github.com/adadsws/fc2cmadb-crawler.git
cd fc2cmadb-crawler
pip install -r requirements.txt
```

## 登录

首次启动时，程序会先启动普通、可见的 Chrome，再通过本机调试端口附加采集程序。请在该窗口中手动登录 `fc2cmadb.com`，完成后回到终端按 Enter。登录状态会保存在用户本机的独立 Chrome profile 中，后续启动优先复用仍在运行的 Chrome、当前页面和登录状态；只有站点确认会话已失效时才需要再次登录。

profile 默认位于 Windows 的 `%LOCALAPPDATA%\fc2cmadb-crawler\chrome-profile`，不在项目目录内，也不会提交到 Git。请勿删除该目录，除非希望清除登录状态。

## 运行爬虫

默认演员 ID 在 `fc2cmadb_crawler/config.py`：

```python
DEFAULT_ACTRESS_ID = 10436
```

启动：

```bash
python -m fc2cmadb_crawler.main
```

Windows 可双击：

```text
run_fc2cmadb_crawler.bat
```

程序会先检查当前持久页面；已登录时不会重复访问首页，无法确认会话时才访问一次准备页。登录准备完成后才显示业务输入菜单：

- 直接回车：使用配置文件默认演员 ID。
- 直接输入多位纯数字：兼容旧版，按演员 ID 处理。
- 输入 `1`：进入演员 ID 模式；需要处理演员 ID `2` 时使用此入口。
- 输入 `2`：进入 FC2 番号模式，再输入不带 `FC2-PPV-` 前缀的纯数字番号。程序会从作品详情页解析唯一演员 ID，然后复用原演员抓取流程。
- 输入 `q`：退出。

FC2 详情页没有演员或包含多个不同演员时，程序会拒绝猜测并返回输入菜单。

演员第一页、分页和 FC2 详情都通过同一个导航入口访问：相同 URL 不重复跳转，连续导航会节流，加载超时只停止加载而不刷新。遇到安全验证时先等待自动完成，超时后才提示人工处理；人工完成后不会刷新验证页。退出 CLI 只断开采集程序，项目 Chrome 默认保持打开，以减少调试和日常运行中的重复登录与验证；如需结束会话，请手动关闭该 Chrome。

## 工具

复制除视频、图片外的文件，保留目录结构：

```bash
python -m tools.copy_non_media_files
python -m tools.copy_non_media_files "D:\source_folder" "D:\target_folder"
```

Windows 可双击 `tools/run_copy_non_media_files.bat`。
未指定目标路径时，默认复制到项目的 `~outputs/<源目录名>_non_media_files/`；显式指定目标路径时使用指定位置。

批量把 `.url` 中域名包含 `fc2` 的链接改为 `fc2cmadb.com`：

```bash
python -m tools.update_shortcut_domains
python -m tools.update_shortcut_domains "D:\shortcut_folder"
```

Windows 可双击 `tools/run_update_shortcut_domains.bat`。

## 目录结构

```text
fc2cmadb-crawler/
├── AGENTS.md
├── AGENT_CONTEXT.md
├── README.md
├── README_EN.md
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
└── tests/                     # 离线自动化测试
```

生成的演员目录默认写入 `~outputs/`。技术架构、开发流程和已知问题见 [AGENT_CONTEXT.md](AGENT_CONTEXT.md)。
