"""Focused tests for the optional Windows API loader; no installed instance."""
import copy
import hashlib
import importlib.util
import json
import http.server
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('demo50_replay',ROOT/'tools/build_demo50_replay.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
SCRIPT=ROOT/'tools/windows/demo50/Import-RackClickDemo50.ps1'
SOURCE=ROOT/'.local/demo50-03/loaded-private.json'
PORTABLE=ROOT/'DEMO-50-CLIENTES-01'
PIN='a3b44a37d8ca81f2f13d515d26905a520af8f09ffb2cfe498f97d06367bf423a'

def ps(code):
    return subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-Command',
        ". '"+str(SCRIPT)+"'; $ErrorActionPreference='Stop'; "+code+";exit 0"],text=True,capture_output=True,timeout=30)

class Demo50ChallengeCookieFlow(unittest.TestCase):
    def test_rejected_cookie_headers_are_not_retained_or_sent(self):
        good='RackClick.MfaChallenge='+'A'*64+'; Path=/api/v1/auth/mfa; HttpOnly; SameSite=Strict'
        cases={
            'broad_path':[good.replace('Path=/api/v1/auth/mfa','Path=/')],
            'missing_httponly':[good.replace('; HttpOnly','')],
            'missing_samesite':[good.replace('; SameSite=Strict','')],
            'weak_samesite':[good.replace('SameSite=Strict','SameSite=Lax')],
            'external_domain':[good+'; Domain=elsewhere.invalid'],
            'session_extra':[good,'RackClick.Session='+'B'*64+'; Path=/; HttpOnly'],
            'duplicate_cookie':[good,good],
            'duplicate_path':[good+'; Path=/'],
            'combined_header':[good+', RackClick.Session='+'B'*64+'; Path=/'],
            'wrong_cookie_name':[good.replace('RackClick.MfaChallenge','RackClick.Session')],
            'missing_cookie':[],
        }
        for label,headers in cases.items():
            with self.subTest(label=label):self._rejected_cookie_http(headers)

    def _rejected_cookie_http(self,headers):
        calls=[]
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                size=int(self.headers.get('Content-Length','0'))
                if size:self.rfile.read(size)
                calls.append(self.path);raw=b'{"mfaRequired":true,"purpose":"verify","csrf":"fixture"}'
                self.send_response(202);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)))
                for header in headers:self.send_header('Set-Cookie',header)
                self.end_headers();self.wfile.write(raw)
            def log_message(self,*args):pass
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            code="""$ctx=@{origin='http://127.0.0.1:@@PORT@@';web=(New-Object Microsoft.PowerShell.Commands.WebRequestSession);csrf=''}
try{$null=Invoke-Demo50Http $ctx POST '/api/v1/auth/login' @{username='fixture';password='DO-NOT-REPORT-PASSWORD'} @{} @(202);exit 8}catch{
 if($_.Exception.Message-cne'demo_mfa_challenge_cookie_invalid'){Get-Demo50FailureReport $_.Exception|ConvertTo-Json -Depth 5 -Compress;exit 9}
}
if($ctx.web.Cookies.GetCookies([uri]($ctx.origin+'/api/v1/me')).Count-ne0-or$ctx.web.Cookies.GetCookies([uri]($ctx.origin+'/api/v1/auth/mfa/verify')).Count-ne0){exit 10}
'COOKIE_REJECTED'
""".replace('@@PORT@@',str(server.server_address[1]))
            result=ps(code)
            self.assertNotIn('A'*64,result.stdout+result.stderr);self.assertNotIn('B'*64,result.stdout+result.stderr)
            self.assertNotIn('DO-NOT-REPORT',result.stdout+result.stderr)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(calls,['/api/v1/auth/login'])
        finally:server.shutdown();server.server_close();thread.join()

    def test_https_cookie_retains_flags_exact_host_and_path(self):
        code="""$ctx=@{origin='https://rackclick.example.invalid:5443';web=(New-Object Microsoft.PowerShell.Commands.WebRequestSession)}
$headers=New-Object Net.WebHeaderCollection
$headers.Add('Set-Cookie',('RackClick.MfaChallenge='+('A'*64)+'; Path=/api/v1/auth/mfa; Secure; HttpOnly; SameSite=Strict; Max-Age=300'))
$response=[pscustomobject]@{BaseResponse=[pscustomobject]@{ResponseUri=[uri]($ctx.origin+'/api/v1/auth/login');Headers=$headers}}
Set-Demo50MfaChallengeCookie $ctx $response
$selected=$ctx.web.Cookies.GetCookies([uri]($ctx.origin+'/api/v1/auth/mfa/verify'))
if($selected.Count-ne1-or-not$selected[0].Secure-or-not$selected[0].HttpOnly-or$selected[0].Path-cne'/api/v1/auth/mfa'){exit 8}
foreach($outside in @('https://rackclick.example.invalid:5443/api/v1/me','http://rackclick.example.invalid:5443/api/v1/auth/mfa/verify','https://sub.rackclick.example.invalid:5443/api/v1/auth/mfa/verify')){if($ctx.web.Cookies.GetCookies([uri]$outside).Count-ne0){exit 9}}
'COOKIE_SCOPE_OK'
"""
        result=ps(code);self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_https_missing_secure_or_changed_response_origin_is_rejected(self):
        code="""foreach($mode in @('no_secure','wrong_origin')){
 $ctx=@{origin='https://rackclick.example.invalid:5443';web=(New-Object Microsoft.PowerShell.Commands.WebRequestSession)}
 $headers=New-Object Net.WebHeaderCollection;$secure='; Secure';$actual=$ctx.origin+'/api/v1/auth/login'
 if($mode-ceq'no_secure'){$secure=''}else{$actual='https://elsewhere.invalid/api/v1/auth/login'}
 $headers.Add('Set-Cookie',('RackClick.MfaChallenge='+('A'*64)+'; Path=/api/v1/auth/mfa; HttpOnly; SameSite=Strict'+$secure))
 $response=[pscustomobject]@{BaseResponse=[pscustomobject]@{ResponseUri=[uri]$actual;Headers=$headers}}
 try{Set-Demo50MfaChallengeCookie $ctx $response;exit 8}catch{if($_.Exception.Message-cne'demo_mfa_challenge_cookie_invalid'){throw}}
 if($ctx.web.Cookies.GetCookies([uri]($ctx.origin+'/api/v1/auth/mfa/verify')).Count-ne0){exit 9}
}
'INVALID_COOKIE_REJECTED'
"""
        result=ps(code);self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_real_login_verify_me_preserves_scoped_challenge_cookie(self):
        calls=[];observed={};challenge='A'*64;session='B'*64
        class Handler(http.server.BaseHTTPRequestHandler):
            def reply(self,status,value=None,cookie=None):
                raw=b'' if status==204 else json.dumps(value).encode()
                self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)))
                if cookie:self.send_header('Set-Cookie',cookie)
                self.end_headers();self.wfile.write(raw)
            def do_GET(self):
                calls.append(('GET',self.path))
                if self.path=='/health/ready':return self.reply(200,{'status':'ready','schemaVersion':43})
                cookie=self.headers.get('Cookie','')
                if self.path=='/api/v1/me':
                    observed['sessionMatches']=('RackClick.Session='+session) in cookie
                    observed['challengeAbsentFromMe']='RackClick.MfaChallenge=' not in cookie
                    if not observed['sessionMatches']:return self.reply(401,{'error':'authentication_required'})
                    return self.reply(200,{'user':{'id':'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'},'csrf':'session-fixture','permissions':{'systemhausCapabilities':['systemhaus.manage','security.manage','customer.manage','inventory.read','inventory.edit']}})
                if self.path=='/api/v1/customers':return self.reply(200,[])
                return self.reply(404,{'error':'not_found'})
            def do_POST(self):
                raw=self.rfile.read(int(self.headers.get('Content-Length','0')));body=json.loads(raw) if raw else None
                calls.append(('POST',self.path))
                if self.path=='/api/v1/auth/login':return self.reply(202,{'mfaRequired':True,'purpose':'verify','csrf':'challenge-fixture'},'RackClick.MfaChallenge='+challenge+'; Path=/api/v1/auth/mfa; Max-Age=300; HttpOnly; SameSite=Strict')
                if self.path=='/api/v1/auth/mfa/verify':
                    observed.update(cookieMatches=('RackClick.MfaChallenge='+challenge) in self.headers.get('Cookie',''),csrfMatches=self.headers.get('X-RackClick-CSRF')=='challenge-fixture',codeMatches=body=={'code':'123456'})
                    if not all(observed.values()):return self.reply(401,{'error':'mfa_challenge_invalid'})
                    return self.reply(200,{'csrf':'session-fixture'},'RackClick.Session='+session+'; Path=/; HttpOnly; SameSite=Strict')
                if self.path=='/api/v1/auth/logout':
                    observed['logoutCsrfMatches']=self.headers.get('X-RackClick-CSRF')=='session-fixture'
                    if not observed['logoutCsrfMatches']:return self.reply(403,{'error':'csrf_invalid'})
                    return self.reply(204)
                return self.reply(500,{'error':'unexpected_inventory_write'})
            def log_message(self,*args):pass
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            code="""function Read-Host {param($Prompt,[switch]$AsSecureString);$value=New-Object Security.SecureString;foreach($c in '123456'.ToCharArray()){$value.AppendChar($c)};return $value}
$secret=New-Object Security.SecureString;foreach($c in 'synthetic-password'.ToCharArray()){$secret.AppendChar($c)}
$credential=New-Object Management.Automation.PSCredential('fixture',$secret)
try{$null=Invoke-Demo50Import -Origin 'http://127.0.0.1:@@PORT@@' -PlanPath '@@PLAN@@' -ExpectedPlanSha256 '@@PIN@@' -Credential $credential -DevelopmentLoopbackHttp $true -Confirmation 'WRONG';exit 8}catch{
 if($_.Exception.Message-cne'demo_confirmation_rejected'){Get-Demo50FailureReport $_.Exception|ConvertTo-Json -Depth 5 -Compress;exit 9}
 'EXPECTED_CONFIRMATION_REJECTION'
}finally{$secret.Dispose()}
""".replace('@@PORT@@',str(server.server_address[1])).replace('@@PLAN@@',str(ROOT/'development/examples/demo50-replay43.json')).replace('@@PIN@@',PIN)
            result=ps(code)
            self.assertNotIn(challenge,result.stdout+result.stderr)
            self.assertNotIn(session,result.stdout+result.stderr)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr+' observed='+json.dumps(observed,sort_keys=True))
            self.assertIn('EXPECTED_CONFIRMATION_REJECTION',result.stdout)
            self.assertTrue(observed and all(observed.values()),observed)
            self.assertEqual(calls,[('GET','/health/ready'),('POST','/api/v1/auth/login'),('POST','/api/v1/auth/mfa/verify'),('GET','/api/v1/me'),('GET','/api/v1/customers'),('POST','/api/v1/auth/logout')])
        finally:server.shutdown();server.server_close();thread.join()

class Demo50HttpDiagnostics(unittest.TestCase):
    """Real HTTP failures through WPS5.1, without database or inventory writes."""
    def diagnose(self,status,body,route='/api/v1/auth/mfa/verify',method='POST'):
        calls=[]
        class Handler(http.server.BaseHTTPRequestHandler):
            def handle_failure(self):
                calls.append(self.path)
                size=int(self.headers.get('Content-Length','0'))
                if size:self.rfile.read(size)
                self.send_response(status);self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(body)));self.send_header('Set-Cookie','private=DO-NOT-REPORT-COOKIE; HttpOnly')
                self.send_header('X-Private','DO-NOT-REPORT-HEADER');self.end_headers();self.wfile.write(body)
            do_GET=handle_failure
            do_POST=handle_failure
            def log_message(self,*args):pass
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            route_literal=route.replace("'","''")
            code="""$ctx=@{origin='http://127.0.0.1:@@PORT@@';web=(New-Object Microsoft.PowerShell.Commands.WebRequestSession);csrf='DO-NOT-REPORT-CSRF'}
try{$null=Invoke-Demo50Http $ctx '@@METHOD@@' '@@ROUTE@@' @{code='654321';password='DO-NOT-REPORT-PASSWORD'};exit 11}catch{
 if(Get-Command Get-Demo50FailureReport -ErrorAction SilentlyContinue){$report=Get-Demo50FailureReport $_.Exception}else{$report=[ordered]@{schemaVersion=1;success=$false;code=$_.Exception.Message;partialDataPreserved=$true;automaticRetry=$false}}
 $report|ConvertTo-Json -Depth 5 -Compress
}
""".replace('@@PORT@@',str(server.server_address[1])).replace('@@METHOD@@',method).replace('@@ROUTE@@',route_literal)
            result=ps(code)
            self.assertEqual(result.returncode,0,result.stderr)
            output=result.stdout+result.stderr
            self.assertNotIn('DO-NOT-REPORT',output)
            self.assertNotIn('654321',output)
            self.assertNotIn('127.0.0.1',output)
            self.assertEqual(len(calls),1,'No automatic HTTP retry')
            return json.loads(result.stdout.strip())
        finally:server.shutdown();server.server_close();thread.join()

    def check_failure(self,report,status,code,route='/api/v1/auth/mfa/verify',method='POST'):
        self.assertEqual(report['code'],'demo_http_rejected_or_uncertain_no_retry')
        self.assertFalse(report['automaticRetry'])
        self.assertFalse(report['success'])
        self.assertEqual(report['httpFailure'],{'method':method,'route':route,'httpStatus':status,'code':code})

    def test_401_mfa_code_reports_only_status_route_and_allowed_code(self):
        body=json.dumps({'error':'mfa_code_invalid','message':'DO-NOT-REPORT-BODY','cookie':'DO-NOT-REPORT-COOKIE','code':'654321'}).encode()
        self.check_failure(self.diagnose(401,body),401,'mfa_code_invalid')

    def test_403_csrf_reports_closed_code(self):
        self.check_failure(self.diagnose(403,b'{"error":"csrf_invalid","message":"DO-NOT-REPORT-BODY"}'),403,'csrf_invalid')

    def test_401_login_failed_preserves_actual_server_code(self):
        self.check_failure(self.diagnose(401,b'{"error":"login_failed","message":"DO-NOT-REPORT-BODY"}','/api/v1/auth/login'),401,'login_failed','/api/v1/auth/login')

    def test_429_without_json_reports_status_with_unavailable_code(self):
        self.check_failure(self.diagnose(429,b'DO-NOT-REPORT-BODY'),429,'unavailable')

    def test_unlisted_error_code_is_not_reflected(self):
        self.check_failure(self.diagnose(401,b'{"error":"DO-NOT-REPORT-SECRET"}'),401,'unavailable')

    def test_nonstring_error_is_not_reflected(self):
        self.check_failure(self.diagnose(401,b'{"error":{"password":"DO-NOT-REPORT-SECRET"}}'),401,'unavailable')

    def test_oversized_error_body_is_not_parsed(self):
        body=json.dumps({'error':'csrf_invalid','padding':'x'*5000,'message':'DO-NOT-REPORT-BODY'}).encode()
        self.check_failure(self.diagnose(403,body),403,'unavailable')

    def test_dynamic_customer_route_uses_template_without_identifier(self):
        route='/api/v1/customers/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/commands'
        report=self.diagnose(409,b'{"error":"revision_conflict"}',route)
        self.check_failure(report,409,'revision_conflict','/api/v1/customers/{customerId}/commands')

    def test_unknown_route_is_not_reflected(self):
        self.check_failure(self.diagnose(404,b'{}','/DO-NOT-REPORT-ROUTE?password=secret'),404,'unavailable','unknown')

    def test_first_failure_survives_later_logout_failure(self):
        calls=[]
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                calls.append(self.path)
                size=int(self.headers.get('Content-Length','0'))
                if size:self.rfile.read(size)
                status,code=(401,'mfa_code_invalid') if self.path.endswith('/verify') else (403,'csrf_invalid')
                raw=json.dumps({'error':code,'message':'DO-NOT-REPORT-BODY'}).encode()
                self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
            def log_message(self,*args):pass
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            code="""$ctx=@{origin='http://127.0.0.1:@@PORT@@';web=(New-Object Microsoft.PowerShell.Commands.WebRequestSession);csrf='fixture'}
try{
 try{$null=Invoke-Demo50Http $ctx POST '/api/v1/auth/mfa/verify' @{code='654321'}}finally{try{$null=Invoke-Demo50Http $ctx POST '/api/v1/auth/logout' $null @{} @(204)}catch{}}
}catch{
 if(Get-Command Get-Demo50FailureReport -ErrorAction SilentlyContinue){$report=Get-Demo50FailureReport $_.Exception}else{$report=[ordered]@{code=$_.Exception.Message;success=$false;automaticRetry=$false}}
 $report|ConvertTo-Json -Depth 5 -Compress
}
""".replace('@@PORT@@',str(server.server_address[1]))
            result=ps(code);self.assertEqual(result.returncode,0,result.stderr)
            self.assertNotIn('DO-NOT-REPORT',result.stdout+result.stderr)
            self.check_failure(json.loads(result.stdout.strip()),401,'mfa_code_invalid')
            self.assertEqual(calls,['/api/v1/auth/mfa/verify','/api/v1/auth/logout'])
        finally:server.shutdown();server.server_close();thread.join()

    def test_transport_failure_is_zero_without_exception_details(self):
        import socket
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        code="""$ctx=@{origin='http://127.0.0.1:@@PORT@@';web=(New-Object Microsoft.PowerShell.Commands.WebRequestSession);csrf='fixture'}
try{$null=Invoke-Demo50Http $ctx GET '/api/v1/me';exit 9}catch{
 if(Get-Command Get-Demo50FailureReport -ErrorAction SilentlyContinue){$report=Get-Demo50FailureReport $_.Exception}else{$report=[ordered]@{code=$_.Exception.Message;success=$false;automaticRetry=$false}}
 $report|ConvertTo-Json -Depth 5 -Compress
}
""".replace('@@PORT@@',str(port))
        result=ps(code);self.assertEqual(result.returncode,0,result.stderr)
        self.check_failure(json.loads(result.stdout.strip()),0,'unavailable','/api/v1/me','GET')

class Demo50WindowsHelpers(unittest.TestCase):
    def test_totp_challenge_is_completed_before_api_preflight(self):
        code="""
$script:callsDemo=New-Object 'Collections.Generic.List[string]'
function Read-Demo50Plan {param($Path,$Expected);return @{customers=@()}}
function Read-Host {param($Prompt,[switch]$AsSecureString);$value=New-Object Security.SecureString;foreach($ch in '123456'.ToCharArray()){$value.AppendChar($ch)};return $value}
function Invoke-Demo50Http {param($Context,$Method,$Route,$Body=$null,$Headers=@{},$Expected=@(200))
 $script:callsDemo.Add($Route)
 switch($Route){
  '/health/ready' {return @{data=@{status='ready';schemaVersion=43}}}
  '/api/v1/auth/login' {return @{status=202;data=@{csrf='challenge-fixture';purpose='verify'}}}
  '/api/v1/auth/mfa/verify' {if($Context.csrf-cne'challenge-fixture'-or$Body.code-cne'123456'){throw 'challenge_fixture_invalid'};return @{status=200;data=@{csrf='session-fixture'}}}
  '/api/v1/me' {if($Context.csrf-cne'session-fixture'){throw 'premature_api_fixture'};return @{data=@{user=@{id='fixture'};csrf='session-fixture';permissions=@{systemhausCapabilities=@('systemhaus.manage','security.manage','customer.manage','inventory.read','inventory.edit')}}}}
  '/api/v1/customers' {return @{data=@()}}
  '/api/v1/auth/logout' {return @{status=200;data=@{}}}
  default {throw 'unexpected_fixture_call'}
 }
}
$secure=New-Object Security.SecureString;foreach($ch in 'fixture'.ToCharArray()){$secure.AppendChar($ch)}
$credential=New-Object Management.Automation.PSCredential('fixture',$secure)
try{Invoke-Demo50Import -Origin 'https://a.invalid' -PlanPath 'ignored' -ExpectedPlanSha256 'ignored' -Credential $credential -Confirmation 'WRONG';exit 8}catch{if($_.Exception.Message-cne'demo_confirmation_rejected'){throw}}
if(($script:callsDemo-join',')-cne'/health/ready,/api/v1/auth/login,/api/v1/auth/mfa/verify,/api/v1/me,/api/v1/customers,/api/v1/auth/logout'){exit 9}
$secure.Dispose()
"""
        result=ps(code);self.assertEqual(result.returncode,0,result.stderr)

    def test_existing_destination_rejection_logs_out_without_inventory_commands(self):
        self._preflight_logout_case('existing')

    def test_confirmation_rejection_logs_out_without_inventory_commands(self):
        self._preflight_logout_case('confirmation')

    def _preflight_logout_case(self,case):
        code="""
$script:callsDemo=New-Object 'Collections.Generic.List[string]'
function Read-Demo50Plan {param($Path,$Expected);return @{customers=@()}}
function Invoke-Demo50Http {param($Context,$Method,$Route,$Body=$null,$Headers=@{},$Expected=@(200))
 $script:callsDemo.Add($Route)
 switch($Route){
  '/health/ready' {return @{data=@{status='ready';schemaVersion=43}}}
  '/api/v1/auth/login' {return @{status=200;data=@{csrf='not-secret-fixture'}}}
  '/api/v1/me' {return @{data=@{user=@{id='fixture'};csrf='fixture';permissions=@{systemhausCapabilities=@('systemhaus.manage','security.manage','customer.manage','inventory.read','inventory.edit')}}}}
  '/api/v1/customers' {return @{data=@@CUSTOMERS@@}}
  '/api/v1/auth/logout' {return @{status=200;data=@{}}}
  default {throw 'unexpected_fixture_call'}
 }
}
$secure=New-Object Security.SecureString;foreach($ch in 'fixture'.ToCharArray()){$secure.AppendChar($ch)}
$credential=New-Object Management.Automation.PSCredential('fixture',$secure)
try{Invoke-Demo50Import -Origin 'https://a.invalid' -PlanPath 'ignored' -ExpectedPlanSha256 'ignored' -Credential $credential -Confirmation 'WRONG';exit 8}catch{if($_.Exception.Message-cne'@@ERROR@@'){throw}}
if(@($script:callsDemo|Where-Object{$_-eq'/api/v1/auth/logout'}).Count-ne1){exit 9}
if(@($script:callsDemo|Where-Object{$_-like'*/commands'}).Count-ne0){exit 10}
$secure.Dispose()
"""
        code=code.replace('@@CUSTOMERS@@','@(@{id="existing"})' if case=='existing' else '@()')
        code=code.replace('@@ERROR@@','demo_empty_installation_required' if case=='existing' else 'demo_confirmation_rejected')
        result=ps(code);self.assertEqual(result.returncode,0,result.stderr)

    def test_json_without_charset_is_decoded_as_utf8(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                raw=json.dumps({'text':'Ubicación · Büro'},ensure_ascii=False).encode('utf8')
                self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
            def log_message(self,*args):pass
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            result=ps("$ctx=@{origin='http://127.0.0.1:"+str(server.server_address[1])+"';web=(New-Object Microsoft.PowerShell.Commands.WebRequestSession);csrf=''};$answer=Invoke-Demo50Http $ctx GET '/';$utf=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"+__import__('base64').b64encode('Ubicación · Büro'.encode()).decode()+"'));if($answer.data.text-cne$utf){exit 7}")
            self.assertEqual(result.returncode,0,result.stderr)
        finally:server.shutdown();server.server_close();thread.join()

    def test_native_parser_and_ascii(self):
        self.assertTrue(SCRIPT.read_bytes().isascii())
        result=ps("$t=$null;$e=$null;[Management.Automation.Language.Parser]::ParseFile('"+str(SCRIPT)+"',[ref]$t,[ref]$e)|Out-Null;if($e.Count){exit 1};'PASS'")
        self.assertEqual(result.returncode,0,result.stderr)

    def test_https_and_explicit_loopback_only(self):
        result=ps("foreach($url in @('http://192.168.1.1:5443','https://a.invalid/path','https://a.invalid/?x=1','https://u:p@a.invalid')){try{$null=Get-Demo50Origin $url $true;exit 1}catch{}};if((Get-Demo50Origin 'http://127.0.0.1:1234' $true)-cne'http://127.0.0.1:1234'){exit 2};try{$null=Get-Demo50Origin 'http://127.0.0.1:1234' $false;exit 3}catch{}")
        self.assertEqual(result.returncode,0,result.stderr)

    def test_unknown_id_is_not_sent_to_another_resource(self):
        result=ps("try{$null=Convert-Demo50Value @{id='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'} @{} $true;exit 1}catch{if($_.Exception.Message-cne'demo_unmapped_source_id'){throw}}")
        self.assertEqual(result.returncode,0,result.stderr)

    def test_mapping_conflict_rejected(self):
        result=ps("$m=@{};Add-Demo50Map $m 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa' 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';try{Add-Demo50Map $m 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa' 'cccccccc-cccc-4ccc-8ccc-cccccccccccc';exit 1}catch{if($_.Exception.Message-cne'demo_resource_map_conflict'){throw}}")
        self.assertEqual(result.returncode,0,result.stderr)

    def test_ports_do_not_match_by_gn_alone(self):
        code="""$id='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';$m=@{};$m[$id]=$id
$collections=@('sites','buildings','rooms','racks','devices','portGroups','ports','connections');$p=[ordered]@{};$e=[ordered]@{};foreach($k in $collections){$p[$k]=@();$e[$k]=@()}
$e.ports=@([pscustomobject]@{id=$id;gn=1;type='rj45';deviceId='source-device';groupId='source-group'})
$p.ports=@([pscustomobject]@{id=$id;gn=1;type='rj45';deviceId='other-device';groupId='other-group'})
try{Assert-Demo50Project ([pscustomobject]$p) ([pscustomobject]$e) $m;exit 1}catch{if($_.Exception.Message-cne'demo_content_mismatch_ports'){throw}}
"""
        result=ps(code);self.assertEqual(result.returncode,0,result.stderr)

    def test_unknown_plan_pin_rejected_before_read(self):
        result=ps("try{$null=Read-Demo50Plan 'Z:\\does-not-exist' ('0'*64);exit 1}catch{if($_.Exception.Message-cne'demo_plan_reference_required'){throw}}")
        self.assertEqual(result.returncode,0,result.stderr)

    def test_tampered_plan_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'plan.json';p.write_bytes(b' '+b'x'*1100)
            result=ps("try{$null=Read-Demo50Plan '"+str(p)+"' '"+PIN+"';exit 1}catch{if($_.Exception.Message-cne'demo_plan_hash_mismatch'){throw}}")
            self.assertEqual(result.returncode,0,result.stderr)

class Demo50ReplayBuilder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SOURCE.is_file() or not (PORTABLE/'manifest.json').is_file():
            raise unittest.SkipTest('Accepted Demo50 development receipts/exports required; not a clean-clone acceptance claim')
        cls.plan=builder.build(SOURCE,PORTABLE)

    def test_replay_exact_digest_and_reproducibility(self):
        raw=builder.encode(self.plan)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),PIN)
        self.assertEqual(raw,builder.encode(builder.build(SOURCE,PORTABLE)))

    def test_inventory_only_closed_metadata(self):
        self.assertEqual(set(self.plan),{'format','schemaVersion','securityIncluded','productionDefault','counts','customers'})
        self.assertFalse(self.plan['securityIncluded'])
        for c in self.plan['customers']:
            self.assertEqual(set(c),{'key','name','sourceCustomerId','commands','expected'})
            for command in c['commands']:
                self.assertEqual(set(command),{'type','payload','sourceResourceId','sourceCreatedIds'})
                self.assertIn(command['type'],builder.KINDS)

    def test_final_state_counts_and_post_receipt_gui_writes(self):
        counts={k:sum(len(c['expected'][k]) for c in self.plan['customers']) for k in builder.COLLECTIONS}
        self.assertEqual(counts,builder.COUNTS)
        self.assertEqual(sum(x['type']=='device.update' for c in self.plan['customers'] for x in c['commands']),10)
        original=json.loads(SOURCE.read_text(encoding='utf8'))
        old_connection_commands=sum(x['kind']=='connections.createBatch' for c in original for x in c['receipts'])
        self.assertEqual(sum(x['type']=='connections.createBatch' for c in self.plan['customers'] for x in c['commands'])-old_connection_commands,3)

    def test_unknown_route_kind_rejected(self):
        data=json.loads(SOURCE.read_text(encoding='utf8'));data[0]['receipts'][0]['kind']='admin.user.create'
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'receipt.json';p.write_text(json.dumps(data),encoding='utf8')
            with self.assertRaisesRegex(ValueError,'demo_command_invalid'):builder.build(p,PORTABLE)

    def test_source_customer_mismatch_rejected(self):
        data=json.loads(SOURCE.read_text(encoding='utf8'));data[0]['customerId']=data[1]['customerId']
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'receipt.json';p.write_text(json.dumps(data),encoding='utf8')
            with self.assertRaisesRegex(ValueError,'demo_source_binding_invalid'):builder.build(p,PORTABLE)

if __name__=='__main__':unittest.main()
