import { confirmedUser, type UserDraft } from './admin-users.ts';
import { ApiError } from './api.ts';

export type UserCreationReceipt = Readonly<{
 actorId: string; requestId: string; userId: string; userName: string; revision: number;
}>;
type Users = { revision: number; users: { id: string }[] } | null;
type Guards = Record<string, (() => boolean) | undefined>;

// Only a validated operation result is evidence of creation. This projection
// deliberately excludes the submitted password, draft and arbitrary API fields.
export function userCreationReceipt(result: any, draft: UserDraft, actor: string): UserCreationReceipt | null {
 if (actor !== draft.actorId) throw new ApiError(409, 'actor_changed');
 if (result?.state === 'cancelled') {
  if (result.requestId !== draft.requestId || result.operation !== null) throw new ApiError(200, 'response_invalid', true);
  return null;
 }
 if (result?.state !== undefined && result.state !== 'committed') throw new ApiError(200, 'response_invalid', true);
 const saved = confirmedUser(result, draft);
 return Object.freeze({ actorId: actor, requestId: saved.requestId, userId: saved.resource.id, userName: saved.resource.userName, revision: saved.systemhausRevision });
}

// Remember the authoritative result before either local I/O can fail. A failed
// cleanup retains the pending operation; a failed reload retains the receipt but
// cannot make its old list current. The caller owns its mount/actor generation.
export async function completeUserCreation(result: any, draft: UserDraft, actor: string, steps: {
 current: () => boolean; remember: (receipt: UserCreationReceipt | null) => void;
 removeJournal: () => Promise<unknown>; clearPending: () => void; reload: () => Promise<unknown>;
}): Promise<void> {
 if (!steps.current()) return;
 steps.remember(userCreationReceipt(result, draft, actor));
 await steps.removeJournal();
 if (!steps.current()) return;
 steps.clearPending();
 await steps.reload();
}

export function visibleUserCreationReceipt(receipt: UserCreationReceipt | null, { actor, apiActor, current, authorized }: {
 actor: string; apiActor: string; current: boolean; authorized: boolean;
}): UserCreationReceipt | null {
 return current && authorized && apiActor === actor && receipt?.actorId === actor ? receipt : null;
}

export function chooseAdminUser({ id, selectedUserId, snapshot, current, guardNames, guards, onSelect }: {
 id: string; selectedUserId: string; snapshot: Users; current: boolean; guardNames: string[]; guards: Guards; onSelect: (id: string) => void;
}): boolean {
 if (!current || !snapshot || (id && !snapshot.users.some(user => user.id === id))) return false;
 // Staying with the same target does not retarget a panel or erase its draft.
 if (id === selectedUserId) return true;
 if (guardNames.some(name => !guards[name] || guards[name]!())) return false;
 onSelect(id); return true;
}

export function userOnboardingBlock({ receipt, actor, apiActor, snapshot, listState, ready, busy, pending, groupsMounted, selectedUserId, guardNames, guards }: {
 receipt: UserCreationReceipt | null; actor: string; apiActor: string; snapshot: Users; listState: string; ready: boolean; busy: boolean; pending: boolean;
 groupsMounted: boolean; selectedUserId: string; guardNames: string[]; guards: Guards;
}): 'loading' | 'pending' | 'refresh' | 'missing' | 'locked' | null {
 if (!receipt || receipt.actorId !== actor || apiActor !== actor) return 'refresh';
 if (!ready || busy || listState === 'loading' || !groupsMounted) return 'loading';
 if (pending) return 'pending';
 if (listState !== 'current' || !snapshot || snapshot.revision < receipt.revision) return 'refresh';
 if (!snapshot.users.some(user => user.id === receipt.userId)) return 'missing';
 // Continuation waits for every panel even when this user is already selected.
 // chooseAdminUser can keep a target without clearing a draft; navigation still
 // requires the independently checked continuation guard.
 if (guardNames.some(name => !guards[name] || guards[name]!())) return 'locked';
 return null;
}
