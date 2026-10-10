{ Shared by the shipping installer and the isolated native regression fixture.
  GuardDataRoot and OwnershipKey are supplied by the including script. }
#define KernelImport(Name) Name + "@" + "kernel32.dll stdcall"
const
  ReceiptName = 'studium-payload.txt';
  ReceiptHeader = 'STUDIUM-PAYLOAD-1';
  ReceiptRegistryValue = 'StudiumPayloadSHA256';
  GuardError = 'Studium: небезопасный каталог или изменённый payload. Выберите отдельный каталог программы; прежняя установка должна иметь исправный список файлов. / Unsafe directory or changed payload; installation stopped.';

type
  TGuardAttributes = record
    Attributes: LongWord;
    ReparseTag: LongWord;
  end;

function GuardCreateFile(Name: String; Access, Share: LongWord; Security: Integer;
  Creation, Flags: LongWord; Template: THandle): THandle;
  external '{#KernelImport("CreateFileW")}';
function GuardCloseHandle(Handle: THandle): Boolean;
  external '{#KernelImport("CloseHandle")}';
function GuardFinalPath(Handle: THandle; Buffer: String; Size, Flags: LongWord): LongWord;
  external '{#KernelImport("GetFinalPathNameByHandleW")}';
function GuardFileAttributes(Name: String): LongWord;
  external '{#KernelImport("GetFileAttributesW")}';
function GuardHandleAttributes(Handle: THandle; InfoClass: Integer;
  var Info: TGuardAttributes; Size: LongWord): Boolean;
  external '{#KernelImport("GetFileInformationByHandleEx")}';
function GuardLastError(): LongWord;
begin
  { Inno can make API calls between statements: use its captured DLL error. }
  Result := DLLGetLastError;
end;

var
  PinnedHandles: array of THandle;
  PinnedNames, NewPayload, OldPayload, ObsoleteFiles: TStringList;
  ProgramLocation, RejectionReason, GuardCheckpoint: String;
  Prepared: Boolean;

function VersionPart(Version: String; PartIndex: Integer): Integer;
var
  I, Index: Integer;
  Part: String;
begin
  Result := -1;
  Index := 0;
  Part := '';
  for I := 1 to Length(Version) + 1 do begin
    if I > Length(Version) then begin
      if Index <> 2 then RaiseException(GuardError);
    end else if Copy(Version, I, 1) <> '.' then begin
      if Pos(Copy(Version, I, 1), '0123456789') = 0 then RaiseException(GuardError);
      Part := Part + Copy(Version, I, 1);
      Continue;
    end;
    if (Part = '') or (Length(Part) > 5) then RaiseException(GuardError);
    if StrToInt(Part) > 65535 then RaiseException(GuardError);
    if Index = PartIndex then Result := StrToInt(Part);
    Index := Index + 1;
    Part := '';
  end;
  if (Index <> 3) or (Result < 0) then RaiseException(GuardError);
end;

procedure CheckVersion(Previous: String);
var
  I, CurrentPart, PreviousPart: Integer;
  Order: Integer;
begin
  Order := 0;
  for I := 0 to 2 do begin
    CurrentPart := VersionPart(GuardAppVersion, I);
    PreviousPart := VersionPart(Previous, I);
    if Order = 0 then begin
      if CurrentPart < PreviousPart then Order := -1;
      if CurrentPart > PreviousPart then Order := 1;
    end;
  end;
  if Order < 0 then begin
    RejectionReason := 'Studium: установка более старой версии запрещена / downgrade is not supported.';
    RaiseException(RejectionReason);
  end;
end;

procedure ReleasePins();
var
  I: Integer;
begin
  for I := 0 to GetArrayLength(PinnedHandles) - 1 do
    GuardCloseHandle(PinnedHandles[I]);
  SetArrayLength(PinnedHandles, 0);
  if PinnedNames <> nil then PinnedNames.Clear;
end;

procedure Refuse();
begin
  Log('STUDIUM_GUARD_REFUSAL ' + GuardCheckpoint);
  RaiseException(GuardError);
end;

function CleanPath(Path: String): String;
var
  I, Start: Integer;
  Part, Remainder, BadCharacters: String;
begin
  Result := ExpandFileName(Path);
  { Local drive paths only; reject UNC/device namespaces and ambiguous drive-relative input. }
  if (Length(Result) < 3) or (Copy(Result, 2, 1) <> ':') or (Copy(Result, 3, 1) <> '\') then begin
    Log('STUDIUM_GUARD_PATH_NAMESPACE');
    Refuse;
  end;
  while (Length(Result) > 3) and (Copy(Result, Length(Result), 1) = '\') do
    Delete(Result, Length(Result), 1);
  { In Pascal Script Pos can select ANSI arguments and turn Cyrillic into '?'.
    Inno's native Unicode helper tests the actual path without changing it. }
  Remainder := Result;
  Delete(Remainder, 1, 3);
  BadCharacters := ':/*?"<>|';
  for I := 1 to Length(BadCharacters) do
    if StringChangeEx(Remainder, Copy(BadCharacters, I, 1), '', True) > 0 then begin
      Log('STUDIUM_GUARD_PATH_CHARACTER');
      Refuse;
    end;
  { Win32 silently trims trailing dots/spaces, even for currently missing components. }
  Start := 4;
  for I := 4 to Length(Result) + 1 do begin
    if I > Length(Result) then Part := Copy(Result, Start, I - Start)
    else if Copy(Result, I, 1) = '\' then Part := Copy(Result, Start, I - Start)
    else Continue;
    if Part <> '' then
      if (Copy(Part, Length(Part), 1) = '.') or (Copy(Part, Length(Part), 1) = ' ') then Refuse;
    Start := I + 1;
  end;
end;

function ParentPath(Path: String): String;
begin
  Path := CleanPath(Path);
  { ExtractFileDir must never turn a drive root into drive-relative C:. }
  if Length(Path) = 3 then begin
    Result := Path;
    Exit;
  end;
  Result := CleanPath(ExtractFileDir(Path));
end;

function ExistingAttributes(Path: String): LongWord;
var
  ErrorCode: LongWord;
begin
  Result := GuardFileAttributes(Path);
  if Result = $FFFFFFFF then begin
    ErrorCode := GuardLastError;
    Log('STUDIUM_GUARD_ATTRIBUTE_ERROR ' + IntToStr(ErrorCode));
    if (ErrorCode <> 2) and (ErrorCode <> 3) then Refuse;
  end;
end;

function RealDirectory(Path: String; RejectLinks, Pin: Boolean): String;
var
  Handle: THandle;
  Info: TGuardAttributes;
  Buffer: String;
  Count, Flags: LongWord;
  Index: Integer;
begin
  Flags := $02000000; { FILE_FLAG_BACKUP_SEMANTICS }
  if RejectLinks then Flags := Flags or $00200000; { OPEN_REPARSE_POINT }
  { READ_ATTRIBUTES, SHARE_READ: pin directories against replacement/redirection. }
  Handle := GuardCreateFile(Path, $80, 1, 0, 3, Flags, 0);
  if Handle = THandle(-1) then begin
    Log('STUDIUM_GUARD_OPEN_ERROR ' + IntToStr(GuardLastError));
    Refuse;
  end;
  try
    if not GuardHandleAttributes(Handle, 9, Info, 8) then begin
      Log('STUDIUM_GUARD_HANDLE_ATTRIBUTE_ERROR ' + IntToStr(GuardLastError));
      Refuse;
    end;
    if (Info.Attributes and $10) = 0 then begin
      Log('STUDIUM_GUARD_EXPECTED_DIRECTORY');
      Refuse;
    end;
    if RejectLinks and ((Info.Attributes and $400) <> 0) then begin
      Log('STUDIUM_GUARD_REPARSE_DIRECTORY');
      Refuse;
    end;
    SetLength(Buffer, 32768);
    Count := GuardFinalPath(Handle, Buffer, Length(Buffer), 0);
    if Count = 0 then Log('STUDIUM_GUARD_FINAL_PATH_ERROR ' + IntToStr(GuardLastError));
    if (Count = 0) or (Count >= LongWord(Length(Buffer))) then Refuse;
    SetLength(Buffer, Count);
    { Normalized DOS volume name, including expansion of existing 8.3 components. }
    if Copy(Buffer, 1, 4) <> '\\?\' then begin
      Log('STUDIUM_GUARD_FINAL_NAMESPACE');
      Refuse;
    end;
    Result := CleanPath(Copy(Buffer, 5, Length(Buffer)));
    if Pin and (PinnedNames.IndexOf(Lowercase(Result)) < 0) then begin
      Index := GetArrayLength(PinnedHandles);
      SetArrayLength(PinnedHandles, Index + 1);
      PinnedHandles[Index] := Handle;
      PinnedNames.Add(Lowercase(Result));
      Handle := THandle(-1);
    end;
  finally
    if Handle <> THandle(-1) then GuardCloseHandle(Handle);
  end;
end;

function CanonicalDirectory(Path: String; RejectLinks, Pin: Boolean): String;
var
  Current, Tail, Parent, Existing: String;
  Attributes: LongWord;
begin
  Current := CleanPath(Path);
  Tail := '';
  Attributes := ExistingAttributes(Current);
  while Attributes = $FFFFFFFF do begin
    Parent := ParentPath(Current);
    if CompareText(Parent, Current) = 0 then Refuse;
    Tail := ExtractFileName(Current) + '\' + Tail;
    Current := Parent;
    Attributes := ExistingAttributes(Current);
  end;
  Existing := Current;
  Result := AddBackslash(RealDirectory(Existing, RejectLinks, Pin)) + Tail;
  Result := CleanPath(Result);
  if RejectLinks then begin
    { Every existing ancestor, not just the nearest one. Fail on junctions/mount points. }
    while True do begin
      RealDirectory(Current, True, Pin);
      Parent := ParentPath(Current);
      if CompareText(Parent, Current) = 0 then Break;
      Current := Parent;
    end;
  end;
end;

function Overlaps(Left, Right: String): Boolean;
begin
  Left := AddBackslash(Left);
  Right := AddBackslash(Right);
  Result := (CompareText(Copy(Left, 1, Length(Right)), Right) = 0) or
    (CompareText(Copy(Right, 1, Length(Left)), Left) = 0);
end;

function PayloadPath(Entry: String): String;
begin
  Result := Copy(Entry, 66, Length(Entry));
end;

function DevicePart(Part: String): Boolean;
var
  Dot: Integer;
begin
  Part := Uppercase(Part);
  Dot := Pos('.', Part);
  if Dot > 0 then Part := Copy(Part, 1, Dot - 1);
  Result := (Part = 'CON') or (Part = 'PRN') or (Part = 'AUX') or (Part = 'NUL');
  if Length(Part) = 4 then
    Result := Result or (((Copy(Part, 1, 3) = 'COM') or (Copy(Part, 1, 3) = 'LPT')) and
      (Pos(Copy(Part, 4, 1), '123456789') > 0));
end;

function SafeRelativePath(Path: String): Boolean;
var
  I: Integer;
  Part: String;
  Boundary: Boolean;
begin
  Result := False;
  if (Path = '') or (Copy(Path, 1, 1) = '\') or (Copy(Path, Length(Path), 1) = '\') then Exit;
  Part := '';
  for I := 1 to Length(Path) + 1 do begin
    Boundary := I > Length(Path);
    if not Boundary then Boundary := Copy(Path, I, 1) = '\';
    if Boundary then begin
      if (Part = '') or (Part = '.') or (Part = '..') then Exit;
      if (Copy(Part, Length(Part), 1) = '.') or (Copy(Part, Length(Part), 1) = ' ') then Exit;
      if DevicePart(Part) then Exit;
      Part := '';
    end else begin
      if Pos(Copy(Path, I, 1), 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.+ -') = 0 then Exit;
      Part := Part + Copy(Path, I, 1);
    end;
  end;
  Result := (CompareText(Path, 'Studium.exe') = 0) or
    (CompareText(Copy(Path, 1, 10), '_internal\') = 0);
end;

function ValidEntry(Entry: String): Boolean;
var
  I: Integer;
begin
  Result := False;
  if Length(Entry) < 67 then Exit;
  if Copy(Entry, 65, 1) <> ' ' then Exit;
  for I := 1 to 64 do
    if Pos(Copy(Entry, I, 1), '0123456789abcdef') = 0 then Exit;
  Result := SafeRelativePath(PayloadPath(Entry));
end;

function FindOwned(Files: TStringList; Path: String): Integer;
var
  I: Integer;
begin
  Result := -1;
  for I := 0 to Files.Count - 1 do
    if CompareText(PayloadPath(Files[I]), Path) = 0 then begin
      Result := I;
      Exit;
    end;
end;

procedure CheckDestination(Relative: String);
var
  Path, Expected: String;
  Attributes: LongWord;
begin
  if not SafeRelativePath(Relative) and (Relative <> ReceiptName) and
    (Relative <> 'unins000.exe') and (Relative <> 'unins000.dat') and
    (Relative <> 'unins000.msg') then Refuse;
  Path := AddBackslash(CleanPath(ExpandConstant('{app}'))) + Relative;
  Expected := ParentPath(AddBackslash(ProgramLocation) + Relative);
  if CompareText(CanonicalDirectory(ParentPath(Path), True, True), Expected) <> 0 then Refuse;
  Attributes := ExistingAttributes(Path);
  if (Attributes <> $FFFFFFFF) and ((Attributes and ($400 or $10)) <> 0) then Refuse;
end;

procedure ReadPreviousPayload();
var
  Receipt, ExpectedHash, Relative, Path, PreviousVersion, PreviousLocation: String;
  Lines: TArrayOfString;
  I: Integer;
  HasHash: Boolean;
begin
  Receipt := AddBackslash(ExpandConstant('{app}')) + ReceiptName;
  CheckDestination(ReceiptName);
  HasHash := RegQueryStringValue(HKCU64, OwnershipKey, ReceiptRegistryValue, ExpectedHash);
  if not HasHash and not FileExists(Receipt) then begin
    { Never guess ownership for a pre-inventory installation or an unrelated existing EXE. }
    if FileExists(AddBackslash(ExpandConstant('{app}')) + 'Studium.exe') or
      DirExists(AddBackslash(ExpandConstant('{app}')) + '_internal') or
      FileExists(AddBackslash(ExpandConstant('{app}')) + 'unins000.exe') or
      FileExists(AddBackslash(ExpandConstant('{app}')) + 'unins000.dat') then Refuse;
    Exit;
  end;
  if not HasHash or not FileExists(Receipt) then Refuse;
  if not RegQueryStringValue(HKCU64, OwnershipKey, 'InstallLocation', PreviousLocation) then Refuse;
  if CompareText(CanonicalDirectory(PreviousLocation, True, True), ProgramLocation) <> 0 then Refuse;
  if not RegQueryStringValue(HKCU64, OwnershipKey, 'DisplayVersion', PreviousVersion) then Refuse;
  CheckVersion(PreviousVersion);
  if (Length(ExpectedHash) <> 64) or
    (CompareText(GetSHA256OfFile(Receipt), ExpectedHash) <> 0) then Refuse;
  if not LoadStringsFromFile(Receipt, Lines) then Refuse;
  if GetArrayLength(Lines) < 2 then Refuse;
  if Lines[0] <> ReceiptHeader then Refuse;
  for I := 1 to GetArrayLength(Lines) - 1 do begin
    if not ValidEntry(Lines[I]) then Refuse;
    Relative := PayloadPath(Lines[I]);
    if FindOwned(OldPayload, Relative) >= 0 then Refuse;
    CheckDestination(Relative);
    Path := AddBackslash(ExpandConstant('{app}')) + Relative;
    { Pascal Script does not promise short-circuit evaluation of and/or. }
    if FindOwned(NewPayload, Relative) < 0 then
      if FileExists(Path) then
        if CompareText(GetSHA256OfFile(Path), Copy(Lines[I], 1, 64)) <> 0 then Refuse;
    OldPayload.Add(Lines[I]);
    if FindOwned(NewPayload, Relative) < 0 then ObsoleteFiles.Add(Relative);
  end;
end;

procedure CheckApplicationClosed();
var
  Path: String;
  Handle: THandle;
begin
  Path := AddBackslash(ExpandConstant('{app}')) + 'Studium.exe';
  if not FileExists(Path) then Exit;
  { Opening for write makes no writes, but Windows denies it for a mapped/running EXE. }
  Handle := GuardCreateFile(Path, $40000000, 7, 0, 3, $00200000, 0);
  if Handle = THandle(-1) then begin
    RejectionReason := 'Studium: закройте приложение перед установкой / close Studium before installing.';
    RaiseException(RejectionReason);
  end;
  GuardCloseHandle(Handle);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  DataLocation, Relative: String;
  I: Integer;
begin
  Result := '';
  RejectionReason := GuardError;
  Prepared := False;
  ReleasePins;
  if PinnedNames = nil then begin
    PinnedNames := TStringList.Create;
    NewPayload := TStringList.Create;
    OldPayload := TStringList.Create;
    ObsoleteFiles := TStringList.Create;
    LoadNewPayload(NewPayload);
  end;
  OldPayload.Clear;
  ObsoleteFiles.Clear;
  try
    GuardCheckpoint := 'data-location';
    DataLocation := CanonicalDirectory(GuardDataRoot, False, False);
    GuardCheckpoint := 'program-location';
    ProgramLocation := CanonicalDirectory(ExpandConstant('{app}'), True, True);
    GuardCheckpoint := 'overlap';
    if Overlaps(ProgramLocation, DataLocation) then Refuse;
    GuardCheckpoint := 'previous-payload';
    ReadPreviousPayload;
    GuardCheckpoint := 'new-payload';
    for I := 0 to NewPayload.Count - 1 do begin
      Relative := PayloadPath(NewPayload[I]);
      CheckDestination(Relative);
      if FileExists(AddBackslash(ExpandConstant('{app}')) + Relative) and
        (FindOwned(OldPayload, Relative) < 0) then Refuse;
    end;
    CheckDestination('unins000.exe');
    CheckDestination('unins000.dat');
    CheckDestination('unins000.msg');
    CheckApplicationClosed;
    Prepared := True;
  except
    Log('STUDIUM_GUARD_CHECKPOINT ' + GuardCheckpoint);
    Result := RejectionReason;
    ReleasePins;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  I: Integer;
  Path, InstalledVersion, InstalledLocation: String;
begin
  if CurStep = ssInstall then begin
    if not Prepared then Refuse;
    CheckApplicationClosed;
    { Check every previous entry again before deleting any of them. }
    for I := 0 to OldPayload.Count - 1 do begin
      Path := PayloadPath(OldPayload[I]);
      CheckDestination(Path);
      Path := AddBackslash(ExpandConstant('{app}')) + Path;
      if FindOwned(NewPayload, PayloadPath(OldPayload[I])) < 0 then
        if FileExists(Path) then
          if CompareText(GetSHA256OfFile(Path), Copy(OldPayload[I], 1, 64)) <> 0 then Refuse;
    end;
    { Preflight has completed before Inno's file and registry installation begins. }
    for I := 0 to ObsoleteFiles.Count - 1 do begin
      CheckDestination(ObsoleteFiles[I]);
      Path := AddBackslash(ExpandConstant('{app}')) + ObsoleteFiles[I];
      if FileExists(Path) then
        if not DeleteFile(Path) then Refuse;
    end;
  end;
  if CurStep = ssPostInstall then begin
    { Inno recreates its uninstall key AFTER [Registry]. Record ownership only
      after that step; Inno's uninstall log removes this entire owned key. }
    CheckDestination(ReceiptName);
    Path := AddBackslash(ExpandConstant('{app}')) + ReceiptName;
    if CompareText(GetSHA256OfFile(Path), '{#PayloadReceiptSHA256}') <> 0 then Refuse;
    if not RegQueryStringValue(HKCU64, OwnershipKey, 'DisplayVersion', InstalledVersion) then Refuse;
    if CompareText(InstalledVersion, GuardAppVersion) <> 0 then Refuse;
    if not RegQueryStringValue(HKCU64, OwnershipKey, 'InstallLocation', InstalledLocation) then Refuse;
    if CompareText(CanonicalDirectory(InstalledLocation, True, True), ProgramLocation) <> 0 then Refuse;
    if not RegWriteStringValue(HKCU64, OwnershipKey, ReceiptRegistryValue,
      '{#PayloadReceiptSHA256}') then Refuse;
    Log('STUDIUM_GUARD_OWNERSHIP_RECORDED');
  end;
end;

procedure DeinitializeSetup();
begin
  ReleasePins;
  if PinnedNames <> nil then begin
    PinnedNames.Free;
    NewPayload.Free;
    OldPayload.Free;
    ObsoleteFiles.Free;
  end;
end;
