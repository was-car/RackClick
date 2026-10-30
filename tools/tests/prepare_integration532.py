"""Create closed532 operators from the reviewed185 transition, preserving originals."""
from pathlib import Path
import ast,json
ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'evidence/s1-20261018/sesenta-tandas-473-532'
def main():
    for directory,name in [('tools/windows','qa_artifact9_source185.py'),('tools/windows','qa_artifact9_update185.py'),('development/server/tests','test_qa_artifact9_update185.py')]:
        source=ROOT/directory/name;target=source.with_name(name.replace('185','532'))
        if target.exists():raise SystemExit('New532 operator already exists; refuse overwrite')
        s=source.read_text(encoding='utf-8').replace('185','__TARGET__').replace('179','185').replace('__TARGET__','532')
        if 'source185' in name:
            lines=s.splitlines()
            for i,line in enumerate(lines):
                if line.startswith('SOURCE_MANIFEST ='):lines[i]="SOURCE_MANIFEST = ROOT / 'evidence/s1-20261017/seis-tandas-180-185/CANDIDATA185.json'"
                elif line.startswith('SOURCE_SHA256 ='):lines[i]="SOURCE_SHA256 = '68aca94da20751b690af0c1c6b764a1db1004d3d63be2a12161938a3624d7706'"
                elif line.startswith('TARGET_MANIFEST ='):lines[i]="TARGET_MANIFEST = ROOT / 'evidence/s1-20261018/sesenta-tandas-473-532/CANDIDATA532.json'"
                elif line.startswith('TARGET532 ='):lines[i]="TARGET532 = None  # Closed until the coordinator freezes and independently reviews the exact manifest."
            s='\n'.join(lines)+'\n'
        if name.startswith('test_'):
            s=s.replace("self.assertEqual(contracts.SOURCE_SHA256, '45631b5a820be45be447aa6ecb81584fcdcb9262584052d6f86de34569aadfd5')","self.assertEqual(contracts.SOURCE_SHA256, '68aca94da20751b690af0c1c6b764a1db1004d3d63be2a12161938a3624d7706')")
        ast.parse(s);target.write_bytes(s.replace('\n','\r\n').encode('utf-8'))
    groups=[('Contrato y compatibilidad',['DTO y límites cerrados','Protocolo de recuperación compacto','Compatibilidad del digest legacy']),('Entrada de configuración',['Parser anidado y claves duplicadas','Tamaños y hash de input','Grupos, GN y familias explícitos']),('Commit de configuración',['Inserción nueva atómica','Replay y fence de intención nueva','Rutas, ETag y límiteHTTP propio']),('Semillas del editor',['Borrador desde privada propia','Borrador vacío para tres tipos','Semilla BASE inmutable']),('Chasis del editor',['Tipo y altura','Icono, color y presupuestoPoE','Familia visual y AUTO']),('Grupos del editor',['Añadir, quitar y reordenar grupos','Familia, nombre y prefijo explícitos','Cantidad conserva atributos retenidos']),('Puertos del editor',['GN y orden explícitos','Tipo y PoE independientes','Etiqueta, color, cara y rol']),('Guardado de copia',['Preview de configuración','Nombre y guardar como nueva','Original y equipos intactos']),('Adaptador y diario',['Adaptador cerrado','Recibos y estado validado','Diario compacto sin blueprint']),('Recuperación del editor',['Consulta y retry en memoria','Cancelación después de recarga','Reautenticación y generaciones']),('Convivencia y autoridad',['PermisosUI y servidor','Conflicto conserva borrador','Click-Click y otros borradores']),('Persistencia de configuración',['Bytes originales y persistenciaPG','Crear equipos de tres tipos y reinicio','Límites y entradas inválidas']),('Atomicidad y concurrencia',['Replay, cancelación y concurrencia','Permisos/expiración tras espera','Rollback de auditoría']),('Pruebas de interfaz',['Node de adaptador y diario','Edge con cuenta propia/lector/otra sesión','EN/DE/ES, teclado y390px']),('Revisión funcional',['Estática independiente','Foco nativo independiente','Contrato y casosQA con atribución']),('Perfiles de paquete',['Perfil cerrado532','Compatibilidad337/397 y negativos','DosZIP532 reproducibles']),('Actualizador compatible',['Identidad cerrada185→532','Cambiar sólo tres campos de artefactos','Fixture poblada: tablas/cuentas/sesiones intactas']),('Fallos y operaciónWindows',['Preflight y recuperación del actualizador','Instalación nativa desde contenido','Backup y recuperación con configuración nueva']),('SelecciónQA',['Revisión independiente antes de selección','Selección compatible real detenida','Matriz de casos/guías y disponibilidad real']),('Cierre verificable',['Manuales y reproducción','Integridad, diff y manifiestos','Continuidad, progreso y commitlocal'])]
    batches=[{'id':473+3*i+j,'group':group,'title':title,'status':'planned','evidence':None,'independentEvidence':None} for i,(group,titles) in enumerate(groups) for j,title in enumerate(titles)]
    p=ROOT/'docs/PLAN-SESENTA-TANDAS-473-532.json'
    if p.exists():raise SystemExit('Milestone plan already exists')
    p.write_text(json.dumps({'group':'473-532','count':60,'completed':0,'initialProgress':76,'progressBasis':'docs/PROGRESO-GLOBAL.md','scope':'45 hitos del editor privado y15 de integración. No60módulos ni60suites. AdopciónWascar pendiente.','batches':batches},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'newOperators':2,'newHarness':1,'milestones':len(batches),'targetManifestPin':'pending-fail-closed'}))
if __name__=='__main__':main()
