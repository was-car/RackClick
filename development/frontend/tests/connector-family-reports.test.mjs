import test from 'node:test';
import assert from 'node:assert/strict';
import {reportColumns,validReportColumns,portReportColumns,connectionReportColumns} from '../src/inventory-reports.ts';
test('physical connector report extension preserves legacy column bytes and order',()=>{
 assert.deepEqual(reportColumns('ports'),portReportColumns);assert.deepEqual(reportColumns('connections'),connectionReportColumns);
 assert.ok(validReportColumns('ports',[portReportColumns]));assert.ok(validReportColumns('connections',[connectionReportColumns]));
});
for(const kind of ['ports','connections'])test(kind+' accepts exactly the typed optional extension and rejects mixed, forged or duplicate headers',()=>{
 const header=reportColumns(kind,true),row=header.map(()=>''),type=kind==='ports'?'type':'from_type',descriptor=kind==='ports'?'physical_connector':'from_physical_connector';
 row[header.indexOf(type)]='console';row[header.indexOf(descriptor)]='serial-10p10c';assert.ok(validReportColumns(kind,[header,row]));
 const forged=[...row];forged[header.indexOf(descriptor)]='iec-c14';assert.equal(validReportColumns(kind,[header,forged]),false);
 forged[header.indexOf(descriptor)]='serial-8p8c<img>';assert.equal(validReportColumns(kind,[header,forged]),false);
 assert.equal(validReportColumns(kind,[header,header.map(()=>'')]),false);
 assert.equal(validReportColumns(kind,[header]),false);
 assert.equal(validReportColumns(kind,[[...header].reverse(),row]),false);
 assert.equal(validReportColumns(kind,[[...header,'physical_connector'],[...row,'iec-c14']]),false);
 assert.equal(validReportColumns(kind,[header,row.slice(1)]),false);
});
