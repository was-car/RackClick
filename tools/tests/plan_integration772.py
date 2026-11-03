"""Bounded operational milestones; completion requires attributed evidence."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
TITLES='''Git y estado inicial
Guardas de QA, candidata y paquetes históricos
Contrato cerrado de integración11
Pin712 y distribución completa
Perfil712 en productor
Perfil712 en lector Windows
SQL001–011 y recuentos38
Stage11 verificado
Readiness11 estricto
New11 sin herramientas de desarrollo
Grants del administrador recuperado11
Negativo backup10 con stage11
Arnés nativo nuevo
HTTPS y secretos de instalación
Login Unicode y propietario
Preferencias de dos cuentas
Lector sin edición de inventario
Recibos y fence personales
Persistencia después del reinicio
Backup11 nativo
Restore11 y CLI real
Comparación de35tablas
Sesiones copiadas revocadas
Administrador nuevo sin preferencias heredadas
Origen y proceso de retorno conservados
Manual del paquete
Manual de construcción
Manual operativo
Manual de recuperación
Congelación de operadores y manuales
Primer ZIP en salida nueva
Segundo ZIP idéntico
Identidad cerrada Source592/schema10
Candidata712/schema11 sin override
Copia de33tablas y dos tablas nuevas vacías
SecretosPG nuevos y privados de aplicación exactos
Recuperación10 separada
Watermark antes del dump
Baseline después de preparar
PID y propiedad de procesos
Control.lock y fuente activa
Preview readiness11 y GUI exacta
Selección atómica y confirmación
Retorno por puntero guardado
Actividad compensada bloquea retorno
Fallo después del puntero conserva ramas
Autovacuum y puerto ajeno
Prueba Windows/PostgreSQL de transición
Revisión independiente de operadores
Foco propio independiente de transición
Preflight estático de QA real
GO técnico con evidencias fijadas
Preparar copia real en clúster nuevo
Seleccionar y validar QA11 sin login
Conservar origen10 y ambas ramas detenidas
Matrices de compatibilidad GUI heredada
QA72–74 detallados y disponibles según snapshot
Regenerar guías y verificar disponibilidad
Continuidad, progreso y mapa
Diff, hashes, revisión y cierre local'''.splitlines()
def main():
    p=ROOT/'docs/PLAN-SESENTA-TANDAS-713-772.json'
    if p.exists():raise SystemExit('Preserve plan')
    assert len(TITLES)==60
    data=dict(revision='2026-10-18',initialProgress=78,completed=0,scope='Integración Windows/QA11; candidata712 reutilizada sin compilación. Hitos internos, no módulos ni suites.',batches=[dict(id=i,title=t,status='planned') for i,t in enumerate(TITLES,713)])
    p.write_bytes((json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode());print('60 planned')
if __name__=='__main__':main()
