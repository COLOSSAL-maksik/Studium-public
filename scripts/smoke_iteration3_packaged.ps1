param([Parameter(Mandatory)][int]$OwnProcessId,[ValidateSet('fresh','migration','workflow','reopen')][string]$Mode='workflow')
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
# Reuse the existing PID-restricted native QA helpers, without its old scenario.
$source=[IO.File]::ReadAllText((Join-Path $PSScriptRoot 'smoke_iteration2_5_packaged.ps1'),[Text.Encoding]::UTF8)
$helpers=$source.Substring($source.IndexOf('$ErrorActionPreference'),$source.IndexOf('$main=Top')-$source.IndexOf('$ErrorActionPreference'))
if($env:STUDIUM_QA_SOURCE -eq '1'){$helpers=$helpers.Replace("'Studium.exe'","'python.exe'")}
Invoke-Expression $helpers
function Assert-Home($root) {
 Named $root 'Добро пожаловать' Text | Out-Null
 if(@(Nodes $root Button | Where-Object {$_.Current.Name -eq 'Назад'}).Count){throw 'Home has Back'}
 if(@(Nodes $root | Where-Object {$_.Current.Name -eq 'Добавить'}).Count){throw 'Global Add remains'}
}
function Open-Library($root,[string]$section) {
 Select-Item $root 'Библиотека' TreeItem
 (Named-All $root $section TabItem).GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern).Select()
 Start-Sleep -Milliseconds 180
}
$main=Top
[StudiumPackagedNative]::Initialize()
[StudiumPackagedNative]::Position([IntPtr]$main.Current.NativeWindowHandle,$OwnProcessId)
Start-Sleep -Milliseconds 250
try {
 Assert-Home $main
 if($Mode -eq 'fresh' -or $Mode -eq 'migration') {
  $main.GetCurrentPattern([System.Windows.Automation.WindowPattern]::Pattern).Close()
  Write-Output "PACKAGED_$($Mode.ToUpper())_PASS"
  exit 0
 }
 $resume=@(Nodes $main Button | Where-Object {$_.Current.Name -like 'Открыть журнал *'})
 if($resume.Count -ne 1){throw 'Single resume target missing'}
 $resume[0].GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
 Start-Sleep -Milliseconds 200
 Named $main 'Журнал' TabItem | Out-Null
 Invoke-Button $main 'Назад'
 Assert-Home $main
 $work=Named $main 'Работа' TreeItem
 Select-Item $main 'Работа' TreeItem
 Keys $main $work '{RIGHT}'
 Named $main 'Все группы' TreeItem | Out-Null
 Select-Item $main 'Все группы' TreeItem
 Keys $main (Nodes $main Table)[0] '{HOME}{ENTER}'
 Named $main 'Журнал' TabItem | Out-Null
 $grid=@(Nodes $main Table | Sort-Object {$_.Current.BoundingRectangle.Width} -Descending)[0]
 $gridPattern=$grid.GetCurrentPattern([System.Windows.Automation.GridPattern]::Pattern)
 $beforeCell=$gridPattern.GetItem(0,1).Current.BoundingRectangle.X
 Keys $main $grid '^{END}'
 if($gridPattern.GetItem(0,1).Current.BoundingRectangle.X -ge $beforeCell){throw 'Journal did not scroll horizontally'}
 # Qt UIA exports the main grid; native Qt geometry verifies the frozen overlay.
 Write-Output 'JOURNAL_HORIZONTAL_SCROLL_PASS'
 Invoke-Button $main 'Назад'
 if(@(Nodes $main TabItem | Where-Object {$_.Current.Name -eq 'Журнал'}).Count){throw 'Work Back did not return to list'}
 $library=Named $main 'Библиотека' TreeItem
 Select-Item $main 'Библиотека' TreeItem
 Keys $main $library '{RIGHT}'
 Select-Item $main 'Банк задач' TreeItem
 Named-All $main 'Банк задач' TabItem | Out-Null
 foreach($section in @('Домашнее задание','Банк задач','Рубежный контроль','Семинары','Лекции','Литература','Методические материалы')) {
  Open-Library $main $section
  Write-Output "LIBRARY_SECTION_PASS: $section"
 }
 Open-Library $main 'Домашнее задание'
 Select-Item $main 'Комплекты условий / общий PDF' TabItem
 Named $main 'Создать материал' Button | Out-Null
 Open-Library $main 'Банк задач'
 $search=(Nodes $main Edit)[0]
 $search.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).SetValue('Равновесие балки')
 Start-Sleep -Milliseconds 200
 Keys $main (Nodes $main Table)[0] '{HOME}{ENTER}'
 (Named-All $main 'Варианты схем' TabItem).GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern).Select()
 Start-Sleep -Milliseconds 180
 $familyGrid=(Nodes $main Table)[0].GetCurrentPattern([System.Windows.Automation.GridPattern]::Pattern)
 if($familyGrid.Current.RowCount -ne 3){throw 'Family variants missing'}
 Invoke-Button $main 'Назад'
 Open-Library $main 'Рубежный контроль'
 Keys $main (Nodes $main Table)[0] '{HOME}{ENTER}'
 Named $main 'Назначения студентам' TabItem | Out-Null
 Invoke-Button $main 'Назад'
 Open-Library $main 'Банк задач'
 Invoke-Button $main 'Добавить задачу'
 Named $main 'Сохранить' Button | Out-Null
 Named $main 'Отмена' Button | Out-Null
 Click-Button $main 'Дополнительно' CheckBox
 $scrolls=@(Nodes $main ScrollBar | Where-Object {$_.Current.BoundingRectangle.Height -gt $_.Current.BoundingRectangle.Width})
 if(-not $scrolls.Count){throw 'Expanded material has no vertical scroll'}
 $range=$scrolls[0].GetCurrentPattern([System.Windows.Automation.RangeValuePattern]::Pattern)
 $range.SetValue($range.Current.Maximum)
 Named $main 'Сохранить' Button | Out-Null
 Invoke-Button $main 'Отмена'
 Click-Button $main 'Настройки' CheckBox
 $theme=Named $main 'Тема оформления' ComboBox
 if($Mode -eq 'reopen') {
  $value=$theme.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).Current.Value
  if($value -ne 'Тёмная'){throw "Restored theme differs: $value"}
  Write-Output 'RESTORED_DARK_THEME_PASS'
 }
 Choose-Combo $main $theme 0
 Choose-Combo $main $theme 1
 Select-Item $main 'Главная' TreeItem
 Assert-Home $main
 $main.GetCurrentPattern([System.Windows.Automation.WindowPattern]::Pattern).Close()
 Write-Output "PACKAGED_$($Mode.ToUpper())_PASS"
} catch {
 Write-Output ('Own visible controls: '+ ((Nodes $main | Where-Object {$_.Current.ControlType.ProgrammaticName -notin @('ControlType.DataItem','ControlType.Header','ControlType.Pane','ControlType.Group')} | ForEach-Object {$_.Current.ControlType.ProgrammaticName+':'+$_.Current.Name}) -join ' | '))
 throw
}
