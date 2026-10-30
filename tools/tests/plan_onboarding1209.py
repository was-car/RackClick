"""Sixty observable internal milestones for one bounded onboarding improvement."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
TITLES=[
'Comprobar Git y fijar base488e6a6','Proteger QA1089/13 e informes anteriores','Contrastar solicitud visual y paneles existentes','Fijar servidor/esquema/dependencias sin cambios','Separar propiedad de implementación y revisión',
'Contratar recorrido Cuenta→Membresías→Permisos','Vincular recibo a actor/solicitud/UUID','Aceptar alta confirmada por POST','Aceptar recuperación committed por consulta','Aceptar cancelación que recupera commit previo','Excluir cancelación real','Excluir resultado no registrado o incierto','Excluir respuesta inválida y éxito por nombre','Retirar recibo al iniciar otra alta','Invalidar actor/generación y respuestas tardías','Conservar contraseña sólo en formulario existente','Conservar evidencia si falla limpieza del journal','Bloquear continuación si falla recarga','Exigir snapshot vigente y cuenta presente','Seleccionar UUID confirmado explícitamente',
'Revalidar guardas síncronas antes de navegar','Proteger borrador de contraseña','Proteger journal/borrador de membresía','Conservar selección del mismo UUID','Cargar journal de grupos sin abrir automáticamente','Enlazar consulta de permisos efectiva existente','Acreditar navegación sin asignación ni POST','Conservar nombre literal y UUID completo','Completar textos EN/DE/ES','Ejecutar foco Node de casos adversos',
'Congelar fuentes de producto','Compilar frontend una vez con Node fijado','Congelar candidata completa de40artefactos','Verificar22servidor exactos y cero buildC#','VerificarCSS y otros17frontend exactos','Preparar fixture PostgreSQL nueva independiente','Recorrer alta real en Edge','Asignar grupo explícitamente y confirmar commit','Consultar permisos efectivos por UUID','Leer acceso desde otra sesión del usuario','Comprobar persistencia tras recarga','Simular pérdida de respuesta después del commit','Recuperar recibo sin repetir alta','Comprobar cancelación/ausencia sin tarjeta falsa','Probar guardas y teclado en GUI real','Inspeccionar390px sin desbordamiento','Denegar administración a lector en servidor','Reiniciar aplicación y releer persistencia',
'Ejecutar foco independiente de recuperación/actor','Resolver hallazgos con pruebas acotadas','EscribirQA85–87 con pasos concretos','Conservar84casos/listas/resultados previos','Regenerar ambas guías desde snapshot real','Verificar nuevos casos no disponibles en QA1089','Actualizar continuidad/mapa/CHANGELOG','Distinguir evidencia nueva/histórica y límites','Verificar guards/artefactos/quietud finales','Obtener adenda independiente de cierre','Preparar diff y SHA256SUMS nuevos','Preparar commit local e informe de alcance'
]
def main():
    assert len(TITLES)==60
    path=ROOT/'docs/PLAN-SESENTA-TANDAS-1150-1209.json';assert not path.exists()
    data=dict(scope='60hitos internos de una mejora guiada de alta; no60funciones ni60suites. Candidata de desarrollo, QA1089/13 conservado.',initialProgress=78,total=60,completed=0,
        batches=[dict(id=i,title=t,status='pending') for i,t in enumerate(TITLES,1150)])
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(total=60,completed=0,progress=78)))
if __name__=='__main__':main()
