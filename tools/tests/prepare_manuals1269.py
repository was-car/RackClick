"""Update the four current manuals before packaging; retain historical instructions."""
from datetime import datetime,timezone
import hashlib,json,platform,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-1210-1269'
MF='evidence/s1-20261018/sesenta-tandas-1150-1209/CANDIDATA1209-01.json';PIN='dc79c53fe188187637972c2cad479edd1868d1942414c602de17bb4454bd153b'
OLDMF='evidence/s1-20261018/sesenta-tandas-1030-1089/CANDIDATA1089-02.json';OLDPIN='c8b3df5b8e0fb6c5db148b7ddca2a8064ade6b90557713fb0835cbf69bb9710c'
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 out=E/'MANUALES-01.json';assert not out.exists();changes={}
 headers={
 'MANUAL-PAQUETE-WINDOWS-S1.md':'**Integración1210–1269 · candidata1209-01/esquema13.** Alta guiada Cuenta creada→Membresías→Permisos efectivos.40 archivos (22 servidor+18 interfaz),7.146.303 bytes exactos; servidor1089 sin cambios. New/Restore se prueban en raíces nuevas; QA actual se actualiza sólo en artefactos, sin copiar ni migrar bases. Instalación Windows definitiva/adopción pendientes.',
 'CONSTRUIR-PAQUETE-WINDOWS-S1.md':'**Integración1210–1269.** Diez perfiles cerrados:337/397/532 de9,592 de10,712/832/849 de11,969 de12 y1089/1209 de13. Candidata1209-01 exacta, cero compilaciones.25 operadores/cuatro manuales congelados antes de dos ZIP idénticos. Versiones fijadas y pines anteriores conservados.',
 'OPERAR-DESPLIEGUE-PRIVADO-WINDOWS-S1.md':'**Aplicación1209/esquema13, servidor1089 exacto.** Alta guiada con UUID confirmado y continuaciones explícitas, sin conceder permisos al navegar. Actualización QA de artefactos sobre la misma principal13/39tablas y recuperación969/12/37tablas: sólo artifactDirectory+bundleSha256, puntero/base/OID/credenciales/sesiones intactos. Las instrucciones de copia12→13 de1090–1149 son históricas.',
 'RECUPERACION-DESPLIEGUE-WINDOWS-S1.md':'**Compatibilidad1209/esquema13.** Mismo servidor/SQL013 y39tablas de1089. Restore administrativo crea raíces/base/roles/TLS/admin nuevos y revoca sesiones copiadas; conserva propietarios originales. ActualizaciónQA1269 sólo de interfaz en la misma raíz13 y recuperación12: retorno privado dentro de la operación fallida condicionado a quietud/inputs/actividad; nunca rollback tardío. Recuperación integral/adopción pendientes.'}
 addition='''

## Alta guiada1209 y operación1210–1269

Candidata1209-01: SHA256 dc79c53fe188187637972c2cad479edd1868d1942414c602de17bb4454bd153b,40 archivos/22+18/7.146.303 bytes/esquema13. Sólo app.js difiere de1089;22 archivos de servidor, SQL001–013, CSS y dependencias exactos. No ejecutar un perfil12 contra una base13. Los apartados de integración1090–1149 describen la copia histórica12→13, no la actualización actual.

En la barra izquierda abre **Administración**, luego **Usuarios**. Crea una cuenta mediante el formulario existente y espera la confirmación del servidor. La tarjeta **Cuenta creada** muestra el nombre literal y UUID completo; ofrece **Membresías** y **Permisos efectivos**. Sigue el botón explícito; no se asignan grupos ni permisos al navegar. En Membresías selecciona un grupo por su UUID y guarda; si el panel de grupos ya estaba abierto antes de crearlo, pulsa Actualizar para leerlo. Consulta después los permisos efectivos desde el servidor. Una cuenta creada sin grupos no obtiene acceso por su nombre ni por verse en la lista. Comprueba el acceso iniciando esa cuenta en otro perfil de navegador.

Ante un guardado incierto usa Consultar original/Reintentar original/Cancelar original con la misma cuenta e intención. Una coincidencia en una lista o notRecorded no demuestra alta. El recibo confirmado permanece sólo en memoria, sin contraseña; un borrador/petición/recuperación pendiente bloquea la continuación. Después de401/403 se retiran sus datos. En390px usa desplazamiento; conserva EN/DE/ES y nombres propios. Los pasos detallados son QA85–87 en la guía, disponibles sólo tras verificar selección real1209, cuentas/roles y configuración. No se sobrescriben resultados de Wascar.

Actualización QA1269 de artefactos: misma raíz/clúster/principal13(39 tablas)/recuperación969/12(37), mismos OIDs/cuentas/sesiones/grants/secretos y puntero. Nueva versión con40 archivos; previous/preview/selected privados sellados. Sólo artifactDirectory y bundleSha256 cambian en manual-qa.json. El preparado1149, su sello, configuración fuente y artefactos1089/969 quedan como evidencia exacta. No hay migrate/bootstrap/recover-admin ni login/DML de aplicación sobre el QA actual. Se comparan datos actuales, no la foto histórica de creación.

Preview/readiness13→parada confirmada→selección atómica→GET/readiness13→parada/verificación. Retorno sólo dentro de la operación fallida si inputs, quietud y watermark de ambasDB coinciden con el baseline original. Actividad incluso compensada o incertidumbre exige recovery_required y conservar selección/versiones; no renovar baseline ni ofrecer rollback posterior. El watermark es conservador por clúster. Siete runtime/logs anteriores se archivan privadamente; no se promete igualdad de archivos físicos PG tras arrancar. Si hay procesos ajenos o sesiones activas, no forzar parada.

Las pruebas New/Restore de Windows1269 usan fixtures nuevos y API/transporte exactoapp.js; no son una nueva pruebaDOM/voz/Office ni instalación limpia en otro Windows/SCM/PKI productiva/CRT elevado/licencias aprobadas. Cero builds/descargas/cambios de versiones al empaquetar. Producto final y QA/adopción de Wascar siguen pendientes.
'''
 for name,header in headers.items():
  p=ROOT/'docs'/name;raw=p.read_bytes();text=raw.decode('utf-8').replace('\r\n','\n');start=text.index('**');end=text.index('\n\n',start);text=text[:start]+header+text[end:]
  if name.startswith('CONSTRUIR-'):
   text=text.replace('estos nueve perfiles','estos diez perfiles')
   anchor='\n\nEl productor exige el hash externo';assert anchor in text
   text=text.replace(anchor,'\n| [1209/alta guiada](../'+MF+') |13 /22+18|7.146.303|`'+PIN+'`|'+anchor)
   text=text.replace('--manifest '+OLDMF,'--manifest '+MF).replace('--expected-manifest-sha '+OLDPIN,'--expected-manifest-sha '+PIN).replace('--evidence evidence/s1-20261018/sesenta-tandas-1090-1149/packaging/NOMBRE-NUEVO','--evidence evidence/s1-20261018/sesenta-tandas-1210-1269/packaging/NOMBRE-NUEVO')
  p.write_bytes((text+addition).replace('\n','\r\n' if b'\r\n' in raw else '\n').encode('utf-8'));changes['docs/'+name]=dict(before=sha(raw),after=sha(p.read_bytes()))
 with out.open('x',encoding='utf-8') as f:json.dump(dict(files=changes,scope='Four manuals frozen before package; historical reports retained.'),f,indent=2);f.write('\n')
 versions={}
 for row in json.loads((ROOT/'development/toolchain.lock.json').read_bytes())['components']:
  command=[str(ROOT/'.local'/row['installDirectory']/row['executable']),'--version'];r=subprocess.run(command,capture_output=True,text=True,check=True);versions[row['id']]=dict(command=command,stdout=r.stdout.strip(),exitCode=r.returncode)
 with (E/'ENTORNO.json').open('x',encoding='utf-8') as f:json.dump(dict(utc=datetime.now(timezone.utc).isoformat(),windows=platform.platform(),python=platform.python_version(),versions=versions,downloads=0,installedDependencies=0,versionChanges=0),f,indent=2);f.write('\n')
 print(json.dumps(dict(manuals=4,versions=versions,applicationBuilds=0,frontendBuilds=0)))
if __name__=='__main__':main()
