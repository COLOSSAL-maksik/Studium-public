param([Parameter(Mandatory)][int]$OwnProcessId,[ValidateSet('fresh','migration','workflow','reopen')][string]$Mode='workflow',[string]$DropImage,[string]$DropPdf,[string]$OutputRoot)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -ReferencedAssemblies System.Windows.Forms,System.Drawing -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Drawing;
using System.Windows.Forms;
public class StudiumPackagedNative {
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
 [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h,int command);
 [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
 [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint a,uint b,bool attach);
 [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
 [DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(IntPtr context);
 [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h,IntPtr after,int x,int y,int cx,int cy,uint flags);
 [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint p);
 [DllImport("user32.dll")] public static extern void mouse_event(uint flags,uint x,uint y,uint data,UIntPtr extra);
 [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h,IntPtr dc,uint flags);
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h,out Rect r);
 [StructLayout(LayoutKind.Sequential)] public struct Rect { public int l,t,r,b; }
 public static void Initialize() {SetProcessDpiAwarenessContext(new IntPtr(-4));}
 public static void Position(IntPtr h,int expected) {
  uint actual; GetWindowThreadProcessId(h,out actual);
  if(actual!=expected) throw new Exception("Only own process may be positioned");
  var area=Screen.PrimaryScreen.WorkingArea;
  SetWindowPos(h,IntPtr.Zero,area.X+20,area.Y+20,0,0,0x15);
 }
 public static void Focus(IntPtr h,int expected) {
  uint actual; GetWindowThreadProcessId(h,out actual);
  if(actual!=expected) throw new Exception("Only own process may receive focus");
  uint current=GetCurrentThreadId(), foreground=GetWindowThreadProcessId(GetForegroundWindow(),out actual);
  bool attached=current!=foreground && AttachThreadInput(current,foreground,true);
  try {ShowWindow(h,9); BringWindowToTop(h); SetForegroundWindow(h);} finally {if(attached) AttachThreadInput(current,foreground,false);}
 }
 public static void Capture(IntPtr h,int expected,string path) {
  uint actual; GetWindowThreadProcessId(h,out actual);
  if(actual!=expected) throw new Exception("Only own process may be captured");
  Rect rect; GetWindowRect(h,out rect);
  using(var bitmap=new Bitmap(rect.r-rect.l,rect.b-rect.t)) using(var g=Graphics.FromImage(bitmap)) {
   var dc=g.GetHdc(); try { if(!PrintWindow(h,dc,2)) throw new Exception("PrintWindow failed"); } finally {g.ReleaseHdc(dc);}
   bitmap.Save(path,System.Drawing.Imaging.ImageFormat.Png);
  }
 }

}
'@
function Top {
 $launcherId=$OwnProcessId
 for($i=0;$i -lt 300;$i++) {
  $processIds=@($launcherId)
  $children=@(Get-CimInstance Win32_Process -Filter "ParentProcessId = $launcherId" | Where-Object {$_.Name -eq 'Studium.exe'})
  foreach($child in $children){$processIds += [int]$child.ProcessId}
  foreach($processId in $processIds){
   $condition=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ProcessIdProperty,[int]$processId)
   $windows=[System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children,$condition)
   foreach($w in $windows){if($w.Current.Name -eq 'Studium'){$script:OwnProcessId=[int]$processId; return $w}}
  }
  Start-Sleep -Milliseconds 100
 }
 foreach($processId in $processIds){
  $condition=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ProcessIdProperty,[int]$processId)
  $windows=[System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children,$condition)
  foreach($w in $windows){Write-Output "Own window: $($w.Current.Name)"}
 }
 throw 'Own Studium window missing'
}
function Nodes($root,[string]$type='') {
 @($root.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition) | Where-Object { -not $_.Current.IsOffscreen -and (-not $type -or $_.Current.ControlType.ProgrammaticName -eq "ControlType.$type") })
}
function Named($root,[string]$name,[string]$type='') {
 $found=@(Nodes $root $type | Where-Object {$_.Current.Name -eq $name})
 if($found.Count -ne 1){throw "Expected one '$name' $type, found $($found.Count)"}
 $found[0]
}
function Select-Item($root,[string]$name,[string]$type){
 if($type -eq 'TreeItem') {
  $item=Named $root $name $type
  [StudiumPackagedNative]::Focus([IntPtr]$root.Current.NativeWindowHandle,$OwnProcessId)
  $actual=[uint32]0
  [StudiumPackagedNative]::GetWindowThreadProcessId([StudiumPackagedNative]::GetForegroundWindow(),[ref]$actual) | Out-Null
  if($actual -ne $OwnProcessId){throw 'Own exe must have pointer focus'}
  $bounds=$item.Current.BoundingRectangle
  [System.Windows.Forms.Cursor]::Position=[System.Drawing.Point]::new([int]($bounds.X+$bounds.Width/2),[int]($bounds.Y+$bounds.Height/2))
  [StudiumPackagedNative]::mouse_event(2,0,0,0,[UIntPtr]::Zero)
  [StudiumPackagedNative]::mouse_event(4,0,0,0,[UIntPtr]::Zero)
  Start-Sleep -Milliseconds 180
  return
 }
 (Named $root $name $type).GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern).Select()
 Start-Sleep -Milliseconds 170
}
function Invoke-Button($root,[string]$name){
 (Named $root $name Button).GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
 Start-Sleep -Milliseconds 170
}
function Click-Button($root,[string]$name) {
 $button=Named $root $name Button
 [StudiumPackagedNative]::Focus([IntPtr]$root.Current.NativeWindowHandle,$OwnProcessId)
 $actual=[uint32]0
 [StudiumPackagedNative]::GetWindowThreadProcessId([StudiumPackagedNative]::GetForegroundWindow(),[ref]$actual) | Out-Null
 if($actual -ne $OwnProcessId){throw 'Own exe must have pointer focus'}
 $bounds=$button.Current.BoundingRectangle
 [System.Windows.Forms.Cursor]::Position=[System.Drawing.Point]::new([int]($bounds.X+$bounds.Width/2),[int]($bounds.Y+$bounds.Height/2))
 [StudiumPackagedNative]::mouse_event(2,0,0,0,[UIntPtr]::Zero)
 [StudiumPackagedNative]::mouse_event(4,0,0,0,[UIntPtr]::Zero)
 Start-Sleep -Milliseconds 200
}
function Keys($root,$target,[string]$keys){
 [StudiumPackagedNative]::Focus([IntPtr]$root.Current.NativeWindowHandle,$OwnProcessId)
 $target.SetFocus()
 $actual=[uint32]0
 [StudiumPackagedNative]::GetWindowThreadProcessId([StudiumPackagedNative]::GetForegroundWindow(),[ref]$actual) | Out-Null
 if($actual -ne $OwnProcessId){throw 'Own exe must have keyboard focus'}
 [System.Windows.Forms.SendKeys]::SendWait($keys)
 Start-Sleep -Milliseconds 220
}
function Capture($root,[string]$name){
 [StudiumPackagedNative]::Capture([IntPtr]$root.Current.NativeWindowHandle,$OwnProcessId,(Join-Path $OutputRoot "iteration2-exe-$name.png"))
}
function Choose-Combo($root,$target,[int]$index) {
 [StudiumPackagedNative]::Focus([IntPtr]$root.Current.NativeWindowHandle,$OwnProcessId)
 $target.SetFocus()
 Start-Sleep -Milliseconds 180
 $bounds=$target.Current.BoundingRectangle
 if($bounds.Width -le 0 -or $bounds.Height -le 0){throw 'Own combo outside viewport'}
 [System.Windows.Forms.Cursor]::Position=[System.Drawing.Point]::new([int]($bounds.X+$bounds.Width/2),[int]($bounds.Y+$bounds.Height/2))
 [StudiumPackagedNative]::mouse_event(2,0,0,0,[UIntPtr]::Zero)
 [StudiumPackagedNative]::mouse_event(4,0,0,0,[UIntPtr]::Zero)
 Start-Sleep -Milliseconds 180
 $expand=$target.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern)
 if($expand.Current.ExpandCollapseState -ne [System.Windows.Automation.ExpandCollapseState]::Expanded){throw 'Own combo popup did not open'}
 $keys='{HOME}'+('{DOWN}'*$index)+'{ENTER}'
 [System.Windows.Forms.SendKeys]::SendWait($keys)
 Start-Sleep -Milliseconds 250
}
function Named-All($root,[string]$name,[string]$type) {
 $found=@($root.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition) | Where-Object {$_.Current.Name -eq $name -and $_.Current.ControlType.ProgrammaticName -eq "ControlType.$type"})
 if($found.Count -ne 1){throw "Expected one own '$name' $type, found $($found.Count)"}
 $found[0]
}
function Owned-Dialog([string]$name) {
 $condition=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ProcessIdProperty,$OwnProcessId)
 for($i=0;$i -lt 50;$i++) {
  $windows=[System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children,$condition)
  foreach($w in $windows){
   $candidates=@($w)+@($w.FindAll([System.Windows.Automation.TreeScope]::Descendants,$condition))
   foreach($candidate in $candidates){
    if($candidate.Current.ControlType.ProgrammaticName -eq 'ControlType.Window' -and $candidate.Current.Name -like $name -and $candidate.Current.NativeWindowHandle -ne 0){return $candidate}
   }
  }
  Start-Sleep -Milliseconds 100
 }
 throw "Own dialog '$name' missing"
}
function Click-Cell($root,[int]$row,[int]$column) {
 $grid=@(Nodes $root Table | Sort-Object { $_.Current.BoundingRectangle.Width } -Descending)[0]
 $pattern=$grid.GetCurrentPattern([System.Windows.Automation.GridPattern]::Pattern)
 $cell=$pattern.GetItem($row,$column)
 [StudiumPackagedNative]::Focus([IntPtr]$root.Current.NativeWindowHandle,$OwnProcessId)
 $bounds=$cell.Current.BoundingRectangle
 if($bounds.Width -le 0 -or $bounds.Height -le 0){throw 'Cell outside own viewport'}
 [System.Windows.Forms.Cursor]::Position=[System.Drawing.Point]::new([int]($bounds.X+$bounds.Width/2),[int]($bounds.Y+$bounds.Height/2))
 [StudiumPackagedNative]::mouse_event(2,0,0,0,[UIntPtr]::Zero)
 [StudiumPackagedNative]::mouse_event(4,0,0,0,[UIntPtr]::Zero)
 Start-Sleep -Milliseconds 200
}
$main=Top
[StudiumPackagedNative]::Initialize()
[StudiumPackagedNative]::Position([IntPtr]$main.Current.NativeWindowHandle,$OwnProcessId)
Start-Sleep -Milliseconds 250
try {
 if($Mode -eq 'fresh' -or $Mode -eq 'migration') {
  if(@(Nodes $main Text | Where-Object {$_.Current.Name -eq 'Studium'}).Count -ne 1){throw 'Main content absent'}
  Capture $main $Mode
  $main.GetCurrentPattern([System.Windows.Automation.WindowPattern]::Pattern).Close()
  Write-Output "PACKAGED_$($Mode.ToUpper())_MAINWINDOW_PASS"
  exit 0
 }
 Select-Item $main 'Дисциплины' TreeItem
 Keys $main (Nodes $main Table)[0] '{HOME}{ENTER}'
 Select-Item $main 'Рабочие программы' TabItem
 Keys $main (Nodes $main Table)[0] '{HOME}{ENTER}'
 Select-Item $main 'Модули / учебный план' TabItem
 Capture $main "program-modules-$Mode"
 Invoke-Button $main '← Назад'
 Invoke-Button $main '← Назад'
 Invoke-Button $main 'Настройки'
 $theme=Named $main 'Тема оформления' ComboBox
 Keys $main $theme '{END}'
 Capture $main "dark-$Mode"
 Keys $main $theme '{HOME}'
 Select-Item $main 'Главная' TreeItem
 Capture $main "home-$Mode"
 Select-Item $main 'Библиотека' TreeItem
 Select-Item $main 'Банк задач' TabItem
 Keys $main (Nodes $main Table)[0] '{HOME}{ENTER}'
 Select-Item $main 'Правильный ответ' TabItem
 if(@(Nodes $main Edit | Where-Object {$_.Current.Name -like '*Синтетический эталон*'}).Count -eq 0){
  # Qt exposes plain text via ValuePattern, not necessarily its accessible Name.
  $texts=@(Nodes $main Edit | ForEach-Object {try {$_.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).Current.Value} catch {''}})
  if(-not ($texts -match 'Синтетический эталон')){throw 'Problem teacher answer absent'}
 }
 Invoke-Button $main '← Назад'
 Select-Item $main 'Литература' TabItem
 Keys $main (Nodes $main Table)[0] '{HOME}{ENTER}'
 Start-Sleep -Milliseconds 600
 Keys $main (Nodes $main Table)[0] '{HOME}{ENTER}'
 Start-Sleep -Milliseconds 600
 Capture $main "pdf-$Mode"
 Invoke-Button $main '← Назад'
 if($Mode -eq 'workflow') {
  Click-Button $main 'Выбрать файлы…'
  $condition=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ProcessIdProperty,$OwnProcessId)
  $picker=$null
  for($i=0;$i -lt 50 -and -not $picker;$i++) {
   $windows=$main.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition)
   foreach($w in $windows){if($w.Current.Name -eq 'Добавить файлы' -and $w.Current.ControlType.ProgrammaticName -eq 'ControlType.Window'){$picker=$w; break}}
   if(-not $picker){Start-Sleep -Milliseconds 100}
  }
  if(-not $picker){throw 'Own native picker absent'}
  try {
   $field=Named $picker 'Имя файла:' Edit
   $field.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).SetValue('"'+$DropImage+'" "'+$DropPdf+'"')
   Keys $picker $field '{ENTER}'
  } catch {
   (Nodes $picker | ForEach-Object {"$($_.Current.ControlType.ProgrammaticName) | $($_.Current.Name)"}) | Set-Content -LiteralPath (Join-Path $OutputRoot 'iteration2-picker.txt') -Encoding UTF8
   throw
  }
  Start-Sleep -Milliseconds 900
  Capture $main 'picker-files'
 }
 Invoke-Button $main '← Назад'
 Select-Item $main 'Работа' TreeItem
 Keys $main (Nodes $main Table)[0] '{HOME}{ENTER}'
 Select-Item $main 'Журнал' TabItem
 Capture $main "journal-$Mode"
 if($Mode -eq 'workflow') {
  Click-Cell $main 0 7
  $attempt=Owned-Dialog 'Записать попытку'
  Choose-Combo $attempt (Named-All $attempt 'Результат попытки' ComboBox) 2
  Capture $attempt 'homework-attempt'
  Click-Button $attempt 'Сохранить'
  Click-Cell $main 0 8
  Select-Item $main 'Результаты частей работы' TabItem
  Invoke-Button $main 'Записать результат части'
  $check=Owned-Dialog 'Попытка 1*'
  Choose-Combo $check (Named-All $check 'Результат части' ComboBox) 1
  Choose-Combo $check (Named-All $check 'Определение знака изгибающего момента · результат навыка' ComboBox) 3
  Capture $check 'control-task-skill'
  Click-Button $check 'Сохранить'
  Click-Button $main 'Записать результат части'
  $emptyCheck=Owned-Dialog 'Попытка 1*'
  Click-Button $emptyCheck 'Сохранить'
  $warning=Owned-Dialog 'Не удалось выполнить действие'
  if(@(Nodes $warning Text | Where-Object {$_.Current.Name -eq 'Укажите результат части или балл.'}).Count -ne 1){throw 'Expected empty-result validation absent'}
  Capture $warning 'empty-result-validation'
  $dismiss=@(Nodes $warning Button | Where-Object {$_.Current.Name -ne 'Close'})
  if($dismiss.Count -ne 1){throw 'Expected one own validation dismiss button'}
  Click-Button $warning $dismiss[0].Current.Name
  Click-Button $emptyCheck 'Отмена'
  Invoke-Button $main '← Назад'
 }
 Select-Item $main 'Аналитика' TabItem
 Select-Item $main 'Прогресс' TabItem
 Capture $main "radial-$Mode"
 Select-Item $main 'Графики' TabItem
 Select-Item $main 'Сдачи по неделям' TabItem
 Capture $main "charts-$Mode"
 Select-Item $main 'Варианты' TabItem
 Select-Item $main 'Сохранённые наборы' TabItem
 Invoke-Button $main 'Открыть набор'
 Keys $main (Nodes $main Table)[0] '{HOME}{ENTER}'
 Select-Item $main 'Файлы (снимок)' TabItem
 Start-Sleep -Milliseconds 600
 Keys $main (Nodes $main Table)[0] '{HOME}{ENTER}'
 Start-Sleep -Milliseconds 500
 Capture $main "image-$Mode"
 Invoke-Button $main '← Назад'
 Invoke-Button $main '← Назад'
 $main.GetCurrentPattern([System.Windows.Automation.WindowPattern]::Pattern).Close()
 Write-Output "PACKAGED_$($Mode.ToUpper())_LIBRARIES_BACK_PDF_IMAGE_QTCHARTS_SNAPSHOT_PASS"
} catch {
 (Nodes $main | ForEach-Object {"$($_.Current.ControlType.ProgrammaticName) | $($_.Current.Name)"}) | Set-Content -LiteralPath (Join-Path $OutputRoot "iteration2-uia-$Mode.txt") -Encoding UTF8
 throw
}
