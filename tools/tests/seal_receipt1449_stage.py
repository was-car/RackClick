"""Preserve raw diff; audit its context-only whitespace exception before commit."""
import argparse,json,re,subprocess
from block1449 import ROOT,E,ER,GIT,sha,save,exact
def old_seal():
 lines=(E/'SHA256SUMS').read_text(encoding='ascii').splitlines();assert len(lines)==74
 for line in lines:
  h,p=line.split('  ',1);assert sha(E/p)==h
def check():
 old_seal();full=subprocess.run([str(GIT),'diff','--cached','--check'],capture_output=True);raw=(E/'CAMBIOS.diff').read_bytes().splitlines();out=full.stdout.decode('utf-8');warnings=re.findall(r'^(.+):(\d+): trailing whitespace\.$',out,re.M)
 assert full.returncode==2 and len(warnings)==17 and not full.stderr
 for path,line in warnings:assert path==ER+'/CAMBIOS.diff' and raw[int(line)-1]==b' '
 bounded=subprocess.run([str(GIT),'diff','--cached','--check','--','.',':(exclude)'+ER+'/CAMBIOS.diff'],capture_output=True);assert bounded.returncode==0 and not bounded.stdout and not bounded.stderr
 assert not subprocess.check_output([str(GIT),'diff','--name-only'])
 (E/'STAGING-DIFF-CHECK-01.log').write_bytes(full.stdout);(E/'STAGING-DIFF-BOUNDED-01.log').write_bytes(bounded.stdout)
 save('STAGING-CHECK.json',dict(rawCheckExitCode=full.returncode,warningCount=len(warnings),onlyException=ER+'/CAMBIOS.diff',reason='A raw Git patch contains one-space context lines representing blank lines. Preserve its bytes; do not reformat executed/pinned evidence.',allWarningLinesAreSingleSpacePatchContext=True,boundedCheckExitCode=bounded.returncode,productAndOtherFilesWhitespaceClean=True,rawPatchSha256=sha(E/'CAMBIOS.diff'),firstSealSha256=sha(E/'SHA256SUMS'),firstSeal74FilesExact=True,actualQaOperations=0,progress=78));print('stage check PASS with17 raw-patch context warnings only; preserved74-file seal')
def finalize():
 old_seal();review=json.loads((E/'revision/ADENDA-SELLO.json').read_bytes());assert review['approved'];exact(review['observedFilesSha256'])
 (E/'CIERRE-SELLO.md').write_text('''# Adenda de sello ·1390–1449

El [cierre funcional](CIERRE.md) y la revisión técnica permanecen exactos. El sello original SHA256SUMS conserva74archivos; **SHA256SUMS-02 es el sello final ampliado**, incorporando esta adenda, comprobación de staging y revisión adicional.

La comprobación Git de staging señaló17líneas de contexto de CAMBIOS.diff, cada una un único espacio que representa una línea vacía en un parche Git. Se conservó el diff original. La comprobación acotada excluye únicamente ese archivo y pasa para producto y demás archivos; no se afirma un check global sin excepciones. Registros STAGING-CHECK.json y revision/ADENDA-SELLO.json.

Sin cambios de producto/artefactos, pruebas adicionales, QA real, versiones o porcentaje. Global78 % aproximado. Commit local y comprobación posterior cierran el bloque; no publicación ni adopción final.
''',encoding='utf-8',newline='\n')
 rows=[sha(p)+'  '+p.relative_to(E).as_posix() for p in sorted(E.rglob('*')) if p.is_file() and p.name!='SHA256SUMS-02'];(E/'SHA256SUMS-02').write_text('\n'.join(rows)+'\n',encoding='ascii');print(json.dumps(dict(finalSealFiles=len(rows),sha256=sha(E/'SHA256SUMS-02'))))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['check','finalize']);a=p.parse_args();globals()[a.action]()
