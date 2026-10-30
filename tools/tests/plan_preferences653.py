"""Create the sixty bounded integration/verification milestones, not sixty modules."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
TITLES='''Referencia RC9 de idioma/tema
Propiedad personal y valores ausentes
Contrato cerrado de rutas/DTO
DDL011 y constraints personales
Migración10→11 sin alterar33tablas
Sesión vigente sin requisito de cliente
ETag/revisión personal
Cambio explícito de una clave
No-op sin incremento de revisión
Digest canónico y propietario
Recibo terminal duradero
Replay y consulta de estado
Cancelación/fence de petición
Orden de locks y aislamiento
Concurrencia y conflicto personal
Revocación de sesión durante espera
Rollback y auditoría atómicos
Límites/validación/OpenAPI
CLI de recuperación fija11 explícita
Textos EN/DE/ES
Fallback anónimo con dos claves locales
Carga de preferencias del actor actual
Cambio de idioma confirmado
Cambio de tema confirmado
Logout/switch sin heredar preferencias
Guardas de generación tras await
Diario compacto por propietario
Carga pendiente sin revisión inventada
Consulta de intención incierta
Reintento de la petición original
Cancelación original y resultado terminal
Conflicto sin rebase automático
Error GET sin éxito fantasma
Revisiones/inventario/Click-Click intactos
Controles/estado accesibles con CSS RC9
Node contratos y diario
Node actor A→B→A
Node integración y errores
Congelación de fuentes de aplicación
Build Windows y pruebas de dominio
Build frontend local con versión fijada
PostgreSQL: esquema/constraints
PostgreSQL: validación/autenticación
PostgreSQL: aislamiento entre usuarios
PostgreSQL: no-op/replay/fences
PostgreSQL: concurrencia/revocación
PostgreSQL: rollback/auditoría/invariantes
PostgreSQL: reinicio/login/lectura
Edge: dos cuentas sin herencia
Edge: recarga y segunda sesión
Edge: intención incierta/conflicto
Edge: idiomas/temas/teclado
Backup/restore aislado de35tablas
Foco PostgreSQL independiente
Revisión independiente de API/GUI
Casos QA72–74 detallados y disponibilidad real
Guías reproducibles sin tocar notas
Criterio global y mapa de entrega
Integridad/diff/historia/continuidad
Commit local y siguiente trabajo'''.splitlines()
def main():
    assert len(TITLES)==60
    p=ROOT/'docs/PLAN-SESENTA-TANDAS-653-712.json'
    if p.exists():raise SystemExit('Preserve plan')
    groups=lambda i:'Contrato y backend' if i<=671 else 'GUI y adaptador' if i<=690 else 'Pruebas y revisión' if i<=707 else 'QA y cierre'
    data={'group':'653-712','count':60,'completed':0,'initialProgress':78,'progressBasis':'docs/PROGRESO-GLOBAL.md','scope':'Personal language/theme persistence with PostgreSQL11 and existing RC9 controls.60 milestones, not60 modules/suites. Current QA592/schema10 and Windows652 package retained; no actual QA application login/DML/selection.','batches':[{'id':i,'group':groups(i),'title':title,'status':'planned','evidence':None,'independentEvidence':None} for i,title in enumerate(TITLES,653)]}
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('Planned653–712:60 milestones')
if __name__=='__main__':main()
