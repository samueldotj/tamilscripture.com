// Community review: suggestions, the moderation queue and roles
// (feature_dictionary.md §6). Every call goes through PostgREST with the user's
// JWT; the security-definer functions in the migration enforce the rules.
import { sb } from '$lib/supabase/client';

export type Role = 'reader' | 'reviewer' | 'moderator';
export type SuggestionStatus = 'open' | 'accepted' | 'rejected';

export interface Suggestion {
	id: string;
	target: string;
	current_text: string;
	suggested_text: string;
	reason: string | null;
	status: SuggestionStatus;
	created_at: string;
	decided_at: string | null;
	decision_note: string | null;
	final_text: string | null;
}

export interface QueueItem extends Suggestion {
	author: string;
	decided_by_name: string | null;
	/** What this contributor has had accepted and rejected before. */
	author_accepted: number;
	author_rejected: number;
}

export interface ModCounts {
	open: number;
	accepted: number;
	rejected: number;
}

export interface ModStats {
	accepted_this_month: number;
	/** Over the last hundred decisions, so one stale row does not stand for all. */
	avg_wait_hours: number | null;
	contributors: number;
}

export interface StaffMember {
	user_id: string;
	display_name: string | null;
	email: string;
	role: Role;
}

export interface ExportStatus {
	accepted: number;
	pending_export: number;
	last_export: string | null;
	last_publish: string | null;
}

/** `name:IRVTAM:Damascus` */
export function nameTarget(version: string, nameEn: string): string {
	return `name:${version}:${nameEn}`;
}
/** `article:eastons/damascus#p1-ee1db5fc` */
export function articleTarget(paragraphId: string): string {
	return `article:${paragraphId}`;
}

/** Why a correction is being suggested (design 8A). The id is what goes into
 *  `reason`, so the queue can show it as a tag; a free note may follow after
 *  ": ". Reasons written before this existed are plain text and still read. */
export const REASONS = [
	{ id: 'wrong-word', en: 'Wrong word', ta: 'பிழையான சொல்' },
	{ id: 'grammar', en: 'Grammar', ta: 'இலக்கணம்' },
	{ id: 'missing', en: 'Missing text', ta: 'விடுபட்டது' },
	{ id: 'phrasing', en: 'Sentence structure', ta: 'வாக்கிய அமைப்பு' }
] as const;

export type ReasonId = (typeof REASONS)[number]['id'];

/** Split a stored reason into its tag and the note after it. */
export function parseReason(reason: string | null): { tag: (typeof REASONS)[number] | null; note: string } {
	if (!reason) return { tag: null, note: '' };
	const [head, ...rest] = reason.split(':');
	const tag = REASONS.find((r) => r.id === head.trim()) ?? null;
	return tag ? { tag, note: rest.join(':').trim() } : { tag: null, note: reason };
}

/** Put a tag and an optional note back together for storage. */
export function formatReason(tag: ReasonId | '', note: string): string | undefined {
	const n = note.trim();
	if (!tag) return n || undefined;
	return n ? `${tag}: ${n}` : tag;
}

export type ParsedTarget =
	| { kind: 'name'; version: string; name_en: string; href: null }
	| { kind: 'article'; article: string; paragraph: string; href: string }
	| { kind: 'unknown'; href: null };

export function parseTarget(t: string): ParsedTarget {
	const n = /^name:([A-Z0-9]+):(.+)$/.exec(t);
	if (n) return { kind: 'name', version: n[1], name_en: n[2], href: null };
	const a = /^article:([a-z0-9]+\/[a-z0-9-]+)#(p[0-9]+-[0-9a-f]{8})$/.exec(t);
	if (a) return { kind: 'article', article: a[1], paragraph: a[2], href: `/dictionary/${a[1]}#${a[2]}` };
	return { kind: 'unknown', href: null };
}

async function rpc<T>(fn: string, args: Record<string, unknown> = {}): Promise<T> {
	const { data, error } = await (await sb()).rpc(fn, args);
	if (error) throw new Error(friendly(error.message));
	return data as T;
}

/** Postgres messages are already written for people; strip the driver prefix. */
function friendly(msg: string): string {
	return msg.replace(/^.*?: /, '').trim() || msg;
}

export async function myRole(): Promise<Role> {
	return rpc<Role>('my_role');
}

export async function suggest(target: string, current: string, suggested: string, reason?: string): Promise<string> {
	return rpc<string>('suggest_correction', { p_target: target, p_current: current, p_suggested: suggested, p_reason: reason ?? null });
}

export async function myContributions(): Promise<Suggestion[]> {
	const { data, error } = await (await sb())
		.from('entity_suggestions')
		.select('id, target, current_text, suggested_text, reason, status, created_at, decided_at, decision_note, final_text')
		.order('created_at', { ascending: false })
		.limit(200);
	if (error) throw new Error(friendly(error.message));
	return data as Suggestion[];
}

export async function modCounts(): Promise<ModCounts> {
	const rows = await rpc<ModCounts[]>('mod_counts');
	return rows?.[0] ?? { open: 0, accepted: 0, rejected: 0 };
}

export async function modStats(): Promise<ModStats> {
	const rows = await rpc<ModStats[]>('mod_stats');
	return rows?.[0] ?? { accepted_this_month: 0, avg_wait_hours: null, contributors: 0 };
}

export async function queue(status: SuggestionStatus | 'all' = 'open', limit = 200): Promise<QueueItem[]> {
	return rpc<QueueItem[]>('mod_queue', { p_status: status, p_limit: limit });
}

export async function accept(id: string, finalText: string): Promise<void> {
	await rpc('accept_suggestion', { p_id: id, p_final: finalText });
}

export async function reject(id: string, note: string): Promise<void> {
	await rpc('reject_suggestion', { p_id: id, p_note: note || null });
}

export async function correctDirectly(target: string, current: string, text: string): Promise<string> {
	return rpc<string>('correct_directly', { p_target: target, p_current: current, p_text: text });
}

export async function exportStatus(): Promise<ExportStatus | null> {
	const rows = await rpc<ExportStatus[]>('export_status');
	return rows?.[0] ?? null;
}

export async function listStaff(): Promise<StaffMember[]> {
	return rpc<StaffMember[]>('list_staff');
}

export async function setRole(userId: string, role: 'reader' | 'reviewer'): Promise<void> {
	await rpc('set_role', { p_user: userId, p_role: role });
}

export async function setRoleByEmail(email: string, role: 'reader' | 'reviewer'): Promise<string> {
	return rpc<string>('set_role_by_email', { p_email: email, p_role: role });
}

/** Ask the site to run the export workflow now (moderators). */
export async function publishNow(): Promise<{ ok: boolean; actions?: string }> {
	const { data } = await (await sb()).auth.getSession();
	const token = data.session?.access_token;
	if (!token) throw new Error('Sign in first');
	const res = await fetch('/api/mod/publish', { method: 'POST', headers: { authorization: `Bearer ${token}` } });
	if (!res.ok) {
		let msg = res.statusText;
		try { msg = ((await res.json()) as { message?: string }).message ?? msg; } catch { /* keep statusText */ }
		throw new Error(msg);
	}
	return res.json();
}
