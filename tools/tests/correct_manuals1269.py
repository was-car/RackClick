"""Correct review findings after native01; never relabel its tested ZIP."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-1210-1269'
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 out=E/'MANUALES-02.json';assert not out.exists();assert json.loads((E/'windows/native01/result.json').read_bytes())['ownedProcessesStopped']
 frozen=json.loads((E/'SOURCE-FREEZE-OPERATORS-01.json').read_bytes())['sources'];changes={}
 names=['MANUAL-PAQUETE-WINDOWS-S1.md','CONSTRUIR-PAQUETE-WINDOWS-S1.md','OPERAR-DESPLIEGUE-PRIVADO-WINDOWS-S1.md','RECUPERACION-DESPLIEGUE-WINDOWS-S1.md']
 common_old='En la barra izquierda abre **Administración**, luego **Usuarios**. Crea una cuenta mediante el formulario existente y espera la confirmación del servidor. La tarjeta **Cuenta creada** muestra el nombre literal y UUID completo; ofrece **Membresías** y **Permisos efectivos**. Sigue el botón explícito; no se asignan grupos ni permisos al navegar. En Membresías selecciona un grupo por su UUID y guarda; si el panel de grupos ya estaba abierto antes de crearlo, pulsa Actualizar para leerlo. Consulta después los permisos efectivos desde el servidor. Una cuenta creada sin grupos no obtiene acceso por su nombre ni por verse en la lista. Comprueba el acceso iniciando esa cuenta en otro perfil de navegador.'
 common_new='En la barra lateral izquierda pulsa **Usuarios**, cerca de la parte inferior. En **Secciones de administración**, a la izquierda del contenido, pulsa **Crear cuenta**. En el centro completa **Nombre de usuario** y **Contraseña**, pulsa **Crear usuario** y espera la confirmación del servidor. La tarjeta **Cuenta creada** muestra nombre literal y UUID completo. Pulsa **Continuar a membresías**: abre **Grupos y permisos** y enfoca **Membresías de usuarios**. Si faltan cuentas nuevas, pulsa **Actualizar grupos**; contrasta UUID, elige un grupo explícito y pulsa **Guardar asignación**. La navegación no asigna grupos ni concede permisos. Vuelve a la tarjeta y pulsa **Revisar permisos efectivos**; en el panel pulsa **Actualizar cuentas** y **Consultar permisos**. Una cuenta sin grupos no obtiene acceso por su nombre ni por aparecer en una lista. Compruébalo iniciando esa cuenta en otro perfil de navegador.'
 for name in names:
  p=ROOT/'docs'/name;raw=p.read_bytes();assert sha(raw)==frozen['docs/'+name];t=raw.decode('utf-8');assert t.count(common_old)==1;t=t.replace(common_old,common_new)
  t=t.replace('Interfaz y servidor1089-02/esquema13 reutilizados sin compilar en1090–1149. Los paquetes337/397/532/592/712/832/849/969','Interfaz1209-01 con servidor1089-02/esquema13 reutilizados sin compilar en1210–1269. Los paquetes337/397/532/592/712/832/849/969/1089')
  t=t.replace('perfil337,397,532,592,712,832,849,969 o1089 registrado','perfil337,397,532,592,712,832,849,969,1089 o1209 registrado').replace('1089: esquema13)','1089/1209: esquema13)').replace('/1089 (esquema13) registrados','/1089,1209 (esquema13) registrados').replace('N=13 para1089)','N=13 para1089/1209)')
  old='[candidata1089 de laboratorio](../evidence/s1-20261018/sesenta-tandas-1030-1089/CANDIDATA1089-02.json) tiene referencia `c8b3df5b8e0fb6c5db148b7ddca2a8064ade6b90557713fb0835cbf69bb9710c`'
  new='[candidata1209 de laboratorio](../evidence/s1-20261018/sesenta-tandas-1150-1209/CANDIDATA1209-01.json) tiene referencia `dc79c53fe188187637972c2cad479edd1868d1942414c602de17bb4454bd153b`'
  if name.startswith('OPERAR-'):assert old in t;t=t.replace(old,new)
  t=t.replace('quietud y watermark de ambasDB coinciden','quietud y watermark único del clúster, comprobado antes/después de ambasDB, coinciden')
  p.write_bytes(t.encode('utf-8'));changes['docs/'+name]=dict(before=sha(raw),after=sha(p.read_bytes()))
 with out.open('x',encoding='utf-8') as f:json.dump(dict(files=changes,reason='Independent review P3: stale profile/current candidate lists and inaccurate onboarding navigation. Corrected before finalZIP02. Native01 remains attributed to ZIP01; only documentary compatibility may carry forward.',operatorOrProductChanges=False),f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps(dict(manuals=4,productChanges=0,operatorChanges=0)))
if __name__=='__main__':main()
