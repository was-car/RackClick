# Revisión independiente · GUI MFA

Revisores separados de los implementadores: `mfa_gui_security_review` (seguridad) y `auditoria_contrato` (criterio/alcance). Implementación: coordinador y trabajadores `mfa_login_ui`/`mfa_gui_lab_test`.

## Seguridad

La revisión de fuente detectó que suspender los hooks de preferencias durante MFA cambiaba su alcance y podía invalidar la reautenticación que acababa de solicitarse. Se conservó su alcance anterior; el idioma del cuadro MFA pasó a estado local. El revisor aceptó la corrección sobre ServerApp SHA256 `4c2aa0f9c9e723f000d6a72f7318acc86df0e069fc0fbe1583c47b24694721d9` y la API final consignada en FUENTES.json.

Revisó separación desafío/sesión, cancelación y respuestas tardías, guardado de secretos, generación local del QR, mensajes constantes y compatibilidad de Promise<Session>. Ejecutó **22/22 pruebas Node** (10 API MFA, 8 mensajes, 4 QR). Dictamen favorable en ese alcance. No ejecutó PostgreSQL, navegador real ni los trece consumidores de reautenticación por GUI. El coordinador ejecutó y conserva el resultado del navegador por separado.

## Contrato y crédito

El revisor de contrato acepta únicamente **F-07.02: 1/2 punto**, combinando prueba real, implementación y revisión de seguridad. Se muestra secreto/QR de forma transitoria; el código inválido no concede acceso y el válido confirma el factor antes de la sesión. Se acredita desarrollo con proveedor sintético permitido expresamente por la dependencia de F-07.

No acredita escaneo físico del QR, proveedor productivo, identidad del servicio ni F-07.04/.05 o F-04. El índice pasa de 641/84 a 683/84 puntos: 7,630952 → 8,130952 de los 100 puntos del pendiente, sin alterar alcance, denominador o pesos. No se recalcula el porcentaje global del producto.
