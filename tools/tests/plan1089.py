"""Create an explicit 60-milestone implementation ledger, without claiming completion."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
titles=[
 'Comprobar Git y fijar base eb97a85', 'Proteger QA969 y distribución Windows1029',
 'Conservar informes y referencia RC9 adoptada', 'Contrastar categorías y presets originales',
 'Contrastar28 claves simétricas incluidas consigo mismas', 'Contrastar diez muestras/toggle/limpieza',
 'Definir contrato personal separado de permisos y puertos', 'Definir clasificación por clave estable del catálogo',
 'Definir prioridad al crear y ausencia de recolor retroactivo', 'Asignar propiedad de archivos y revisión separada',
 'Añadir SQL013 aditiva y privilegios de runtime', 'Alinear migrador y recuperación administrativa13',
 'Implementar snapshot personal sin escrituras al leer', 'Validar cuerpo cerrado y muestras/claves',
 'Aplicar propietario de sesión y revisión personal', 'Guardar agregado/recibo/auditoría atómicos',
 'Implementar noop/replay y conflictos de intención', 'Implementar consulta/cancelación y fence persistido',
 'Revalidar sesiones tras espera y antes del commit', 'Declarar rutas/DTO/ETag en OpenAPI',
 'Leer una paleta confirmada por comando de conexión', 'Resolver categorías por UUID y ámbito del servidor',
 'Aplicar prioridad explícito/pareja/null en creación simple', 'Aplicar default por pareja en lote heterogéneo atómico',
 'Conservar restricciones de extremos/reservas/PoE/ocupación', 'Conservar update/reconnect/conexiones existentes',
 'Implementar adaptador de snapshot y operaciones cerrado', 'Implementar journal personal e intención original',
 'Invalidar respuestas tardías al cambiar propietario', 'Integrar sección RC9 de28 parejas',
 'Conservar diez muestras/toggle/× y borrador', 'Confirmar Guardar mediante servidor y GET',
 'Resolver error incierto por consulta/reintento/cancelación', 'Conservar prioridad visual/caras/estados/Click-Click',
 'Conservar EN/DE/ES y nombres literales', 'Ejecutar focos Node de adaptador/journal',
 'Congelar fuentes y publicar servidor una vez', 'Ejecutar dominio Windows y compilar frontend común',
 'Congelar candidata completa con esquema13', 'Probar aislamiento personal y persistencia PostgreSQL',
 'Probar validación/límites/noop/replay/cancelación', 'Probar sesión/CSRF/permisos/revocación tras espera',
 'Probar clasificación clave frente a etiquetas traducidas', 'Probar single/cross-rack/lotes y prioridad por extremo',
 'Probar atomicidad/rollback/auditoría e inventario intacto', 'Probar migración12→13/repetición/reinicio/restore39tablas',
 'Ejecutar GUI real: guardar/recargar/otra sesión', 'Ejecutar GUI real: otro actor/error/cambio de propietario',
 'Ejecutar GUI real: creación y no recolor retroactivo', 'Verificar teclado/390px/EN/DE/ES y declarar límites',
 'Realizar foco PostgreSQL propio del revisor independiente', 'Resolver hallazgos con pruebas y fallos conservados',
 'Añadir QA82–84 con ubicación/pasos/resultado/disponibilidad', 'Regenerar guías conservando81 casos y resultados previos',
 'Actualizar continuidad/alcance/mapa/CHANGELOG', 'Contrastar regresión pertinente sin suites duplicadas',
 'Verificar guards/fuentes/artefactos/procesos detenidos', 'Preparar adenda independiente del cierre',
 'Preparar sellado de diff y SHA256SUMS de evidencias nuevas', 'Preparar cierre Git local e informe de porcentaje/límites'
]
assert len(titles)==60
path=ROOT/'docs/PLAN-SESENTA-TANDAS-1030-1089.json'
with path.open('x',encoding='utf-8') as stream:
 json.dump(dict(scope='Paleta personal por parejas de categorías RC9 y default de conexión autoritativo; candidata desarrollo13, QA969 conservado.60hitos internos, no60funciones/suites.',initialProgress=78,total=60,completed=0,
  batches=[dict(id=1030+i,title=title,status='pending') for i,title in enumerate(titles)]),stream,ensure_ascii=False,indent=2);stream.write('\n')
print('60 hitos pendientes registrados')
