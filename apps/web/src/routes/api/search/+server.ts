import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { SUPABASE_ANON_KEY, SUPABASE_URL } from '$lib/supabase/config';
import { manifest } from '$lib/content/manifest';

export const prerender = false;

const MAX_Q = 120;
const PAGE = 50;

// GET /api/search?q=...&v=IRVTAM,TCV&offset=0
// Quoted queries ("...", “...”) are exact phrase matches; otherwise full text
// with a trigram fallback, all inside the Postgres function search_verses.
export const GET: RequestHandler = async ({ url, fetch, setHeaders }) => {
	const raw = (url.searchParams.get('q') ?? '').trim().slice(0, MAX_Q);
	if (raw.length < 2) error(400, 'Query too short');
	const exact = /^["“”].*["“”]$/.test(raw);
	const q = exact ? raw.slice(1, -1).trim() : raw;
	if (!q) error(400, 'Empty query');

	const known = new Set(manifest.versions.map((v) => v.code));
	const versions = (url.searchParams.get('v') ?? 'IRVTAM')
		.split(',')
		.map((v) => v.trim().toUpperCase())
		.filter((v) => known.has(v));
	if (!versions.length) error(400, 'Unknown version');
	const offset = Math.max(0, Number(url.searchParams.get('offset') ?? 0) || 0);

	const started = Date.now();
	const res = await fetch(`${SUPABASE_URL}/rest/v1/rpc/search_verses`, {
		method: 'POST',
		headers: {
			apikey: SUPABASE_ANON_KEY,
			authorization: `Bearer ${SUPABASE_ANON_KEY}`,
			'content-type': 'application/json'
		},
		body: JSON.stringify({ q, versions, exact, lim: PAGE, off: offset })
	});
	if (!res.ok) {
		console.error('search_verses failed', res.status, await res.text());
		error(502, 'Search is unavailable right now');
	}
	const hits = (await res.json()) as { verse_id: string; version: string; text: string; rank: number; book_ord: number; total: number }[];
	const total = hits[0]?.total ?? 0;

	// Anonymous log for common searches; fire and forget.
	if (offset === 0) {
		fetch(`${SUPABASE_URL}/rest/v1/rpc/log_search`, {
			method: 'POST',
			headers: { apikey: SUPABASE_ANON_KEY, authorization: `Bearer ${SUPABASE_ANON_KEY}`, 'content-type': 'application/json' },
			body: JSON.stringify({ q: raw, lang: /[஀-௿]/.test(q) ? 'ta' : 'en', results: total })
		}).catch(() => {});
	}

	setHeaders({ 'cache-control': 'public, s-maxage=60, stale-while-revalidate=300' });
	return json({
		query: raw,
		exact,
		versions,
		hits: hits.map(({ total: _t, ...h }) => h),
		total,
		took_ms: Date.now() - started
	});
};
