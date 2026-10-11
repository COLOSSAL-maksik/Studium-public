param([Parameter(Mandatory)][int]$OwnProcessId, [switch]$LeaveOpen, [switch]$CloseOnly)
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'Native Windows UI Automation required.' }
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$main = $null
$deadline = [DateTime]::UtcNow.AddSeconds(45)
while (-not $main -and [DateTime]::UtcNow -lt $deadline) {
    $ids = @($OwnProcessId)
    $ids += @(Get-CimInstance Win32_Process -Filter "ParentProcessId = $OwnProcessId" |
        Where-Object Name -eq 'Studium.exe' | ForEach-Object { [int]$_.ProcessId })
    foreach ($processId in $ids) {
        $condition = [System.Windows.Automation.PropertyCondition]::new(
            [System.Windows.Automation.AutomationElement]::ProcessIdProperty, [int]$processId)
        $windows = [System.Windows.Automation.AutomationElement]::RootElement.FindAll(
            [System.Windows.Automation.TreeScope]::Children, $condition)
        foreach ($window in $windows) {
            if ($window.Current.Name -eq 'Studium') { $main = $window; break }
        }
    }
    if (-not $main) { Start-Sleep -Milliseconds 100 }
}
if (-not $main) { throw 'Visible installed Studium window was not found.' }
if ($CloseOnly) {
    $main.GetCurrentPattern([System.Windows.Automation.WindowPattern]::Pattern).Close()
    return
}
function Named([string]$name) {
    $condition = [System.Windows.Automation.PropertyCondition]::new(
        [System.Windows.Automation.AutomationElement]::NameProperty, $name)
    $control = $main.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $condition)
    if (-not $control) { throw 'Required installed-app control was not found.' }
    return $control
}
# No desktop-wide keystrokes, input injection, screenshots or source-runtime hooks.
Named 'Добро пожаловать' | Out-Null
(Named 'Справка').GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
Start-Sleep -Milliseconds 300
Named 'Статья справки' | Out-Null
$search = Named 'Поиск в справке'
$search.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).SetValue('дата получения')
Start-Sleep -Milliseconds 300
$results = @($main.FindAll([System.Windows.Automation.TreeScope]::Descendants,
    [System.Windows.Automation.PropertyCondition]::new(
        [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
        [System.Windows.Automation.ControlType]::ListItem)) | Where-Object { -not $_.Current.IsOffscreen })
if ($results.Count -eq 0) { throw 'Installed offline Help resources did not load.' }
if (-not $LeaveOpen) { $main.GetCurrentPattern([System.Windows.Automation.WindowPattern]::Pattern).Close() }
Write-Output 'INSTALLED_WINDOW_AND_OFFLINE_HELP_PASS'
