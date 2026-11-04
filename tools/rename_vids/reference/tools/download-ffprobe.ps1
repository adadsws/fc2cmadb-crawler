# 下载固定 FFprobe 构建包，校验包与可执行文件后放入视频重命名工具目录。
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$target = Join-Path $root 'ffprobe.exe'
$expectedExeHash = 'f0d36ecbbdd3bcfac3efa078c96c7271c2e68b3810595552ac3b7f17e9a65c52'
if (Test-Path -LiteralPath $target) {
    if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ieq $expectedExeHash) {
        Write-Host "FFprobe 已存在并通过校验：$target"
        return
    }
    throw "现有 ffprobe.exe 校验失败，请先人工核对：$target"
}

$temp = Join-Path $root '~temp/ffprobe'
$archive = Join-Path $temp 'ffmpeg-9.0.2-essentials_build.7z'
$extracted = Join-Path $temp 'extracted'
$url = 'https://github.com/GyanD/codexffmpeg/releases/download/9.0.2/ffmpeg-9.0.2-essentials_build.7z'
$expectedArchiveHash = '4705843ccaaf54257c16ad90f3e952ece33c17df964ecf7bfdbb0f49c7171077'
New-Item -ItemType Directory -Path $temp -Force | Out-Null
if (-not (Test-Path -LiteralPath $archive)) {
    Write-Host '正在下载 FFmpeg 9.0.2 Essentials Build…'
    Invoke-WebRequest -Uri $url -OutFile $archive
}
if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ine $expectedArchiveHash) {
    throw "下载包校验失败：$archive"
}
New-Item -ItemType Directory -Path $extracted -Force | Out-Null
$sevenZip = Get-Command '7z.exe' -ErrorAction SilentlyContinue
if ($null -ne $sevenZip) { $sevenZip = $sevenZip.Source }
elseif (Test-Path -LiteralPath 'C:\Program Files\7-Zip\7z.exe') { $sevenZip = 'C:\Program Files\7-Zip\7z.exe' }
else { throw '解压固定 7z 包需要 7-Zip，请先安装 7-Zip。' }
& $sevenZip x '-aos' "-o$extracted" $archive 'ffmpeg-9.0.2-essentials_build/bin/ffprobe.exe' | Out-Null
if ($LASTEXITCODE -ne 0) { throw "解压失败：$archive" }
$source = Join-Path $extracted 'ffmpeg-9.0.2-essentials_build/bin/ffprobe.exe'
if (-not (Test-Path -LiteralPath $source) -or (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ine $expectedExeHash) {
    throw "FFprobe 校验失败：$source"
}
Move-Item -LiteralPath $source -Destination $target
Write-Host "FFprobe 已安装并通过校验：$target"
