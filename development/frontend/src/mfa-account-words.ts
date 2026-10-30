export const mfaAccountWords = {
 en: {
  selfTitle: 'My security', adminTitle: 'Authentication methods', title: 'Multifactor authentication', user: 'User',
  refresh: 'Refresh status', loading: 'Reading the security status from the server…', choose: 'Select a user to manage their authentication methods.',
  active: 'Authenticator configured', pending: 'Authenticator setup pending', disabled: 'Authenticator deactivated', none: 'Authenticator not configured',
  required: 'MFA required', optional: 'MFA can be configured now', exempt: 'Global Systemhaus administrators are exempt from the deadline. You can still protect your account with MFA.',
  grace: 'You have {days} days left to configure MFA.', deadline: 'The registration deadline has been reached. MFA must be configured before normal access.',
  noPolicy: 'No registration deadline has been activated for this installation.', unavailable: 'MFA is not available in this installation. No security change can be confirmed here.',
  serverDate: 'Registration deadline', enable: 'Activate MFA', disable: 'Deactivate MFA', reset: 'Require authenticator setup again',
  enableHelp: 'All sessions of this account will end. The account holder must sign in and configure an authenticator before receiving access.',
  disableHelp: 'All sessions and pending challenges of this account will end. The registration deadline is retained; deactivation does not extend the grace period.',
  resetHelp: 'The existing factor will stop working and all sessions will end. The account holder must configure a new authenticator at the next sign-in.',
  confirm: 'I understand the effect on this account and its sessions', save: 'Confirm change', password: 'Your current password', working: 'Waiting for server confirmation…',
  verifyAdmin: 'To change another account, sign in with MFA as an administrator with security-management permission.',
  verifySession: 'This change requires a session verified with MFA. Sign in with your authenticator first.',
  selfService: 'To manage your own authenticator, open My security from the dashboard.',
  selfHelp: 'Use your current password to confirm changes to your account. QR codes and setup keys are shown only to the account holder during sign-in.',
  adminHelp: 'Administrators manage requirements and resets. They do not receive another user’s setup key or QR code.',
  saved: 'Security change confirmed by the server.', reauthenticate: 'Sign in again', signInHelp: 'Sign in again to complete setup or verify the current state.',
  pendingRequest: 'This change is awaiting confirmation. The original account, action and request are retained; no password is stored.',
  check: 'Check original result', retry: 'Retry original request', notRecorded: 'The server has no recorded result yet. This does not confirm cancellation. Keep the original request.',
  recoverTarget: 'An earlier security request belongs to this account', cancelForm: 'Close confirmation', requestId: 'Request reference',
  denied: 'The server did not authorize this change.', expired: 'Your session is unavailable. Sign in again as the same user to check the original request.',
  conflict: 'The revision changed. Refresh the status before a new change. An unconfirmed original request must be checked first.',
  passwordInvalid: 'The current password was not accepted.', passwordLength: 'Enter your current password.',
  policyRequired: 'MFA is required by policy. Change or reset the authenticator instead of removing the requirement.',
  uncertain: 'No valid server confirmation was received. Check the original result before making another change.',
  storage: 'The recovery journal is unavailable. No new change has been sent.', error: 'The security request could not be confirmed.',
  manage: 'Manage my MFA', remaining: 'Time to configure MFA', lastAdmin: 'This action would remove the last usable global administrator. Use the protected recovery procedure.',
 },
 de: {
  selfTitle: 'Meine Sicherheit', adminTitle: 'Authentifizierungsmethoden', title: 'Mehrstufige Authentifizierung', user: 'Benutzer',
  refresh: 'Status aktualisieren', loading: 'Sicherheitsstatus wird vom Server gelesen…', choose: 'Wählen Sie einen Benutzer aus, um dessen Authentifizierungsmethoden zu verwalten.',
  active: 'Authenticator eingerichtet', pending: 'Authenticator-Einrichtung ausstehend', disabled: 'Authenticator deaktiviert', none: 'Authenticator nicht eingerichtet',
  required: 'MFA erforderlich', optional: 'MFA kann jetzt eingerichtet werden', exempt: 'Globale Systemhaus-Administratoren sind von der Frist ausgenommen. Sie können ihr Konto trotzdem mit MFA schützen.',
  grace: 'Sie haben noch {days} Tage, um MFA einzurichten.', deadline: 'Die Einrichtungsfrist ist abgelaufen. MFA muss vor dem normalen Zugriff eingerichtet werden.',
  noPolicy: 'Für diese Installation wurde keine Einrichtungsfrist aktiviert.', unavailable: 'MFA ist in dieser Installation nicht verfügbar. Hier kann keine Sicherheitsänderung bestätigt werden.',
  serverDate: 'Einrichtungsfrist', enable: 'MFA aktivieren', disable: 'MFA deaktivieren', reset: 'Neue Authenticator-Einrichtung verlangen',
  enableHelp: 'Alle Sitzungen dieses Kontos werden beendet. Der Kontoinhaber muss sich anmelden und einen Authenticator einrichten, bevor der Zugriff erteilt wird.',
  disableHelp: 'Alle Sitzungen und ausstehenden Anfragen dieses Kontos werden beendet. Die Einrichtungsfrist bleibt bestehen; die Deaktivierung verlängert sie nicht.',
  resetHelp: 'Der bisherige Faktor funktioniert danach nicht mehr, und alle Sitzungen werden beendet. Der Kontoinhaber muss bei der nächsten Anmeldung einen neuen Authenticator einrichten.',
  confirm: 'Ich verstehe die Auswirkungen auf dieses Konto und seine Sitzungen', save: 'Änderung bestätigen', password: 'Ihr aktuelles Passwort', working: 'Warten auf Serverbestätigung…',
  verifyAdmin: 'Um ein anderes Konto zu ändern, melden Sie sich mit MFA als Administrator mit Sicherheitsverwaltungsrecht an.',
  verifySession: 'Diese Änderung erfordert eine mit MFA bestätigte Sitzung. Melden Sie sich zuerst mit Ihrem Authenticator an.',
  selfService: 'Öffnen Sie Meine Sicherheit im Dashboard, um Ihren eigenen Authenticator zu verwalten.',
  selfHelp: 'Bestätigen Sie Änderungen am eigenen Konto mit Ihrem aktuellen Passwort. QR-Code und Einrichtungsschlüssel werden nur dem Kontoinhaber bei der Anmeldung gezeigt.',
  adminHelp: 'Administratoren verwalten Anforderungen und Zurücksetzungen. Sie erhalten weder Einrichtungsschlüssel noch QR-Code anderer Benutzer.',
  saved: 'Sicherheitsänderung vom Server bestätigt.', reauthenticate: 'Erneut anmelden', signInHelp: 'Melden Sie sich erneut an, um die Einrichtung abzuschließen oder den aktuellen Status zu prüfen.',
  pendingRequest: 'Diese Änderung wartet auf Bestätigung. Konto, Aktion und Auftrag bleiben erhalten; kein Passwort wird gespeichert.',
  check: 'Ursprüngliches Ergebnis prüfen', retry: 'Ursprünglichen Auftrag wiederholen', notRecorded: 'Der Server hat noch kein Ergebnis gespeichert. Dies bestätigt keinen Abbruch. Bewahren Sie den ursprünglichen Auftrag auf.',
  recoverTarget: 'Ein früherer Sicherheitsauftrag gehört zu diesem Konto', cancelForm: 'Bestätigung schließen', requestId: 'Auftragsreferenz',
  denied: 'Der Server hat diese Änderung nicht autorisiert.', expired: 'Ihre Sitzung ist nicht verfügbar. Melden Sie sich als derselbe Benutzer an, um den ursprünglichen Auftrag zu prüfen.',
  conflict: 'Die Revision wurde geändert. Aktualisieren Sie den Status vor einer neuen Änderung. Ein unbestätigter Auftrag muss zuerst geprüft werden.',
  passwordInvalid: 'Das aktuelle Passwort wurde nicht akzeptiert.', passwordLength: 'Geben Sie Ihr aktuelles Passwort ein.',
  policyRequired: 'Die Richtlinie verlangt MFA. Ändern Sie den Authenticator oder setzen Sie ihn zurück, statt die Anforderung zu entfernen.',
  uncertain: 'Keine gültige Serverbestätigung empfangen. Prüfen Sie das ursprüngliche Ergebnis vor einer weiteren Änderung.',
  storage: 'Das Wiederherstellungsjournal ist nicht verfügbar. Es wurde keine neue Änderung gesendet.', error: 'Der Sicherheitsauftrag konnte nicht bestätigt werden.',
  manage: 'Meine MFA verwalten', remaining: 'Zeit zur MFA-Einrichtung', lastAdmin: 'Diese Aktion würde den letzten nutzbaren globalen Administrator entfernen. Verwenden Sie das geschützte Wiederherstellungsverfahren.',
 },
 es: {
  selfTitle: 'Mi seguridad', adminTitle: 'Métodos de autenticación', title: 'Autenticación multifactor', user: 'Usuario',
  refresh: 'Actualizar estado', loading: 'Leyendo el estado de seguridad del servidor…', choose: 'Selecciona un usuario para gestionar sus métodos de autenticación.',
  active: 'Autenticador configurado', pending: 'Configuración del autenticador pendiente', disabled: 'Autenticador desactivado', none: 'Autenticador sin configurar',
  required: 'MFA obligatorio', optional: 'Puedes configurar MFA ahora', exempt: 'Los administradores globales de Systemhaus están exentos del plazo. Aun así, puedes proteger tu cuenta con MFA.',
  grace: 'Te quedan {days} días para configurar MFA.', deadline: 'El plazo de configuración ha vencido. Debes configurar MFA antes de obtener acceso normal.',
  noPolicy: 'No se ha activado un plazo de configuración para esta instalación.', unavailable: 'MFA no está disponible en esta instalación. Aquí no se puede confirmar ningún cambio de seguridad.',
  serverDate: 'Fecha límite de configuración', enable: 'Activar MFA', disable: 'Desactivar MFA', reset: 'Exigir una nueva configuración del autenticador',
  enableHelp: 'Se cerrarán todas las sesiones de esta cuenta. Su titular deberá iniciar sesión y configurar un autenticador antes de obtener acceso.',
  disableHelp: 'Se cerrarán todas las sesiones y desafíos pendientes de esta cuenta. La fecha límite se conserva; desactivarlo no amplía el periodo de gracia.',
  resetHelp: 'El factor anterior dejará de funcionar y se cerrarán todas las sesiones. Su titular deberá configurar un nuevo autenticador en el siguiente inicio de sesión.',
  confirm: 'Entiendo el efecto sobre esta cuenta y sus sesiones', save: 'Confirmar cambio', password: 'Tu contraseña actual', working: 'Esperando confirmación del servidor…',
  verifyAdmin: 'Para modificar otra cuenta, inicia sesión con MFA como administrador con permiso de gestión de seguridad.',
  verifySession: 'Este cambio requiere una sesión verificada con MFA. Inicia sesión primero con tu autenticador.',
  selfService: 'Para gestionar tu propio autenticador, abre Mi seguridad desde el dashboard.',
  selfHelp: 'Confirma los cambios de tu cuenta con tu contraseña actual. El QR y la clave de configuración sólo se muestran al titular durante el inicio de sesión.',
  adminHelp: 'El administrador gestiona requisitos y restablecimientos. No recibe la clave de configuración ni el QR de otro usuario.',
  saved: 'Cambio de seguridad confirmado por el servidor.', reauthenticate: 'Iniciar sesión de nuevo', signInHelp: 'Inicia sesión de nuevo para completar la configuración o comprobar el estado actual.',
  pendingRequest: 'Este cambio está pendiente de confirmación. Se conservan la cuenta, la acción y la solicitud originales; no se guarda ninguna contraseña.',
  check: 'Consultar resultado original', retry: 'Reintentar solicitud original', notRecorded: 'El servidor todavía no tiene un resultado registrado. No confirma una cancelación. Conserva la solicitud original.',
  recoverTarget: 'Una solicitud de seguridad anterior pertenece a esta cuenta', cancelForm: 'Cerrar confirmación', requestId: 'Referencia de solicitud',
  denied: 'El servidor no ha autorizado este cambio.', expired: 'Tu sesión no está disponible. Inicia sesión como el mismo usuario para consultar la solicitud original.',
  conflict: 'La revisión cambió. Actualiza el estado antes de un cambio nuevo. Primero debes consultar cualquier solicitud original sin confirmar.',
  passwordInvalid: 'No se ha aceptado la contraseña actual.', passwordLength: 'Introduce tu contraseña actual.',
  policyRequired: 'La política exige MFA. Cambia o restablece el autenticador en lugar de quitar la obligación.',
  uncertain: 'No se recibió una confirmación válida del servidor. Consulta el resultado original antes de realizar otro cambio.',
  storage: 'El registro de recuperación no está disponible. No se ha enviado ningún cambio nuevo.', error: 'No se pudo confirmar la solicitud de seguridad.',
  manage: 'Gestionar mi MFA', remaining: 'Plazo para configurar MFA', lastAdmin: 'Esta acción dejaría sin acceso al último administrador global utilizable. Usa el procedimiento protegido de recuperación.',
 },
};

export function mfaAccountError(error: { code?: string; status?: number; uncertain?: boolean } = {}) {
 if (error.uncertain || error.code === 'network_unconfirmed' || error.code === 'response_invalid' || error.status === 0) return 'uncertain';
 if (error.code === 'draft_storage_unavailable') return 'storage';
 if (error.code === 'mfa_use_self_service') return 'selfService';
 if (error.code === 'mfa_verification_required') return 'verifySession';
 if (error.code === 'mfa_required_by_policy' || error.code === 'mfa_policy_required') return 'policyRequired';
 if (error.code === 'last_administrator' || error.code === 'last_global_administrator') return 'lastAdmin';
 if (error.code === 'password_invalid' || error.code === 'login_failed' || error.code === 'mfa_reauthentication_required') return 'passwordInvalid';
 if (error.code === 'password_length') return 'passwordLength';
 if (error.code === 'mfa_unavailable' || error.status === 503) return 'unavailable';
 if (error.status === 412 || error.code === 'revision_changed') return 'conflict';
 if (error.status === 401 || error.code === 'actor_changed') return 'expired';
 if (error.status === 403) return 'denied';
 return 'error';
}

export function mfaAccountNotice(status: { factorState: string; enrollmentPending: boolean; available: boolean; globalAdministratorExempt: boolean; deadlineReached: boolean; daysRemaining: number | null; globalPolicyEnabled: boolean }) {
 if (!status.available) return 'unavailable';
 if (status.enrollmentPending) return 'pending';
 if (status.factorState === 'active') return 'active';
 if (status.globalAdministratorExempt) return 'exempt';
 if (status.deadlineReached) return 'deadline';
 if (status.daysRemaining !== null) return 'grace';
 return 'noPolicy';
}
