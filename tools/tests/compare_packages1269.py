"""Prove precisely which transported ZIP bytes changed; no new native test claim."""
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-1210-1269'
def read(name):return json.loads((E/name).read_bytes())
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 out=E/'COMPATIBILIDAD-DOCUMENTAL-02.json';assert not out.exists();a,b=read('PACKAGES-01.json'),read('PACKAGES-02.json')
 assert a['valid'] and b['valid'] and a['sourceManifestSha256']==b['sourceManifestSha256'] and b['byteIdentical']
 paths=[ROOT/x['outputs'][0]['path'] for x in [a,b]];assert [sha(p) for p in paths]==[x['outputs'][0]['sha256'] for x in [a,b]]
 with zipfile.ZipFile(paths[0]) as old,zipfile.ZipFile(paths[1]) as new:
  assert old.namelist()==new.namelist();changes=[p for p in old.namelist() if old.read(p)!=new.read(p)]
  manuals=list(read('MANUALES-02.json')['files'])
  assert set(changes)==set(manuals+['bundle.json']),changes
  ob,nb=[json.loads(z.read('bundle.json')) for z in [old,new]]
  for k,v in ob.items():
   if k not in ['files','id']:assert nb[k]==v,(k,nb[k],v)
  inventory=[p for p in ob['files'] if ob['files'][p]!=nb['files'][p]];assert set(inventory)==set(manuals)
  exact=[p for p in old.namelist() if p not in changes];assert len([p for p in exact if p.startswith(('application/server/','application/frontend/'))])==40 and len([p for p in exact if p.startswith('operators/')])==25
 native=read('windows/native01/result.json');assert native['successful'] and native['archiveSha256']==a['outputs'][0]['sha256']
 record=dict(valid=True,testedNativeArchiveSha256=native['archiveSha256'],finalArchiveSha256=b['outputs'][0]['sha256'],changedZipEntries=changes,changedInventoryEntries=inventory,otherZipEntriesByteExact=len(exact),applicationFilesExact=40,operatorsExact=25,dependenciesLicensesExact=True,nativeNewRestoreRerun=False,scope='Native01 actually executed ZIP01. Static exact content compatibility only: finalZIP02 changes four manuals plus generated inventory/id. Native observations apply to identical app/operators/dependencies, not a second execution.')
 with out.open('x',encoding='utf-8') as f:json.dump(record,f,indent=2);f.write('\n')
 print(json.dumps(record))
if __name__=='__main__':main()
