import { ApiError, type RackClickApi } from './api.ts';

export type AuditFilters = { actorId: string; resourceId: string };
export type AuditCursor = { id: string; occurredAt: string };
export type AuditEvent = AuditCursor & { actor: { id: string; userName: string }; requestId: string; action: string; resourceId: string };
export type AuditPage = { revision: number; events: AuditEvent[]; nextBeforeId: string | null };
export type AuditNameState = { name: string; revision: number };
export type AuditDetail = { revision: number; event: AuditEvent; detail: { status: 'available' | 'unavailable'; revisionScope: 'systemhaus' | 'customer' | null; customerId: string | null; before: AuditNameState | null; after: AuditNameState | null } };
const keys = (x: any, expected: string) => !!x && typeof x === 'object' && !Array.isArray(x) && Object.keys(x).sort().join() === expected;
const uuid = (x: unknown): x is string => typeof x === 'string' && /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(x) && x !== '00000000-0000-0000-0000-000000000000';
const text = (x: any) => typeof x === 'string' && /\P{White_Space}/u.test(x);
export function timestamp(value: unknown): string | null {
 if (typeof value !== 'string') return null;
 const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,7}))?Z$/.exec(value);
 if (!m || +m[1] < 1) return null;
 const d = new Date(value), parts = [d.getUTCFullYear(), d.getUTCMonth() + 1, d.getUTCDate(), d.getUTCHours(), d.getUTCMinutes(), d.getUTCSeconds()];
 if (!Number.isFinite(d.getTime()) || parts.some((v, i) => v !== +m[i + 1])) return null;
 // Preserve sub-millisecond precision when comparing timestamps with equal milliseconds.
 return value.slice(0, 19) + '.' + (m[7] || '').padEnd(7, '0');
}
const orderKey = (event: AuditCursor) => timestamp(event.occurredAt)! + event.id.toLowerCase();
export const validEvent = (event: any): event is AuditEvent => keys(event, 'action,actor,id,occurredAt,requestId,resourceId') && uuid(event.id) && !!timestamp(event.occurredAt) && uuid(event.requestId) && uuid(event.resourceId) && text(event.action) && keys(event.actor, 'id,userName') && uuid(event.actor.id) && text(event.actor.userName);
function actor(api: RackClickApi, expected: string) {
 if (!uuid(expected) || api.actorId !== expected) throw new ApiError(409, 'actor_changed');
}
export function validateAuditFilters(value: AuditFilters): AuditFilters {
 if (!keys(value, 'actorId,resourceId') || [value.actorId, value.resourceId].some(id => id !== '' && !uuid(id))) throw new ApiError(422, 'audit_filter_invalid');
 return { actorId: value.actorId.toLowerCase(), resourceId: value.resourceId.toLowerCase() };
}
export async function readAuditPage(api: RackClickApi, before: AuditCursor | null = null, expected = api.actorId, filters: AuditFilters = {actorId:'',resourceId:''}): Promise<AuditPage> {
 actor(api, expected);
 const selected = validateAuditFilters(filters);
 if (before !== null && (!keys(before, 'id,occurredAt') || !uuid(before.id) || !timestamp(before.occurredAt))) throw new ApiError(422, 'request_invalid');
 const query = (selected.actorId ? '&actorId=' + encodeURIComponent(selected.actorId) : '') + (selected.resourceId ? '&resourceId=' + encodeURIComponent(selected.resourceId) : '');
 const { data, etag } = await api.request('/admin/audit?limit=50' + (before ? '&beforeId=' + encodeURIComponent(before.id) : '') + query);
 actor(api, expected);
 const invalid = () => { throw new ApiError(200, 'response_invalid'); };
 if (!keys(data, 'events,nextBeforeId,revision') || !Number.isSafeInteger(data.revision) || data.revision < 1 || etag !== '"' + data.revision + '"' || !Array.isArray(data.events) || data.events.length > 50) invalid();
 const seen = new Set<string>();
 let prior = before ? orderKey(before) : null;
 for (const event of data.events) {
  if (!validEvent(event)) invalid();
  if ((selected.actorId && event.actor.id.toLowerCase() !== selected.actorId) || (selected.resourceId && event.resourceId.toLowerCase() !== selected.resourceId)) invalid();
  const key = orderKey(event), id = event.id.toLowerCase();
  if (seen.has(id) || (prior !== null && key >= prior)) invalid();
  seen.add(id); prior = key;
 }
 if (data.nextBeforeId !== null && (!uuid(data.nextBeforeId) || data.events.length !== 50 || data.nextBeforeId.toLowerCase() !== data.events[49].id.toLowerCase())) invalid();
 return data;
}

export async function readAuditDetail(api: RackClickApi, event: AuditEvent, expected = api.actorId): Promise<AuditDetail> {
 actor(api, expected);
 if (!validEvent(event)) throw new ApiError(422, 'request_invalid');
 // Capture immutable event identity before awaiting; the current actor name may change.
 const selected = { ...event, actor: { ...event.actor } };
 const { data, etag } = await api.request('/admin/audit/' + encodeURIComponent(selected.id));
 actor(api, expected);
 const invalid = () => { throw new ApiError(200, 'response_invalid'); };
 const sameId = (a: string, b: string) => a.toLowerCase() === b.toLowerCase();
 if (!keys(data, 'detail,event,revision') || !Number.isSafeInteger(data.revision) || data.revision < 1 || etag !== '"' + data.revision + '"' || !validEvent(data.event)) invalid();
 const found = data.event;
 if (!sameId(found.id, selected.id) || !sameId(found.actor.id, selected.actor.id) || !sameId(found.requestId, selected.requestId) || !sameId(found.resourceId, selected.resourceId) || found.action !== selected.action || timestamp(found.occurredAt) !== timestamp(selected.occurredAt)) invalid();
 const detail = data.detail;
 if (!keys(detail, 'after,before,customerId,revisionScope,status')) invalid();
 if (detail.status === 'unavailable') {
  if ([detail.revisionScope, detail.customerId, detail.before, detail.after].some(value => value !== null)) invalid();
 } else if (detail.status === 'available') {
  const name = (value: any) => typeof value === 'string' && value.length > 0 && !/^\p{White_Space}|\p{White_Space}$/u.test(value) && Array.from(value).length <= 100 && !/\p{Cc}/u.test(value) && Array.from(value).every(c => c.codePointAt(0)! < 0xd800 || c.codePointAt(0)! > 0xdfff);
  const state = (value: any) => keys(value, 'name,revision') && name(value.name) && Number.isSafeInteger(value.revision) && value.revision > 0;
  const house = found.action === 'systemhaus.rename', create = found.action === 'customer.create';
  if ((!house && !create && found.action !== 'customer.rename') || !state(detail.after)) invalid();
  if (house ? detail.revisionScope !== 'systemhaus' || detail.customerId !== null : detail.revisionScope !== 'customer' || !uuid(detail.customerId) || !sameId(detail.customerId, found.resourceId)) invalid();
  if (create ? detail.before !== null || detail.after.revision !== 1 : !state(detail.before) || !Number.isSafeInteger(detail.before.revision + 1) || detail.after.revision !== detail.before.revision + 1) invalid();
 } else invalid();
 return data;
}

export type AuditFieldType = 'uuid' | 'name' | 'userName' | 'boolean' | 'capability' | 'scope' | 'groupKind' | 'state';
export type AuditAdministrativeField = { field: string; type: AuditFieldType; before: string | null; after: string | null };
export type AuditAdministrativeDetail = { revision: number; event: AuditEvent; detail: { status: 'available' | 'unavailable'; fields: AuditAdministrativeField[] } };
const administrativeFields: Record<string, readonly (readonly [string, AuditFieldType])[]> = {
 'user.create': [['userId','uuid'],['userName','userName'],['active','boolean']],
 'userGroup.create': [['groupId','uuid'],['name','name'],['groupKind','groupKind']],
 'customerGroup.create': [['groupId','uuid'],['name','name'],['groupKind','groupKind']],
 'userGroup.member.set': [['groupId','uuid'],['userId','uuid'],['assigned','boolean']],
 'customerGroup.member.set': [['groupId','uuid'],['customerId','uuid'],['assigned','boolean']],
 'userGroup.grant.set': [['groupId','uuid'],['grantId','uuid'],['capability','capability'],['scope','scope'],['targetId','uuid'],['assigned','boolean']],
 'user.state.set': [['userId','uuid'],['userName','userName'],['active','boolean']],
 'user.password.reset': [['userId','uuid'],['userName','userName'],['active','boolean'],['passwordReset','boolean']],
 'user.session.revoke': [['userId','uuid'],['sessionId','uuid'],['revoked','boolean'],['wasCurrent','boolean']]
};
const cancelFields = [['requestId','uuid'],['state','state']] as const;
for (const action of Object.keys(administrativeFields)) administrativeFields[action + '.cancel'] = action === 'user.session.revoke'
 ? [['userId','uuid'],['sessionId','uuid'],...cancelFields] : cancelFields;
export function isAdministrativeAuditAction(action: string): boolean { return Object.hasOwn(administrativeFields, action); }
const auditCapabilities = new Set(['systemhaus.read','systemhaus.manage','customer.create','customer.manage','inventory.read','inventory.edit','inventory.delete','security.manage','reports.export','templates.publish']);
const historicalAuditName = (value: unknown): value is string => typeof value === 'string' && value.length > 0 && !/^\p{White_Space}|\p{White_Space}$/u.test(value) && Array.from(value).length <= 100 && !/\p{Cc}/u.test(value) && Array.from(value).every(c => c.codePointAt(0)! < 0xd800 || c.codePointAt(0)! > 0xdfff);
export async function readAdministrativeAuditDetail(api: RackClickApi, event: AuditEvent, expected = api.actorId): Promise<AuditAdministrativeDetail> {
 actor(api, expected);
 if (!validEvent(event) || !isAdministrativeAuditAction(event.action)) throw new ApiError(422, 'request_invalid');
 const selected = { ...event, actor: { ...event.actor } };
 const { data, etag } = await api.request('/admin/audit/' + encodeURIComponent(selected.id) + '/administrative-detail');
 actor(api, expected);
 const invalid = (): never => { throw new ApiError(200, 'response_invalid'); };
 const same = (a: string | null, b: string | null) => a === null || b === null ? a === b : a.toLowerCase() === b.toLowerCase();
 if (!keys(data, 'detail,event,revision') || !Number.isSafeInteger(data.revision) || data.revision < 1 || etag !== '"' + data.revision + '"' || !validEvent(data.event)) invalid();
 const found = data.event;
 if (!same(found.id, selected.id) || !same(found.actor.id, selected.actor.id) || !same(found.requestId, selected.requestId) || !same(found.resourceId, selected.resourceId) || found.action !== selected.action || timestamp(found.occurredAt) !== timestamp(selected.occurredAt)) invalid();
 const detail = data.detail;
 if (!keys(detail, 'fields,status') || !Array.isArray(detail.fields)) invalid();
 if (detail.status === 'unavailable') { if (detail.fields.length !== 0) invalid(); return data; }
 if (detail.status !== 'available') invalid();
 const expectedFields = administrativeFields[selected.action];
 if (detail.fields.length !== expectedFields.length) invalid();
 const validValue = (type: AuditFieldType, value: unknown) => value === null || (type === 'uuid' ? uuid(value)
  : type === 'name' || type === 'userName' ? historicalAuditName(value)
  : type === 'boolean' ? value === 'true' || value === 'false'
  : type === 'capability' ? typeof value === 'string' && auditCapabilities.has(value)
  : type === 'scope' ? ['systemhaus','customer','customerGroup'].includes(value as string)
  : type === 'groupKind' ? value === 'userGroup' || value === 'customerGroup'
  : type === 'state' && value === 'cancelled');
 const values = new Map<string, AuditAdministrativeField>();
 detail.fields.forEach((field: any, i: number) => {
  const [name,type] = expectedFields[i];
  if (!keys(field, 'after,before,field,type') || field.field !== name || field.type !== type || !validValue(type,field.before) || !validValue(type,field.after)) invalid();
  values.set(name,field);
 });
 const value = (key: string, side: 'before' | 'after') => values.get(key)![side];
 const requireValue = (condition: boolean) => { if (!condition) invalid(); };
 const action = selected.action;
 if (action.endsWith('.cancel')) {
  requireValue(value('requestId','before') === null && same(value('requestId','after'),selected.requestId) && value('state','before') === null && value('state','after') === 'cancelled');
  if (action === 'user.session.revoke.cancel') requireValue(uuid(value('userId','before')) && same(value('sessionId','before'),selected.resourceId) && value('userId','after') === null && value('sessionId','after') === null);
  return data;
 }
 const create = action.endsWith('.create');
 for (const field of values.values()) {
  const extra = field.field === 'passwordReset' || field.field === 'revoked' || field.field === 'wasCurrent';
  if (create || extra) requireValue(field.before === null);
  else if (field.field !== 'targetId') requireValue(field.before !== null);
  if (field.field !== 'targetId') requireValue(field.after !== null);
 }
 const bothSame = (key: string, identity = false) => requireValue(identity ? same(value(key,'before'),value(key,'after')) : value(key,'before') === value(key,'after'));
 const resource = action.startsWith('userGroup.') || action === 'customerGroup.create' || action === 'customerGroup.member.set' ? 'groupId' : action === 'user.session.revoke' ? 'sessionId' : 'userId';
 requireValue(same(value(resource,'after'),selected.resourceId));
 if (create) {
  if (action === 'user.create') requireValue(value('active','after') === 'true');
  else requireValue(value('groupKind','after') === (action === 'userGroup.create' ? 'userGroup' : 'customerGroup'));
 } else if (action === 'user.state.set' || action === 'user.password.reset') {
  bothSame('userId',true); bothSame('userName');
  if (action === 'user.password.reset') { bothSame('active'); requireValue(value('passwordReset','after') === 'true'); }
 } else if (action === 'user.session.revoke') {
  bothSame('userId',true); bothSame('sessionId',true); requireValue(value('revoked','after') === 'true');
  if (value('wasCurrent','after') === 'true') requireValue(same(value('userId','after'),selected.actor.id));
 } else {
  for (const field of values.values()) if (field.field !== 'assigned') bothSame(field.field,field.type === 'uuid');
  if (action === 'userGroup.grant.set') requireValue(value('scope','after') === 'systemhaus' ? value('targetId','after') === null : uuid(value('targetId','after')));
 }
 return data;
}
