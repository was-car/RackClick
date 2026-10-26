import { confirmedGroup, type GroupDraft } from './admin-groups.ts';
import { ApiError } from './api.ts';

export type GroupCreationReceipt = Readonly<{
 actorId: string; requestId: string; groupId: string; name: string; kind: 'userGroup' | 'customerGroup'; revision: number;
}>;
type Snapshot = { revision: number; userGroups: { id: string }[]; customerGroups: { id: string }[] } | null;

// Project only the authoritative operation result. The submitted draft and
// arbitrary response fields are deliberately excluded from this memory receipt.
export function groupCreationReceipt(result: any, draft: GroupDraft, actor: string): GroupCreationReceipt | null {
 if (actor !== draft.actorId) throw new ApiError(409, 'actor_changed');
 if (result?.state === 'cancelled') {
  if (result.requestId !== draft.requestId || result.operation !== null) throw new ApiError(200, 'response_invalid', true);
  return null;
 }
 if (result?.state !== undefined && result.state !== 'committed') throw new ApiError(200, 'response_invalid', true);
 const saved=confirmedGroup(result,draft);
 return Object.freeze({actorId:actor,requestId:saved.requestId,groupId:saved.resource.id,name:saved.resource.name,kind:saved.resource.kind,revision:saved.systemhausRevision});
}

// A local journal failure must not erase a commit already acknowledged by the
// server. Keep its pending request until cleanup succeeds, and require a fresh
// snapshot before offering the read-only continuation.
export async function completeGroupCreation(result: any, draft: GroupDraft, actor: string, steps: {
 current: () => boolean; remember: (receipt: GroupCreationReceipt | null) => void;
 removeJournal: () => Promise<unknown>; clearPending: () => void; reload: () => unknown;
}): Promise<void> {
 if (!steps.current()) return;
 // The status adapter maps notRecorded to null. It establishes no new evidence
 // and cannot revoke an earlier validated commit retained after local failure.
 if (result === null) return;
 steps.remember(groupCreationReceipt(result,draft,actor));
 await steps.removeJournal();
 if (!steps.current()) return;
 steps.clearPending();
 await steps.reload();
}

export function groupReceiptBlock({ receipt, actor, apiActor, snapshot, ready, busy, pending, current }: {
 receipt: GroupCreationReceipt | null; actor: string; apiActor: string; snapshot: Snapshot;
 ready: boolean; busy: boolean; pending: boolean; current: boolean;
}): 'loading' | 'pending' | 'refresh' | 'missing' | null {
 if (!receipt || receipt.actorId !== actor || apiActor !== actor || !current) return 'refresh';
 if (pending) return 'pending';
 if (!ready || busy) return 'loading';
 if (!snapshot || snapshot.revision < receipt.revision) return 'refresh';
 const groups=receipt.kind==='userGroup'?snapshot.userGroups:snapshot.customerGroups;
 return groups.some(group=>group.id===receipt.groupId)?null:'missing';
}
