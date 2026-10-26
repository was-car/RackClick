import { ApiError, type RackClickApi } from './api.ts';
import { readUsers } from './admin-users.ts';
import { readCustomerMemberTargets } from './admin-customer-group-members.ts';

const keys = (x: any, expected: string) => !!x && typeof x === 'object' && !Array.isArray(x) && Object.keys(x).sort().join() === expected;
const uuid = (x: unknown): x is string => typeof x === 'string' && /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(x) && x !== '00000000-0000-0000-0000-000000000000';
const text = (x: unknown) => typeof x === 'string' && x.trim().length > 0;
const unique = (xs: any[], key: (x: any) => string) => new Set(xs.map(key)).size === xs.length;
const caps = (xs: any) => Array.isArray(xs) && xs.every(text) && unique(xs, x => x);
const user = (x: any) => keys(x, 'active,id,userName') && uuid(x.id) && text(x.userName) && typeof x.active === 'boolean';
const invalid = () => { throw new ApiError(200, 'response_invalid'); };
function actor(api: RackClickApi, expected: string) {
 if (!uuid(expected) || api.actorId !== expected) throw new ApiError(409, 'actor_changed');
}
// Only user and effective-permission routes promise ETag; group targets use body revision.
function guarded(api: RackClickApi, expected: string): RackClickApi {
 actor(api, expected);
 return { get actorId() { return api.actorId; }, async request(path: string) {
  actor(api, expected); const response = await api.request(path); actor(api, expected);
  if (!Number.isSafeInteger(response.data?.revision) || response.data.revision < 1 || ((path === '/admin/users' || path.endsWith('/effective-permissions')) && response.etag !== '"' + response.data.revision + '"')) invalid();
  return response;
 } } as RackClickApi;
}
export async function readEffectivePermissionAccounts(api: RackClickApi, expected = api.actorId) {
 const data = await readUsers(guarded(api, expected)); actor(api, expected);
 if (!keys(data, 'revision,users') || !data.users.every(user) || !unique(data.users, (u: any) => u.id.toLowerCase())) invalid();
 return data;
}
export async function readEffectivePermissions(api: RackClickApi, userId: string, expected = api.actorId) {
 actor(api, expected); if (!uuid(userId)) throw new ApiError(422, 'request_invalid');
 const { data } = await guarded(api, expected).request('/admin/users/' + userId + '/effective-permissions'); actor(api, expected);
 if (!keys(data, 'permissions,revision,user') || !user(data.user) || data.user.id !== userId || !keys(data.permissions, 'customers,sources,systemhausCapabilities')) invalid();
 const p = data.permissions;
 if (!caps(p.systemhausCapabilities) || !Array.isArray(p.customers) || !Array.isArray(p.sources)) invalid();
 if (!p.customers.every((c: any) => keys(c, 'capabilities,customerId') && uuid(c.customerId) && caps(c.capabilities) && c.capabilities.includes('inventory.read')) || !unique(p.customers, (c: any) => c.customerId.toLowerCase())) invalid();
 // Legacy grants can repeat the same source tuple; the API preserves these rows.
 if (!p.sources.every((s: any) => keys(s, 'capability,scopeId,scopeType,userGroupId,userGroupName') && uuid(s.userGroupId) && text(s.userGroupName) && text(s.capability) && (s.scopeType === 'systemhaus' ? s.scopeId === null : ['customer', 'customerGroup'].includes(s.scopeType) && uuid(s.scopeId)))) invalid();
 if (!data.user.active && (p.systemhausCapabilities.length || p.customers.length || p.sources.length)) invalid();
 return data;
}
export async function readEffectivePermissionView(api: RackClickApi, userId: string, expected = api.actorId) {
 actor(api, expected);
 const [snapshot, targets] = await Promise.all([readEffectivePermissions(api, userId, expected), readCustomerMemberTargets(guarded(api, expected))]); actor(api, expected);
 if (snapshot.revision !== targets.revision) throw new ApiError(409, 'groups_changed');
 for (const list of [targets.customers, targets.customerGroups, targets.userGroups]) {
  if (!list.every((x: any) => uuid(x.id) && text(x.name)) || !unique(list, (x: any) => x.id.toLowerCase())) invalid();
 }
 if (!targets.users.every(user) || !unique(targets.users, (x: any) => x.id.toLowerCase())) invalid();
 const selected = targets.users.find((u: any) => u.id === userId);
 if (!selected || selected.userName !== snapshot.user.userName || selected.active !== snapshot.user.active) invalid();
 for (const c of snapshot.permissions.customers) if (!targets.customers.some((x: any) => x.id === c.customerId)) invalid();
 for (const s of snapshot.permissions.sources) {
  if (!targets.userGroups.some((g: any) => g.id === s.userGroupId && g.name === s.userGroupName)) invalid();
  if (s.scopeType !== 'systemhaus' && !(s.scopeType === 'customer' ? targets.customers : targets.customerGroups).some((x: any) => x.id === s.scopeId)) invalid();
 }
 return { snapshot, targets };
}
