export type Resource = { id: string; name: string; revision: number; houseId?: string };
export type Session = {
  user: { id: string; houseId: string; userName: string }; csrf: string;
  permissions: { systemhausCapabilities: string[]; customers: { customerId: string; capabilities: string[] }[] };
};
export type Mutation = Readonly<{ path: string; method: 'POST' | 'PUT'; body: string; etag: string; requestId: string; actorId: string }>;
export type MfaChallenge = Readonly<{ purpose: 'enroll' | 'verify'; csrf: string; generation: number }>;
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
  onMfaRequired: ((challenge: MfaChallenge) => Promise<Session>) | null = null;
  private authenticationGeneration = 0;
  private authenticationPending = false;
  private challenge: MfaChallenge | null = null;
  private enrollmentStarted = false;
  fetcher: typeof fetch;
  constructor(fetcher: typeof fetch = fetch) { this.fetcher = fetcher; }
  async request(path: string, init: RequestInit = {}) {
    let response: Response;
    try { response = await this.fetcher.call(globalThis, '/api/v1' + path, { ...init, credentials: 'same-origin', cache: 'no-store', redirect: 'error' }); }
    catch { throw new ApiError(0, 'network_unconfirmed', !!init.method && init.method !== 'GET'); }
    if (response.status === 204) return { data: null, etag: null, status: response.status };
    let data: any;
    try { data = await response.json(); }
    catch { throw new ApiError(response.status, 'response_invalid', response.ok || response.status >= 500); }
    if (!response.ok) throw new ApiError(response.status, typeof data?.error === 'string' ? data.error : 'request_failed', response.status >= 500);
    return { data, etag: response.headers.get('ETag'), status: response.status };
  }
  cancelAuthentication() {
    this.authenticationGeneration++;
    this.authenticationPending = false; this.challenge = null; this.enrollmentStarted = false;
    this.csrf = ''; this.actorId = '';
  }
  private requireGeneration(generation: number) {
    if (generation !== this.authenticationGeneration) throw new ApiError(409, 'authentication_changed');
  }
  private validateSession(data: any): Session {
    if (!data?.user?.id || typeof data.csrf !== 'string' || !data.csrf || !Array.isArray(data.permissions?.systemhausCapabilities) || !Array.isArray(data.permissions?.customers)) throw new ApiError(200, 'response_invalid');
    return data;
  }
  private async completeAuthentication(csrf: unknown, generation: number): Promise<Session> {
    this.requireGeneration(generation);
    if (typeof csrf !== 'string' || !csrf) throw new ApiError(200, 'response_invalid');
    // The server cookie is HttpOnly. Only an authenticated /me response grants local authority.
    const { data } = await this.request('/me');
    this.requireGeneration(generation);
    const session = this.validateSession(data);
    this.challenge = null; this.authenticationPending = false; this.enrollmentStarted = false;
    this.csrf = session.csrf; this.actorId = session.user.id;
    return session;
  }
  async login(username: string, password: string): Promise<Session> {
    const generation = ++this.authenticationGeneration;
    this.authenticationPending = true; this.challenge = null; this.enrollmentStarted = false;
    this.csrf = ''; this.actorId = '';
    try {
      const { data, status } = await this.request('/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) });
      this.requireGeneration(generation);
      if (status === 202) {
        if (data?.mfaRequired !== true || !['enroll', 'verify'].includes(data?.purpose) || typeof data.csrf !== 'string' || !data.csrf) throw new ApiError(202, 'response_invalid');
        const challenge = Object.freeze({ purpose: data.purpose, csrf: data.csrf, generation }) as MfaChallenge;
        this.challenge = challenge;
        if (!this.onMfaRequired) throw new ApiError(202, 'mfa_required');
        const identity = await this.onMfaRequired(challenge);
        this.requireGeneration(generation);
        if (this.authenticationPending || !this.actorId || identity?.user?.id !== this.actorId) throw new ApiError(200, 'response_invalid');
        return identity;
      }
      if (status !== 200 || data?.mfaRequired === true) throw new ApiError(status, 'response_invalid');
      return await this.completeAuthentication(data?.csrf, generation);
    } catch (error) {
      if (generation === this.authenticationGeneration) {
        this.authenticationPending = false; this.challenge = null; this.enrollmentStarted = false;
        this.csrf = ''; this.actorId = '';
      }
      throw error;
    }
  }
  private requireChallenge(challenge: MfaChallenge, purpose: 'enroll' | 'verify') {
    this.requireGeneration(challenge.generation);
    if (!this.authenticationPending || this.challenge !== challenge || challenge.generation !== this.authenticationGeneration || challenge.purpose !== purpose) throw new ApiError(401, 'mfa_challenge_invalid');
  }
  async startMfaEnrollment(challenge: MfaChallenge): Promise<{ secret: string; otpauth: string }> {
    this.requireChallenge(challenge, 'enroll');
    if (this.enrollmentStarted) throw new ApiError(409, 'mfa_enrollment_already_started');
    this.enrollmentStarted = true;
    const { data, status } = await this.request('/auth/mfa/enroll/start', { method: 'POST', headers: { 'X-RackClick-CSRF': challenge.csrf } });
    this.requireChallenge(challenge, 'enroll');
    if (status !== 200 || typeof data?.secret !== 'string' || !/^[A-Z2-7]{16,128}$/.test(data.secret) || typeof data.otpauth !== 'string' || data.otpauth.length > 4096) throw new ApiError(status, 'response_invalid', true);
    let uri: URL;
    try { uri = new URL(data.otpauth); } catch { throw new ApiError(status, 'response_invalid', true); }
    if (uri.protocol !== 'otpauth:' || uri.hostname !== 'totp' || uri.searchParams.get('secret') !== data.secret) throw new ApiError(status, 'response_invalid', true);
    return { secret: data.secret, otpauth: data.otpauth };
  }
  private async finishMfa(challenge: MfaChallenge, code: string, purpose: 'enroll' | 'verify'): Promise<Session> {
    this.requireChallenge(challenge, purpose);
    if (typeof code !== 'string' || !/^[0-9]{6}$/.test(code)) throw new ApiError(422, 'mfa_code_invalid');
    const path = purpose === 'enroll' ? '/auth/mfa/enroll/confirm' : '/auth/mfa/verify';
    const { data, status } = await this.request(path, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-RackClick-CSRF': challenge.csrf }, body: JSON.stringify({ code }) });
    this.requireChallenge(challenge, purpose);
    if (status !== 200) throw new ApiError(status, 'response_invalid', true);
    return this.completeAuthentication(data?.csrf, challenge.generation);
  }
  async confirmMfaEnrollment(challenge: MfaChallenge, code: string) { return this.finishMfa(challenge, code, 'enroll'); }
  async verifyMfa(challenge: MfaChallenge, code: string) { return this.finishMfa(challenge, code, 'verify'); }
  async recoverMfa(challenge: MfaChallenge, code: string): Promise<MfaChallenge> {
    this.requireChallenge(challenge, 'verify');
    if (typeof code !== 'string' || !/^(?:[a-f0-9]{32}|(?:[a-f0-9]{4}-){7}[a-f0-9]{4})$/i.test(code.trim())) throw new ApiError(422, 'mfa_recovery_code_invalid');
    const { data, status } = await this.request('/auth/mfa/recover', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-RackClick-CSRF': challenge.csrf }, body: JSON.stringify({ code: code.trim() }) });
    this.requireChallenge(challenge, 'verify');
    if (status !== 202 || data?.mfaRequired !== true || data?.purpose !== 'enroll' || typeof data.csrf !== 'string' || !data.csrf || data.csrf === challenge.csrf) throw new ApiError(status, 'response_invalid', true);
    const next = Object.freeze({ purpose: 'enroll', csrf: data.csrf, generation: challenge.generation }) as MfaChallenge;
    this.challenge = next; this.enrollmentStarted = false;
    // Recovery is only an enrollment challenge. It must not install local authority or call /me.
    return next;
  }
  async me(): Promise<Session> {
    if (this.authenticationPending) throw new ApiError(401, 'authentication_required');
    const generation = this.authenticationGeneration;
    const { data } = await this.request('/me');
    this.requireGeneration(generation);
    if (this.authenticationPending) throw new ApiError(401, 'authentication_required');
    const identity = this.validateSession(data);
    this.csrf = identity.csrf;
    this.actorId = identity.user.id;
    return identity;
  }
  async logout() { await this.request('/auth/logout', { method: 'POST', headers: { 'X-RackClick-CSRF': this.csrf } }); this.cancelAuthentication(); }
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
