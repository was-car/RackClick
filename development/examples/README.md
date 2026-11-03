> **02.11.2026 · Demo50 adicional preparada.** [Datos, alcance y reproducción](../../docs/LABORATORIO-50-CLIENTES.md):50clientes nuevos y868parejas perfil/revisión en laboratorio43. Es opcional, sin seguridad, y su integraciónWindows queda enpunto5. Los diez originales y el cargador15 descritos debajo se conservan; no usar ese cargador paraDemo50 ni copiar datos a una instalación existente.

# Inventario sintetico original

`demo-original.inventory.json` contiene solo inventario de los diez clientes ficticios aportados por Wascar, convertido desde RC9 al formato canonico del cargador. SHA256: `cbfe4b43a0148299f6f4c24a21dfcb5e21a8efd5ca2d08d552119ac0cd292bd7`.

No contiene cuentas, passwords, sesiones, factores MFA ni conexiones PostgreSQL. No es una copia completa de seguridad. No se importa a una base en uso: el cargador exige destino vacio, actor global autorizado, esquema15 y rol de ejecucion limitado.

Seguir [Instalacion desde GitHub](../../docs/INSTALACION-DESDE-GITHUB.md) para cargarlo automaticamente en un laboratorio nuevo. El auxiliar conserva las identidades de inventario y genera cuentas/secretos nuevos localmente. La base actual de Wascar no se copia.
