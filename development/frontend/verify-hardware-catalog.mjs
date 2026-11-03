// Build-time consistency guard. Digests detect stale derivatives, not signatures.
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';

const source = 'development/hardware/catalog-source-v1.json';
const lock = 'development/hardware/catalog-schema16.lock.json';
const reference = 'development/frontend/src/hardware-reference.json';
const server = 'development/server/src/RackClick.Server/InventoryHardwareProfiles.Generated.cs';
const frontend = 'development/frontend/src/hardware-catalog.generated.json';
const sha = value => createHash('sha256').update(value).digest('hex');
export async function verifyHardwareCatalog(root) {
 const read = name => readFile(path.join(root, name));
 const manifest = JSON.parse(await read('development/hardware/catalog-generated.manifest.json'));
 if (manifest.formatVersion !== 1 || manifest.targetSchema !== 16 ||
     manifest.state !== 'synthetic_development_not_a_release' || !manifest.files ||
     Object.keys(manifest.files).sort().join('|') !== [server,frontend].sort().join('|')) throw Error('hardware_catalog_manifest_invalid');
 for (const [name,expected] of [[source,manifest.sourceSha256],[lock,manifest.lockSha256],[reference,manifest.referenceSha256],
                              [server,manifest.files[server]],[frontend,manifest.files[frontend]]]) {
  if (!/^[0-9a-f]{64}$/.test(expected) || sha(await read(name)) !== expected) throw Error('hardware_catalog_stale');
 }
}
export async function verifyCommercialHardwareCatalog(root) {
 const read = name => readFile(path.join(root,name));
 const manifest=JSON.parse(await read('development/hardware/catalog-commercial.manifest.json'));
 const inputs=['development/hardware/catalog-commercial-v1.json','development/hardware/catalog-schema18.lock.json','development/hardware/startech-c6panelutp241uft.facts.json','development/server/database/017-hardware-catalog.sql'];
 const files=['development/server/src/RackClick.Server/CommercialHardwareProfiles.Generated.cs','development/frontend/src/hardware-commercial.generated.json','development/server/database/018-commercial-hardware.sql'];
 const same=(actual,expected)=>actual&&Object.keys(actual).sort().join('|')===expected.sort().join('|');
 if(manifest.formatVersion!==1||manifest.targetSchema!==18||manifest.state!=='curated_development_not_a_release'||!same(manifest.inputs,inputs)||!same(manifest.files,files))throw Error('commercial_catalog_manifest_invalid');
 for(const [name,expected] of Object.entries({...manifest.inputs,...manifest.files})){
  if(!/^[0-9a-f]{64}$/.test(expected)||sha(await read(name))!==expected)throw Error('commercial_catalog_stale');
 }
}

export async function verifyArubaHardwareCatalog(root) {
 const read = name => readFile(path.join(root,name));
 const manifest=JSON.parse(await read('development/hardware/catalog-aruba.manifest.json'));
 const inputs=['development/hardware/catalog-aruba-v1.json','development/hardware/aruba-jl682a.facts.json','development/hardware/catalog-schema19.lock.json','development/server/database/018-commercial-hardware.sql'];
 const files=['development/server/src/RackClick.Server/ArubaHardwareProfiles.Generated.cs','development/frontend/src/hardware-aruba.generated.json','development/server/database/019-aruba-hardware.sql'];
 const same=(actual,expected)=>actual&&Object.keys(actual).sort().join('|')===expected.sort().join('|');
 if(manifest.formatVersion!==1||manifest.targetSchema!==19||manifest.state!=='curated_development_not_a_release'||!same(manifest.inputs,inputs)||!same(manifest.files,files))throw Error('aruba_catalog_manifest_invalid');
 for(const [name,expected] of Object.entries({...manifest.inputs,...manifest.files})){
  if(!/^[0-9a-f]{64}$/.test(expected)||sha(await read(name))!==expected)throw Error('aruba_catalog_stale');
 }
}

export async function verifyFortinetHardwareCatalog(root) {
 const read = name => readFile(path.join(root,name));
 const manifest=JSON.parse(await read('development/hardware/catalog-fortinet.manifest.json'));
 const inputs=['development/hardware/catalog-fortinet-v1.json','development/hardware/fortinet-fg60f.facts.json','development/hardware/catalog-schema20.lock.json','development/server/database/019-aruba-hardware.sql'];
 const files=['development/server/src/RackClick.Server/FortinetHardwareProfiles.Generated.cs','development/frontend/src/hardware-fortinet.generated.json','development/server/database/020-fortinet-hardware.sql'];
 const same=(actual,expected)=>actual&&Object.keys(actual).sort().join('|')===expected.sort().join('|');
 if(manifest.formatVersion!==1||manifest.targetSchema!==20||manifest.state!=='curated_development_not_a_release'||!same(manifest.inputs,inputs)||!same(manifest.files,files))throw Error('fortinet_catalog_manifest_invalid');
 for(const [name,expected] of Object.entries({...manifest.inputs,...manifest.files})){
  if(!/^[0-9a-f]{64}$/.test(expected)||sha(await read(name))!==expected)throw Error('fortinet_catalog_stale');
 }
}

export async function verifySynologyHardwareCatalog(root) {
 const read = name => readFile(path.join(root,name));
 const manifest=JSON.parse(await read('development/hardware/catalog-synology.manifest.json'));
 const inputs=['development/hardware/catalog-synology-v1.json','development/hardware/synology-rs1221plus.facts.json','development/hardware/catalog-schema21.lock.json','development/server/database/020-fortinet-hardware.sql'];
 const files=['development/server/src/RackClick.Server/SynologyHardwareProfiles.Generated.cs','development/frontend/src/hardware-synology.generated.json','development/server/database/021-synology-hardware.sql'];
 const same=(actual,expected)=>actual&&Object.keys(actual).sort().join('|')===expected.sort().join('|');
 if(manifest.formatVersion!==1||manifest.targetSchema!==21||manifest.state!=='curated_development_not_a_release'||!same(manifest.inputs,inputs)||!same(manifest.files,files))throw Error('synology_catalog_manifest_invalid');
 for(const [name,expected] of Object.entries({...manifest.inputs,...manifest.files})){
  if(!/^[0-9a-f]{64}$/.test(expected)||sha(await read(name))!==expected)throw Error('synology_catalog_stale');
 }
}

export async function verifyDiskStationHardwareCatalog(root) {
 const read = name => readFile(path.join(root,name));
 const manifest=JSON.parse(await read('development/hardware/catalog-diskstation.manifest.json'));
 const inputs=['development/hardware/catalog-diskstation-v1.json','development/hardware/synology-ds423plus.facts.json','development/hardware/catalog-schema22.lock.json','development/server/database/021-synology-hardware.sql'];
 const files=['development/server/src/RackClick.Server/DiskStationHardwareProfiles.Generated.cs','development/frontend/src/hardware-diskstation.generated.json','development/server/database/022-diskstation-hardware.sql'];
 const same=(actual,expected)=>actual&&Object.keys(actual).sort().join('|')===expected.sort().join('|');
 if(manifest.formatVersion!==1||manifest.targetSchema!==22||manifest.state!=='curated_development_not_a_release'||!same(manifest.inputs,inputs)||!same(manifest.files,files))throw Error('diskstation_catalog_manifest_invalid');
 for(const [name,expected] of Object.entries({...manifest.inputs,...manifest.files})){
  if(!/^[0-9a-f]{64}$/.test(expected)||sha(await read(name))!==expected)throw Error('diskstation_catalog_stale');
 }
}

export async function verifyQnapHardwareCatalog(root) {
 const read = name => readFile(path.join(root,name));
 const manifest=JSON.parse(await read('development/hardware/catalog-qnap.manifest.json'));
 const inputs=['development/hardware/catalog-qnap-v1.json','development/hardware/qnap-ts464-8g.facts.json','development/hardware/catalog-schema23.lock.json','development/server/database/022-diskstation-hardware.sql'];
 const files=['development/server/src/RackClick.Server/QnapHardwareProfiles.Generated.cs','development/frontend/src/hardware-qnap.generated.json','development/server/database/023-qnap-hardware.sql'];
 const same=(actual,expected)=>actual&&Object.keys(actual).sort().join('|')===expected.sort().join('|');
 if(manifest.formatVersion!==1||manifest.targetSchema!==23||manifest.state!=='curated_development_not_a_release'||!same(manifest.inputs,inputs)||!same(manifest.files,files))throw Error('qnap_catalog_manifest_invalid');
 for(const [name,expected] of Object.entries({...manifest.inputs,...manifest.files})){
  if(!/^[0-9a-f]{64}$/.test(expected)||sha(await read(name))!==expected)throw Error('qnap_catalog_stale');
 }
}

export async function verifyBatch50HardwareCatalog(root) {
 const read=name=>readFile(path.join(root,name));
 const manifest=JSON.parse(await read('development/hardware/catalog-batch50.manifest.json'));
 const inputs=['development/hardware/batch50/synology.json','development/hardware/batch50/qnap.json','development/hardware/batch50/network.json','development/hardware/catalog-schema24.lock.json','development/server/database/023-qnap-hardware.sql','tools/build_hardware_batch50.py'];
 const files=['development/server/src/RackClick.Server/Batch50HardwareProfiles.Generated.cs','development/frontend/src/hardware-batch50.generated.json','development/server/database/024-batch50-hardware.sql'];
 const same=(actual,expected)=>actual&&Object.keys(actual).sort().join('|')===expected.sort().join('|');
 if(manifest.formatVersion!==1||manifest.targetSchema!==24||manifest.state!=='curated_development_not_a_release'||!same(manifest.inputs,inputs)||!same(manifest.files,files))throw Error('batch50_catalog_manifest_invalid');
 for(const [name,expected]of Object.entries({...manifest.inputs,...manifest.files}))if(!/^[0-9a-f]{64}$/.test(expected)||sha(await read(name))!==expected)throw Error('batch50_catalog_stale');
}

export async function verifyBatch50BHardwareCatalog(root) {
 const read=name=>readFile(path.join(root,name));
 const manifest=JSON.parse(await read('development/hardware/catalog-batch50b.manifest.json'));
 const inputs=['development/hardware/batch50b/synology.json','development/hardware/batch50b/qnap.json','development/hardware/batch50b/network.json','development/hardware/catalog-schema25.lock.json','development/server/database/024-batch50-hardware.sql','tools/build_hardware_batch50.py','tools/build_hardware_batch50b.py',
  ...['aruba','commercial','diskstation','fortinet','qnap','source','synology'].map(n=>'development/hardware/catalog-'+n+'-v1.json'),
  ...['network','qnap','synology'].map(n=>'development/hardware/batch50/'+n+'.json')];
 const files=['development/server/src/RackClick.Server/Batch50BHardwareProfiles.Generated.cs','development/frontend/src/hardware-batch50b.generated.json','development/server/database/025-batch50b-hardware.sql'];
 const same=(actual,expected)=>actual&&Object.keys(actual).sort().join('|')===expected.sort().join('|');
 if(manifest.formatVersion!==1||manifest.targetSchema!==25||manifest.state!=='curated_development_not_a_release'||!same(manifest.inputs,inputs)||!same(manifest.files,files))throw Error('batch50b_catalog_manifest_invalid');
 for(const [name,expected]of Object.entries({...manifest.inputs,...manifest.files}))if(!/^[0-9a-f]{64}$/.test(expected)||sha(await read(name))!==expected)throw Error('batch50b_catalog_stale');
}

export async function verifyBatch100HardwareCatalog(root) {
 const read=name=>readFile(path.join(root,name));
 const manifest=JSON.parse(await read('development/hardware/catalog-batch100.manifest.json'));
 const inputs=['development/hardware/batch100/security.json','development/hardware/batch100/network.json','development/hardware/batch100/nas.json','development/hardware/catalog-schema26.lock.json','development/server/database/025-batch50b-hardware.sql','tools/build_hardware_batch50.py','tools/build_hardware_batch100.py',
  ...['aruba','commercial','diskstation','fortinet','qnap','source','synology'].map(n=>'development/hardware/catalog-'+n+'-v1.json'),
  ...['batch50','batch50b'].flatMap(folder=>['network','qnap','synology'].map(n=>'development/hardware/'+folder+'/'+n+'.json'))];
 const files=['development/server/src/RackClick.Server/Batch100HardwareProfiles.Generated.cs','development/frontend/src/hardware-batch100.generated.json','development/server/database/026-batch100-hardware.sql'];
 const same=(actual,expected)=>actual&&Object.keys(actual).sort().join('|')===expected.sort().join('|');
 if(manifest.formatVersion!==1||manifest.targetSchema!==26||manifest.state!=='curated_development_not_a_release'||!same(manifest.inputs,inputs)||!same(manifest.files,files))throw Error('batch100_catalog_manifest_invalid');
 for(const [name,expected]of Object.entries({...manifest.inputs,...manifest.files}))if(!/^[0-9a-f]{64}$/.test(expected)||sha(await read(name))!==expected)throw Error('batch100_catalog_stale');
}

export async function verifyBatch100BHardwareCatalog(root) {
 const read=name=>readFile(path.join(root,name));
 const manifest=JSON.parse(await read('development/hardware/catalog-batch100b.manifest.json'));
 const inputs=['development/hardware/batch100b/security.json','development/hardware/batch100b/network.json','development/hardware/batch100b/nas.json','development/hardware/catalog-schema27.lock.json','development/server/database/026-batch100-hardware.sql','tools/build_hardware_batch50.py','tools/build_hardware_batch100b.py',
  ...['aruba','commercial','diskstation','fortinet','qnap','source','synology'].map(n=>'development/hardware/catalog-'+n+'-v1.json'),
  ...['batch50','batch50b'].flatMap(folder=>['network','qnap','synology'].map(n=>'development/hardware/'+folder+'/'+n+'.json')),
  ...['nas','network','security'].map(n=>'development/hardware/batch100/'+n+'.json')];
 const files=['development/server/src/RackClick.Server/Batch100BHardwareProfiles.Generated.cs','development/frontend/src/hardware-batch100b.generated.json','development/server/database/027-batch100b-hardware.sql'];
 const same=(actual,expected)=>actual&&Object.keys(actual).sort().join('|')===expected.sort().join('|');
 if(manifest.formatVersion!==1||manifest.targetSchema!==27||manifest.state!=='curated_development_not_a_release'||!same(manifest.inputs,inputs)||!same(manifest.files,files))throw Error('batch100b_catalog_manifest_invalid');
 for(const [name,expected]of Object.entries({...manifest.inputs,...manifest.files}))if(!/^[0-9a-f]{64}$/.test(expected)||sha(await read(name))!==expected)throw Error('batch100b_catalog_stale');
}

export async function verifyBatch100CHardwareCatalog(root) {
 const read=name=>readFile(path.join(root,name));
 const manifest=JSON.parse(await read('development/hardware/catalog-batch100c.manifest.json'));
 const inputs=['development/hardware/batch100c/security.json','development/hardware/batch100c/network.json','development/hardware/batch100c/nas.json','development/hardware/catalog-schema28.lock.json','development/server/database/027-batch100b-hardware.sql','tools/build_hardware_batch50.py','tools/build_hardware_batch100c.py',
  ...['aruba','commercial','diskstation','fortinet','qnap','source','synology'].map(n=>'development/hardware/catalog-'+n+'-v1.json'),
  ...['batch50','batch50b'].flatMap(folder=>['network','qnap','synology'].map(n=>'development/hardware/'+folder+'/'+n+'.json')),
  ...['batch100','batch100b'].flatMap(folder=>['nas','network','security'].map(n=>'development/hardware/'+folder+'/'+n+'.json'))];
 const files=['development/server/src/RackClick.Server/Batch100CHardwareProfiles.Generated.cs','development/frontend/src/hardware-batch100c.generated.json','development/server/database/028-batch100c-hardware.sql'];
 const same=(actual,expected)=>actual&&Object.keys(actual).sort().join('|')===expected.sort().join('|');
 if(manifest.formatVersion!==1||manifest.targetSchema!==28||manifest.state!=='curated_development_not_a_release'||!same(manifest.inputs,inputs)||!same(manifest.files,files))throw Error('batch100c_catalog_manifest_invalid');
 for(const [name,expected]of Object.entries({...manifest.inputs,...manifest.files}))if(!/^[0-9a-f]{64}$/.test(expected)||sha(await read(name))!==expected)throw Error('batch100c_catalog_stale');
}

export async function verifySelected506AHardwareCatalog(root) {
 const read=name=>readFile(path.join(root,name));
 const manifest=JSON.parse(await read('development/hardware/catalog-selected506a.manifest.json'));
 const inputs=['development/hardware/selected506a/aruba.json','development/hardware/selected506a/ubiquiti.json','development/hardware/selected-models-506.json',
  'development/hardware/selection462/plan.json','development/hardware/catalog-schema29.lock.json',
  'development/server/database/028-batch100c-hardware.sql','tools/build_hardware_batch50.py','tools/build_hardware_selected506a.py',
  ...['aruba','commercial','diskstation','fortinet','qnap','source','synology'].map(n=>'development/hardware/catalog-'+n+'-v1.json'),
  ...['batch50','batch50b'].flatMap(folder=>['network','qnap','synology'].map(n=>'development/hardware/'+folder+'/'+n+'.json')),
  ...['batch100','batch100b','batch100c'].flatMap(folder=>['nas','network','security'].map(n=>'development/hardware/'+folder+'/'+n+'.json'))];
 const files=['development/server/src/RackClick.Server/Selected506AHardwareProfiles.Generated.cs',
  'development/frontend/src/hardware-selected506a.generated.json','development/server/database/029-selected506a-hardware.sql'];
 const same=(actual,expected)=>actual&&Object.keys(actual).sort().join('|')===[...expected].sort().join('|');
 const ids=['aruba-jl675a','aruba-r9y04a','nb-7b81ceb62353c88e','nb-90ee2ca04fd0e2d5',
  'nb-f505dfd941515251','nb-842ab89f3df610f2','nb-4f13830c6517574d','nb-a77e3ed47a30e394',
  'nb-adf2142c84f07df9','nb-f6915d5d3881b84d','nb-b331c13345891559','nb-3af5a2fcbefac97c',
  'nb-0c303ce9bca6c601','nb-d064231ab7e45734','nb-e5030fe747d79fe6','nb-eaa7b5f1797fad5b','nb-f83ce1b7723518c4'].sort();
 if(manifest.formatVersion!==1||manifest.targetSchema!==29||manifest.catalogKey!=='rackclick-selected506a'||
  manifest.state!=='curated_development_not_a_release'||!same(manifest.inputs,inputs)||!same(manifest.files,files)||
  JSON.stringify(manifest.selectionIds)!==JSON.stringify(ids))throw Error('selected506a_catalog_manifest_invalid');
 for(const [name,expected]of Object.entries({...manifest.inputs,...manifest.files}))
  if(!/^[0-9a-f]{64}$/.test(expected)||sha(await read(name))!==expected)throw Error('selected506a_catalog_stale');
}


export async function verifySelected506BHardwareCatalog(root) {
 const read=name=>readFile(path.join(root,name));
 const manifest=JSON.parse(await read('development/hardware/catalog-selected506b.manifest.json'));
 const inputs=["development/hardware/selected506b/core.json","development/hardware/selected506b/access.json","development/hardware/selected-models-506.json","development/hardware/selection462/plan.json","development/hardware/catalog-schema30.lock.json","development/server/database/029-selected506a-hardware.sql","tools/build_hardware_batch50.py","tools/build_hardware_selected506b.py","development/hardware/batch100/nas.json","development/hardware/batch100/network.json","development/hardware/batch100/security.json","development/hardware/batch100b/nas.json","development/hardware/batch100b/network.json","development/hardware/batch100b/security.json","development/hardware/batch100c/nas.json","development/hardware/batch100c/network.json","development/hardware/batch100c/security.json","development/hardware/batch50/network.json","development/hardware/batch50/qnap.json","development/hardware/batch50/synology.json","development/hardware/batch50b/network.json","development/hardware/batch50b/qnap.json","development/hardware/batch50b/synology.json","development/hardware/catalog-aruba-v1.json","development/hardware/catalog-commercial-v1.json","development/hardware/catalog-diskstation-v1.json","development/hardware/catalog-fortinet-v1.json","development/hardware/catalog-qnap-v1.json","development/hardware/catalog-source-v1.json","development/hardware/catalog-synology-v1.json","development/hardware/selected506a/aruba.json","development/hardware/selected506a/ubiquiti.json"];
 const files=["development/server/src/RackClick.Server/Selected506BHardwareProfiles.Generated.cs","development/frontend/src/hardware-selected506b.generated.json","development/server/database/030-selected506b-hardware.sql"];
 const ids=["nb-0323789c8aa37403","nb-0378e314e40b7a32","nb-06c19caa563462d0","nb-06d181bdfaacef1b","nb-0ae02d5176e83b35","nb-0e0d436b707c6222","nb-13db0a5351fdba7d","nb-1520b9b243e9bb38","nb-1629a1d59aad162f","nb-1e89ff3122676000","nb-2213f0b401bb1b4b","nb-22ec22b8ee2c893a","nb-25db6819881d422b","nb-2f1c864cfa97acee","nb-2ffc5d29f711ec36","nb-3a4c93d66b83c701","nb-491844a78b378fad","nb-4b21539470f6d751","nb-4b362a024923dd51","nb-4bed5077703a33ad","nb-553b794d5e1846af","nb-5bd28430fbf397fc","nb-6061e8a5e3e5a74c","nb-73489c7e191a0d9b","nb-746a1ccfbf605854","nb-759e188d649a5347","nb-7e1c09817aeccd5f","nb-88bc04bb88386c00","nb-8ab74e30b670198e","nb-938151a02eb5e5d0","nb-9445f595338fc17a","nb-98efee7ae64ea280","nb-9f4e39d04b4eef89","nb-a82a300904414f52","nb-b332648f50e7f0ed","nb-b3dc322f7f5ffa4d","nb-b789b2ec357d683f","nb-ba01da0f6a8e0932","nb-be67a5901b5f1fb8","nb-bf7b6e396d81b183","nb-c9dda6663d585595","nb-d4d0d201f9d0e748","nb-dc46d6be5cb5b6af","nb-dc6cdf07e279b4a0","nb-e6c2c9e3f06a3b7e","nb-edb5b19d211b3fd8","nb-f4684dfd15513291","nb-fc86b47706121d42","nb-fcc0548ac0e54478","nb-fedc94752959d1f9"];
 const same=(actual,expected)=>actual&&Object.keys(actual).sort().join('|')===[...expected].sort().join('|');
 if(manifest.formatVersion!==1||manifest.targetSchema!==30||manifest.catalogKey!=='rackclick-selected506b'||
  manifest.state!=='curated_development_not_a_release'||!same(manifest.inputs,inputs)||!same(manifest.files,files)||
  JSON.stringify(manifest.selectionIds)!==JSON.stringify(ids))throw Error('selected506b_catalog_manifest_invalid');
 for(const [name,expected]of Object.entries({...manifest.inputs,...manifest.files}))
  if(!/^[0-9a-f]{64}$/.test(expected)||sha(await read(name))!==expected)throw Error('selected506b_catalog_stale');
}


export async function verifySelected506CHardwareCatalog(root) {
 const read=name=>readFile(path.join(root,name));
 const manifest=JSON.parse(await read('development/hardware/catalog-selected506c.manifest.json'));
 const inputs=["development/hardware/selected506c/firewalls.json","development/hardware/selected506c/edge.json","development/hardware/selected-models-506.json","development/hardware/selected-profile-links.json","evidence/s1-20261101/integracion506c/PLAN-50.json","development/hardware/catalog-schema31.lock.json","development/server/database/030-selected506b-hardware.sql","tools/build_hardware_selected506b.py","tools/build_hardware_batch50.py","tools/build_hardware_selected506c.py","development/hardware/batch100/nas.json","development/hardware/batch100/network.json","development/hardware/batch100/security.json","development/hardware/batch100b/nas.json","development/hardware/batch100b/network.json","development/hardware/batch100b/security.json","development/hardware/batch100c/nas.json","development/hardware/batch100c/network.json","development/hardware/batch100c/security.json","development/hardware/batch50/network.json","development/hardware/batch50/qnap.json","development/hardware/batch50/synology.json","development/hardware/batch50b/network.json","development/hardware/batch50b/qnap.json","development/hardware/batch50b/synology.json","development/hardware/catalog-aruba-v1.json","development/hardware/catalog-commercial-v1.json","development/hardware/catalog-diskstation-v1.json","development/hardware/catalog-fortinet-v1.json","development/hardware/catalog-qnap-v1.json","development/hardware/catalog-source-v1.json","development/hardware/catalog-synology-v1.json","development/hardware/selected506a/aruba.json","development/hardware/selected506a/ubiquiti.json","development/hardware/selected506b/access.json","development/hardware/selected506b/core.json"];
 const files=["development/server/src/RackClick.Server/Selected506CHardwareProfiles.Generated.cs","development/frontend/src/hardware-selected506c.generated.json","development/server/database/031-selected506c-hardware.sql"];
 const ids=["cisco-isr4331","fortinet-fortigate-100f","fortinet-fortigate-80f","nb-026eafe7e1684a8c","nb-068b536b05b168d6","nb-083677535cff6791","nb-14b4f71277d991de","nb-1569935c143ae3b4","nb-16082636813a2c65","nb-1dda3b7e93aeec53","nb-229917b69a037991","nb-23bca6f7679f1595","nb-3c48ca91bd3e9e90","nb-5a7762f3d43d50a1","nb-5f2f318828e8a714","nb-60535d6487d8c516","nb-640a1e0ad66b9b51","nb-67a1252a6921143c","nb-6c1be13449ccaccb","nb-6c3c831ad8429c1d","nb-74505fc219eccc33","nb-7a9733566074ec15","nb-7e1f01ffe3e19e8a","nb-86babf3249d2b78a","nb-87d53966e8a77039","nb-8ad4df2cb7211e53","nb-8db15759990d4860","nb-908ff89d52fbb695","nb-91b2bc4ecae870e8","nb-920e5812c8fd4f87","nb-9b7461820cabfd63","nb-9e1720811fc797a6","nb-9e6429de560eb723","nb-9f034976d9130ca7","nb-a121938648f6b54a","nb-a954659fb87b4e11","nb-b953f55ddfc9d913","nb-bb280d4ca41dc95b","nb-c0a3827bad315c40","nb-c81defef5301d096","nb-d18ad51e4dbe98fd","nb-d71c560a21e0db1e","nb-dfed66cafdc81794","nb-ed10b6f53c36d127","nb-f545d3718ff68f34","nb-f9a7d60382905603","sophos-xg-135","sophos-xgs-116","sophos-xgs-138","ubiquiti-udm-pro"];
 const same=(actual,expected)=>actual&&Object.keys(actual).sort().join('|')===[...expected].sort().join('|');
 if(manifest.formatVersion!==1||manifest.targetSchema!==31||manifest.catalogKey!=='rackclick-selected506c'||
  manifest.state!=='curated_development_not_a_release'||!same(manifest.inputs,inputs)||!same(manifest.files,files)||
  JSON.stringify(manifest.selectionIds)!==JSON.stringify(ids))throw Error('selected506c_catalog_manifest_invalid');
 for(const [name,expected]of Object.entries({...manifest.inputs,...manifest.files}))
  if(!/^[0-9a-f]{64}$/.test(expected)||sha(await read(name))!==expected)throw Error('selected506c_catalog_stale');
}


export async function verifySelected506DHardwareCatalog(root) {
 const read=name=>readFile(path.join(root,name));
 const manifest=JSON.parse(await read('development/hardware/catalog-selected506d.manifest.json'));
 const inputs=["development/hardware/selected506d/core.json","development/hardware/selected506d/edge.json","development/hardware/selected-models-506.json","development/hardware/selected-profile-links.json","evidence/s1-20261101/integracion506d/PLAN-50.json","development/hardware/catalog-schema32.lock.json","development/server/database/031-selected506c-hardware.sql","tools/hardware_physical_v2.py","tools/build_hardware_batch50.py","tools/build_hardware_catalog.py","tools/build_hardware_catalog19.py","tools/build_hardware_catalog20.py","tools/build_hardware_catalog21.py","tools/build_hardware_catalog22.py","tools/build_hardware_catalog23.py","tools/build_hardware_selected506d.py","development/hardware/batch100/nas.json","development/hardware/batch100/network.json","development/hardware/batch100/security.json","development/hardware/batch100b/nas.json","development/hardware/batch100b/network.json","development/hardware/batch100b/security.json","development/hardware/batch100c/nas.json","development/hardware/batch100c/network.json","development/hardware/batch100c/security.json","development/hardware/batch50/network.json","development/hardware/batch50/qnap.json","development/hardware/batch50/synology.json","development/hardware/batch50b/network.json","development/hardware/batch50b/qnap.json","development/hardware/batch50b/synology.json","development/hardware/catalog-aruba-v1.json","development/hardware/catalog-commercial-v1.json","development/hardware/catalog-diskstation-v1.json","development/hardware/catalog-fortinet-v1.json","development/hardware/catalog-qnap-v1.json","development/hardware/catalog-source-v1.json","development/hardware/catalog-synology-v1.json","development/hardware/selected506a/aruba.json","development/hardware/selected506a/ubiquiti.json","development/hardware/selected506b/access.json","development/hardware/selected506b/core.json","development/hardware/selected506c/edge.json","development/hardware/selected506c/firewalls.json"];
 const files=["development/server/src/RackClick.Server/Selected506DHardwareProfiles.Generated.cs","development/frontend/src/hardware-selected506d.generated.json","development/server/database/032-selected506d-hardware.sql"];
 const ids=["nb-01d2c09685f7b01f","nb-0981324ffcccabc6","nb-1e541b78ab2e12a9","nb-22b5637a0a90560a","nb-2b0409c6beac1731","nb-40628e190c9e9ada","nb-41262e318167a929","nb-4c713694453b3ee3","nb-4d5610318b7474da","nb-56979e7752a9d231","nb-56ae91b8f6b2852d","nb-58601e584ebb26d1","nb-5cfeedda20abb6ba","nb-61497bf34bd5fcfd","nb-68e3c1e22fd81ed1","nb-6ba786cfed3ab9a5","nb-6d4a191cda45f6d1","nb-77e3ae7a8fab715b","nb-78642bb08e8fc74c","nb-8a9952b05c0840d1","nb-8f68dd201f3c0c5e","nb-9960b794c01f49b4","nb-99fbabbfd63a81ae","nb-9af4f14b030fd0a3","nb-9d2017e0aa6f2f3c","nb-a02305d3072dc01b","nb-a4126d6cef91ca26","nb-a864e7299035e225","nb-b93fdf2565924f3e","nb-c3a2a8dfb0d28694","nb-d827296bb530c875","nb-e043a5a21e4bc6c2","nb-e5b040471a978eae","nb-e83c62d66ebe38fa","nb-e98baee54dcf5404","nb-f0537901a8b1edc9","nb-f0851cec3521e33f","nb-f48a3b395614b14f","nb-f6e0bb626755510b","nb-fe00cb2fcd751efc","palo-alto-pa-3260","palo-alto-pa-3410","palo-alto-pa-3420","palo-alto-pa-3430","palo-alto-pa-3440","palo-alto-pa-5260","palo-alto-pa-5410","palo-alto-pa-5420","palo-alto-pa-5430","palo-alto-pa-5440"];
 const same=(actual,expected)=>actual&&Object.keys(actual).sort().join('|')===[...expected].sort().join('|');
 if(manifest.formatVersion!==1||manifest.targetSchema!==32||manifest.catalogKey!=='rackclick-selected506d'||
  manifest.state!=='curated_development_not_a_release'||!same(manifest.inputs,inputs)||!same(manifest.files,files)||
  JSON.stringify(manifest.selectionIds)!==JSON.stringify(ids))throw Error('selected506d_catalog_manifest_invalid');
 for(const [name,expected]of Object.entries({...manifest.inputs,...manifest.files}))
  if(!/^[0-9a-f]{64}$/.test(expected)||sha(await read(name))!==expected)throw Error('selected506d_catalog_stale');
}


export async function verifySelected506EHardwareCatalog(root) {
 const read=name=>readFile(path.join(root,name));
 const manifest=JSON.parse(await read('development/hardware/catalog-selected506e.manifest.json'));
 const inputs=["development/hardware/selected506e/core.json","development/hardware/selected506e/edge.json","development/hardware/selected-models-506.json","development/hardware/selected-profile-links.json","evidence/s1-20261101/integracion506e/PLAN-50.json","development/hardware/catalog-schema33.lock.json","development/server/database/032-selected506d-hardware.sql","tools/hardware_physical_v2.py","tools/build_hardware_batch50.py","tools/build_hardware_catalog.py","tools/build_hardware_catalog19.py","tools/build_hardware_catalog20.py","tools/build_hardware_catalog21.py","tools/build_hardware_catalog22.py","tools/build_hardware_catalog23.py","tools/build_hardware_selected506e.py","development/hardware/batch100/nas.json","development/hardware/batch100/network.json","development/hardware/batch100/security.json","development/hardware/batch100b/nas.json","development/hardware/batch100b/network.json","development/hardware/batch100b/security.json","development/hardware/batch100c/nas.json","development/hardware/batch100c/network.json","development/hardware/batch100c/security.json","development/hardware/batch50/network.json","development/hardware/batch50/qnap.json","development/hardware/batch50/synology.json","development/hardware/batch50b/network.json","development/hardware/batch50b/qnap.json","development/hardware/batch50b/synology.json","development/hardware/catalog-aruba-v1.json","development/hardware/catalog-commercial-v1.json","development/hardware/catalog-diskstation-v1.json","development/hardware/catalog-fortinet-v1.json","development/hardware/catalog-qnap-v1.json","development/hardware/catalog-source-v1.json","development/hardware/catalog-synology-v1.json","development/hardware/selected506a/aruba.json","development/hardware/selected506a/ubiquiti.json","development/hardware/selected506b/access.json","development/hardware/selected506b/core.json","development/hardware/selected506c/edge.json","development/hardware/selected506c/firewalls.json","development/hardware/selected506d/core.json","development/hardware/selected506d/edge.json"];
 const files=["development/server/src/RackClick.Server/Selected506EHardwareProfiles.Generated.cs","development/frontend/src/hardware-selected506e.generated.json","development/server/database/033-selected506e-hardware.sql"];
 const ids=["cisco-c9200l-24t-4g","cisco-c9200l-48p-4g","nb-00de5627d2ff4666","nb-0355b604a6794595","nb-0e6accdf31d7d113","nb-1adb46683cc91954","nb-24e436f8efc76877","nb-3a0dec7f06699680","nb-3b6043083efdc428","nb-44d618c14f1ee6e3","nb-520f1d7a35b7e950","nb-53d11b15f96aebfd","nb-56d658406c3821e4","nb-59ffa19030bec2db","nb-5e6bc5b25105aac2","nb-63eb4152092cd08f","nb-66c3ee1f91a9421d","nb-69510e57b0827c16","nb-6de5e10b8660c81a","nb-703a133fe021a249","nb-75adec80da5ff093","nb-7d81ebcda392315d","nb-823b267b5cd72e2c","nb-857386ff2603fa07","nb-858c4b2d8df65bb9","nb-89d64c27c959137e","nb-8daa73dfc2be1ec5","nb-99ab5630f088ba2c","nb-9d22e570931da32f","nb-b00080f2380582f6","nb-b68b49db7fee9c88","nb-ba797213d2a5841a","nb-c0ac0f175a7366e6","nb-c6ac814fdd7b9934","nb-c8a9b3d42f78ee94","nb-cd1c3bbe082c129d","nb-cf0f597e804145ae","nb-dc19eda57299b02a","nb-dd10d7331f22b8bf","nb-e2f5cc04c6ef0ee3","nb-e4457af07a020f38","nb-e94a1bc6fc227b74","nb-e9dabe5202e7c565","nb-ec11fe6fea97c18d","nb-f05a32f1a3f1d292","nb-f390c56e840a7483","palo-alto-pa-1410","palo-alto-pa-1420","palo-alto-pa-3220","ubiquiti-usw-24-poe"];
 const same=(actual,expected)=>actual&&Object.keys(actual).sort().join('|')===[...expected].sort().join('|');
 if(manifest.formatVersion!==1||manifest.targetSchema!==33||manifest.catalogKey!=='rackclick-selected506e'||
  manifest.state!=='curated_development_not_a_release'||!same(manifest.inputs,inputs)||!same(manifest.files,files)||
  JSON.stringify(manifest.selectionIds)!==JSON.stringify(ids))throw Error('selected506e_catalog_manifest_invalid');
 for(const [name,expected]of Object.entries({...manifest.inputs,...manifest.files}))
  if(!/^[0-9a-f]{64}$/.test(expected)||sha(await read(name))!==expected)throw Error('selected506e_catalog_stale');
}


export async function verifySelected506FHardwareCatalog(root) {
 const read=name=>readFile(path.join(root,name));
 const manifest=JSON.parse(await read('development/hardware/catalog-selected506f.manifest.json'));
 const inputs=["development/hardware/selected506f/core.json","development/hardware/selected506f/edge.json","development/hardware/selected-models-506.json","development/hardware/selected-profile-links.json","evidence/s1-20261101/integracion506f/PLAN-50.json","development/hardware/catalog-schema34.lock.json","development/server/database/033-selected506e-hardware.sql","tools/hardware_physical_v2.py","tools/build_hardware_batch50.py","tools/build_hardware_catalog.py","tools/build_hardware_catalog19.py","tools/build_hardware_catalog20.py","tools/build_hardware_catalog21.py","tools/build_hardware_catalog22.py","tools/build_hardware_catalog23.py","tools/build_hardware_selected506f.py","development/hardware/batch100/nas.json","development/hardware/batch100/network.json","development/hardware/batch100/security.json","development/hardware/batch100b/nas.json","development/hardware/batch100b/network.json","development/hardware/batch100b/security.json","development/hardware/batch100c/nas.json","development/hardware/batch100c/network.json","development/hardware/batch100c/security.json","development/hardware/batch50/network.json","development/hardware/batch50/qnap.json","development/hardware/batch50/synology.json","development/hardware/batch50b/network.json","development/hardware/batch50b/qnap.json","development/hardware/batch50b/synology.json","development/hardware/catalog-aruba-v1.json","development/hardware/catalog-commercial-v1.json","development/hardware/catalog-diskstation-v1.json","development/hardware/catalog-fortinet-v1.json","development/hardware/catalog-qnap-v1.json","development/hardware/catalog-source-v1.json","development/hardware/catalog-synology-v1.json","development/hardware/selected506a/aruba.json","development/hardware/selected506a/ubiquiti.json","development/hardware/selected506b/access.json","development/hardware/selected506b/core.json","development/hardware/selected506c/edge.json","development/hardware/selected506c/firewalls.json","development/hardware/selected506d/core.json","development/hardware/selected506d/edge.json","development/hardware/selected506e/core.json","development/hardware/selected506e/edge.json"];
 const files=["development/server/src/RackClick.Server/Selected506FHardwareProfiles.Generated.cs","development/frontend/src/hardware-selected506f.generated.json","development/server/database/034-selected506f-hardware.sql"];
 const ids=["dell-r350","hpe-dl360-gen10","nb-1397e3169b861f26","nb-149a66cfbe4b740e","nb-14bfeedc875ce4de","nb-1949dff7c63dc370","nb-22f6dc2225b95f69","nb-302f3fd979788f2e","nb-31017da140e60303","nb-33c7e52f1cb00564","nb-417dcd51ce56234d","nb-4b73963d18934c09","nb-4f6f5a063ccdaf07","nb-58396084a7d0cb50","nb-5ceaeace0476cada","nb-665e9fb0c5bbe24e","nb-6a0159c3c324ded0","nb-73980deb1c5f24bc","nb-775999426472421b","nb-7a4f104d07cdb0f2","nb-80c45eaf78955607","nb-87abdfb9366e4dcc","nb-90d3445d2598509a","nb-9363a14b01cfb299","nb-949bb6f1695a8037","nb-a177f34a640c5260","nb-b47c684d217e4ade","nb-b96a0faf83d55061","nb-c1f158f64ea1ee8a","nb-c2987ad4b24bf989","nb-c7a6bbe78d369445","nb-c7c438542f1254b3","nb-cb719f76ccc4e4c8","nb-cbcbd6a95a949d7a","nb-cd689cba786b2529","nb-ce11d1eae1be7887","nb-d0eebb2cb671d40b","nb-d532953f6aab1767","nb-d6c7e4ca54f24095","nb-d9ade587e7147b9a","nb-e9b61460b1aac8e0","nb-efc4c57b1d5c811d","nb-f7f404654aad4d5a","nb-fb93dfe85c1f7a8b","nb-fbdb4552eed0ee61","nb-fce19920137ab0c4","nb-fe8d278736262b7c","nb-ff98cf8f1bf55eb7","palo-alto-pa-415","palo-alto-pa-445"];
 const same=(actual,expected)=>actual&&Object.keys(actual).sort().join('|')===[...expected].sort().join('|');
 if(manifest.formatVersion!==1||manifest.targetSchema!==34||manifest.catalogKey!=='rackclick-selected506f'||
  manifest.state!=='curated_development_not_a_release'||!same(manifest.inputs,inputs)||!same(manifest.files,files)||
  JSON.stringify(manifest.selectionIds)!==JSON.stringify(ids))throw Error('selected506f_catalog_manifest_invalid');
 for(const [name,expected]of Object.entries({...manifest.inputs,...manifest.files}))
  if(!/^[0-9a-f]{64}$/.test(expected)||sha(await read(name))!==expected)throw Error('selected506f_catalog_stale');
}


export async function verifySelected506GHardwareCatalog(root) {
 const read=name=>readFile(path.join(root,name));
 const manifest=JSON.parse(await read('development/hardware/catalog-selected506g.manifest.json'));
 const inputs=["development/hardware/selected506g/core.json","development/hardware/selected506g/edge.json","development/hardware/selected-models-506.json","development/hardware/selected-profile-links.json","evidence/s1-20261101/integracion506g/PLAN-50.json","development/hardware/catalog-schema35.lock.json","development/server/database/034-selected506f-hardware.sql","tools/hardware_physical_v2.py","tools/build_hardware_batch50.py","tools/build_hardware_catalog.py","tools/build_hardware_catalog19.py","tools/build_hardware_catalog20.py","tools/build_hardware_catalog21.py","tools/build_hardware_catalog22.py","tools/build_hardware_catalog23.py","tools/build_hardware_selected506g.py","development/hardware/batch100/nas.json","development/hardware/batch100/network.json","development/hardware/batch100/security.json","development/hardware/batch100b/nas.json","development/hardware/batch100b/network.json","development/hardware/batch100b/security.json","development/hardware/batch100c/nas.json","development/hardware/batch100c/network.json","development/hardware/batch100c/security.json","development/hardware/batch50/network.json","development/hardware/batch50/qnap.json","development/hardware/batch50/synology.json","development/hardware/batch50b/network.json","development/hardware/batch50b/qnap.json","development/hardware/batch50b/synology.json","development/hardware/catalog-aruba-v1.json","development/hardware/catalog-commercial-v1.json","development/hardware/catalog-diskstation-v1.json","development/hardware/catalog-fortinet-v1.json","development/hardware/catalog-qnap-v1.json","development/hardware/catalog-source-v1.json","development/hardware/catalog-synology-v1.json","development/hardware/selected506a/aruba.json","development/hardware/selected506a/ubiquiti.json","development/hardware/selected506b/access.json","development/hardware/selected506b/core.json","development/hardware/selected506c/edge.json","development/hardware/selected506c/firewalls.json","development/hardware/selected506d/core.json","development/hardware/selected506d/edge.json","development/hardware/selected506e/core.json","development/hardware/selected506e/edge.json","development/hardware/selected506f/core.json","development/hardware/selected506f/edge.json"];
 const files=["development/server/src/RackClick.Server/Selected506GHardwareProfiles.Generated.cs","development/frontend/src/hardware-selected506g.generated.json","development/server/database/035-selected506g-hardware.sql"];
 const ids=["nb-021661043dd2d49f","nb-028e1d1cc36b14e6","nb-0c237b37d9df0ddb","nb-0e9380b77257926e","nb-15047e48f0df3f18","nb-177693053e26efa4","nb-18abeefcccac198a","nb-22aef0e6cd06d2b7","nb-2565622a0959d865","nb-2b88f84c9db567bf","nb-2cb44217d425b70f","nb-32bb124abaaa021b","nb-34f23e64e816971f","nb-35d87f3fc5c78828","nb-36567f277193e94e","nb-418d42c0d18a34a4","nb-4a0b0e3bbe63b84a","nb-5d4d2d2ec5a6b81b","nb-5eb1039c16a0df6a","nb-672799eaa4f759d6","nb-75df9fe3366f5eba","nb-765b000f7862b2a5","nb-79c9c5a3726513c9","nb-7a6f331eb573b567","nb-7b7fd92e11204896","nb-9127f2021330b9a8","nb-948fad2f13709dc9","nb-9c4abe55a270318f","nb-a8af9348bfc46f13","nb-b1f6fce68b44bdac","nb-c263db2c3b4a2925","nb-c5937f7093956ec3","nb-c6b1705740436107","nb-d3f25e78482e4bff","nb-d45ace2059d491dd","nb-d7b89b29215a9708","nb-e4121ee57f092985","nb-e54b976f708867aa","nb-ec99b9ef925f518f","nb-ecabe45d7f7fcc48","nb-eda39086bd9e9cda","nb-f5940bcac5635cc5","nb-f73dd791a2fc73e8","nb-f802ebc80b7bb96e","nb-fb08077e5b9dd1cd","nb-fe8f97a3849d4e66","nb-feb9fd36baf516b8","palo-alto-pa-5445","palo-alto-pa-5450","sonicwall-tz370w"];
 const same=(actual,expected)=>actual&&Object.keys(actual).sort().join('|')===[...expected].sort().join('|');
 if(manifest.formatVersion!==1||manifest.targetSchema!==35||manifest.catalogKey!=='rackclick-selected506g'||
  manifest.state!=='curated_development_not_a_release'||!same(manifest.inputs,inputs)||!same(manifest.files,files)||
  JSON.stringify(manifest.selectionIds)!==JSON.stringify(ids))throw Error('selected506g_catalog_manifest_invalid');
 for(const [name,expected]of Object.entries({...manifest.inputs,...manifest.files}))
  if(!/^[0-9a-f]{64}$/.test(expected)||sha(await read(name))!==expected)throw Error('selected506g_catalog_stale');

 // Authoring names become server group names; the frontend projection omits them.
 // Count raw Unicode scalars, with stricter authoring checks and no normalization.
 for(const source of ['development/hardware/selected506g/core.json','development/hardware/selected506g/edge.json'])
  for(const row of JSON.parse(await read(source)).models)for(const group of row.definition.groups){
   const name=group.name;
   if(typeof name!=='string'||!name.trim()||Array.from(name).length>100||/[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u.test(name))
    throw Error('selected506g_group_name_invalid');
  }
}


export async function verifySelected506HHardwareCatalog(root) {
 const read=name=>readFile(path.join(root,name));
 const manifest=JSON.parse(await read('development/hardware/catalog-selected506h.manifest.json'));
 const inputs=["development/hardware/selected506h/aruba.json","development/hardware/selected506h/nokia.json","development/hardware/selected-models-506.json","development/hardware/selected-profile-links.json","evidence/s1-20261101/integracion506h/PLAN-6.json","development/hardware/catalog-schema37.lock.json","development/server/database/036-physical-media.sql","tools/hardware_physical_v3.py","tools/build_hardware_batch50.py","tools/hardware_physical_v2.py","tools/build_hardware_catalog.py","tools/build_hardware_catalog19.py","tools/build_hardware_catalog20.py","tools/build_hardware_catalog21.py","tools/build_hardware_catalog22.py","tools/build_hardware_catalog23.py","tools/build_hardware_selected506h.py","development/hardware/batch100/nas.json","development/hardware/batch100/network.json","development/hardware/batch100/security.json","development/hardware/batch100b/nas.json","development/hardware/batch100b/network.json","development/hardware/batch100b/security.json","development/hardware/batch100c/nas.json","development/hardware/batch100c/network.json","development/hardware/batch100c/security.json","development/hardware/batch50/network.json","development/hardware/batch50/qnap.json","development/hardware/batch50/synology.json","development/hardware/batch50b/network.json","development/hardware/batch50b/qnap.json","development/hardware/batch50b/synology.json","development/hardware/catalog-aruba-v1.json","development/hardware/catalog-commercial-v1.json","development/hardware/catalog-diskstation-v1.json","development/hardware/catalog-fortinet-v1.json","development/hardware/catalog-qnap-v1.json","development/hardware/catalog-source-v1.json","development/hardware/catalog-synology-v1.json","development/hardware/selected506a/aruba.json","development/hardware/selected506a/ubiquiti.json","development/hardware/selected506b/access.json","development/hardware/selected506b/core.json","development/hardware/selected506c/edge.json","development/hardware/selected506c/firewalls.json","development/hardware/selected506d/core.json","development/hardware/selected506d/edge.json","development/hardware/selected506e/core.json","development/hardware/selected506e/edge.json","development/hardware/selected506f/core.json","development/hardware/selected506f/edge.json","development/hardware/selected506g/core.json","development/hardware/selected506g/edge.json"];
 const files=["development/server/src/RackClick.Server/Selected506HHardwareProfiles.Generated.cs","development/frontend/src/hardware-selected506h.generated.json","development/server/database/037-selected506h-hardware.sql"];
 const ids=["nb-086e891acea2817b","nb-14eb45daaa9298fa","nb-460527db3780ce3d","nb-51dcd09a4e5de9b0","nb-dbb1fdc53d9b42a1","nb-f9014eaa7cd819dc"];
 const same=(actual,expected)=>actual&&Object.keys(actual).sort().join('|')===[...expected].sort().join('|');
 if(manifest.formatVersion!==1||manifest.targetSchema!==37||manifest.catalogKey!=='rackclick-selected506h'||
  manifest.state!=='curated_development_not_a_release'||!same(manifest.inputs,inputs)||!same(manifest.files,files)||
  JSON.stringify(manifest.selectionIds)!==JSON.stringify(ids))throw Error('selected506h_catalog_manifest_invalid');
 for(const [name,expected]of Object.entries({...manifest.inputs,...manifest.files}))
  if(!/^[0-9a-f]{64}$/.test(expected)||sha(await read(name))!==expected)throw Error('selected506h_catalog_stale');

 // Authoring names become server group names; the frontend projection omits them.
 // Count raw Unicode scalars, with stricter authoring checks and no normalization.
 for(const source of ['development/hardware/selected506h/aruba.json','development/hardware/selected506h/nokia.json'])
  for(const row of JSON.parse(await read(source)).models)for(const group of row.definition.groups){
   const name=group.name,prefix=group.prefix;
   if(typeof name!=='string'||!name.trim()||Array.from(name).length>100||/[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u.test(name))
    throw Error('selected506h_group_name_invalid');
   if(typeof prefix!=='string'||Array.from(prefix).length>100||/[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u.test(prefix))throw Error('selected506h_group_prefix_invalid');
  }
}


export async function verifySelected506IHardwareCatalog(root) {
 const read=name=>readFile(path.join(root,name));
 const manifest=JSON.parse(await read('development/hardware/catalog-selected506i.manifest.json'));
 const inputs=["development/hardware/selected506i/enterprise.json","development/hardware/selected506i/transport.json","development/hardware/selected-models-506.json","development/hardware/selected-profile-links.json","evidence/s1-20261101/integracion506i/PLAN-6.json","development/hardware/catalog-schema38.lock.json","development/server/database/037-selected506h-hardware.sql","tools/hardware_physical_v3.py","tools/build_hardware_batch50.py","tools/hardware_physical_v2.py","tools/build_hardware_catalog.py","tools/build_hardware_catalog19.py","tools/build_hardware_catalog20.py","tools/build_hardware_catalog21.py","tools/build_hardware_catalog22.py","tools/build_hardware_catalog23.py","tools/build_hardware_selected506i.py","development/hardware/batch100/nas.json","development/hardware/batch100/network.json","development/hardware/batch100/security.json","development/hardware/batch100b/nas.json","development/hardware/batch100b/network.json","development/hardware/batch100b/security.json","development/hardware/batch100c/nas.json","development/hardware/batch100c/network.json","development/hardware/batch100c/security.json","development/hardware/batch50/network.json","development/hardware/batch50/qnap.json","development/hardware/batch50/synology.json","development/hardware/batch50b/network.json","development/hardware/batch50b/qnap.json","development/hardware/batch50b/synology.json","development/hardware/catalog-aruba-v1.json","development/hardware/catalog-commercial-v1.json","development/hardware/catalog-diskstation-v1.json","development/hardware/catalog-fortinet-v1.json","development/hardware/catalog-qnap-v1.json","development/hardware/catalog-source-v1.json","development/hardware/catalog-synology-v1.json","development/hardware/selected506a/aruba.json","development/hardware/selected506a/ubiquiti.json","development/hardware/selected506b/access.json","development/hardware/selected506b/core.json","development/hardware/selected506c/edge.json","development/hardware/selected506c/firewalls.json","development/hardware/selected506d/core.json","development/hardware/selected506d/edge.json","development/hardware/selected506e/core.json","development/hardware/selected506e/edge.json","development/hardware/selected506f/core.json","development/hardware/selected506f/edge.json","development/hardware/selected506g/core.json","development/hardware/selected506g/edge.json","development/hardware/selected506h/aruba.json","development/hardware/selected506h/nokia.json"];
 const files=["development/server/src/RackClick.Server/Selected506IHardwareProfiles.Generated.cs","development/frontend/src/hardware-selected506i.generated.json","development/server/database/038-selected506i-hardware.sql"];
 const ids=["nb-015e42f0df73715b","nb-268313b973eee49c","nb-595b36736b9f95f2","nb-5bbf29fdc1f2fb3c","palo-alto-pa-5580"];
 const same=(actual,expected)=>actual&&Object.keys(actual).sort().join('|')===[...expected].sort().join('|');
 if(manifest.formatVersion!==1||manifest.targetSchema!==38||manifest.catalogKey!=='rackclick-selected506i'||
  manifest.state!=='curated_development_not_a_release'||!same(manifest.inputs,inputs)||!same(manifest.files,files)||
  JSON.stringify(manifest.selectionIds)!==JSON.stringify(ids))throw Error('selected506i_catalog_manifest_invalid');
 for(const [name,expected]of Object.entries({...manifest.inputs,...manifest.files}))
  if(!/^[0-9a-f]{64}$/.test(expected)||sha(await read(name))!==expected)throw Error('selected506i_catalog_stale');

 // Authoring names become server group names; the frontend projection omits them.
 // Count raw Unicode scalars, with stricter authoring checks and no normalization.
 for(const source of ['development/hardware/selected506i/enterprise.json','development/hardware/selected506i/transport.json'])
  for(const row of JSON.parse(await read(source)).models)for(const group of row.definition.groups){
   const name=group.name,prefix=group.prefix;
   if(typeof name!=='string'||!name.trim()||Array.from(name).length>100||/[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u.test(name))
    throw Error('selected506i_group_name_invalid');
   if(typeof prefix!=='string'||Array.from(prefix).length>100||/[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u.test(prefix))throw Error('selected506i_group_prefix_invalid');
  }
}


export async function verifySelected506JHardwareCatalog(root) {
 const read=name=>readFile(path.join(root,name));
 const manifest=JSON.parse(await read('development/hardware/catalog-selected506j.manifest.json'));
 const inputs=["development/hardware/selected506j/passive-panels.json","development/hardware/selected506j/access-points.json","development/hardware/selected-models-506.json","development/hardware/selected-profile-links.json","evidence/s1-20261101/integracion506j/PLAN-FAMILIAS.json","development/hardware/catalog-schema39.lock.json","development/server/database/038-selected506i-hardware.sql","tools/hardware_passive_family_v1.py","tools/build_hardware_batch50.py","tools/hardware_physical_v3.py","tools/hardware_physical_v2.py","tools/build_hardware_catalog.py","tools/build_hardware_catalog19.py","tools/build_hardware_catalog20.py","tools/build_hardware_catalog21.py","tools/build_hardware_catalog22.py","tools/build_hardware_catalog23.py","tools/build_hardware_selected506j.py","development/hardware/batch100/nas.json","development/hardware/batch100/network.json","development/hardware/batch100/security.json","development/hardware/batch100b/nas.json","development/hardware/batch100b/network.json","development/hardware/batch100b/security.json","development/hardware/batch100c/nas.json","development/hardware/batch100c/network.json","development/hardware/batch100c/security.json","development/hardware/batch50/network.json","development/hardware/batch50/qnap.json","development/hardware/batch50/synology.json","development/hardware/batch50b/network.json","development/hardware/batch50b/qnap.json","development/hardware/batch50b/synology.json","development/hardware/catalog-aruba-v1.json","development/hardware/catalog-commercial-v1.json","development/hardware/catalog-diskstation-v1.json","development/hardware/catalog-fortinet-v1.json","development/hardware/catalog-qnap-v1.json","development/hardware/catalog-source-v1.json","development/hardware/catalog-synology-v1.json","development/hardware/selected506a/aruba.json","development/hardware/selected506a/ubiquiti.json","development/hardware/selected506b/access.json","development/hardware/selected506b/core.json","development/hardware/selected506c/edge.json","development/hardware/selected506c/firewalls.json","development/hardware/selected506d/core.json","development/hardware/selected506d/edge.json","development/hardware/selected506e/core.json","development/hardware/selected506e/edge.json","development/hardware/selected506f/core.json","development/hardware/selected506f/edge.json","development/hardware/selected506g/core.json","development/hardware/selected506g/edge.json","development/hardware/selected506h/aruba.json","development/hardware/selected506h/nokia.json","development/hardware/selected506i/enterprise.json","development/hardware/selected506i/transport.json"];
 const files=["development/server/src/RackClick.Server/Selected506JHardwareProfiles.Generated.cs","development/frontend/src/hardware-selected506j.generated.json","development/server/database/039-selected506j-hardware.sql"];
 const ids=["nb-0b8ba8c517126e6a","nb-3ee579cb14778d23","nb-47531f3ce888df83","nb-86a48551b44be392","nb-88aa53e158b54b05","nb-b0fab63898dd7024","nb-bf62e427e934e0d4","nb-c06c7dc6eccf5e90","nb-c391d0a9345caadb","nb-e5e2d32326c01d41","nb-e8d124c1106f5ffd","nb-f0cd8b333b81d486","nb-f2e21430ea7914ec"];
 const same=(actual,expected)=>actual&&Object.keys(actual).sort().join('|')===[...expected].sort().join('|');
 if(manifest.formatVersion!==1||manifest.targetSchema!==39||manifest.catalogKey!=='rackclick-selected506j'||
  manifest.state!=='curated_development_not_a_release'||!same(manifest.inputs,inputs)||!same(manifest.files,files)||
  JSON.stringify(manifest.selectionIds)!==JSON.stringify(ids))throw Error('selected506j_catalog_manifest_invalid');
 for(const [name,expected]of Object.entries({...manifest.inputs,...manifest.files}))
  if(!/^[0-9a-f]{64}$/.test(expected)||sha(await read(name))!==expected)throw Error('selected506j_catalog_stale');

 // Authoring names become server group names; the frontend projection omits them.
 // Count raw Unicode scalars, with stricter authoring checks and no normalization.
 for(const source of ['development/hardware/selected506j/passive-panels.json','development/hardware/selected506j/access-points.json'])
  for(const row of JSON.parse(await read(source)).models)for(const group of row.definition.groups){
   const name=group.name,prefix=group.prefix;
   if(typeof name!=='string'||!name.trim()||Array.from(name).length>100||/[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u.test(name))
    throw Error('selected506j_group_name_invalid');
   if(typeof prefix!=='string'||Array.from(prefix).length>100||/[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u.test(prefix))throw Error('selected506j_group_prefix_invalid');
  }

 for(const [source,passive] of [
  ['development/hardware/selected506j/passive-panels.json',true],
  ['development/hardware/selected506j/access-points.json',false]])
  for(const row of JSON.parse(await read(source)).models){
   const definition=row.definition,rule=definition.passthrough,groups=definition.groups;
   if(!passive){if(rule!==null)throw Error('selected506j_continuity_invalid');continue;}
   const keys=['frontGroup','rearGroup','count','mapping','tracingAvailable'];
   if(!rule||!same(rule,keys)||rule.mapping!=='one-to-one'||rule.tracingAvailable!==false||
    !Number.isInteger(rule.count)||rule.count<1||rule.count>96||groups.length!==2||
    groups.some(g=>g.type!=='rj45'||g.powerRole!=='unspecified')||
    typeof rule.frontGroup!=='string'||typeof rule.rearGroup!=='string'||rule.frontGroup===rule.rearGroup)
     throw Error('selected506j_continuity_invalid');
   const front=groups.find(g=>g.key===rule.frontGroup),rear=groups.find(g=>g.key===rule.rearGroup);
   if(!front||!rear||front.face!=='front'||rear.face!=='rear'||front.count!==rule.count||rear.count!==rule.count)
    throw Error('selected506j_continuity_invalid');
  }
}


export async function verifySelected506KHardwareCatalog(root) {
 const read=name=>readFile(path.join(root,name));
 const manifest=JSON.parse(await read('development/hardware/catalog-selected506k.manifest.json'));
 const inputs=["development/hardware/selected506k/power.json","development/hardware/selected506k/passive.json","development/hardware/selected506k/mechanical.json","development/hardware/selected506k/storage.json","development/hardware/selected506k/serial.json","development/hardware/selected-models-506.json","development/hardware/selected-profile-links.json","evidence/s1-20261101/integracion506k/PLAN-FAMILIAS.json","development/hardware/catalog-schema41.lock.json","development/server/database/040-hardware-families.sql","development/server/database/039-selected506j-hardware.sql","development/hardware/selected506k/support.json","tools/hardware_family_v2.py","tools/build_hardware_batch50.py","tools/hardware_physical_v3.py","tools/hardware_physical_v2.py","tools/build_hardware_catalog.py","tools/build_hardware_catalog19.py","tools/build_hardware_catalog20.py","tools/build_hardware_catalog21.py","tools/build_hardware_catalog22.py","tools/build_hardware_catalog23.py","tools/build_hardware_selected506k.py","development/hardware/batch100/nas.json","development/hardware/batch100/network.json","development/hardware/batch100/security.json","development/hardware/batch100b/nas.json","development/hardware/batch100b/network.json","development/hardware/batch100b/security.json","development/hardware/batch100c/nas.json","development/hardware/batch100c/network.json","development/hardware/batch100c/security.json","development/hardware/batch50/network.json","development/hardware/batch50/qnap.json","development/hardware/batch50/synology.json","development/hardware/batch50b/network.json","development/hardware/batch50b/qnap.json","development/hardware/batch50b/synology.json","development/hardware/catalog-aruba-v1.json","development/hardware/catalog-commercial-v1.json","development/hardware/catalog-diskstation-v1.json","development/hardware/catalog-fortinet-v1.json","development/hardware/catalog-qnap-v1.json","development/hardware/catalog-source-v1.json","development/hardware/catalog-synology-v1.json","development/hardware/selected506a/aruba.json","development/hardware/selected506a/ubiquiti.json","development/hardware/selected506b/access.json","development/hardware/selected506b/core.json","development/hardware/selected506c/edge.json","development/hardware/selected506c/firewalls.json","development/hardware/selected506d/core.json","development/hardware/selected506d/edge.json","development/hardware/selected506e/core.json","development/hardware/selected506e/edge.json","development/hardware/selected506f/core.json","development/hardware/selected506f/edge.json","development/hardware/selected506g/core.json","development/hardware/selected506g/edge.json","development/hardware/selected506h/aruba.json","development/hardware/selected506h/nokia.json","development/hardware/selected506i/enterprise.json","development/hardware/selected506i/transport.json","development/hardware/selected506j/access-points.json","development/hardware/selected506j/passive-panels.json"];
 const files=["development/server/src/RackClick.Server/Selected506KHardwareProfiles.Generated.cs","development/frontend/src/hardware-selected506k.generated.json","development/server/database/041-selected506k-hardware.sql"];
 const ids=["apc-smt1500rmi2u","eaton-5px1500irt2ug2","nb-04f3c36861d3b6f5","nb-07e5ff352f97fad1","nb-08b0ee66b1eb36c8","nb-0ada4f1bb27f261c","nb-1157b9a10bc8e5f4","nb-15a85a8a3b05a92f","nb-19ed1459663d3e17","nb-1b78d3ee187d5923","nb-21d28e7d5a06429b","nb-23088fe782f499ac","nb-29ce493b266db9c3","nb-2d5dd2ca4dacb1c5","nb-476a5e2e14826616","nb-4b2e4c72b9d36b73","nb-4de91d17b80dbbff","nb-503a26493f9206a4","nb-624f4c89a65b309a","nb-682f01a7e3775f50","nb-70f105515d0bf559","nb-75ff355641be29f1","nb-78fb5e27dc863dbc","nb-7dd2b21e61ad99a0","nb-7ea04d02eec80c94","nb-81391abd9812b183","nb-8575f3e84e37fd0d","nb-908a100c3ca29495","nb-93773a73e59631e4","nb-9b748f4aeb7c8a2d","nb-a30f5454503d7402","nb-a6a79509854ba38b","nb-a966d159c428b1d4","nb-aa67f910589a5502","nb-b924dbf6777c2eb2","nb-bdf6ab2dce05aee0","nb-c2814dde21fa98df","nb-c7a1f257de229c1c","nb-c91a00ac9965db90","nb-ce5e88c6a9b7562d","nb-d14bed6bc445f3b0","nb-d3866e263332a4fc","nb-d9eff11e7e0c11f7","nb-dbdce8efed0e65d8","nb-de900000f3f9295d","nb-e195af6788f9b56c","nb-edde85c1a3ba283d","nb-f060040e382de573","nb-f5d26f8fec76743c","nb-f9fc50287eafd86c","raritan-px3-5190r","startech-cabshelf1u"];
 const same=(actual,expected)=>actual&&Object.keys(actual).sort().join('|')===[...expected].sort().join('|');
 if(manifest.formatVersion!==1||manifest.targetSchema!==41||manifest.catalogKey!=='rackclick-selected506k'||
  manifest.state!=='curated_development_not_a_release'||!same(manifest.inputs,inputs)||!same(manifest.files,files)||
  JSON.stringify(manifest.selectionIds)!==JSON.stringify(ids))throw Error('selected506k_catalog_manifest_invalid');
 for(const [name,expected]of Object.entries({...manifest.inputs,...manifest.files}))
  if(!/^[0-9a-f]{64}$/.test(expected)||sha(await read(name))!==expected)throw Error('selected506k_catalog_stale');


 const forms={"power":["iec-c13","iec-c14","iec-c19","iec-c20","nema-5-15p","nema-5-15r","nema-5-20p","nema-5-20r","nema-l5-30p","nema-l5-30r","nema-l6-20p","nema-l6-20r","nema-l6-30p","nema-l6-30r","iec60309-16a-2p-e-plug","iec60309-16a-2p-e-connector","iec60309-32a-2p-e-plug"],"console":["serial-8p8c","serial-10p10c","serial-de9","serial-rj12"],"idc":["idc-110","idc-dual-110-krone"]};
 for(const source of ["development/hardware/selected506k/power.json","development/hardware/selected506k/passive.json","development/hardware/selected506k/mechanical.json","development/hardware/selected506k/storage.json","development/hardware/selected506k/serial.json"])
  for(const row of JSON.parse(await read(source)).models){
   const model=row.definition,groups=model.groups;
   for(const group of groups){
    if(typeof group.name!=='string'||!group.name.trim()||Array.from(group.name).length>100||/[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u.test(group.name))throw Error('selected506k_group_name_invalid');
    if(typeof group.prefix!=='string'||Array.from(group.prefix).length>100||/[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u.test(group.prefix))throw Error('selected506k_group_prefix_invalid');
    if(group.physicalConnector!=null&&!forms[group.type]?.includes(group.physicalConnector))throw Error('selected506k_physical_connector_invalid');
   }
   const rule=model.passthrough;if(rule==null)continue;
   const front=groups.find(g=>g.key===rule.frontGroup),rear=groups.find(g=>g.key===rule.rearGroup);
   if(!same(rule,['frontGroup','rearGroup','count','mapping','tracingAvailable'])||rule.mapping!=='one-to-one'||rule.tracingAvailable!==false||
    !Number.isInteger(rule.count)||rule.count<1||rule.count>96||!front||!rear||front===rear||front.face!=='front'||rear.face!=='rear'||
    front.type!=='rj45'||!['rj45','idc'].includes(rear.type)||front.count!==rule.count||rear.count!==rule.count)
    throw Error('selected506k_continuity_invalid');
  }
}


// Closed L input/output inventory. A caller cannot choose its own manifest paths.
export async function verifySelected506LHardwareCatalog(root) {
 const read=name=>readFile(path.join(root,name));
 const manifest=JSON.parse(await read('development/hardware/catalog-selected506l.manifest.json'));
 const inputs=["development/hardware/batch100/nas.json", "development/hardware/batch100/network.json", "development/hardware/batch100/security.json", "development/hardware/batch100b/nas.json", "development/hardware/batch100b/network.json", "development/hardware/batch100b/security.json", "development/hardware/batch100c/nas.json", "development/hardware/batch100c/network.json", "development/hardware/batch100c/security.json", "development/hardware/batch50/network.json", "development/hardware/batch50/qnap.json", "development/hardware/batch50/synology.json", "development/hardware/batch50b/network.json", "development/hardware/batch50b/qnap.json", "development/hardware/batch50b/synology.json", "development/hardware/catalog-aruba-v1.json", "development/hardware/catalog-commercial-v1.json", "development/hardware/catalog-diskstation-v1.json", "development/hardware/catalog-fortinet-v1.json", "development/hardware/catalog-qnap-v1.json", "development/hardware/catalog-schema41.lock.json", "development/hardware/catalog-schema43.lock.json", "development/hardware/catalog-source-v1.json", "development/hardware/catalog-synology-v1.json", "development/hardware/selected-models-506.json", "development/hardware/selected-profile-links.json", "development/hardware/selected506a/aruba.json", "development/hardware/selected506a/ubiquiti.json", "development/hardware/selected506b/access.json", "development/hardware/selected506b/core.json", "development/hardware/selected506c/edge.json", "development/hardware/selected506c/firewalls.json", "development/hardware/selected506d/core.json", "development/hardware/selected506d/edge.json", "development/hardware/selected506e/core.json", "development/hardware/selected506e/edge.json", "development/hardware/selected506f/core.json", "development/hardware/selected506f/edge.json", "development/hardware/selected506g/core.json", "development/hardware/selected506g/edge.json", "development/hardware/selected506h/aruba.json", "development/hardware/selected506h/nokia.json", "development/hardware/selected506i/enterprise.json", "development/hardware/selected506i/transport.json", "development/hardware/selected506j/access-points.json", "development/hardware/selected506j/passive-panels.json", "development/hardware/selected506k/mechanical.json", "development/hardware/selected506k/passive.json", "development/hardware/selected506k/power.json", "development/hardware/selected506k/serial.json", "development/hardware/selected506k/storage.json", "development/hardware/selected506k/support.json", "development/hardware/selected506l/mechanical-copper.json", "development/hardware/selected506l/network.json", "development/hardware/selected506l/storage.json", "development/hardware/selected506l/support-revisions.json", "development/server/database/039-selected506j-hardware.sql", "development/server/database/040-hardware-families.sql", "development/server/database/041-selected506k-hardware.sql", "development/server/database/042-hardware-family-l.sql", "evidence/s1-20261101/integracion506l/PLAN-FAMILIAS.json", "tools/build_hardware_batch50.py", "tools/build_hardware_catalog.py", "tools/build_hardware_catalog19.py", "tools/build_hardware_catalog20.py", "tools/build_hardware_catalog21.py", "tools/build_hardware_catalog22.py", "tools/build_hardware_catalog23.py", "tools/build_hardware_selected506k.py", "tools/build_hardware_selected506l.py", "tools/hardware_family_l.py", "tools/hardware_family_l_contract.json", "tools/hardware_family_v2.py", "tools/hardware_physical_v2.py", "tools/hardware_physical_v3.py"];
 const files=["development/frontend/src/hardware-selected506l.generated.json", "development/server/database/043-selected506l-hardware.sql", "development/server/src/RackClick.Server/Selected506LHardwareProfiles.Generated.cs"];
 const ids=["apc-ar3100", "digitus-dn19-16-u-sw", "nb-00976b7274a49cd1", "nb-03c8ee9bbb014c7c", "nb-0948d9cade199a0b", "nb-125f92d869fe9f59", "nb-19c462f073983955", "nb-1a5e040822eebdd7", "nb-1dd7604442a1239d", "nb-2174af86248be3c0", "nb-21beeace01ead0ab", "nb-22691841537ee307", "nb-26b1060dca08dcdb", "nb-2c5c7ea175f64187", "nb-2da2003e6dc8a96f", "nb-346372afd400f875", "nb-385b1e5bac71b7ef", "nb-3ad914fbc8c9cb70", "nb-459e071f45ef28d0", "nb-592d7bf6fa2dc5f9", "nb-5bb0012c11525238", "nb-6177840266a34e21", "nb-61c1119b6a8fb4cf", "nb-6a9f15ba9e440e40", "nb-6b344ae9fceb207f", "nb-6f1403f8ddecb484", "nb-712e46e426c32606", "nb-7b2b8f9a08ca79dc", "nb-7e5c43b083d87aa3", "nb-7e63582b264848f9", "nb-800f8ec3e0535314", "nb-8311f81875534b26", "nb-84908ff0a7aae399", "nb-8551913e785b8dcd", "nb-95ffc21479b7db70", "nb-9dd49be51e6860a8", "nb-a283ed5b907280be", "nb-a90ded005fd46d23", "nb-af1698f9a4a852f5", "nb-b49efa2c795bb352", "nb-b4a7fc7373f9706c", "nb-b6192e3e8a90a5fe", "nb-bd5913fe938354ff", "nb-bd9d2291941ee640", "nb-be59e710a51d5844", "nb-cb0da37cc251724e", "nb-d1adbd24989d63bf", "nb-d201c4c7e7756c85", "nb-d669b5e97362251a", "nb-d6dd7311f2ef95bd", "nb-d711e2c300ede120", "nb-e449413120cc6f09", "nb-ee49def444e1ec30", "nb-f01b85bd214e6930", "nb-f31245615c072a97", "nb-f5d67a61fbc01300", "nb-fbfb065dfbbbb4ca", "nb-fc3db9baa232b775", "nb-fd5b5a585af75ae9", "palo-alto-pa-7050", "rittal-vxit-5306122", "startech-rk1236bkf"];
 const same=(actual,expected)=>actual&&Object.keys(actual).sort().join('|')===[...expected].sort().join('|');
 if(manifest.formatVersion!==1||manifest.targetSchema!==43||manifest.catalogKey!=='rackclick-selected506l'||manifest.state!=='curated_development_not_a_release'||!same(manifest.inputs,inputs)||!same(manifest.files,files)||JSON.stringify(manifest.selectionIds)!==JSON.stringify(ids)||manifest.definitions.length!==63)throw Error('selected506l_manifest_invalid');
 for(const [name,pin] of Object.entries({...manifest.inputs,...manifest.files}))if(!/^[0-9a-f]{64}$/.test(pin)||sha(await read(name))!==pin)throw Error('selected506l_catalog_stale');
 const definitions=[];
 for(const source of ['development/hardware/selected506l/mechanical-copper.json','development/hardware/selected506l/storage.json','development/hardware/selected506l/network.json','development/hardware/selected506l/support-revisions.json']){
  const data=JSON.parse(await read(source));
  for(const row of data.models){
   const d=row.definition;definitions.push([d.key,d.revision]);
   for(const g of d.groups)for(const key of ['name','prefix'])if(typeof g[key]!=='string'||Array.from(g[key]).length>100||key==='name'&&!g[key].trim()||/[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u.test(g[key]))throw Error('selected506l_group_text_invalid');
  }
 }
 if(definitions.length!==63||new Set(definitions.map(v=>JSON.stringify(v))).size!==63||manifest.definitions.some(d=>!definitions.some(([key,revision])=>key===d.key&&revision===d.revision)))throw Error('selected506l_manifest_definitions_invalid');
}

// Additive German CPE44; catalogue43 and all506 selected definitions remain immutable.
export async function verifyGermanCpeHardwareCatalog(root) {
 const read=name=>readFile(path.join(root,name));
 const raw=await read('development/hardware/catalog-german-cpe.manifest.json');
 if(sha(raw)!=='50cfd57b483d5d3155c2a2a39eb9a3af15d44f2807608043e497e8fcf0752d11')throw Error('german_cpe_manifest_changed');
 const manifest=JSON.parse(raw);
 if(manifest.targetSchema!==44||manifest.catalogKey!=='rackclick-german-cpe'||manifest.definitions.length!==6||manifest.modelKeys.join('|')!=='draytek-vigor167|draytek-vigor2766|draytek-vigor2766ac|fritz-7530ax-de|fritz-7590ax-v2-de|fritz-7690-de')throw Error('german_cpe_manifest_invalid');
 for(const [name,pin] of Object.entries({...manifest.inputs,...manifest.files}))if(!/^[0-9a-f]{64}$/.test(pin)||sha(await read(name))!==pin)throw Error('german_cpe_catalog_stale');
}

// Schema45 additive room repeaters, with pinned authoring and immutable outputs.
export async function verifyGermanRepeatersHardwareCatalog(root) {
 const read=name=>readFile(path.join(root,name));
 const raw=await read('development/hardware/catalog-german-repeaters.manifest.json');
 if(sha(raw)!=='6349a1370f4ffc6b1ed2ada66816c2a67aa1ad7c4ffad2bf3ec064d599b2dd56')throw Error('german_repeaters_manifest_changed');
 const manifest=JSON.parse(raw);
 const inputs=["development/hardware/catalog-schema43.lock.json", "development/hardware/catalog-schema44.lock.json", "development/hardware/german-repeaters/contract.json", "development/hardware/german-repeaters/devolo-reference.md", "development/hardware/german-repeaters/devolo.json", "development/hardware/german-repeaters/fritz-reference.md", "development/hardware/german-repeaters/fritz.json", "development/hardware/german-repeaters/telekom-reference.md", "development/hardware/german-repeaters/telekom.json", "development/hardware/german-repeaters/tplink-reference.md", "development/hardware/german-repeaters/tplink.json", "development/server/database/042-hardware-family-l.sql", "development/server/database/043-selected506l-hardware.sql", "development/server/database/044-german-cpe-hardware.sql", "tools/build_hardware_batch50.py", "tools/build_hardware_german_repeaters.py", "tools/build_hardware_selected506l.py", "tools/hardware_family_l.py", "tools/hardware_family_l_contract.json", "tools/hardware_family_v2.py", "tools/hardware_physical_v2.py", "tools/hardware_physical_v3.py", "development/hardware/catalog-schema45.lock.json"],files=["development/server/src/RackClick.Server/GermanRepeatersHardwareProfiles.Generated.cs", "development/frontend/src/hardware-german-repeaters.generated.json", "development/server/database/045-german-repeaters-hardware.sql"],ids=["devolo-wifi6-repeater3000-eu", "devolo-wifi6-repeater5400-eu", "fritz-repeater1200ax-de", "fritz-repeater2400-de", "fritz-repeater3000ax-de", "fritz-repeater600-de", "fritz-repeater6000-de", "telekom-speedhome-wlan-2021", "tplink-re605x-eu", "tplink-re700x-eu"];
 const same=(actual,expected)=>actual&&Object.keys(actual).sort().join('|')===[...expected].sort().join('|');
 if(manifest.formatVersion!==1||manifest.targetSchema!==45||manifest.catalogKey!=='rackclick-german-repeaters'||manifest.state!=='curated_development_not_a_release'||manifest.definitions.length!==10||!same(manifest.inputs,inputs)||!same(manifest.files,files)||JSON.stringify(manifest.modelKeys)!==JSON.stringify(ids))throw Error('german_repeaters_manifest_invalid');
 for(const [name,pin] of Object.entries({...manifest.inputs,...manifest.files}))if(!/^[0-9a-f]{64}$/.test(pin)||sha(await read(name))!==pin)throw Error('german_repeaters_catalog_stale');
}
