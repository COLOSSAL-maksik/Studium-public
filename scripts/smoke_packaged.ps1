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
 $condition=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ProcessIdProperty,$OwnProcessId)
 for($i=0;$i -lt 100;$i++) {
  $windows=[System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children,$condition)
  foreach($w in $windows){if($w.Current.Name -eq 'Studium'){return $w}}
  Start-Sleep -Milliseconds 100
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
 [StudiumPackagedNative]::Capture([IntPtr]$root.Current.NativeWindowHandle,$OwnProcessId,(Join-Path $OutputRoot "phase66-exe-$name.png"))
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
 Select-Item $main 'Материалы' TreeItem
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
   (Nodes $picker | ForEach-Object {"$($_.Current.ControlType.ProgrammaticName) | $($_.Current.Name)"}) | Set-Content -LiteralPath (Join-Path $OutputRoot 'phase66-picker.txt') -Encoding UTF8
   throw
  }
  Start-Sleep -Milliseconds 900
  Capture $main 'picker-files'
 }
 Invoke-Button $main '← Назад'
 Select-Item $main 'Группы' TreeItem
 Keys $main (Nodes $main Table)[0] '{HOME}{ENTER}'
 Select-Item $main 'Аналитика' TabItem
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
 (Nodes $main | ForEach-Object {"$($_.Current.ControlType.ProgrammaticName) | $($_.Current.Name)"}) | Set-Content -LiteralPath (Join-Path $OutputRoot "phase66-uia-$Mode.txt") -Encoding UTF8
 throw
}
