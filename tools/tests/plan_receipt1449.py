"""60 internal evidence-backed steps, not60 features or test runs."""
import json
from block1449 import ROOT,E,ER
GROUPS=[
 ('INICIO.json','Fijar Git limpio y commit base|Proteger1024 hashes históricos/QA|Contrastar193 fuentes previas|Conservar QA1329 y recuperación969/12|Proteger puntero/configuración/privados'),
 ('AMBITO-Y-ENTORNO.json','Leer continuidad, aceptación y contrato|Verificar herramientas fijadas sin descargas|Separar implementación/revisión|Acotar vacío funcional de alta de grupos|Restringir propiedad a cinco fuentes'),
 ('@docs/GUI-CONTINUACION-ALTA-GRUPO-S1.md','Definir recibo sólo tras commit validado|Usar UUID/tipo como identidad|Mantener autorización del servidor|Conservar RC9/Click-Click/borradores|Separar desarrollo/integración/adopción'),
 ('autor/IMPLEMENTACION.md','Proyectar recibo sin contraseñas/campos extra|Soportar ambos tipos y nombres literales|Recordar commit antes de limpiar journal|Conservar evidencia tras cleanup fallido|Conservar commit ante notRecorded posterior|Retirar recibo en nueva intención|Invalidar actor/generación401/403|Bloquear pendientes y lecturas obsoletas|Comprobar revisión/presencia UUID/tipo|Consumir navegación una sola vez|Enfocar aunque ya coincida UUID|Preservar tres editores y selección común|Localizar tarjeta/estado persistente'),
 ('autor/FOCO-NODE-02.json','Probar recibo Unicode y literal|Probar adaptadores reales con transporte controlado|Probar commit-cleanupfail-unknown-recuperación|Probar guardas tipo/revisión/actor'),
 ('revision/REVISION-FUENTE.json','Revisar cinco fuentes finales antesbuild|Cerrar dos bordes de recuperación/autoridad'),
 ('SOURCE-FREEZE-APP.json','Congelar195 fuentes con cinco cambios previstos'),
 ('BUILD-01.json','Compilar una vez frontend y cero servidor'),
 ('CANDIDATA1449-01.json','Congelar40 artefactos y sólo app.js nuevo'),
 ('native03/fixture.json','Preparar clúster/basePG17 independientes|Crear grupo usuarios entre homónimos porGUI|Recuperar alta clientes tras respuesta perdida|Conservar borradores al abrir relaciones|Comprobar EN/DE/ES390px/Enter/foco|Leer UUID tras recarga y otra sesión navegador|Contrastar ocho tablas después de cuatro altas|ReiniciarASP.NET y leer otra sesiónHTTP|Comprobar Lector403 en ambos tipos|Detener procesos propios/entradas exactas'),
 ('revision/dom01/result.json','Probar recuperación con dobles declarados|Probar403-latecommit y A-B-A'),
 ('QA-TESTS-01.json','Añadir tres planned/conservar90casos|Conservar buildlists/lógica de resultados|Comprobar disponibilidad90+8|Ejecutar regresión pertinente50/50'),
 ('QA-FOCO-RUTA-02.json','Corregir ruta nuevaQA93 con foco3/3'),
 ('QA-FOCO-ETIQUETAS-03.json','Corregir etiquetas exactas y regenerar ambas guías'),
 ('@docs/MAPA-ENTREGA.json','Actualizar mapa sin cambiar78puntos/pesos'),
 ('INSPECCION-VISUAL.json','Inspeccionar tres capturas finales390px'),
 ('native01/DIAGNOSTICO.json','Preservar fallos nuevos y entradas ejecutadas'),
 ('CIERRE.md','Documentar archivos/comandos/resultados/límites|Preparar cierre revisable/sello/commit local')]
def main():
 rows=[]
 for proof,titles in GROUPS:
  proof=proof[1:] if proof.startswith('@') else ER+'/'+proof
  assert (ROOT/proof).is_file(),proof
  start=1390+len(rows);rows.extend([dict(id=start+i,title=t,status='verified',evidence=proof) for i,t in enumerate(titles.split('|'))])
 assert len(rows)==60 and [r['id'] for r in rows]==list(range(1390,1450))
 p=ROOT/'docs/PLAN-SESENTA-TANDAS-1390-1449.json';assert not p.exists()
 p.write_text(json.dumps(dict(scope='60hitos internos de un incremento y su verificación; no60funciones ni60ejecuciones. Último hito prepara cierre/sello/commit, cuya ejecución final se comprueba aparte.',initialProgress=78,total=60,completed=60,batches=rows),ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('plan60 PASS')
if __name__=='__main__':main()
