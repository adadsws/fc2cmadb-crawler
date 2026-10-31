# FFmpeg / FFprobe

- 用途：由 `tools/rename_videos_by_media_info.bat` 调用 `ffprobe.exe`，读取视频容器总比特率与视频流帧高度。
- 使用方式：完整调用预编译的 Windows 64 位静态程序；项目没有复制或修改 FFmpeg 源码。
- 构建来源：https://www.gyan.dev/ffmpeg/builds/
- 镜像仓库：https://github.com/GyanD/codexffmpeg
- 固定版本：GyanD/codexffmpeg Release `9.0.2`，Essentials Build。
- 上游源码：https://github.com/FFmpeg/FFmpeg/commit/946fcce07b
- 上游源码提交：`946fcce07b`（构建发布页所列提交）。
- 下载包：`ffmpeg-9.0.2-essentials_build.7z`
- 下载包 SHA-256：`4705843ccaaf54257c16ad90f3e952ece33c17df964ecf7bfdbb0f49c7171077`
- `ffprobe.exe` 大小：`105221120` 字节。
- `ffprobe.exe` SHA-256：`f0d36ecbbdd3bcfac3efa078c96c7271c2e68b3810595552ac3b7f17e9a65c52`
- 未纳入本地 Git 的原因：单文件超过 100 MiB；可按 [下载脚本](download-ffprobe.ps1) 重建。
- 许可证：GPLv3；构建包中的 `LICENSE` 为完整许可证文本。

## 重建方法

1. 安装 7-Zip 后运行 [下载脚本](download-ffprobe.ps1)，或从固定 Release 下载 `ffmpeg-9.0.2-essentials_build.7z`。
2. 校验下载包 SHA-256 与上方固定值完全一致。
3. 从包内 `bin/ffprobe.exe` 提取到 `tools/rename_vids/`。
4. 执行 `ffprobe.exe -version`，确认首行版本为 `9.0.2-essentials_build-www.gyan.dev`。

最小放置树：

```text
tools/
  rename_videos_by_media_info.bat
  rename_vids/
    ffprobe.exe
```
