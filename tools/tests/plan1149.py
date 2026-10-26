"""Record the sixty internal Windows/QA13 integration milestones before execution."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
titles=[
'Inspeccionar Git y fijar base6086885','Conservar informes/candidatas1089 y1029','Fijar cuarenta artefactos y190 fuentes sin builds','Proteger QA969 principal12 y recuperación849/11','Archivar siete runtime/logs originales privadamente',
'Contrastar perfil cerrado1089 y ocho anteriores','Ampliar verificador a22+18/esquema13','Ampliar Stage/readiness13 conservando anteriores','Probar perfiles y negativos nativos','Congelar cinco fuentes de productor/operadores',
'Actualizar manual Windows y navegación real','Actualizar manual de construcción/perfiles/hash','Actualizar operación y fuentes heterogéneas','Actualizar recuperación39/37/35 y límites','Congelar25 operadores/cuatro manuales/entradas',
'Generar ZIPa sin recompilar ni descargar','Generar ZIPb y comprobar identidad binaria','Ejecutar New público desde ZIP transportado','Verificar runtime sin SDK/HTTPS/cookies','Verificar paletas012/013 y lector sin clientes',
'Verificar defaults por preset/UUID/ámbito','Verificar prioridad manual/replay/no recolor','Verificar single/batch con expiración final','Verificar preferencias011/XLS/recibos','Verificar reinicio persistente y tablas39',
'Ejecutar backup nativo desde operador público','Ejecutar Restore público y administrador13','Comparar39 tablas con excepciones administrativas','Verificar revocación/roles/secretos/TLS nuevos','Verificar CRT/intactos y parada de procesos propios',
'Cerrar Source969 y preparado/sello1029','Separar historias12/11 y permisos/artefactos','Definir Prepared1149 y recuperación969/12','Copiar principal actual a dos bases nuevas','Migrar sólo SQL013 en la nueva principal',
'Verificar37 tablas previas y dos nuevas vacías','Verificar recuperación12/37 exacta y cinco secretos','Probar quietud/locks/rutas/identidad/puntero','Probar selección y retorno sin actividad','Probar actividad compensada sin renovar baselines',
'Probar arranque compatible13 y recuperación12','Confirmar lifecycles completos de fixtures nuevos','Ejecutar focoPG independiente de recuperación849/11','Resolver hallazgos con atribución/evidencia real','Emitir gate técnico independiente previo al GO',
'Reconfirmar quietud y entradas del QA real','Registrar GO del coordinador con hashes','Preparar copia real en otra instancia','Seleccionar copia real tras readiness/quietud','Validar puntero/pareja/configuración y parada',
'Añadir pareja1089 a listas heredadas pertinentes','Habilitar QA82–84 sólo tras selección real','Conservar81 casos/notas/resultados previos','Regenerar ambas guías y pruebas de disponibilidad','Actualizar continuidad/mapa/CHANGELOG',
'Separar resultados nuevos/históricos y límites','Preparar verificación final de guards/artefactos','Preparar adenda final independiente','Preparar diff y SHA256SUMS nuevos','Preparar cierre local e informe de avance/pendientes'
]
assert len(titles)==60
p=ROOT/'docs/PLAN-SESENTA-TANDAS-1090-1149.json'
with p.open('x',encoding='utf-8') as f:json.dump(dict(scope='Integración Windows y nueva copia QA13, sin recompilar;60hitos internos, no60funciones/suites.',initialProgress=78,total=60,completed=0,batches=[dict(id=1090+i,title=t,status='pending') for i,t in enumerate(titles)]),f,ensure_ascii=False,indent=2);f.write('\n')
print('60 hitos pendientes registrados')
