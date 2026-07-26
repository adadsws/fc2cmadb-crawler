# FC2 PPV Data Crawler

用于抓取 `fc2cmadb.com` 演员影片信息，并按作品自动创建文件夹和 `.url` 快捷方式。

请不要滥用本脚本。如本项目侵犯版权，请联系删除。

## 功能

- 抓取指定演员的所有影片，支持分页。
- 按 `fc2-ppv-{ID} {制作商}-{影片名}` 创建文件夹。
- 文件夹名过长时自动截断并以 `+++` 标记。
- 自动检测 Chrome 主版本。
- 抓取结束后校验影片数量，数量一致才提示成功。
- 附带非媒体文件复制工具和快捷方式域名修复工具。

## 安装

需要 Python 3.x 和 Chrome。

```bash
git clone https://github.com/adadsws/fc2ppvdb-crawler.git
cd fc2ppvdb-crawler
pip install -r requirements.txt
```

## Cookie

登录 `fc2cmadb.com` 后，用浏览器插件导出 Cookie：

https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc

保存为：

```text
secrets/fc2cmadb.com_cookies.txt
```

项目提供了 `secrets/fc2cmadb.com_cookies.txt.example`。可复制该文件并替换示例值，也可以使用浏览器插件导出后直接覆盖真实文件。脚本会跳过 `cf_clearance`，保留浏览器自己的会话验证。

真实 Cookie 会进入本地 Git 提交，因此包含该文件或其历史的源仓库不得直接 `push`。发布时只能使用独立脱敏导出仓库，并只携带 `.example`。

## 脱敏发布

源仓库保留本地私有历史，不与远程的脱敏历史合并，也不得直接
`push`。需要发布时：

1. 用 `git clone` 将远程 `main` 放到 `output/github-export/`。
2. 只复制允许发布的普通源码、测试、必要文档和脱敏示例；相同路径用
   本地版本覆盖。
3. 不复制 `~archived/`、`~ref/`、真实 `secrets/**` 或含隐私的原始
   `data/`；`data/` 只能使用示例值。
4. 不适合远程平台的大目录不复制实际内容，在原位置放置同名 `.md`，
   记录用途、主要结构、不发布原因、来源、版本和重建方法。
5. 检查待发布文件、导出仓库提交历史和隐私，运行测试及
   `pre-push` hook。
6. 导出仓库只保留 `main`。远程有更新时先同步，只允许
   fast-forward `push`，禁止 force push。
7. `push` 后确认源仓库、`output/github-export/` 导出仓库和远程都只有
   `main`。

## 运行爬虫

默认演员 ID 在 `fc2cmadb_crawler/config.py`：

```python
DEFAULT_ACTRESS_ID = 6061
```

启动：

```bash
python main.py
```

Windows 可双击：

```text
run_fc2cmadb_crawler.bat
```

启动后直接输入演员 ID；直接回车使用配置文件默认 ID。完成一个演员后会回到输入提示，可继续输入下一个演员 ID，输入 `q` 退出。

如需手动指定 Chrome 主版本：

```powershell
$env:CHROME_VERSION_MAIN="148"
python main.py
```

## 工具

复制除视频、图片外的文件，保留目录结构：

```bash
python -m fc2cmadb_crawler.copy_non_media_files
python -m fc2cmadb_crawler.copy_non_media_files "D:\source_folder" "D:\target_folder"
```

Windows 可双击 `run_copy_non_media_files.bat`。

批量把 `.url` 中域名包含 `fc2` 的链接改为 `fc2cmadb.com`：

```bash
python -m fc2cmadb_crawler.update_shortcut_domains
python -m fc2cmadb_crawler.update_shortcut_domains "D:\shortcut_folder"
```

Windows 可双击 `run_update_shortcut_domains.bat`。

## 目录结构

```text
fc2ppvdb-crawler/
├── main.py
├── fc2cmadb_crawler/
│   ├── config.py
│   ├── crawler.py
│   ├── copy_non_media_files.py
│   ├── copy_non_media.py
│   ├── update_shortcut_domains.py
│   └── shortcut_domains.py
├── run_fc2cmadb_crawler.bat
├── run_copy_non_media_files.bat
├── run_update_shortcut_domains.bat
├── requirements.txt
├── CHANGELOG.md
├── secrets/                   # 本地真实隐私配置及脱敏示例，本地提交
├── ~ref/                      # 参考项目，本地提交
├── ~archived/                 # 旧文件和历史内容，本地提交
├── recommend_20260629/
├── output/                    # 生成输出，不提交
└── ~temp/                     # 临时文件，不提交
```
