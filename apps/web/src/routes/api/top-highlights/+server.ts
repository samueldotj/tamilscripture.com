import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { SUPABASE_ANON_KEY, SUPABASE_URL } from '$lib/supabase/config';
import { findBook } from '$lib/content/manifest';

export const prerender = false;

export interface TopHighlight {
	book: string;
	chapter: number;
	verse: number;
	users: number;
}

// GET /api/top-highlights: the ten verses most readers highlighted in the last
// 30 days (R-2.5), from verse_highlight_month (three readers or more, refreshed
// hourly). Ties go to canonical order.
export const GET: RequestHandler = async ({ fetch, setHeaders }) => {
	const params = new URLSearchParams({ select: 'book,chapter,verse,users', order: 'users.desc', limit: '40' });
	const res = await fetch(`${SUPABASE_URL}/rest/v1/verse_highlight_month?${params}`, {
		headers: { apikey: SUPABASE_ANON_KEY, authorization: `Bearer ${SUPABASE_ANON_KEY}` }
	});
	if (!res.ok) {
		console.error('top highlights failed', res.status, await res.text());
		error(502, 'Unavailable right now');
	}
	const rows = ((await res.json()) as TopHighlight[]).filter((r) => findBook(r.book));
	const order = (r: TopHighlight) => findBook(r.book)!.order;
	rows.sort((a, b) => b.users - a.users || order(a) - order(b) || a.chapter - b.chapter || a.verse - b.verse);
	setHeaders({ 'cache-control': 'public, s-maxage=3600, stale-while-revalidate=86400' });
	return json(rows.slice(0, 10));
};
