#requires -Version 5.1
# Read-only inventory of the known failed attempts. Never reads secrets or request.json.
[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$roots=@('C:\RackClick-Servidor-01','C:\RackClick-Instancia-01','C:\RackClick-Instancia-02','C:\Users\RackClickOperador\Documents\RackClick-Instancia-01')
$items=@()
foreach($root in $roots){
    $record=[ordered]@{path=$root;exists=$false;reparse=$false;state=$null;receiptPresent=$false;postgresPidFilePresent=$false;inspectionComplete=$false}
    try {
        if(Test-Path -LiteralPath $root){
            $item=Get-Item -LiteralPath $root -Force
            $record.exists=$true;$record.reparse=($item.Attributes-band[IO.FileAttributes]::ReparsePoint)-ne0
            if(-not$record.reparse){
                $statePath=Join-Path $root 'installation-state.json'
                if(Test-Path -LiteralPath $statePath){
                    $stateItem=Get-Item -LiteralPath $statePath -Force
                    if(($stateItem.Attributes-band[IO.FileAttributes]::ReparsePoint)-ne0-or$stateItem.Length-gt4096){throw 'inventory_state_not_regular'}
                    $state=Get-Content -LiteralPath $statePath -Raw|ConvertFrom-Json
                    $record.state=@{status=([string]$state.status -replace '[^a-z_]','');code=([string]$state.code -replace '[^a-z0-9_]','')}
                }
                $record.receiptPresent=Test-Path -LiteralPath (Join-Path $root 'installation.json')
                $record.postgresPidFilePresent=Test-Path -LiteralPath (Join-Path $root 'deployment\instance\pgdata\postmaster.pid')
                $record.inspectionComplete=$true
            }
        }else{$record.inspectionComplete=$true}
    }catch{$record.inspectionComplete=$false}
    $items+=,$record
}
$services=@(Get-CimInstance Win32_Service|Where-Object{$_.Name-like'RackClick*'}|ForEach-Object{@{name=$_.Name;state=$_.State;startMode=$_.StartMode;account=$_.StartName}})
$ports=@(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue|Where-Object{$_.LocalPort-in@(5443,55441)}|ForEach-Object{@{address=$_.LocalAddress;port=$_.LocalPort;pid=$_.OwningProcess}})
[ordered]@{schemaVersion=1;generatedUtc=[DateTime]::UtcNow.ToString('o');computer=$env:COMPUTERNAME;readOnly=$true;deletedObjects=0;paths=$items;services=$services;listeners=$ports;nextStep='Preserve evidence and verify exact identities before any removal.'}|ConvertTo-Json -Depth 7
