#requires -Version 5.1
param([string]$OutputPath='')
$ErrorActionPreference='Stop'
$env:PSModulePath='C:\Windows\System32\WindowsPowerShell\v1.0\Modules'
. (Join-Path $PSScriptRoot '..\..\windows\server-install\Show-RackClickDatabaseAccess.ps1') -FunctionsOnly
Initialize-RcDatabaseAccessReader
$base=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..\.local'))
$root=Join-Path $base ('db-container-proof-'+[guid]::NewGuid().ToString('N'))
$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$ordinary='O:'+$sid+'G:SYD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;'+$sid+')'
$container='O:'+$sid+'G:SYD:P(A;OICI;FA;;;SY)(A;;0xA0;;;BA)(A;OICI;FA;;;'+$sid+')'
function Set-ProofAcl([string]$Path,[string]$Sddl){
 $item=Get-Item -LiteralPath $Path
 $acl=$item.GetAccessControl([Security.AccessControl.AccessControlSections]::Access)
 $acl.SetSecurityDescriptorSddlForm($Sddl,[Security.AccessControl.AccessControlSections]::Access)
 $item.SetAccessControl($acl)
}
$method=[RackClickDatabasePrivateReader].GetMethod('ReadCore',[Reflection.BindingFlags]'NonPublic,Static')
function Read-Proof([string]$Path){
 $args=New-Object object[] 5
 $args[0]=$Path.PSObject.BaseObject;$args[1]=$root.PSObject.BaseObject;$args[2]=$sid.PSObject.BaseObject;$args[3]=$false;$args[4]=1024
 return ,($method.Invoke($null,$args))
}
$count=0
try{
 $null=[IO.Directory]::CreateDirectory($root)
 Set-ProofAcl $root $ordinary
 $file=Join-Path $root 'admin-login.json'
 [IO.File]::WriteAllText($file,'synthetic-container-proof')
 Set-ProofAcl $file $ordinary
 $before=Read-Proof $file
 if([Text.Encoding]::UTF8.GetString($before)-cne'synthetic-container-proof'){throw 'ordinary_control_failed'}
 $count++
 Set-ProofAcl $root $container
 # This reaches the real retained-handle parent validation, with the exact
 # administrative mask observed on the installed13 container; no privilege seam.
 $bytes=Read-Proof $file
 if([Text.Encoding]::UTF8.GetString($bytes)-cne'synthetic-container-proof'){throw 'container_control_failed'}
 $count++
 Set-ProofAcl $file $container
 $failed=$false;try{$null=Read-Proof $file}catch{$failed=$true}
 if(-not$failed){throw 'file_exception_was_broadened'}
 $count++
 Set-ProofAcl $file $ordinary
 $child=Join-Path $root 'child';$null=[IO.Directory]::CreateDirectory($child)
 Set-ProofAcl $child $container
 $childFile=Join-Path $child 'admin-login.json';[IO.File]::WriteAllText($childFile,'synthetic-child')
 Set-ProofAcl $childFile $ordinary
 $failed=$false;try{$null=Read-Proof $childFile}catch{$failed=$true}
 if(-not$failed){throw 'child_exception_was_broadened'}
 $count++
 $result=@{valid=$true;checks=$count;realWindowsHandles=$true;syntheticOnly=$true;privilegesEnabled=$false;vmOperations=0}
 if($OutputPath){[IO.File]::WriteAllText($OutputPath,($result|ConvertTo-Json -Compress))}
 $result|ConvertTo-Json -Compress
}finally{
 $resolved=[IO.Path]::GetFullPath($root)
 if($resolved.StartsWith($base+'\',[StringComparison]::OrdinalIgnoreCase)-and[IO.Path]::GetFileName($resolved)-cmatch'^db-container-proof-[a-f0-9]{32}$'){
  Remove-Item -LiteralPath $resolved -Recurse -Force -ErrorAction SilentlyContinue
 }
}
