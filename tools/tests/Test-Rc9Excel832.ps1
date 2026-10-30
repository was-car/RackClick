param([Parameter(Mandatory=$true)][string]$ArtifactPath,[Parameter(Mandatory=$true)][string]$ExpectedPath,[Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $OutputPath){throw 'Preserve previous Office evidence'}
$artifact=(Resolve-Path -LiteralPath $ArtifactPath).Path
$expected=Get-Content -LiteralPath $ExpectedPath -Raw -Encoding UTF8|ConvertFrom-Json
$beforeHash=(Get-FileHash -LiteralPath $artifact -Algorithm SHA256).Hash.ToLowerInvariant()
if($beforeHash -ne $expected.sha256){throw 'Fixture checksum mismatch'}
$baseline=@(Get-Process -Name EXCEL -ErrorAction SilentlyContinue|Select-Object -ExpandProperty Id)
Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public static class Rc9Excel832Window { [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId); }'
$report=[ordered]@{utc=[DateTime]::UtcNow.ToString('o');successful=$false;artifactSha256=$beforeHash;baselineExcelPids=$baseline;ownProcess=$false;readOnly=$false;officePoliciesChanged=$false;userWorkbooksAccessed=$false;actualQaAccessed=$false;macroExecutionDisabledInOwnedInstance=$false;updateLinks=0;addToMru=$false;instanceDisplayAlerts=$false;worksheets=@();observedCells=@();error=$null}
$excel=$null;$books=$null;$book=$null;$owned=$false;$excelProcessId=0
try {
    $excel=New-Object -ComObject Excel.Application
    [uint32]$excelProcessId=0
    [void][Rc9Excel832Window]::GetWindowThreadProcessId([IntPtr]$excel.Hwnd,[ref]$excelProcessId)
    if($excelProcessId -eq 0 -or $baseline -contains $excelProcessId){throw 'Cannot prove an independent Excel process; no properties changed or Quit issued'}
    $books=$excel.Workbooks
    if($books.Count -ne 0){throw 'Unexpected existing workbook in newly created instance; no documents accessed'}
    $owned=$true;$report.ownProcess=$true;$report.excelPid=$excelProcessId;$report.excelVersion=[string]$excel.Version;$report.excelBuild=[string]$excel.Build
    $excel.Visible=$false;$excel.DisplayAlerts=$false;$excel.EnableEvents=$false;$excel.AskToUpdateLinks=$false;$excel.AutomationSecurity=3
    $report.macroExecutionDisabledInOwnedInstance=$true
    # Open exact trusted synthetic output only. DisplayAlerts is instance-only; no registry/GPO/trust setting is changed.
    $book=$books.Open($artifact,0,$true)
    $report.readOnly=[bool]$book.ReadOnly
    if(-not $report.readOnly -or $book.HasVBProject){throw 'Workbook not read-only or contains VBA'}
    if($null -ne $book.LinkSources(1) -or $null -ne $book.LinkSources(2) -or $book.Connections.Count -ne 0){throw 'Unexpected external link or connection'}
    $sheetList=$book.Worksheets;$values=New-Object 'System.Collections.Generic.List[string]'
    for($index=1;$index -le $sheetList.Count;$index++){
        $sheet=$sheetList.Item($index);$used=$sheet.UsedRange
        try {
            $hasFormula=$used.HasFormula
            if($null -eq $hasFormula -or $hasFormula -ne $false){throw 'Formula or mixed formula range found'}
            if($sheet.Hyperlinks.Count -ne 0 -or $sheet.QueryTables.Count -ne 0){throw 'Unexpected active worksheet object'}
            $matrix=$used.Value2;$rows=[int]$used.Rows.Count;$columns=[int]$used.Columns.Count
            $report.worksheets += [ordered]@{name=[string]$sheet.Name;rows=$rows;columns=$columns;hasFormula=$hasFormula;hyperlinks=0;queryTables=0}
            for($rowIndex=1;$rowIndex -le $rows;$rowIndex++){
                for($columnIndex=1;$columnIndex -le $columns;$columnIndex++){
                    $value=if($matrix -is [Array]){$matrix.GetValue($rowIndex,$columnIndex)}else{$matrix}
                    if($null -ne $value -and [string]$value -ne ''){
                        if($value -isnot [string]){throw 'A text-marked cell was coerced into a non-string value'}
                        $values.Add([string]$value)
                    }
                }
            }
        } finally {
            [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($used)
            [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($sheet)
        }
    }
    $report.worksheetCount=$sheetList.Count
    [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($sheetList)
    $report.observedCells=@($values.ToArray());$report.expectedNonemptyCells=@($expected.cells).Count
    $expectedCounts=@{};$actualCounts=@{}
    foreach($value in $expected.cells){$key=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes([string]$value));$expectedCounts[$key]=1+$expectedCounts[$key]}
    foreach($value in $values){$key=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes([string]$value));$actualCounts[$key]=1+$actualCounts[$key]}
    if($expectedCounts.Count -ne $actualCounts.Count){throw 'Nonempty cell content differs from the generated HTML tables'}
    foreach($key in $expectedCounts.Keys){if($expectedCounts[$key] -ne $actualCounts[$key]){throw 'Nonempty cell multiplicity or exact UTF8 text differs'}}
    $report.allNonemptyCellsExact=$true;$report.noEffectiveFormulas=$true;$report.successful=$true
} catch {$report.error=$_.Exception.Message}
finally {
    if($owned -and $null -ne $book){$book.Close($false)}
    if($owned -and $null -ne $excel){$excel.Quit()}
    foreach($object in @($book,$books,$excel)){if($null -ne $object -and [Runtime.InteropServices.Marshal]::IsComObject($object)){[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($object)}}
    [GC]::Collect();[GC]::WaitForPendingFinalizers()
    if($owned){
        $stopDeadline=[DateTime]::UtcNow.AddSeconds(3)
        while($null -ne (Get-Process -Id $excelProcessId -ErrorAction SilentlyContinue) -and [DateTime]::UtcNow -lt $stopDeadline){Start-Sleep -Milliseconds 100}
    }
    $report.artifactUnchanged=((Get-FileHash -LiteralPath $artifact -Algorithm SHA256).Hash.ToLowerInvariant() -eq $beforeHash)
    $report.ownedProcessStopped=($owned -and $null -eq (Get-Process -Id $excelProcessId -ErrorAction SilentlyContinue))
    $remaining=@(Get-Process -Name EXCEL -ErrorAction SilentlyContinue|Select-Object -ExpandProperty Id)
    $report.baselineUserProcessesStillPresent=(@($baseline|Where-Object{$remaining -notcontains $_}).Count -eq 0)
    $report.successful=($report.successful -and $report.artifactUnchanged -and $report.ownedProcessStopped -and $report.baselineUserProcessesStillPresent)
    $text=$report|ConvertTo-Json -Depth 10
    [IO.File]::WriteAllText([IO.Path]::GetFullPath($OutputPath),$text+[Environment]::NewLine,[Text.UTF8Encoding]::new($false))
}
if(-not $report.successful){exit 1}
