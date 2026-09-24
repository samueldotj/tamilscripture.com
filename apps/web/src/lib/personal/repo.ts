// Personal data access: highlights, notes, history. All calls go straight to
// PostgREST with the user's JWT; RLS limits rows to the caller (ADR-4).
import { sb } from '$lib/supabase/client';

export type HighlightColor = 'yellow' | 'green' | 'blue' | 'pink';
export const COLORS: HighlightColor[] = ['yellow', 'green', 'blue', 'pink'];

/** A word range (R-10.15): code-point offsets into one version's verse text,
 *  `char_start` into `verse_start` and `char_end` (exclusive) into `verse_end`. */
export interface TextRange {
	version: string;
	verse_start: number;
	char_start: number;
	verse_end: number;
	char_end: number;
	/** the marked words, for the notes and highlights pages */
	quote: string;
}

/** Offsets and quote of a row: all null for a whole-verse row. */
export interface RangeFields {
	version: string | null;
	char_start: number | null;
	char_end: number | null;
	quote: string | null;
}

export interface Highlight extends RangeFields {
	id: string;
	book: string;
	chapter: number;
	verse_start: number;
	verse_end: number;
	color: HighlightColor;
	updated_at: string;
}

export interface Note extends RangeFields {
	id: string;
	book: string;
	chapter: number;
	verse_start: number;
	verse_end: number;
	body: string;
	updated_at: string;
}

export const isPartial = (r: RangeFields): boolean => r.char_start !== null && r.char_end !== null && r.version !== null;

/** Whether two word ranges in the same version share at least one character. */
export function rangesOverlap(a: Omit<TextRange, 'quote'>, b: Omit<TextRange, 'quote'>): boolean {
	const before = (v1: number, c1: number, v2: number, c2: number) => v1 < v2 || (v1 === v2 && c1 < c2);
	return a.version === b.version && before(a.verse_start, a.char_start, b.verse_end, b.char_end) && before(b.verse_start, b.char_start, a.verse_end, a.char_end);
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
		.select('id, book, chapter, verse_start, verse_end, color, version, char_start, char_end, quote, updated_at')
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
	const rows: { user_id: string; book: string; chapter: number; verse_start: number; verse_end: number; color: HighlightColor }[] = [];
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
	// split so the untouched verses keep their colour. A word-range row that
	// touches the verses goes whole: its offsets belong to its end verses.
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
		if (isPartial(h)) continue;
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

/** Colour a word range; word-range highlights it overlaps are replaced. */
export async function setRangeHighlight(book: string, chapter: number, r: TextRange, color: HighlightColor): Promise<void> {
	const client = await sb();
	const { data: userRes } = await client.auth.getUser();
	const user_id = userRes.user?.id;
	if (!user_id) throw new Error('not signed in');
	await removeRangeHighlight(book, chapter, r);
	const { error } = await client.from('highlights').insert({ user_id, book, chapter, ...r, color });
	if (error) throw error;
}

/** Remove the word-range highlights that overlap a word range. */
export async function removeRangeHighlight(book: string, chapter: number, r: Omit<TextRange, 'quote'>): Promise<void> {
	const existing = await chapterHighlights(book, chapter);
	const ids = existing.filter((h) => isPartial(h) && rangesOverlap(h as unknown as TextRange, r)).map((h) => h.id);
	if (!ids.length) return;
	const { error } = await (await sb()).from('highlights').delete().in('id', ids);
	if (error) throw error;
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

export async function saveNote(note: { id?: string; book: string; chapter: number; verse_start: number; verse_end: number; body: string; range?: TextRange | null }): Promise<Note> {
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
	const { range, ...row } = note;
	const { data, error } = await client.from('notes').insert({ ...row, ...(range ?? {}), user_id: userRes.user!.id }).select().single();
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
