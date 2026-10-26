export type Resource = { id: string; name: string; revision: number; houseId?: string };
export type Session = {
  user: { id: string; houseId: string; userName: string }; csrf: string;
  permissions: { systemhausCapabilities: string[]; customers: { customerId: string; capabilities: string[] }[] };
};
export type Mutation = Readonly<{ path: string; method: 'POST' | 'PUT'; body: string; etag: string; requestId: string; actorId: string }>;
export class ApiError extends Error {
  status: number; code: string; uncertain: boolean;
  constructor(status: number, code: string, uncertain = false) {
    super(code); this.status = status; this.code = code; this.uncertain = uncertain;
  }
}
const resource = (value: any): value is Resource => typeof value?.id === 'string' && typeof value?.name === 'string' && Number.isSafeInteger(value?.revision) && value.revision > 0;
export class RackClickApi {
  csrf = '';
  actorId = '';
  fetcher: typeof fetch;
  constructor(fetcher: typeof fetch = fetch) { this.fetcher = fetcher; }
  async request(path: string, init: RequestInit = {}) {
    let response: Response;
    try { response = await this.fetcher.call(globalThis, '/api/v1' + path, { ...init, credentials: 'same-origin', cache: 'no-store', redirect: 'error' }); }
    catch { throw new ApiError(0, 'network_unconfirmed', !!init.method && init.method !== 'GET'); }
    if (response.status === 204) return { data: null, etag: null };
    let data: any;
    try { data = await response.json(); }
    catch { throw new ApiError(response.status, 'response_invalid', response.ok || response.status >= 500); }
    if (!response.ok) throw new ApiError(response.status, typeof data?.error === 'string' ? data.error : 'request_failed', response.status >= 500);
    return { data, etag: response.headers.get('ETag') };
  }
  async login(username: string, password: string) {
    const { data } = await this.request('/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) });
    if (typeof data?.csrf !== 'string') throw new ApiError(200, 'response_invalid');
    this.csrf = data.csrf;
    return this.me();
  }
  async me(): Promise<Session> {
    const { data } = await this.request('/me');
    if (!data?.user?.id || typeof data.csrf !== 'string' || !Array.isArray(data.permissions?.systemhausCapabilities) || !Array.isArray(data.permissions?.customers)) throw new ApiError(200, 'response_invalid');
    this.csrf = data.csrf;
    this.actorId = data.user.id;
    return data;
  }
  async logout() { await this.request('/auth/logout', { method: 'POST', headers: { 'X-RackClick-CSRF': this.csrf } }); this.csrf = ''; this.actorId = ''; }
  async house(): Promise<Resource> {
    const { data, etag } = await this.request('/systemhaus');
    if (!resource(data) || etag !== '"' + data.revision + '"') throw new ApiError(200, 'response_invalid');
    return data;
  }
  async customers(): Promise<Resource[]> {
    const { data } = await this.request('/customers');
    if (!Array.isArray(data) || !data.every(resource)) throw new ApiError(200, 'response_invalid');
    return data;
  }
  prepare(kind: 'house' | 'create' | 'customer', name: string, revision: number, id?: string, actorId = this.actorId): Mutation {
    if (!Number.isSafeInteger(revision) || revision < 1 || (kind === 'customer' && !id)) throw new ApiError(422, 'revision_invalid');
    return Object.freeze({ path: kind === 'house' ? '/systemhaus' : kind === 'create' ? '/customers' : '/customers/' + encodeURIComponent(id!), method: kind === 'create' ? 'POST' : 'PUT', body: JSON.stringify({ name }), etag: '"' + revision + '"', requestId: crypto.randomUUID(), actorId });
  }
  async sendMutation(operation: Mutation) {
    if (!this.csrf) throw new ApiError(401, 'authentication_required');
    if (!this.actorId || this.actorId !== operation.actorId) throw new ApiError(409, 'actor_changed');
    const { data } = await this.request(operation.path, { method: operation.method, headers: { 'Content-Type': 'application/json', 'X-RackClick-CSRF': this.csrf, 'X-RackClick-Actor': operation.actorId, 'If-Match': operation.etag, 'Idempotency-Key': operation.requestId }, body: operation.body });
    return data;
  }
  async execute(operation: Mutation): Promise<{ resource: Resource; systemhausRevision: number; requestId: string }> {
    const data = await this.sendMutation(operation);
    if (!resource(data?.resource) || data.requestId !== operation.requestId || !Number.isSafeInteger(data.systemhausRevision) || data.systemhausRevision < 1) throw new ApiError(200, 'response_invalid', true);
    return data;
  }
}
export function allows(session: Session | null, capability: string, customerId?: string): boolean {
  if (!session) return false;
  return customerId ? !!session.permissions.customers.find(c => c.customerId === customerId)?.capabilities.includes(capability) : session.permissions.systemhausCapabilities.includes(capability);
}
// A later authorization/validation failure cannot prove an earlier lost response rolled back.
export function mutationRemainsUnconfirmed(wasUnconfirmed: boolean, error: { uncertain?: boolean }): boolean {
  return wasUnconfirmed || error.uncertain === true;
}
