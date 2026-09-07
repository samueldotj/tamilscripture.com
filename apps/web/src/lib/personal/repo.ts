// Personal data access: highlights, notes, history. All calls go straight to
// PostgREST with the user's JWT; RLS limits rows to the caller (ADR-4).
import { sb } from '$lib/supabase/client';

export type HighlightColor = 'yellow' | 'green' | 'blue' | 'pink';
export const COLORS: HighlightColor[] = ['yellow', 'green', 'blue', 'pink'];

export interface Highlight {
	id: string;
	book: string;
	chapter: number;
	verse_start: number;
	verse_end: number;
	color: HighlightColor;
	updated_at: string;
}

export interface Note {
	id: string;
	book: string;
	chapter: number;
	verse_start: number;
	verse_end: number;
	body: string;
	updated_at: string;
}

export interface Visit {
	id: number;
	book: string;
	chapter: number;
	verse_start: number | null;
	verse_end: number | null;
	version: string;
	visited_at: string;
}

export async function chapterHighlights(book: string, chapter: number): Promise<Highlight[]> {
	const { data, error } = await (await sb())
		.from('highlights')
		.select('id, book, chapter, verse_start, verse_end, color, updated_at')
		.eq('book', book)
		.eq('chapter', chapter);
	if (error) throw error;
	return data as Highlight[];
}

export async function setHighlight(book: string, chapter: number, verses: number[], color: HighlightColor): Promise<void> {
	// One row per contiguous run of verses; existing rows for those verses are replaced.
	const sorted = [...new Set(verses)].sort((a, b) => a - b);
	const client = await sb();
	const { data: userRes } = await client.auth.getUser();
	const user_id = userRes.user?.id;
	if (!user_id) throw new Error('not signed in');
	await removeHighlight(book, chapter, sorted);
	const rows: (Omit<Highlight, 'id' | 'updated_at'> & { user_id: string })[] = [];
	let start = sorted[0], prev = sorted[0];
	for (const v of sorted.slice(1).concat(NaN)) {
		if (v === prev + 1) { prev = v; continue; }
		rows.push({ user_id, book, chapter, verse_start: start, verse_end: prev, color });
		start = prev = v;
	}
	const { error } = await client.from('highlights').insert(rows);
	if (error) throw error;
}

export async function removeHighlight(book: string, chapter: number, verses: number[]): Promise<void> {
	// Delete rows overlapping any of the verses; rows partly overlapping are
	// split so the untouched verses keep their colour.
	const client = await sb();
	const existing = await chapterHighlights(book, chapter);
	const set = new Set(verses);
	const touched = existing.filter((h) => {
		for (let v = h.verse_start; v <= h.verse_end; v++) if (set.has(v)) return true;
		return false;
	});
	if (!touched.length) return;
	const { data: userRes } = await client.auth.getUser();
	const user_id = userRes.user!.id;
	const keep: { user_id: string; book: string; chapter: number; verse_start: number; verse_end: number; color: HighlightColor }[] = [];
	for (const h of touched) {
		let s: number | null = null;
		for (let v = h.verse_start; v <= h.verse_end + 1; v++) {
			const inside = v <= h.verse_end && !set.has(v);
			if (inside && s === null) s = v;
			if (!inside && s !== null) { keep.push({ user_id, book, chapter, verse_start: s, verse_end: v - 1, color: h.color }); s = null; }
		}
	}
	const { error } = await client.from('highlights').delete().in('id', touched.map((h) => h.id));
	if (error) throw error;
	if (keep.length) {
		const { error: e2 } = await client.from('highlights').insert(keep);
		if (e2) throw e2;
	}
}

export async function allHighlights(): Promise<Highlight[]> {
	const { data, error } = await (await sb()).from('highlights').select('*').order('book').order('chapter').order('verse_start');
	if (error) throw error;
	return data as Highlight[];
}

export async function chapterNotes(book: string, chapter: number): Promise<Note[]> {
	const { data, error } = await (await sb()).from('notes').select('*').eq('book', book).eq('chapter', chapter).order('verse_start');
	if (error) throw error;
	return data as Note[];
}

export async function saveNote(note: { id?: string; book: string; chapter: number; verse_start: number; verse_end: number; body: string }): Promise<Note> {
	const client = await sb();
	if (!note.body.trim() && note.id) {
		await deleteNote(note.id);
		return { ...note, id: note.id, updated_at: new Date().toISOString() } as Note;
	}
	if (note.id) {
		const { data, error } = await client.from('notes').update({ body: note.body }).eq('id', note.id).select().single();
		if (error) throw error;
		return data as Note;
	}
	const { data: userRes } = await client.auth.getUser();
	const { data, error } = await client.from('notes').insert({ ...note, user_id: userRes.user!.id }).select().single();
	if (error) throw error;
	return data as Note;
}

export async function deleteNote(id: string): Promise<void> {
	const { error } = await (await sb()).from('notes').delete().eq('id', id);
	if (error) throw error;
}

export async function allNotes(query = ''): Promise<Note[]> {
	let q = (await sb()).from('notes').select('*').order('updated_at', { ascending: false });
	if (query.trim()) q = q.textSearch('body', query.trim(), { type: 'websearch', config: 'simple' });
	const { data, error } = await q;
	if (error) throw error;
	return data as Note[];
}

export async function recordVisit(book: string, chapter: number, version: string, range?: { start: number; end: number } | null): Promise<void> {
	await (await sb()).rpc('record_visit', {
		p_book: book,
		p_chapter: chapter,
		p_version: version,
		p_verse_start: range?.start ?? null,
		p_verse_end: range?.end ?? null
	});
}

export async function history(limit = 200): Promise<Visit[]> {
	const { data, error } = await (await sb()).from('history').select('*').order('visited_at', { ascending: false }).limit(limit);
	if (error) throw error;
	return data as Visit[];
}

export async function clearHistory(): Promise<void> {
	const { data: userRes } = await (await sb()).auth.getUser();
	const { error } = await (await sb()).from('history').delete().eq('user_id', userRes.user!.id);
	if (error) throw error;
}

export async function profile(): Promise<{ history_paused: boolean; share_aggregates: boolean; settings: Record<string, unknown> } | null> {
	const { data, error } = await (await sb()).from('profiles').select('history_paused, share_aggregates, settings').maybeSingle();
	if (error) throw error;
	return data;
}

export async function updateProfile(patch: Partial<{ history_paused: boolean; share_aggregates: boolean; settings: Record<string, unknown>; display_name: string }>): Promise<void> {
	const { data: userRes } = await (await sb()).auth.getUser();
	const { error } = await (await sb()).from('profiles').update(patch).eq('user_id', userRes.user!.id);
	if (error) throw error;
}

export async function exportMyData(): Promise<unknown> {
	const { data, error } = await (await sb()).rpc('export_my_data');
	if (error) throw error;
	return data;
}

export async function deleteMyAccount(): Promise<void> {
	const { error } = await (await sb()).rpc('delete_my_account');
	if (error) throw error;
	await (await sb()).auth.signOut();
}
