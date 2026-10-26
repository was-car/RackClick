import test from 'node:test';
import assert from 'node:assert/strict';
import {poeEnabled,poeBudget} from '../src/poe-budget.ts';
test('RC9 eligibility: legacy RJ45PoE, explicit OFF and non-RJ45 never inferred from watts',()=>{
 for(const p of [{type:'rj45',poe:true},{type:'rj45_poe'},{type:'rj45_poe',poe:null}])assert.equal(poeEnabled(p),true);
 for(const p of [{type:'rj45'},{type:'rj45',poe:false},{type:'rj45_poe',poe:false},{type:'power',poe:true},{type:'sfp',poe:true}])assert.equal(poeEnabled(p),false);
});
test('null is unknown, zero known; OFF watts9.5 and AC do not count; disabled/faulty remain ON',()=>{
 const ports=[{type:'rj45',poe:true,watts:null},{type:'rj45',poe:true,watts:0},{type:'rj45',poe:false,watts:9.5},{type:'power',watts:90},{type:'rj45_poe',poe:true,watts:5,status:'disabled'},{type:'rj45',poe:true,watts:2.5,status:'faulty'}];
 const original=structuredClone(ports);assert.deepEqual(poeBudget({poeBudget:0},ports),{sum:7.5,unknown:1,eligible:4,budget:0,exceeded:true,incomplete:true});assert.deepEqual(ports,original);
});
test('budget missing differs from zero; exact limit is not exceeded and unknown never declares complete',()=>{
 const ports=[{type:'rj45',poe:true,watts:5}];
 assert.deepEqual(poeBudget({poeBudget:null},ports),{sum:5,unknown:0,eligible:1,budget:null,exceeded:false,incomplete:true});
 assert.equal(poeBudget({poeBudget:0},ports).exceeded,true);assert.equal(poeBudget({poeBudget:5},ports).exceeded,false);assert.equal(poeBudget({poeBudget:5},ports).incomplete,false);
 assert.equal(poeBudget({poeBudget:5},[...ports,{type:'rj45',poe:true,watts:null}]).incomplete,true);
});
test('malformed watts and budget fail honest as unknown, never numeric strings/coerced0 or negative consumption',()=>{
 for(const watts of [undefined,null,NaN,Infinity,-1,'0'])assert.equal(poeBudget({poeBudget:10},[{type:'rj45',poe:true,watts}]).unknown,1);
 for(const poeBudgetValue of [undefined,null,NaN,Infinity,-1,'0'])assert.equal(poeBudget({poeBudget:poeBudgetValue},[]).budget,null);
});
test('fresh committed snapshots recompute, do not retain sums/budgets from previous state',()=>{
 const before={poeBudget:4},ports=[{type:'rj45',poe:false,watts:9.5}];assert.equal(poeBudget(before,ports).sum,0);
 const after=poeBudget({...before,poeBudget:0},ports.map(p=>({...p,poe:true})));assert.equal(after.sum,9.5);assert.equal(after.exceeded,true);assert.equal(ports[0].poe,false);
});
test('decimal equality 0.1+0.2 equals budget0.3 without false excess',()=>{
 const result=poeBudget({poeBudget:0.3},[0.1,0.2].map(watts=>({type:'rj45',poe:true,watts})));
 assert.equal(result.sum,0.3);assert.equal(result.exceeded,false);
});
test('decimal comparison preserves smallest real represented excess without arbitrary tolerance',()=>{
 const result=poeBudget({poeBudget:0.3},[0.1,0.20000000000000004].map(watts=>({type:'rj45',poe:true,watts})));
 assert.equal(result.exceeded,true);
});
test('decimal scientific notation aligns exponents without intermediate float overflow or underflow',()=>{
 const p=watts=>({type:'rj45',poe:true,watts});
 assert.equal(poeBudget({poeBudget:3e-7},[p(1e-7),p(2e-7)]).exceeded,false);
 assert.equal(poeBudget({poeBudget:3e-7},[p(1e-7),p(2.0000000000000002e-7)]).exceeded,true);
 assert.equal(poeBudget({poeBudget:1e308},[p(1e308),p(5e-324)]).exceeded,true);
 assert.equal(poeBudget({poeBudget:1e308},[p(1e308),p(5e-324)]).sum,1e308);
 assert.equal(poeBudget({poeBudget:1e-323},[p(5e-324),p(5e-324)]).exceeded,false);
});
