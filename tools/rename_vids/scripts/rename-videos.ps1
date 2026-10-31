# 负责递归读取媒体信息、重命名视频，并从最深层开始重命名包含视频的目录。
$ErrorActionPreference = 'Stop'

function Write-WarningLine {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-TextWithHighlightedMediaTag {
    param([string]$Text)

    $matches = [regex]::Matches($Text, '\[\d+Mbps_\d+p\]')
    if ($matches.Count -eq 0) {
        Write-Host $Text -NoNewline
        return
    }

    # 完整路径的父目录也可能含媒体标签，只高亮当前项目名称中的最后一个标签。
    $match = $matches[$matches.Count - 1]
    if ($match.Index -gt 0) {
        Write-Host $Text.Substring(0, $match.Index) -NoNewline
    }
    Write-Host $match.Value -NoNewline -ForegroundColor Black -BackgroundColor Yellow
    $position = $match.Index + $match.Length
    if ($position -lt $Text.Length) {
        Write-Host $Text.Substring($position) -NoNewline
    }
}

# 预览保持整行正常颜色，只突出将被替换的旧标签或冲突目标标签。
function Write-RenamePreviewLine {
    param(
        [string]$Kind,
        [string]$SourcePath,
        [string]$DestinationPath,
        [bool]$HighlightSourceTag,
        [bool]$HighlightDestinationTag
    )

    Write-Host "[$Kind] " -NoNewline
    if ($HighlightSourceTag) {
        Write-TextWithHighlightedMediaTag -Text $SourcePath
    }
    else {
        Write-Host $SourcePath -NoNewline
    }
    Write-Host ' -> ' -NoNewline
    if ($HighlightDestinationTag) {
        Write-TextWithHighlightedMediaTag -Text $DestinationPath
    }
    else {
        Write-Host $DestinationPath -NoNewline
    }
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
        Write-Host '[0] 取消并返回主菜单'
        $rawConfirmation = Read-Host '请输入数字，直接回车默认选择 1'
        if ($null -eq $rawConfirmation) { return $false }
        $confirmation = ([string]$rawConfirmation).Trim()
        switch ($confirmation) {
            '1' { return $true }
            ''  { return $true }
            '0' { return $false }
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

function Save-UndoLog {
    param([object]$Log)
    $json = $Log | ConvertTo-Json -Depth 5
    [IO.File]::WriteAllText((Get-UndoLogPath), $json, [Text.UTF8Encoding]::new($false))
}

function Undo-LastOperation {
    $logPath = Get-UndoLogPath
    if (-not (Test-Path -LiteralPath $logPath -PathType Leaf)) {
        Write-Host '没有可撤销的重命名记录。' -ForegroundColor Yellow
        return
    }

    $log = Get-Content -Raw -Encoding UTF8 -LiteralPath $logPath | ConvertFrom-Json
    if ($null -ne $log.UndoneAt -and -not [string]::IsNullOrWhiteSpace([string]$log.UndoneAt)) {
        Write-Host "最近一次操作已经在 $($log.UndoneAt) 撤销。" -ForegroundColor Yellow
        return
    }

    $entries = @($log.Entries)
    if ($entries.Count -eq 0) {
        Write-Host '撤销记录中没有实际改名项目。' -ForegroundColor Yellow
        return
    }

    [Array]::Reverse($entries)
    $pendingDirectoryRestores = @($entries | Where-Object { $_.Kind -eq 'Directory' -and (Test-Path -LiteralPath $_.NewPath) -and -not (Test-Path -LiteralPath $_.OldPath) })

    Write-Host ''
    Write-Host '撤销预览（按以下顺序恢复）：' -ForegroundColor Cyan
    foreach ($entry in $entries) {
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
        Write-Host "[$status] $($entry.NewPath) -> $($entry.OldPath)"
    }
    if (-not (Confirm-PreviewExecution)) {
        Write-Host '已取消撤销，未修改任何名称。' -ForegroundColor Yellow
        return
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
        Save-UndoLog -Log $log
        Write-Host "撤销完成。已恢复：$restored；此前已恢复：$alreadyRestored。" -ForegroundColor Green
    }
    else {
        Write-WarningLine "撤销未完全完成。已恢复：$restored；失败：$failed。可排除冲突后再次选择撤销。"
    }
}

function Invoke-RenameOperation {
    $inputPath = ([string](Read-Host '请粘贴文件夹路径')).Trim()
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

    $scriptDirectory = Split-Path -Parent $env:MEDIA_RENAMER_SELF
    $localFfprobe = Join-Path $scriptDirectory 'ffprobe.exe'
    if (Test-Path -LiteralPath $localFfprobe -PathType Leaf) {
        $ffprobe = $localFfprobe
    }
    else {
        $ffprobeCommand = Get-Command 'ffprobe.exe' -ErrorAction SilentlyContinue
        if ($null -eq $ffprobeCommand) {
            throw '未找到 ffprobe.exe。请将它放在本 BAT 同目录，或把 FFmpeg bin 加入 PATH。'
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
    $groups = @($records | Group-Object Directory | Sort-Object { $_.Name.Length } -Descending)
    $previewActionCount = 0
    $previewHasDestinationOverwrite = $false
    Write-Host ''
    Write-Host '重命名预览：' -ForegroundColor Cyan
    foreach ($record in $records) {
        $file = $record.File
        $tag = Format-MediaTag -BitRateBps $record.BitRateBps -Height $record.Height
        $baseName = Get-CleanBaseName -Name $file.BaseName
        $newName = "$baseName $tag$($file.Extension)"
        $destination = Join-Path $file.DirectoryName $newName

        if ($file.Name -ceq $newName -or (Test-SamePath -FirstPath $file.FullName -SecondPath $destination)) { continue }
        $hasExistingTag = $baseName -cne $file.BaseName
        $destinationExists = Test-Path -LiteralPath $destination
        Write-RenamePreviewLine -Kind $(if ($destinationExists) { '文件：将归档目标' } else { '文件' }) -SourcePath $file.FullName -DestinationPath $destination -HighlightSourceTag $hasExistingTag -HighlightDestinationTag $destinationExists
        $previewHasDestinationOverwrite = $previewHasDestinationOverwrite -or $destinationExists
        $previewActionCount++
    }

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

        if ($directory.Name -ceq $newName -or (Test-SamePath -FirstPath $directory.FullName -SecondPath $destination)) { continue }
        $hasExistingTag = $baseName -cne $directory.Name
        $destinationExists = Test-Path -LiteralPath $destination
        Write-RenamePreviewLine -Kind $(if ($destinationExists) { '目录：将归档目标' } else { '目录' }) -SourcePath $directory.FullName -DestinationPath $destination -HighlightSourceTag $hasExistingTag -HighlightDestinationTag $destinationExists
        $previewHasDestinationOverwrite = $previewHasDestinationOverwrite -or $destinationExists
        $previewActionCount++
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
        })
    }

    Write-Host ''
    Write-Host "完成。文件改名：$renamedFiles；文件跳过：$skippedFiles；目录改名：$renamedFolders；目录跳过：$skippedFolders。" -ForegroundColor Green
    if ($records.Count -lt $files.Count) {
        Write-WarningLine "$($files.Count - $records.Count) 个视频无法读取，已保持不变。"
    }
}

# 主菜单持续循环；每次操作完成或出错后均返回菜单，输入 0 才正常退出。
Write-Host '视频递归重命名（总比特率 + 帧高度）' -ForegroundColor Cyan
Write-Host '示例：movie.mp4 -> movie [023Mbps_2048p].mp4'

while ($true) {
    Write-Host ''
    Write-Host '[1] 重命名视频和目录'
    Write-Host '[2] 撤销最近一次重命名'
    Write-Host '[0] 退出'
    $rawChoice = Read-Host '直接回车默认选择 1'
    if ($null -eq $rawChoice) { exit 0 }
    $choice = ([string]$rawChoice).Trim()

    try {
        switch ($choice) {
            ''  { Invoke-RenameOperation }
            '1' { Invoke-RenameOperation }
            '2' { Undo-LastOperation }
            '0' {
                Write-Host '已退出。'
                exit 0
            }
            default { Write-WarningLine "无效选择：$choice" }
        }
    }
    catch {
        Write-Host "[错误] $($_.Exception.Message)" -ForegroundColor Red
    }

    Write-Host ''
    Read-Host '按回车返回主菜单' | Out-Null
}
