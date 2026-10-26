export const groupCompensationWords = {
 en: {
  title:'Review undo of port groups',
  groupGrowth:'The server will remove only the added groups and ports listed below. Existing ports and cables are preserved.',
  groupReduction:'The server will restore the original groups, ports and cables listed below using its recorded evidence. It will not disconnect current cables to make room.',
  limits:'Only a pure addition or removal is supported: 1–256 ports, up to 32 groups and 256 combined port/group IDs. Mixed edits are excluded. The server checks complete evidence, current permissions and conflicts before committing.',
  confirm:'I have reviewed these exact IDs and confirm this undo.',
  context:'This scope describes the confirmed operation. Historical port/cable details are not available for this structural undo; they are not reported as updated ports.'
 },
 de: {
  title:'Rücknahme der Portgruppen prüfen',
  groupGrowth:'Der Server entfernt nur die unten aufgeführten hinzugefügten Gruppen und Ports. Vorhandene Ports und Kabel bleiben erhalten.',
  groupReduction:'Der Server stellt die unten aufgeführten ursprünglichen Gruppen, Ports und Kabel anhand seiner Nachweise wieder her. Aktuelle Kabel werden dafür nicht getrennt.',
  limits:'Nur reines Hinzufügen oder Entfernen: 1–256 Ports, bis zu 32 Gruppen und zusammen 256 Port-/Gruppen-IDs. Gemischte Änderungen sind ausgeschlossen. Der Server prüft vollständige Nachweise, aktuelle Berechtigungen und Konflikte vor dem Speichern.',
  confirm:'Ich habe diese genauen IDs geprüft und bestätige die Rücknahme.',
  context:'Dieser Umfang beschreibt den bestätigten Vorgang. Historische Port-/Kabeldetails sind für diese strukturelle Rücknahme nicht verfügbar; sie werden nicht als aktualisierte Ports ausgegeben.'
 },
 es: {
  title:'Revisar Deshacer de grupos de puertos',
  groupGrowth:'El servidor eliminará únicamente los grupos y puertos añadidos que aparecen abajo. Se conservan los puertos y cables anteriores.',
  groupReduction:'El servidor restaurará los grupos, puertos y cables originales indicados abajo usando su evidencia registrada. No desconectará cables actuales para hacerles sitio.',
  limits:'Sólo altas o bajas puras: 1–256 puertos, hasta 32 grupos y 256 IDs combinados de puertos/grupos. Se excluyen cambios mixtos. El servidor comprueba evidencia completa, permisos actuales y conflictos antes del commit.',
  confirm:'He revisado estos IDs exactos y confirmo este Deshacer.',
  context:'Este alcance describe la operación confirmada. El detalle histórico de puertos/cables no está disponible para esta inversa estructural; no se presenta como puertos actualizados.'
 }
};
