// Validate actual isolated-server responses through the same strict download gate.
import {readFile,writeFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
import {validateReportResult,decodeReportValue} from '../src/inventory-reports.ts';
import {validateSpreadsheetResult} from '../src/inventory-spreadsheet-reports.ts';
const [input,output]=process.argv.slice(2),fixtures=JSON.parse(await readFile(input,'utf8')),results=[];
for(const item of fixtures){
 const parsed=await (item.format==='csv'?validateReportResult:validateSpreadsheetResult)(item.data,item.operation);
 const header=parsed.rows[0],names=item.kind==='ports'?['physical_connector']:['from_physical_connector','to_physical_connector'];
 for(const name of names)assert.ok(header.includes(name));
 const values=parsed.rows.slice(1).flatMap(row=>names.map(name=>item.format==='csv'?decodeReportValue(row[header.indexOf(name)]):row[header.indexOf(name)]));
 assert.ok(values.includes('idc-110'));results.push({format:item.format,kind:item.kind,rows:parsed.rows.length-1,columns:header.length,descriptorPreserved:true});
}
assert.equal(results.length,4);await writeFile(output,JSON.stringify({result:'PASS',results},null,2)+'\n');
console.log(JSON.stringify({result:'PASS',responses:results.length}));
