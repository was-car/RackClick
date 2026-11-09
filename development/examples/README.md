# Inventarios sintéticos

## Diez clientes originales

`demo-original.inventory.json` conserva el inventario de los diez clientes ficticios aportados por Wascar, convertido desde RC9 al formato canónico del cargador. SHA256: `cbfe4b43a0148299f6f4c24a21dfcb5e21a8efd5ca2d08d552119ac0cd292bd7`.

La [guía desde GitHub](../../docs/INSTALACION-DESDE-GITHUB.md) lo carga automáticamente en un laboratorio PostgreSQL nuevo con credenciales aleatorias. El cargador de la demo acepta únicamente sus perfiles cerrados de esquema 15/45; no importa seguridad ni modifica una base instalada.

## Cincuenta clientes adicionales

[Colección Demo50, visor y alcance](../../docs/DEMO50.es.md). Los archivos están en `DEMO-50-CLIENTES-01/`, fijados por hashes y separados de la demo anterior. Sus868 parejas perfil/revisión corresponden al catálogo histórico43; el catálogo actual completo incluye884 revisiones. No usar el cargador de los diez clientes para este conjunto ni copiar archivos a una base existente.

Ambos ejemplos son sólo inventario: sin usuarios, contraseñas, sesiones, factores MFA ni cadenas PostgreSQL. No equivalen a backups completos. La publicación no copia las bases actuales de Wascar.
