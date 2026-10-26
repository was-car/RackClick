#requires -Version 5.1
[CmdletBinding()]
param([string]$DeploymentPath='',[string]$ExpectedDeploymentSha256='',[switch]$Maintenance)
$deploymentInputs=@{path=$DeploymentPath;digest=$ExpectedDeploymentSha256;maintenance=[bool]$Maintenance}
. (Join-Path $PSScriptRoot 'RackClick.Deployment.ps1')
$report=[ordered]@{valid=$false;exitCode=2;code='deployment_verification_failed';deploymentPath='';deploymentId='';instanceId='';url='';httpsValidated=$false;scope='Integrity only; not current readiness/SCM, installation, recovery or acceptance'}
if ($deploymentInputs.maintenance) { $report.scope='Maintenance core integrity only; TLS not validated; not current readiness/SCM, installation, recovery or acceptance' }
$deployment=$null
try {
    $deployment=Read-RackClickPrivateDeployment -DeploymentPath $deploymentInputs.path -ExpectedDeploymentSha256 $deploymentInputs.digest -Maintenance:$deploymentInputs.maintenance
    $report.valid=$true;$report.exitCode=0;$report.code='deployment_verified'
    if ($deploymentInputs.maintenance) { $report.code='deployment_maintenance_verified' }
    $report.deploymentPath=$deployment.root;$report.deploymentId=$deployment.id;$report.instanceId=$deployment.instance.id;$report.url=('https://127.0.0.1:'+[string]$deployment.instance.httpPort);$report.httpsValidated=$deployment.httpsValidated
} catch {
    foreach ($pair in @(@('deploymentCode','deploymentExit'),@('httpsCode','httpsExit'),@('instanceCode','instanceExit'),@('stageCode','stageExit'),@('code','exitCode'))) {
        if ($_.Exception.Data.Contains($pair[0])) { $report.code=$_.Exception.Data[$pair[0]];$report.exitCode=[int]$_.Exception.Data[$pair[1]];break }
    }
} finally { Close-RackClickPrivateDeployment $deployment }
$report|ConvertTo-Json -Compress
exit $report.exitCode
