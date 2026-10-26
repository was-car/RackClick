"""Update four current Windows manuals before freezing the schema13 package."""
from datetime import datetime,timezone
import hashlib,json,platform,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-1090-1149'
MF='evidence/s1-20261018/sesenta-tandas-1030-1089/CANDIDATA1089-02.json'
PIN='c8b3df5b8e0fb6c5db148b7ddca2a8064ade6b90557713fb0835cbf69bb9710c'
OLDMF='evidence/s1-20261018/sesenta-tandas-970-1029/CANDIDATA969-FIX02.json';OLDPIN='b589609154fed1567106ef0865972155258f0f5474128c73076f4697d43b8bda'
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 out=E/'MANUALES-01.json';assert not out.exists()
 headers={
 'MANUAL-PAQUETE-WINDOWS-S1.md':'**Integración1090–1149 · candidata1089-02/esquema13.** Aplicación completa de40 archivos (22 servidor+18 interfaz),7.133.395 bytes reutilizados exactamente. Nuevo perfil Windows cerrado y paleta personal por parejas de categorías. New/Restore y copia QA se verifican por separado; no es adopción ni instalación Windows definitiva.',
 'CONSTRUIR-PAQUETE-WINDOWS-S1.md':'**Integración1090–1149.** Nueve perfiles cerrados:337/397/532 de9,592 de10,712/832/849 de11,969 de12 y1089 de13. Candidata1089-02 exacta, sin publicar servidor ni compilar frontend.25 operadores y4 manuales se congelan antes de dos ZIP idénticos. No pines arbitrarios.',
 'OPERAR-DESPLIEGUE-PRIVADO-WINDOWS-S1.md':'**Aplicación1089/esquema13.** Paletas personales de tipos y parejas de categorías; SQL013 aditiva con39 tablas. Default al crear decidido por servidor y expiración de sesión revalidada antes de commit. Copia QA969/12→1089/13 en clúster nuevo con recuperación969/12; origen completo y su recuperación849/11 se conservan por separado. Sin bootstrap/recover-admin en la copia.',
 'RECUPERACION-DESPLIEGUE-WINDOWS-S1.md':'**Compatibilidad1089/esquema13.** Backup/Restore conserva39 tablas, ambas paletas y recibos/fences originales. Restore administrativo crea raíces/clúster/base/roles/TLS/administrador nuevos y revoca sesiones copiadas con diferencias explícitas. Copia QA12→13 mantiene cuentas/sesiones/privados y deja nueva recuperación969/12; conserva origen969/12 y recuperación849/11. Recuperación integral de host y adopción pendientes.'}
 changes={}
 for name,header in headers.items():
  p=ROOT/'docs'/name;raw=p.read_bytes();text=raw.decode().replace('\r\n','\n');start=text.index('**');end=text.index('\n\n',start);text=text[:start]+header+text[end:]
  text=text.replace('estos ocho perfiles','estos nueve perfiles').replace('los36,37 o38 hashes','los36,37,38,39 o40 hashes').replace('los36,37 o38 artefactos','los36,37,38,39 o40 artefactos')
  text=text.replace('perfil337,397,532,592,712,832,849 o969 registrado','perfil337,397,532,592,712,832,849,969 o1089 registrado')
  text=text.replace('969 de12.','969 de12 y1089 de13.').replace('969: esquema12)','969: esquema12;1089: esquema13)')
  text=text.replace('/969 (esquema12) registrados','/969 (esquema12)/1089 (esquema13) registrados').replace('N=12 para969)','N=12 para969; N=13 para1089)')
  text=text.replace('según el perfil validado9/10/11;','según el perfil validado9/10/11/12/13;').replace('de ese esquema (9,10 u11, incluido templates.publish en10/11','de ese esquema (9,10,11,12 o13, incluido templates.publish en10/11/12/13')
  text=text.replace('vuelve a Infraestructura/Clientes desde la barra izquierda','pulsa Todos los clientes en la barra izquierda, debajo del título Infraestructura')
  text=text.replace('La paleta automática por parejas de categorías es otra función pendiente.','La sección Parejas de categorías de1089 permite preferencias personales para conexiones nuevas; se explica debajo.')
  text=text.replace('Interfaz969/esquema12 reutilizada; servidor969-FIX02 republicado una vez en970–1029 por P1 en recuperación administrativa12. Los paquetes337/397/532/592/712/832/849','Interfaz y servidor1089-02/esquema13 reutilizados sin compilar en1090–1149. Los paquetes337/397/532/592/712/832/849/969')
  text=text.replace('[candidata969 de laboratorio](../'+OLDMF+') tiene referencia `'+OLDPIN+'` y21archivos','[candidata1089 de laboratorio](../'+MF+') tiene referencia `'+PIN+'` y22archivos')
  if name.startswith('CONSTRUIR-'):
   anchor='\n\nEl productor exige el hash externo';assert anchor in text
   row='\n| [1089/parejas de categorías](../'+MF+') |13 /22+18|7.133.395|`'+PIN+'`|'
   text=text.replace(anchor,row+anchor)
   text=text.replace('--manifest '+OLDMF,'--manifest '+MF).replace('--expected-manifest-sha '+OLDPIN,'--expected-manifest-sha '+PIN)
   text=text.replace('--evidence evidence/s1-20261018/sesenta-tandas-970-1029/packaging/NOMBRE-NUEVO','--evidence evidence/s1-20261018/sesenta-tandas-1090-1149/packaging/NOMBRE-NUEVO')
  if name.startswith('MANUAL-'):
   text+='''\n\n## Paleta por parejas de categorías en1089\n\nEn la barra izquierda pulsa **Todos los clientes**, debajo del título Infraestructura. Arriba a la derecha pulsa **Paleta**. Dentro del diálogo pulsa **Parejas de categorías**. Hay28 parejas simétricas y diez muestras. Selecciona una muestra; repetirla o × quita el color del borrador. **Restablecer todo** también sólo cambia el borrador. Pulsa **Guardar** abajo a la derecha y espera la confirmación del servidor y su GET. Cambiar a Tipos de puerto y volver conserva borradores; Cerrar los descarta.\n\nCada cuenta, incluido Lector, conserva su preferencia. Misma cuenta en otra sesión la recupera; otra cuenta no la hereda. Al crear conexiones, el servidor usa color manual válido→pareja de categorías→sin color. Se clasifica por clave real del preset de los equipos, no por su nombre traducido ni gn. El color queda guardado en el cable compartido. Cambiar la preferencia no recolorea conexiones anteriores, reconexiones, duplicados, puertos ni estados. No concede permisos de crear conexiones. El antiguo almacenamiento local de RC9 no se importa ni impone defaults.\n\nAnte incertidumbre usa Consultar original/Reintentar original/Cancelar original con la misma cuenta e intención; no declares guardado por un mensaje pendiente. QA82–84 detallan los recorridos y sólo se habilitan tras selección/readiness real del nuevo QA13. No se modifican resultados anteriores de Wascar.\n'''
  text+='''\n\nIntegración1090–1149: perfil1089 cerrado por el manifiesto CANDIDATA1089-02 (SHA256 c8b3df5b8e0fb6c5db148b7ddca2a8064ade6b90557713fb0835cbf69bb9710c), SQL001–013 y22+18 artefactos. Un backup13 requiere ese perfil13: no ejecutar binarios12 sobre13. La copia de laboratorio es distinta de Restore administrativo: protege por separado principal969/12 (37 tablas) y recuperación849/11 (35), conserva preparado/sello1029 y copia sólo principal a nuevas1089/13 (39) y recuperación969/12 (37). SQL013 corre sólo en la nueva principal; sus dos tablas nuevas empiezan vacías. Cinco secretosPG nuevos y datos/cuentas/sesiones/privados/grants conservados; sin bootstrap/recover-admin. Retorno condicionado por ausencia de actividad en las cuatro ramas, incluso actividad compensada; ante incertidumbre conservarlas y resolver recovery_required, sin reescribir baselines. Pruebas Windows/QA nuevas1090–1149 se separan de1030–1089 y anteriores. No se compila ni se cambian dependencias al empaquetar.\n'''
  p.write_bytes(text.replace('\n','\r\n' if b'\r\n' in raw else '\n').encode());changes['docs/'+name]=dict(before=sha(raw),after=sha(p.read_bytes()))
 with out.open('x',encoding='utf-8') as f:f.write(json.dumps(dict(files=changes,scope='Four current manuals before immutable package inputs; historic reports untouched.'),indent=2)+'\n')
 versions={}
 for row in json.loads((ROOT/'development/toolchain.lock.json').read_bytes())['components']:
  command=[str(ROOT/'.local'/row['installDirectory']/row['executable']),'--version'];r=subprocess.run(command,capture_output=True,text=True,check=True)
  versions[row['id']]=dict(command=command,stdout=r.stdout.strip(),exitCode=r.returncode)
 with (E/'ENTORNO.json').open('x',encoding='utf-8') as f:f.write(json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(),windows=platform.platform(),python=platform.python_version(),versions=versions,downloads=0,installedDependencies=0,versionChanges=0),indent=2)+'\n')
 print(json.dumps(dict(manuals=4,versions=versions,applicationBuilds=0,frontendBuilds=0)))
if __name__=='__main__':main()
