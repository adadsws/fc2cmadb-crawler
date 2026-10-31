# 负责递归读取媒体信息、重命名视频，并从最深层开始重命名包含视频的目录。
$ErrorActionPreference = 'Stop'

function Write-WarningLine {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

# 只给源路径与目标路径不同的片段着色，公共前后缀保持终端默认颜色。
function Write-PathWithHighlightedDifference {
    param(
        [string]$Text,
        [int]$PrefixLength,
        [int]$SuffixLength,
        [ConsoleColor]$BackgroundColor
    )

    if ($PrefixLength -gt 0) {
        Write-Host $Text.Substring(0, $PrefixLength) -NoNewline
    }
    $changedLength = $Text.Length - $PrefixLength - $SuffixLength
    if ($changedLength -gt 0) {
        Write-Host $Text.Substring($PrefixLength, $changedLength) -NoNewline -ForegroundColor White -BackgroundColor $BackgroundColor
    }
    if ($SuffixLength -gt 0) {
        Write-Host $Text.Substring($Text.Length - $SuffixLength) -NoNewline
    }
}

function Write-RenamePreviewLine {
    param(
        [string]$Kind,
        [string]$SourcePath,
        [string]$DestinationPath
    )

    $commonPrefix = 0
    $shorterLength = [Math]::Min($SourcePath.Length, $DestinationPath.Length)
    while ($commonPrefix -lt $shorterLength -and $SourcePath[$commonPrefix] -ceq $DestinationPath[$commonPrefix]) {
        $commonPrefix++
    }
    $commonSuffix = 0
    while ($commonSuffix -lt ($SourcePath.Length - $commonPrefix) -and
           $commonSuffix -lt ($DestinationPath.Length - $commonPrefix) -and
           $SourcePath[$SourcePath.Length - 1 - $commonSuffix] -ceq $DestinationPath[$DestinationPath.Length - 1 - $commonSuffix]) {
        $commonSuffix++
    }

    if ($Kind -like '*归档目标*') {
        Write-Host "[$Kind] " -NoNewline -ForegroundColor Yellow
    }
    else {
        Write-Host "[$Kind] " -NoNewline
    }
    Write-PathWithHighlightedDifference -Text $SourcePath -PrefixLength $commonPrefix -SuffixLength $commonSuffix -BackgroundColor DarkRed
    Write-Host ' -> ' -NoNewline
    Write-PathWithHighlightedDifference -Text $DestinationPath -PrefixLength $commonPrefix -SuffixLength $commonSuffix -BackgroundColor DarkGreen
    Write-Host ''
}

function Get-CleanBaseName {
    param([string]$Name)
    return $Name -replace ' \[\d+Mbps_\d+p\]$', ''
}

function Test-SamePath {
    param(
        [string]$FirstPath,
        [string]$SecondPath
    )

    $firstFullPath = [IO.Path]::GetFullPath($FirstPath).TrimEnd('\', '/')
    $secondFullPath = [IO.Path]::GetFullPath($SecondPath).TrimEnd('\', '/')
    return [string]::Equals($firstFullPath, $secondFullPath, [StringComparison]::OrdinalIgnoreCase)
}

# 冲突目标集中移到所选目录同盘的归档批次，保留原相对路径及恢复记录。
function Move-RenameTargetToArchive {
    param(
        [string]$SourcePath,
        [string]$DestinationPath,
        [string]$ArchiveRoot,
        [string]$ArchiveBase
    )

    if (Test-SamePath -FirstPath $SourcePath -SecondPath $DestinationPath) {
        throw "源路径与覆盖目标相同：$SourcePath"
    }
    if (-not (Test-Path -LiteralPath $DestinationPath)) {
        return $null
    }
    $basePrefix = [IO.Path]::GetFullPath($ArchiveBase).TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar
    $fullDestination = [IO.Path]::GetFullPath($DestinationPath)
    if (-not $fullDestination.StartsWith($basePrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "覆盖目标不在归档范围内：$DestinationPath"
    }
    $relative = $fullDestination.Substring($basePrefix.Length)
    $archivePath = Join-Path $ArchiveRoot $relative
    $archiveParent = Split-Path -Parent $archivePath
    New-Item -ItemType Directory -Path $archiveParent -Force | Out-Null
    if (Test-Path -LiteralPath $archivePath) {
        throw "归档路径已存在：$archivePath"
    }
    Move-Item -LiteralPath $DestinationPath -Destination $archivePath
    return $archivePath
}

function Get-MediaInfo {
    param(
        [System.IO.FileInfo]$File,
        [string]$FfprobePath
    )

    try {
        $jsonText = & $FfprobePath -v error -show_entries 'format=bit_rate,duration:stream=codec_type,height' -of json $File.FullName 2>$null | Out-String
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($jsonText)) {
            throw 'ffprobe returned no usable result.'
        }

        $probe = $jsonText | ConvertFrom-Json
        $bitRate = 0.0
        if ($null -ne $probe.format.bit_rate) {
            [double]::TryParse([string]$probe.format.bit_rate, [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$bitRate) | Out-Null
        }

        # 某些容器没有 bit_rate；此时用文件大小和时长估算总比特率。
        if ($bitRate -le 0 -and $null -ne $probe.format.duration) {
            $duration = 0.0
            [double]::TryParse([string]$probe.format.duration, [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$duration) | Out-Null
            if ($duration -gt 0) {
                $bitRate = ($File.Length * 8.0) / $duration
            }
        }

        $heights = @(
            $probe.streams |
                Where-Object { $_.codec_type -eq 'video' -and [int]$_.height -gt 0 } |
                ForEach-Object { [int]$_.height }
        )
        if ($bitRate -le 0 -or $heights.Count -eq 0) {
            throw 'total bitrate or video height is missing.'
        }

        [pscustomobject]@{
            File       = $File
            Directory  = $File.Directory.FullName
            BitRateBps = $bitRate
            Height     = ($heights | Measure-Object -Maximum).Maximum
        }
    }
    catch {
        Write-WarningLine "Skipped unreadable video: $($File.FullName) ($($_.Exception.Message))"
        return $null
    }
}

function Format-MediaTag {
    param(
        [double]$BitRateBps,
        [int]$Height
    )

    $mbps = [int][Math]::Round($BitRateBps / 1000000.0, [MidpointRounding]::AwayFromZero)
    return '[{0}Mbps_{1}p]' -f $mbps.ToString('D3'), $Height
}

# 所有会修改磁盘名称的操作都必须先预览，再用数字明确确认。
function Confirm-PreviewExecution {
    while ($true) {
        Write-Host ''
        Write-Host '[1] 确认执行' -ForegroundColor Yellow
        Write-Host '[b] 返回主菜单    [q] 退出'
        $rawConfirmation = Read-Host '请输入数字，直接回车默认选择 1'
        if ($null -eq $rawConfirmation) { throw [System.OperationCanceledException]::new('QuitTool') }
        $confirmation = ([string]$rawConfirmation).Trim()
        switch ($confirmation) {
            '1' { return $true }
            ''  { return $true }
            'b' { throw [System.OperationCanceledException]::new('BackToMainMenu') }
            'q' { throw [System.OperationCanceledException]::new('QuitTool') }
            default {
                Write-WarningLine "无效选择：$confirmation"
            }
        }
    }
}

# 撤销记录保存在用户本地应用数据中，不会写入被处理的视频目录。
function Get-UndoLogPath {
    $localData = $env:LOCALAPPDATA
    if ([string]::IsNullOrWhiteSpace($localData)) {
        $localData = [Environment]::GetFolderPath([Environment+SpecialFolder]::LocalApplicationData)
    }
    $logDirectory = Join-Path $localData 'VideoMediaRenamer'
    if (-not (Test-Path -LiteralPath $logDirectory -PathType Container)) {
        New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
    }
    return (Join-Path $logDirectory 'last-operation.json')
}

function Get-UndoHistoryDirectory {
    $directory = Join-Path (Split-Path -Parent (Get-UndoLogPath)) 'history'
    if (-not (Test-Path -LiteralPath $directory -PathType Container)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }
    return $directory
}

function Save-UndoLog {
    param([object]$Log, [string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) {
        $name = (Get-Date -Format 'yyyyMMdd-HHmmss-fffffff') + '-' + [guid]::NewGuid().ToString('N') + '.json'
        $Path = Join-Path (Get-UndoHistoryDirectory) $name
    }
    $json = $Log | ConvertTo-Json -Depth 5
    [IO.File]::WriteAllText($Path, $json, [Text.UTF8Encoding]::new($false))
    return $Path
}

function Get-PendingUndoLogs {
    $pending = [Collections.Generic.List[object]]::new()
    $files = @(Get-ChildItem -LiteralPath (Get-UndoHistoryDirectory) -Filter '*.json' -File | Sort-Object Name -Descending)
    foreach ($file in $files) {
        try {
            $log = Get-Content -Raw -Encoding UTF8 -LiteralPath $file.FullName | ConvertFrom-Json
            if ([string]::IsNullOrWhiteSpace([string]$log.UndoneAt)) {
                $pending.Add([pscustomobject]@{ Path = $file.FullName; Log = $log })
            }
        }
        catch { Write-WarningLine "无法读取撤销记录：$($file.FullName)" }
    }
    $legacyPath = Get-UndoLogPath
    if (Test-Path -LiteralPath $legacyPath -PathType Leaf) {
        try {
            $legacy = Get-Content -Raw -Encoding UTF8 -LiteralPath $legacyPath | ConvertFrom-Json
            if ([string]::IsNullOrWhiteSpace([string]$legacy.UndoneAt)) {
                $pending.Add([pscustomobject]@{ Path = $legacyPath; Log = $legacy })
            }
        }
        catch { Write-WarningLine "无法读取撤销记录：$legacyPath" }
    }
    return $pending.ToArray()
}

function Undo-LastOperation {
    param([string]$LogPath)
    $log = Get-Content -Raw -Encoding UTF8 -LiteralPath $logPath | ConvertFrom-Json
    $entries = @($log.Entries)
    if ($entries.Count -eq 0) {
        Write-Host '撤销记录中没有实际改名项目。' -ForegroundColor Yellow
        return $false
    }

    [Array]::Reverse($entries)
    $pendingDirectoryRestores = @($entries | Where-Object { $_.Kind -eq 'Directory' -and (Test-Path -LiteralPath $_.NewPath) -and -not (Test-Path -LiteralPath $_.OldPath) })
    # 展示顺序按原目录分组；执行仍使用反向记录顺序，先恢复上级路径。
    $previewEntries = @($entries | Sort-Object `
        @{ Expression = { if ($_.Kind -eq 'Directory') { [string]$_.OldPath } else { [IO.Path]::GetDirectoryName([string]$_.OldPath) } } }, `
        @{ Expression = { if ($_.Kind -eq 'Directory') { 0 } else { 1 } } }, `
        @{ Expression = { [string]$_.OldPath } })

    Write-Host ''
    Write-Host '所选批次撤销预览（按目录及所属文件展示）：' -ForegroundColor Cyan
    Write-Host "记录：$([IO.Path]::GetFileName($logPath))"
    foreach ($entry in $previewEntries) {
        $newExists = Test-Path -LiteralPath $entry.NewPath
        $oldExists = Test-Path -LiteralPath $entry.OldPath
        $archiveExists = [string]::IsNullOrWhiteSpace([string]$entry.ArchivedTargetPath) -or (Test-Path -LiteralPath $entry.ArchivedTargetPath)
        if ($newExists -and -not $oldExists -and $archiveExists) {
            $status = '将恢复'
        }
        elseif (-not $newExists -and $oldExists) {
            $status = if ([string]::IsNullOrWhiteSpace([string]$entry.ArchivedTargetPath) -or -not (Test-Path -LiteralPath $entry.ArchivedTargetPath)) { '已恢复' } else { '将恢复归档目标' }
        }
        elseif (-not $newExists -and -not $oldExists -and @($pendingDirectoryRestores | Where-Object { $entry.NewPath.StartsWith(([string]$_.OldPath).TrimEnd('\', '/') + '\', [StringComparison]::OrdinalIgnoreCase) }).Count -gt 0) {
            $status = '待上级目录恢复'
        }
        else {
            $status = '冲突或缺失'
        }
        Write-RenamePreviewLine -Kind $status -SourcePath $entry.NewPath -DestinationPath $entry.OldPath
        if (-not [string]::IsNullOrWhiteSpace([string]$entry.ArchivedTargetPath) -and (Test-Path -LiteralPath $entry.ArchivedTargetPath)) {
            Write-RenamePreviewLine -Kind '归档目标恢复' -SourcePath $entry.ArchivedTargetPath -DestinationPath $entry.NewPath
        }
    }
    if (-not (Confirm-PreviewExecution)) {
        Write-Host '已取消撤销，未修改任何名称。' -ForegroundColor Yellow
        return $false
    }

    $restored = 0
    $alreadyRestored = 0
    $failed = 0
    foreach ($entry in $entries) {
        $newExists = Test-Path -LiteralPath $entry.NewPath
        $oldExists = Test-Path -LiteralPath $entry.OldPath
        $archiveExists = [string]::IsNullOrWhiteSpace([string]$entry.ArchivedTargetPath) -or (Test-Path -LiteralPath $entry.ArchivedTargetPath)
        if ($newExists -and -not $oldExists -and $archiveExists) {
            try {
                Rename-Item -LiteralPath $entry.NewPath -NewName ([IO.Path]::GetFileName([string]$entry.OldPath))
                if (-not [string]::IsNullOrWhiteSpace([string]$entry.ArchivedTargetPath)) {
                    Move-Item -LiteralPath $entry.ArchivedTargetPath -Destination $entry.NewPath
                }
                Write-Host "[撤销] $($entry.NewPath) -> $($entry.OldPath)"
                $restored++
            }
            catch {
                Write-WarningLine "撤销失败：$($entry.NewPath)（$($_.Exception.Message)）"
                $failed++
            }
        }
        elseif (-not $newExists -and $oldExists) {
            if (-not [string]::IsNullOrWhiteSpace([string]$entry.ArchivedTargetPath) -and (Test-Path -LiteralPath $entry.ArchivedTargetPath)) {
                try {
                    Move-Item -LiteralPath $entry.ArchivedTargetPath -Destination $entry.NewPath
                    Write-Host "[恢复归档目标] $($entry.ArchivedTargetPath) -> $($entry.NewPath)"
                    $restored++
                }
                catch {
                    Write-WarningLine "恢复归档目标失败：$($entry.ArchivedTargetPath)（$($_.Exception.Message)）"
                    $failed++
                }
            }
            else {
                $alreadyRestored++
            }
        }
        else {
            Write-WarningLine "无法安全撤销，路径缺失或发生冲突：$($entry.NewPath)"
            $failed++
        }
    }

    if ($failed -eq 0) {
        $log | Add-Member -NotePropertyName UndoneAt -NotePropertyValue ([DateTime]::Now.ToString('yyyy-MM-dd HH:mm:ss')) -Force
        Save-UndoLog -Log $log -Path $logPath | Out-Null
        Write-Host "撤销完成。已恢复：$restored；此前已恢复：$alreadyRestored。" -ForegroundColor Green
        return $true
    }
    else {
        Write-WarningLine "撤销未完全完成。已恢复：$restored；失败：$failed。可排除冲突后再次选择撤销。"
        return $false
    }
}

function Invoke-UndoOperations {
    while ($true) {
        $logs = @(Get-PendingUndoLogs)
        if ($logs.Count -eq 0) {
            Write-Host '没有可撤销的重命名记录。' -ForegroundColor Yellow
            return
        }
        Write-Host ''
        Write-Host '最近处理的文件夹（选择要撤销的一批）：' -ForegroundColor Cyan
        for ($index = 0; $index -lt $logs.Count; $index++) {
            $log = $logs[$index].Log
            $rootPath = [string]$log.RootPath
            if ([string]::IsNullOrWhiteSpace($rootPath)) {
                $firstEntry = @($log.Entries | Select-Object -First 1)
                if ($firstEntry.Count -gt 0) {
                    $rootPath = [IO.Path]::GetDirectoryName([string]$firstEntry[0].OldPath)
                }
            }
            if ([string]::IsNullOrWhiteSpace($rootPath)) { $rootPath = '[路径未知]' }
            $when = [string]$log.CreatedAt
            $timeLabel = if ([string]::IsNullOrWhiteSpace($when)) { '' } else { " ($when)" }
            Write-Host "[$($index + 1)] $rootPath$timeLabel"
        }
        Write-Host '[b] 返回主菜单    [q] 退出'
        $rawChoice = Read-Host '选择编号，直接回车默认选择 1'
        if ($null -eq $rawChoice) { throw [System.OperationCanceledException]::new('QuitTool') }
        $choice = ([string]$rawChoice).Trim()
        if ($choice -ieq 'b') { throw [System.OperationCanceledException]::new('BackToMainMenu') }
        if ($choice -ieq 'q') { throw [System.OperationCanceledException]::new('QuitTool') }
        if ($choice -eq '') { $choice = '1' }
        $selected = 0
        if ([int]::TryParse($choice, [ref]$selected) -and $selected -ge 1 -and $selected -le $logs.Count) {
            Undo-LastOperation -LogPath $logs[$selected - 1].Path | Out-Null
            continue
        }
        Write-WarningLine "请输入 1 到 $($logs.Count) 的编号。"
    }
}

function Invoke-RenameOperation {
    $rawPath = Read-Host '请粘贴文件夹路径（b 返回主菜单，q 退出）'
    if ($null -eq $rawPath) { return 'exit' }
    $inputPath = ([string]$rawPath).Trim()
    if ($inputPath -ieq 'b') { return 'back' }
    if ($inputPath -ieq 'q') { return 'exit' }
    if ([string]::IsNullOrWhiteSpace($inputPath)) {
        Write-WarningLine '文件夹路径不能为空。'
        return
    }
    if (($inputPath.StartsWith('"') -and $inputPath.EndsWith('"')) -or ($inputPath.StartsWith("'") -and $inputPath.EndsWith("'"))) {
        $inputPath = $inputPath.Substring(1, $inputPath.Length - 2)
    }
    if ($inputPath -ne [IO.Path]::GetPathRoot($inputPath)) {
        $inputPath = $inputPath.TrimEnd('\', '/')
    }

    if (-not (Test-Path -LiteralPath $inputPath -PathType Container)) {
        throw "文件夹不存在：$inputPath"
    }
    $rootPath = (Resolve-Path -LiteralPath $inputPath).Path

    $toolDirectory = Split-Path -Parent $PSScriptRoot
    $localFfprobe = Join-Path $toolDirectory 'ffprobe.exe'
    if (Test-Path -LiteralPath $localFfprobe -PathType Leaf) {
        $ffprobe = $localFfprobe
    }
    else {
        $ffprobeCommand = Get-Command 'ffprobe.exe' -ErrorAction SilentlyContinue
        if ($null -eq $ffprobeCommand) {
            throw '未找到 ffprobe.exe。请将它放在 tools/rename_vids 目录，或把 FFmpeg bin 加入 PATH。'
        }
        $ffprobe = $ffprobeCommand.Source
    }

    $videoExtensions = @(
        '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v',
        '.mpg', '.mpeg', '.ts', '.m2ts', '.mts', '.vob', '.ogv', '.3gp',
        '.rm', '.rmvb', '.asf', '.divx', '.f4v'
    )
    $files = @(
        Get-ChildItem -LiteralPath $rootPath -File -Recurse -Force -ErrorAction SilentlyContinue |
            Where-Object { $videoExtensions -contains $_.Extension.ToLowerInvariant() -and $_.FullName -notmatch '[\\/]~archive[\\/]' }
    )

    if ($files.Count -eq 0) {
        Write-Host '没有找到支持的视频文件。' -ForegroundColor Yellow
        return
    }

    Write-Host "找到 $($files.Count) 个视频，正在读取媒体信息……"
    $records = @($files | ForEach-Object { Get-MediaInfo -File $_ -FfprobePath $ffprobe } | Where-Object { $null -ne $_ })
    if ($records.Count -eq 0) {
        throw '没有视频包含可用的总比特率和帧高度信息。'
    }

    # 先根据当前磁盘状态构建完整预览；确认前不执行任何 Rename-Item。
    $groups = @($records | Group-Object Directory | Sort-Object Name)
    $previewActionCount = 0
    $previewHasDestinationOverwrite = $false
    Write-Host ''
    Write-Host '重命名预览：' -ForegroundColor Cyan
    # 预览按目录聚合，先展示目录自身的变更，再展示该目录内每个待改文件。
    foreach ($group in $groups) {
        $directoryPath = $group.Name
        if (-not (Test-Path -LiteralPath $directoryPath -PathType Container)) {
            Write-Host "[跳过：目录缺失] $directoryPath" -ForegroundColor Yellow
            continue
        }

        $averageBitRate = ($group.Group | Measure-Object -Property BitRateBps -Average).Average
        $maxHeight = ($group.Group | Measure-Object -Property Height -Maximum).Maximum
        $tag = Format-MediaTag -BitRateBps $averageBitRate -Height $maxHeight
        $directory = Get-Item -LiteralPath $directoryPath
        $baseName = Get-CleanBaseName -Name $directory.Name
        $newName = "$baseName $tag"
        $destination = Join-Path $directory.Parent.FullName $newName

        Write-Host ''
        if ($directory.Name -cne $newName -and -not (Test-SamePath -FirstPath $directory.FullName -SecondPath $destination)) {
            $destinationExists = Test-Path -LiteralPath $destination
            Write-RenamePreviewLine -Kind $(if ($destinationExists) { '目录：将归档目标' } else { '目录' }) -SourcePath $directory.FullName -DestinationPath $destination
            $previewHasDestinationOverwrite = $previewHasDestinationOverwrite -or $destinationExists
            $previewActionCount++
        }
        else {
            Write-Host "[目录：名称不变] $directoryPath"
        }

        foreach ($record in @($group.Group | Sort-Object { $_.File.Name })) {
            $file = $record.File
            $fileTag = Format-MediaTag -BitRateBps $record.BitRateBps -Height $record.Height
            $fileBaseName = Get-CleanBaseName -Name $file.BaseName
            $fileNewName = "$fileBaseName $fileTag$($file.Extension)"
            $fileDestination = Join-Path $file.DirectoryName $fileNewName
            if ($file.Name -ceq $fileNewName -or (Test-SamePath -FirstPath $file.FullName -SecondPath $fileDestination)) { continue }
            $fileDestinationExists = Test-Path -LiteralPath $fileDestination
            Write-RenamePreviewLine -Kind $(if ($fileDestinationExists) { '文件：将归档目标' } else { '文件' }) -SourcePath $file.FullName -DestinationPath $fileDestination
            $previewHasDestinationOverwrite = $previewHasDestinationOverwrite -or $fileDestinationExists
            $previewActionCount++
        }
    }

    if ($previewActionCount -eq 0) {
        Write-Host '没有需要执行的重命名。' -ForegroundColor Yellow
        return
    }
    if ($previewHasDestinationOverwrite) {
        Write-Host '标为“将归档目标”的现有内容会移入同盘 ~archive，并记入撤销记录。'
    }
    if (-not (Confirm-PreviewExecution)) {
        Write-Host '已取消重命名，未修改任何名称。' -ForegroundColor Yellow
        return
    }

    $changes = [Collections.Generic.List[object]]::new()
    $archiveBase = Split-Path -Parent $rootPath
    if ([string]::IsNullOrWhiteSpace($archiveBase)) { $archiveBase = $rootPath }
    $archiveRoot = Join-Path $archiveBase (Join-Path '~archive' ((Get-Date -Format 'yyyyMMdd-HHmmss') + '-rename-conflict-' + [guid]::NewGuid().ToString('N')))
    $renamedFiles = 0
    $skippedFiles = 0
    foreach ($record in $records) {
        $file = $record.File
        $tag = Format-MediaTag -BitRateBps $record.BitRateBps -Height $record.Height
        $baseName = Get-CleanBaseName -Name $file.BaseName
        $newName = "$baseName $tag$($file.Extension)"
        $destination = Join-Path $file.DirectoryName $newName

        if ($file.Name -ceq $newName -or (Test-SamePath -FirstPath $file.FullName -SecondPath $destination)) { continue }

        $archivedTargetPath = $null
        try {
            $oldPath = $file.FullName
            $overwriting = Test-Path -LiteralPath $destination
            $archivedTargetPath = Move-RenameTargetToArchive -SourcePath $oldPath -DestinationPath $destination -ArchiveRoot $archiveRoot -ArchiveBase $archiveBase
            Rename-Item -LiteralPath $oldPath -NewName $newName
            $changes.Add([pscustomobject]@{ Kind = 'File'; OldPath = $oldPath; NewPath = $destination; ArchivedTargetPath = $archivedTargetPath })
            if ($overwriting) {
                Write-Host "[文件：已归档目标] $($file.Name) -> $newName；归档：$archivedTargetPath"
            }
            else {
                Write-Host "[文件] $($file.Name) -> $newName"
            }
            $renamedFiles++
        }
        catch {
            $failure = $_.Exception.Message
            if ($archivedTargetPath -and (Test-Path -LiteralPath $archivedTargetPath) -and -not (Test-Path -LiteralPath $destination)) {
                try { Move-Item -LiteralPath $archivedTargetPath -Destination $destination }
                catch { Write-WarningLine "归档目标自动恢复失败，请检查：$archivedTargetPath（$($_.Exception.Message)）" }
            }
            Write-WarningLine "文件改名失败：$($file.FullName)（$failure）"
            $skippedFiles++
        }
    }

    # 先处理最深层目录；撤销时反向执行，会先恢复父目录，再恢复子目录和文件。
    $groups = @($records | Group-Object Directory | Sort-Object { $_.Name.Length } -Descending)
    $renamedFolders = 0
    $skippedFolders = 0
    foreach ($group in $groups) {
        $directoryPath = $group.Name
        if (-not (Test-Path -LiteralPath $directoryPath -PathType Container)) {
            Write-WarningLine "目录路径已变化或消失，已跳过：$directoryPath"
            $skippedFolders++
            continue
        }

        $averageBitRate = ($group.Group | Measure-Object -Property BitRateBps -Average).Average
        $maxHeight = ($group.Group | Measure-Object -Property Height -Maximum).Maximum
        $tag = Format-MediaTag -BitRateBps $averageBitRate -Height $maxHeight
        $directory = Get-Item -LiteralPath $directoryPath
        $baseName = Get-CleanBaseName -Name $directory.Name
        $newName = "$baseName $tag"
        $destination = Join-Path $directory.Parent.FullName $newName

        if ($directory.Name -ceq $newName -or (Test-SamePath -FirstPath $directory.FullName -SecondPath $destination)) { continue }

        $archivedTargetPath = $null
        try {
            $oldPath = $directory.FullName
            $overwriting = Test-Path -LiteralPath $destination
            $archivedTargetPath = Move-RenameTargetToArchive -SourcePath $oldPath -DestinationPath $destination -ArchiveRoot $archiveRoot -ArchiveBase $archiveBase
            Rename-Item -LiteralPath $oldPath -NewName $newName
            $changes.Add([pscustomobject]@{ Kind = 'Directory'; OldPath = $oldPath; NewPath = $destination; ArchivedTargetPath = $archivedTargetPath })
            if ($overwriting) {
                Write-Host "[目录：已归档目标] $($directory.Name) -> $newName；归档：$archivedTargetPath"
            }
            else {
                Write-Host "[目录] $($directory.Name) -> $newName"
            }
            $renamedFolders++
        }
        catch {
            $failure = $_.Exception.Message
            if ($archivedTargetPath -and (Test-Path -LiteralPath $archivedTargetPath) -and -not (Test-Path -LiteralPath $destination)) {
                try { Move-Item -LiteralPath $archivedTargetPath -Destination $destination }
                catch { Write-WarningLine "归档目标自动恢复失败，请检查：$archivedTargetPath（$($_.Exception.Message)）" }
            }
            Write-WarningLine "目录改名失败：$($directory.FullName)（$failure）"
            $skippedFolders++
        }
    }

    if ($changes.Count -gt 0) {
        Save-UndoLog -Log ([pscustomobject]@{
            Version   = 1
            CreatedAt = [DateTime]::Now.ToString('yyyy-MM-dd HH:mm:ss')
            RootPath  = $rootPath
            Entries   = $changes.ToArray()
        }) | Out-Null
    }

    Write-Host ''
    Write-Host "完成。文件改名：$renamedFiles；文件跳过：$skippedFiles；目录改名：$renamedFolders；目录跳过：$skippedFolders。" -ForegroundColor Green
    if ($records.Count -lt $files.Count) {
        Write-WarningLine "$($files.Count - $records.Count) 个视频无法读取，已保持不变。"
    }
}

# 主菜单选择重命名后保持该模式；撤销为单次操作，完成后返回主菜单。
Write-Host '视频递归重命名（总比特率 + 帧高度）' -ForegroundColor Cyan
Write-Host '示例：movie.mp4 -> movie [023Mbps_2048p].mp4'

$currentMode = $null
while ($true) {
    if ($null -eq $currentMode) {
        Write-Host ''
        Write-Host '[1] 重命名视频和目录'
        Write-Host '[2] 按文件夹选择并撤销重命名'
        Write-Host '[q] 退出'
        $rawChoice = Read-Host '直接回车默认选择 1'
        if ($null -eq $rawChoice) { exit 0 }
        $choice = ([string]$rawChoice).Trim()
        if ($choice -eq '') { $choice = '1' }
        if ($choice -eq '1') { $currentMode = 'rename' }
    }
    else {
        $choice = '1'
    }

    try {
        switch ($choice) {
            '1' {
                $result = Invoke-RenameOperation
                if ($result -eq 'exit') { exit 0 }
                if ($result -eq 'back') { $currentMode = $null }
            }
            '2' { Invoke-UndoOperations; $currentMode = $null }
            'q' {
                Write-Host '已退出。'
                exit 0
            }
            default { Write-WarningLine "无效选择：$choice" }
        }
    }
    catch {
        if ($_.Exception.Message -eq 'BackToMainMenu') { $currentMode = $null }
        elseif ($_.Exception.Message -eq 'QuitTool') { exit 0 }
        else { Write-Host "[错误] $($_.Exception.Message)" -ForegroundColor Red }
    }

    if ($null -ne $currentMode) {
        Write-Host '当前为重命名模式，可继续输入文件夹；b 返回主菜单，q 退出。'
    }
}
