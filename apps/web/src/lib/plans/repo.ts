// Reading plans: community plans through PostgREST (published ones for
// everyone, drafts and writes for moderators, all under RLS), and a reader's
// progress — in this browser while signed out, in plan_progress once signed in.
import { browser } from '$app/environment';
import { sb } from '$lib/supabase/client';
import { SUPABASE_ANON_KEY, SUPABASE_URL } from '$lib/supabase/config';
import type { PlanRow, TrackSpec } from './schedule';

const COLS = 'id, title_ta, title_en, blurb, days, tracks, status';

/** Published community plans, oldest first. A plain anon request, so a reader
 *  who is not signed in never loads supabase-js for them. */
export async function publishedPlans(fetchFn: typeof fetch = fetch): Promise<PlanRow[]> {
	const q = `select=${COLS.replace(/ /g, '')}&status=eq.published&order=published_at.asc`;
	const res = await fetchFn(`${SUPABASE_URL}/rest/v1/reading_plans?${q}`, {
		headers: { apikey: SUPABASE_ANON_KEY, authorization: `Bearer ${SUPABASE_ANON_KEY}` }
	});
	if (!res.ok) throw new Error(`reading plans failed: ${res.status}`);
	return (await res.json()) as PlanRow[];
}

/** Every community plan, drafts included (moderators; others get the published ones). */
export async function allPlans(): Promise<PlanRow[]> {
	const { data, error } = await (await sb()).from('reading_plans').select(COLS).order('created_at');
	if (error) throw error;
	return data as PlanRow[];
}

export interface PlanDraft {
	title_ta: string;
	title_en: string;
	blurb: string;
	days: number;
	tracks: TrackSpec[];
}

export async function savePlan(id: string | null, form: PlanDraft, status: PlanRow['status']): Promise<PlanRow> {
	const client = await sb();
	const row = { ...form, status, ...(status === 'published' ? { published_at: new Date().toISOString() } : {}) };
	if (id) {
		const { data, error } = await client.from('reading_plans').update(row).eq('id', id).select(COLS).single();
		if (error) throw error;
		return data as PlanRow;
	}
	const { data: userRes } = await client.auth.getUser();
	const created_by = userRes.user?.id;
	if (!created_by) throw new Error('not signed in');
	const { data, error } = await client.from('reading_plans').insert({ ...row, created_by }).select(COLS).single();
	if (error) throw error;
	return data as PlanRow;
}

export async function deletePlan(id: string): Promise<void> {
	const { error } = await (await sb()).from('reading_plans').delete().eq('id', id);
	if (error) throw error;
}

// ---- progress ---------------------------------------------------------------------

/** Progress as stored: the start date and the "day-track" keys read. */
export interface ProgressRow {
	start: string;
	done: string[];
}
export type ProgressMap = Record<string, ProgressRow>;

const KEY = 'readingPlans';

function loadLocal(): ProgressMap {
	if (!browser) return {};
	try {
		const r = JSON.parse(localStorage.getItem(KEY) || '{}');
		return r && typeof r === 'object' ? r : {};
	} catch {
		return {};
	}
}
function saveLocal(m: ProgressMap) {
	try {
		if (Object.keys(m).length) localStorage.setItem(KEY, JSON.stringify(m));
		else localStorage.removeItem(KEY);
	} catch { /* storage full or blocked */ }
}

async function userId(): Promise<string> {
	const { data } = await (await sb()).auth.getUser();
	if (!data.user) throw new Error('not signed in');
	return data.user.id;
}

/** The reader's plans. Signed in, progress kept in this browser from before is
 *  moved to the account the first time (when the account has none yet). */
export async function loadProgress(signedIn: boolean): Promise<ProgressMap> {
	const local = loadLocal();
	if (!signedIn) return local;
	const client = await sb();
	const { data, error } = await client.from('plan_progress').select('plan, start_date, done');
	if (error) throw error;
	const out: ProgressMap = {};
	for (const r of data as { plan: string; start_date: string; done: string[] }[]) out[r.plan] = { start: r.start_date, done: r.done };
	if (!data.length && Object.keys(local).length) {
		const user_id = await userId();
		const rows = Object.entries(local).map(([plan, p]) => ({ user_id, plan, start_date: p.start, done: p.done }));
		const { error: e2 } = await client.from('plan_progress').upsert(rows);
		if (e2) throw e2;
		saveLocal({});
		return local;
	}
	return out;
}

// Writes for one plan run in order, so a quick tick-untick lands as the last.
const queue = new Map<string, Promise<unknown>>();
function inOrder(plan: string, job: () => Promise<void>): Promise<void> {
	const next = (queue.get(plan) ?? Promise.resolve()).catch(() => {}).then(job);
	queue.set(plan, next);
	return next;
}

export function saveProgress(signedIn: boolean, plan: string, p: ProgressRow | null): Promise<void> {
	if (!signedIn) {
		const m = loadLocal();
		if (p) m[plan] = p;
		else delete m[plan];
		saveLocal(m);
		return Promise.resolve();
	}
	return inOrder(plan, async () => {
		const client = await sb();
		if (!p) {
			const { error } = await client.from('plan_progress').delete().eq('plan', plan);
			if (error) throw error;
			return;
		}
		const { error } = await client.from('plan_progress').upsert({ user_id: await userId(), plan, start_date: p.start, done: p.done });
		if (error) throw error;
	});
}
