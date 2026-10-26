import test from 'node:test';
import assert from 'node:assert/strict';
import {prepareConnectionBatch} from '../src/connection-batch.ts';
const project=()=>({portGroups:[{id:'g1',deviceId:'a',type:'rj45'},{id:'g2',deviceId:'b',type:'rj45'}],ports:[{id:'a1',deviceId:'a',groupId:'g1',type:'rj45',gn:1,status:'free'},{id:'b1',deviceId:'b',groupId:'g2',type:'rj45',gn:1,status:'free'}],connections:[]});
const pairs=()=>[{from:{groupId:'g1',groupType:'rj45',portId:'a1'},to:{groupId:'g2',groupType:'rj45',portId:'b1'}}];
test('números repetidos no identifican extremos: IDs/grupo/tipo explícitos, uncomando atómico',()=>assert.deepEqual(prepareConnectionBatch(project(),pairs()),{type:'connections.createBatch',payload:{pairs:[{fromPortId:'a1',toPortId:'b1',color:null}],confirmedReservedPortIds:[]}}));
test('reserved requiereconfirmación exacta, sinincluirpuertoreservadoajeno',()=>{const p=project();p.ports[0].status='reserved';assert.throws(()=>prepareConnectionBatch(p,pairs()),{code:'reserved_confirmation_required'});assert.deepEqual(prepareConnectionBatch(p,pairs(),true).payload.confirmedReservedPortIds,['a1'])});
for(const [name,mutate,code]of[
 ['grupo',p=>p[0].from.groupId='g2','port_scope_invalid'],['tipo',p=>p[0].from.groupType='sfp','port_scope_invalid'],['duplicado',p=>p.push(p[0]),'duplicate_ids'],['vacío',p=>p.pop(),'pairs_required']
])test('rechaza '+name,()=>{const p=pairs();mutate(p);assert.throws(()=>prepareConnectionBatch(project(),p),{code})});
test('ocupado/disabled/faulty rechazanloteantesescritura',()=>{for(const status of ['disabled','faulty']){const p=project();p.ports[1].status=status;assert.throws(()=>prepareConnectionBatch(p,pairs()),{code:'blocked_port'})}const p=project();p.connections=[{fromPortId:'b1',toPortId:'x'}];assert.throws(()=>prepareConnectionBatch(p,pairs()),{code:'port_occupied'})});
