// A late read must not replace a snapshot already confirmed at a newer revision.
export class RevisionGate {
 sequence = 0;
 revision = 0;
 begin() { return ++this.sequence; }
 confirm(revision: number) { this.revision = Math.max(this.revision, revision); }
 accept(sequence: number, revision: number) {
  if (sequence !== this.sequence || revision < this.revision) return false;
  this.confirm(revision); return true;
 }
}
