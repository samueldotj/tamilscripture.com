import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { SUPABASE_ANON_KEY, SUPABASE_URL } from '$lib/supabase/config';
import { findBook, manifest } from '$lib/content/manifest';

export const prerender = false;

// GET /api/heat/john.json  → { "3": { "16": 12, "17": 5 }, ... }  (chapter → verse → users)
// GET /api/heat/all.json   → { "JHN": { "3": 41 }, ... }            (book → chapter → total users)
// Served from the hourly materialised view; cached one hour at the CDN.
export const GET: RequestHandler = async ({ params, fetch, setHeaders }) => {
	const headers = { apikey: SUPABASE_ANON_KEY, authorization: `Bearer ${SUPABASE_ANON_KEY}` };
	setHeaders({ 'cache-control': 'public, s-maxage=3600, stale-while-revalidate=86400' });

	if (params.book === 'all') {
		const res = await fetch(`${SUPABASE_URL}/rest/v1/verse_highlight_counts?select=book,chapter,users`, { headers });
		if (!res.ok) return json({});
		const rows = (await res.json()) as { book: string; chapter: number; users: number }[];
		const out: Record<string, Record<string, number>> = {};
		for (const r of rows) {
			out[r.book] ??= {};
			out[r.book][r.chapter] = (out[r.book][r.chapter] ?? 0) + r.users;
		}
		return json(out);
	}

	const book = findBook(params.book);
	if (!book || !manifest.books.includes(book)) error(404, 'Unknown book');
	const res = await fetch(`${SUPABASE_URL}/rest/v1/verse_highlight_counts?select=chapter,verse,users&book=eq.${book.code}`, { headers });
	if (!res.ok) return json({});
	const rows = (await res.json()) as { chapter: number; verse: number; users: number }[];
	const out: Record<string, Record<string, number>> = {};
	for (const r of rows) {
		out[r.chapter] ??= {};
		out[r.chapter][r.verse] = r.users;
	}
	return json(out);
};
