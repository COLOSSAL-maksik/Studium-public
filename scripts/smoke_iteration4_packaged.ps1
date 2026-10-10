param([Parameter(Mandatory)][int]$OwnProcessId,[ValidateSet('fresh','migration','workflow','reopen')][string]$Mode='workflow')
$ErrorActionPreference = 'Stop'
$InputPdf=$env:STUDIUM_QA_PDF
$tracePath = if ($env:STUDIUM_QA_TRACE) { $env:STUDIUM_QA_TRACE } else { Join-Path $PSScriptRoot '../tmp/iteration4-native-trace.txt' }
Start-Transcript -Path $tracePath -Force | Out-Null
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
# Reuse the existing PID-restricted native QA helpers, without its old scenario.
$source=[IO.File]::ReadAllText((Join-Path $PSScriptRoot 'smoke_iteration2_5_packaged.ps1'),[Text.Encoding]::UTF8)
$helpers=$source.Substring($source.IndexOf('$ErrorActionPreference'),$source.IndexOf('$main=Top')-$source.IndexOf('$ErrorActionPreference'))
if($env:STUDIUM_QA_SOURCE -eq '1'){$helpers=$helpers.Replace("'Studium.exe'","'python.exe'")}
$helpers=$helpers.Replace('[StudiumPackagedNative]::Focus([IntPtr]$root.Current.NativeWindowHandle,$OwnProcessId)','Ensure-QAFocus $root')
$helpers=$helpers.Replace('$target.SetFocus()','$target.SetFocus(); Start-Sleep -Milliseconds 120')
Invoke-Expression $helpers
function Ensure-QAFocus($root) {
 for($attempt=0;$attempt -lt 10;$attempt++){
  [StudiumPackagedNative]::Focus([IntPtr]$root.Current.NativeWindowHandle,$OwnProcessId)
  Start-Sleep -Milliseconds 100
  $actual=[uint32]0
  [StudiumPackagedNative]::GetWindowThreadProcessId([StudiumPackagedNative]::GetForegroundWindow(),[ref]$actual) | Out-Null
  if($actual -eq $OwnProcessId){return}
 }
 throw 'Own QA window could not acquire focus; no input was sent'
}
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
 if($Mode -eq 'workflow') {
  Click-Cell $main 0 6
  Keys $main (Nodes $main Table)[0] '+{DOWN}+{DOWN}'
  Invoke-Button $main 'Отметить выбранных (3)'
  Write-Output 'ATTENDANCE_THREE_SELECTED_PASS'
 }
 Select-Item $main 'Студенты' TabItem
 Keys $main (Nodes $main Table)[0] '{HOME}'
 Click-Cell $main 0 0
 Click-Cell $main 0 0
 Select-Item $main 'Работы' TabItem
 foreach($category in @('Рубежный контроль','Экзамен','Домашнее задание')) {Select-Item $main $category TabItem}
 $workTable=@(Nodes $main Table | Where-Object {$_.GetCurrentPattern([System.Windows.Automation.GridPattern]::Pattern).Current.ColumnCount -eq 5})[0]
 $workGrid=$workTable.GetCurrentPattern([System.Windows.Automation.GridPattern]::Pattern)
 $workRow=-1
 for($row=0;$row -lt $workGrid.Current.RowCount;$row++){
  if($workGrid.GetItem($row,2).Current.Name -match '^[3-9]'){$workRow=$row;break}
 }
 if($workRow -lt 0){throw 'Work with multiple Attempts missing'}
 Keys $main $workTable ('{HOME}'+('{DOWN}'*$workRow))
 $attemptTable=@(Nodes $main Table | Where-Object {
  $g=$_.GetCurrentPattern([System.Windows.Automation.GridPattern]::Pattern)
  $g.Current.ColumnCount -eq 6 -and $g.Current.RowCount -ge 3
 })[0]
 if(-not $attemptTable){throw 'Full Attempt history missing'}
 Keys $main $attemptTable '{HOME}'
 Invoke-Button $main 'Открыть попытку'
 Select-Item $main 'Файлы' TabItem
 Start-Sleep -Milliseconds 450
 $fileTable=(Nodes $main Table)[0]
 $fileGrid=$fileTable.GetCurrentPattern([System.Windows.Automation.GridPattern]::Pattern)
 $pdfRow=-1
 for($row=0;$row -lt $fileGrid.Current.RowCount;$row++){
  if($fileGrid.GetItem($row,4).Current.Name -eq 'application/pdf'){$pdfRow=$row;break}
 }
 if($pdfRow -lt 0){throw 'Managed PDF attachment absent'}
 Keys $main $fileTable ('{HOME}'+('{DOWN}'*$pdfRow))
 Invoke-Button $main 'Просмотреть'
 Start-Sleep -Milliseconds 650
 if(-not @(Nodes $main Text | Where-Object {$_.Current.Name -like '*application/pdf*'}).Count){throw 'Attempt PDF metadata absent'}
 Invoke-Button $main 'Назад'
 Invoke-Button $main 'Назад'
 Select-Item $main 'Прогресс' TabItem
 foreach($category in @('Рубежный контроль','Домашнее задание')) {Select-Item $main $category TabItem}
 Write-Output 'STUDENT_WORKS_ATTEMPT_PDF_PROGRESS_PASS'
 Invoke-Button $main 'Назад'
 Invoke-Button $main 'Назад'
 Assert-Home $main
 $work=Named $main 'Работа' TreeItem
 Select-Item $main 'Работа' TreeItem
 Keys $main $work '{RIGHT}'
 Named $main 'Все группы' TreeItem | Out-Null
 Select-Item $main 'Все группы' TreeItem
 Keys $main (Nodes $main Table)[0] '{HOME}{ENTER}'
 Named $main 'Журнал' TabItem | Out-Null
 Select-Item $main 'Журнал' TabItem
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
 foreach($section in @('Литература','Домашнее задание')) {
  Open-Library $main $section
  Keys $main (Nodes $main Table)[0] '{HOME}{ENTER}'
  Invoke-Button $main 'Назад'
  Write-Output "MATERIAL_OPEN_PASS: $section"
 }
 if($Mode -eq 'workflow') {
  Open-Library $main 'Семинары'
  Invoke-Button $main 'Создать материал'
  (Nodes $main Edit)[0].GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).SetValue('Native QA seminar')
  $plan=@(Nodes $main Edit | Where-Object {$_.Current.BoundingRectangle.Height -gt 60})[0]
  $plan.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).SetValue('Native synthetic seminar plan')
  Select-Item $main 'Задачи' TabItem
  Keys $main (Named-All $main 'Добавить из банка задач' Button) ' '
  $picker=Owned-Dialog 'Добавить из банка задач'
  Keys $picker (Nodes $picker Table)[0] '{HOME}'
  Click-Cell $picker 0 0
  $selected=$picker.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.SelectionItemPattern]::IsSelectedProperty,$true))
  if(-not $selected.Count){throw 'Bank task was not selected'}
  Click-Button $picker 'Добавить выбранные'
  Keys $main (Named-All $main 'Создать новую задачу' Button) ' '
  $problem=Owned-Dialog 'Новая задача для семинара'
  (Nodes $problem Edit)[0].GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).SetValue('Native QA new task')
  Click-Button $problem 'Сохранить'
  Select-Item $main 'Файлы' TabItem
  Keys $main (Named-All $main 'Выбрать файлы…' Button) ' '
  $filePicker=Owned-Dialog 'Добавить файлы'
  $field=Named $filePicker 'Имя файла:' Edit
  $field.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).SetValue($InputPdf)
  Keys $filePicker $field '{ENTER}'
  Invoke-Button $main 'Сохранить'
  Invoke-Button $main 'Назад'
  Write-Output 'SEMINAR_CREATE_BANK_NEW_TASK_FILE_PICKER_PASS'
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
 $scrolls=@(Nodes $main ScrollBar | Where-Object {$_.Current.BoundingRectangle.Height -gt $_.Current.BoundingRectangle.Width})
 if(-not $scrolls.Count){throw 'Expanded material has no vertical scroll'}
 $range=$scrolls[0].GetCurrentPattern([System.Windows.Automation.RangeValuePattern]::Pattern)
 $range.SetValue($range.Current.Maximum)
 Named $main 'Сохранить' Button | Out-Null
 Invoke-Button $main 'Отмена'
 # A native selection resolves the image from managed storage, after sources were removed.
 Open-Library $main 'Банк задач'
 $search=(Nodes $main Edit)[0]
 $search.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).SetValue('Равновесие балки')
 Start-Sleep -Milliseconds 250
 Keys $main (Nodes $main Table)[0] '{HOME}'
 Choose-Combo $main (Named $main 'Вариант условия' ComboBox) 1
 Start-Sleep -Milliseconds 400
 Named $main 'Изображение условия' | Out-Null
 Write-Output 'MANAGED_IMAGE_SOURCE_REMOVED_PREVIEW_PASS'
 Invoke-Button $main 'Справка'
 Named $main 'Статья справки' | Out-Null
 $helpSearch=Named $main 'Поиск в справке' Edit
 $helpSearch.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).SetValue('переделка всегда')
 Start-Sleep -Milliseconds 200
 $results=@(Nodes $main ListItem)
 if(-not $results.Count){throw 'Help search has no article'}
 Write-Output 'OFFLINE_HELP_SEARCH_NAVIGATION_PASS'
 $period=Named $main 'Учебный период' ComboBox
 Choose-Combo $main $period 2
 $periods=Owned-Dialog 'Учебные периоды'
 Named $periods 'Добавить' Button | Out-Null
 Keys $periods (Nodes $periods Table)[0] '{ESC}'
 Write-Output 'PERIOD_SELECTOR_MANAGEMENT_PASS'
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
