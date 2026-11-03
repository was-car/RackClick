import test from 'node:test';
import assert from 'node:assert/strict';
import {RackClickApi} from '../src/api.ts';
import {recoveryCodeFormat,validateRecoveryGeneration,generateRecoveryCodes,recoveryCodesReceipt,recoveryCodesJournal} from '../src/mfa-recovery.ts';
import {mfaRecoveryWords} from '../src/mfa-recovery-words.ts';
const id='11111111-1111-4111-8111-111111111111',other='22222222-2222-4222-8222-222222222222',requestId='33333333-3333-4333-8333-333333333333';
const draft={actorId:id,requestId,revision:2},codes=Array.from({length:10},(_,i)=>(i+1).toString(16).padStart(32,'0'));
const generation={userId:id,requestId,remaining:10,systemhausRevision:3,codesAvailable:true,codes};
const response=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json'}});
const session={user:{id,houseId:other,userName:'synthetic'},csrf:'new-session',permissions:{systemhausCapabilities:[],customers:[]}};
test('recovery replaces challenge only; API authority waits for new enrollment confirmation',async()=>{
 const calls=[];
 const api=new RackClickApi(async(path,init)=>{calls.push(path);
  if(path.endsWith('/auth/login'))return response({mfaRequired:true,purpose:'verify',csrf:'old-challenge'},202);
  if(path.endsWith('/recover')){assert.equal(init.headers['X-RackClick-CSRF'],'old-challenge');return response({mfaRequired:true,purpose:'enroll',csrf:'new-challenge'},202);}
  if(path.endsWith('/start')){assert.equal(init.headers['X-RackClick-CSRF'],'new-challenge');return response({secret:'JBSWY3DPEHPK3PXP',otpauth:'otpauth://totp/synthetic?secret=JBSWY3DPEHPK3PXP'});}
  if(path.endsWith('/confirm'))return response({csrf:'new-session'});
  if(path.endsWith('/me'))return response(session);throw Error('unexpected');
 });
 api.onMfaRequired=async old=>{const next=await api.recoverMfa(old,codes[0]);assert.equal(api.actorId,'');assert.equal(api.csrf,'');assert.equal(calls.some(p=>p.endsWith('/me')),false);
  await assert.rejects(api.verifyMfa(old,'123456'),e=>e.code==='mfa_challenge_invalid');await api.startMfaEnrollment(next);return api.confirmMfaEnrollment(next,'123456');};
 assert.deepEqual(await api.login('synthetic','not-stored'),session);assert.equal(calls.filter(p=>p.endsWith('/me')).length,1);
});
test('recovery rejects a normal session-shaped response and never calls me',async()=>{
 const calls=[];const api=new RackClickApi(async p=>{calls.push(p);return p.endsWith('/login')?response({mfaRequired:true,purpose:'verify',csrf:'challenge'},202):response({csrf:'session'});});
 api.onMfaRequired=c=>api.recoverMfa(c,codes[0]);await assert.rejects(api.login('synthetic','not-stored'),e=>e.code==='response_invalid');assert.equal(api.actorId,'');assert.equal(calls.some(p=>p.endsWith('/me')),false);
});
test('cancelled challenge cannot accept a delayed recovery result',async()=>{
 let release;const api=new RackClickApi(async p=>p.endsWith('/login')?response({mfaRequired:true,purpose:'verify',csrf:'challenge'},202):new Promise(r=>{release=r;}));
 api.onMfaRequired=async c=>{const pending=api.recoverMfa(c,codes[0]);api.cancelAuthentication();release(response({mfaRequired:true,purpose:'enroll',csrf:'next'},202));return pending;};
 await assert.rejects(api.login('synthetic','not-stored'));assert.equal(api.actorId,'');
});
test('recovery format is bounded and accepts grouped/un-grouped hex, not TOTP or arbitrary text',()=>{
 assert.ok(recoveryCodeFormat(codes[0]));assert.ok(recoveryCodeFormat(codes[0].match(/.{4}/g).join('-')));for(const v of ['123456','<img>',codes[0]+'0',null])assert.equal(recoveryCodeFormat(v),false);
});
test('code-free replay and receipt cannot redisclose values',()=>{
 assert.equal(validateRecoveryGeneration({...generation,codesAvailable:false,codes:null},draft,true).codes,null);
 assert.throws(()=>validateRecoveryGeneration(generation,draft,true),e=>e.code==='response_invalid');
 assert.throws(()=>validateRecoveryGeneration({...generation,codes:[...codes.slice(0,9),codes[0]]},draft),e=>e.code==='response_invalid');
});
test('generation is tied to actor, revision and request ID; it is not automatically retried',async()=>{
 let count=0;const api=new RackClickApi(async(p,init)=>{count++;assert.equal(p,'/api/v1/me/mfa/recovery-codes');assert.equal(init.headers['If-Match'],'"2"');assert.equal(init.headers['Idempotency-Key'],requestId);assert.equal(init.headers['X-RackClick-Actor'],id);return response(generation);});api.actorId=id;api.csrf='csrf';
 assert.deepEqual((await generateRecoveryCodes(api,draft,'not-stored')).codes,codes);assert.equal(count,1);api.actorId=other;await assert.rejects(generateRecoveryCodes(api,draft,'not-stored'),e=>e.code==='actor_changed');assert.equal(count,1);
});
test('actor change while generation is in flight does not disclose codes to the new actor',async()=>{
 let done;const api=new RackClickApi(()=>new Promise(r=>{done=r;}));api.actorId=id;api.csrf='csrf';const pending=generateRecoveryCodes(api,draft,'not-stored');api.actorId=other;done(response(generation));await assert.rejects(pending,e=>e.code==='actor_changed');
});
test('receipt lookup enforces original actor and rejects code-bearing receipts',async()=>{
 const api=new RackClickApi(async()=>response({recorded:true,requestId,result:generation}));api.actorId=id;await assert.rejects(recoveryCodesReceipt(api,draft),e=>e.code==='response_invalid');
});
test('journal contains only intent identifiers; secrets/extra fields are rejected before storage',()=>{
 const map=new Map(),storage={getItem:k=>map.get(k)||null,setItem:(k,v)=>map.set(k,v),removeItem:k=>map.delete(k)};
 recoveryCodesJournal('write',id,draft,storage);assert.deepEqual(recoveryCodesJournal('read',id,undefined,storage),draft);
 for(const secret of ['password','codes','secret'])assert.throws(()=>recoveryCodesJournal('write',id,{...draft,[secret]:'must-not-store'},storage));
 assert.equal([...map.values()].some(v=>v.includes('must-not-store')),false);recoveryCodesJournal('remove',id,draft,storage);assert.equal(map.size,0);
});
test('recovery UI exposes the same keys in all supported languages',()=>{
 const keys=Object.keys(mfaRecoveryWords.en).sort();for(const lang of ['de','es'])assert.deepEqual(Object.keys(mfaRecoveryWords[lang]).sort(),keys);
});
