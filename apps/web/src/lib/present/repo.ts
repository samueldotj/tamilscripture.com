// Presentations: the owner's rows through PostgREST under RLS (ADR-4), the
// audience's copy through presentation_by_slug(), which needs no session and
// no supabase-js, so a shared link loads without either.
import { sb } from '$lib/supabase/client';
import { SUPABASE_ANON_KEY, SUPABASE_URL } from '$lib/supabase/config';
import { newId, newSlide, type Presentation, type Slide, type Visibility } from './types';

const COLS = 'id, slug, title, subtitle, version, visibility, slides, votes_up, votes_down, created_at, updated_at';

export async function myPresentations(): Promise<Presentation[]> {
	const { data, error } = await (await sb()).from('presentations').select(COLS).order('updated_at', { ascending: false });
	if (error) throw error;
	return data as Presentation[];
}

export async function myPresentation(slug: string): Promise<Presentation | null> {
	const { data, error } = await (await sb()).from('presentations').select(COLS).eq('slug', slug).maybeSingle();
	if (error) throw error;
	return data as Presentation | null;
}

export async function createPresentation(version: string, title = ''): Promise<Presentation> {
	const client = await sb();
	const { data: userRes } = await client.auth.getUser();
	const user_id = userRes.user?.id;
	if (!user_id) throw new Error('not signed in');
	const first: Slide = { ...newSlide(), title };
	const { data, error } = await client
		.from('presentations')
		.insert({ user_id, slug: newId(10), title, version: version.toUpperCase(), slides: [first] })
		.select(COLS)
		.single();
	if (error) throw error;
	return data as Presentation;
}

export type PresentationPatch = Partial<Pick<Presentation, 'title' | 'subtitle' | 'version' | 'visibility' | 'slides'>>;

export async function savePresentation(id: string, patch: PresentationPatch): Promise<Presentation> {
	const { data, error } = await (await sb()).from('presentations').update(patch).eq('id', id).select(COLS).single();
	if (error) throw error;
	return data as Presentation;
}

export async function setVisibility(id: string, visibility: Visibility): Promise<void> {
	await savePresentation(id, { visibility });
}

export async function deletePresentation(id: string): Promise<void> {
	const { error } = await (await sb()).from('presentations').delete().eq('id', id);
	if (error) throw error;
}

/** A presentation shared by link, or null when private or missing. Works on
 *  the server (for the page title in link previews) and in the browser. */
export async function sharedPresentation(fetchFn: typeof fetch, slug: string): Promise<Presentation | null> {
	if (!/^[a-z0-9]{8,16}$/.test(slug)) return null;
	const res = await fetchFn(`${SUPABASE_URL}/rest/v1/rpc/presentation_by_slug`, {
		method: 'POST',
		headers: { apikey: SUPABASE_ANON_KEY, authorization: `Bearer ${SUPABASE_ANON_KEY}`, 'content-type': 'application/json' },
		body: JSON.stringify({ p_slug: slug })
	});
	if (!res.ok) throw new Error(`presentation lookup failed: ${res.status}`);
	const doc = (await res.json()) as Presentation | null;
	return doc && Array.isArray(doc.slides) ? doc : null;
}

/** Thumbs up or down from the closing slide. `previous` is this browser's earlier
 *  vote, if any, so changing one's mind moves the vote instead of doubling it.
 *  Returns the new counts, or null when the presentation is not shared. */
export async function votePresentation(fetchFn: typeof fetch, slug: string, up: boolean, previous: boolean | null): Promise<{ up: number; down: number } | null> {
	const res = await fetchFn(`${SUPABASE_URL}/rest/v1/rpc/presentation_vote`, {
		method: 'POST',
		headers: { apikey: SUPABASE_ANON_KEY, authorization: `Bearer ${SUPABASE_ANON_KEY}`, 'content-type': 'application/json' },
		body: JSON.stringify({ p_slug: slug, p_up: up, p_previous: previous })
	});
	if (!res.ok) throw new Error(`vote failed: ${res.status}`);
	return (await res.json()) as { up: number; down: number } | null;
}

export function presentUrl(slug: string, slide?: number): string {
	return `/present/${slug}${slide && slide > 1 ? `#${slide}` : ''}`;
}

// ---- editor ↔ presenter, in the same browser ----------------------------------
// The editor broadcasts every change so a presenter tab opened from it shows
// edits at once; the presenter reports the slide it is on so the editor can
// follow along. Other browsers see changes on their next load.
export type PresentMessage = { type: 'doc'; presentation: Presentation } | { type: 'slide'; index: number };

export function presentChannel(slug: string): BroadcastChannel | null {
	if (typeof BroadcastChannel === 'undefined') return null;
	return new BroadcastChannel(`ts-present-${slug}`);
}
