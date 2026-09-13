import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { SUPABASE_ANON_KEY, SUPABASE_URL } from '$lib/supabase/config';

export const prerender = false;

const MAX_Q = 80;

// GET /api/entities/search?q=தமஸ்&limit=6 → [{ id, type, slug, name_en, names_ta, rank }]
// Place names in either script through the Postgres function search_entities;
// cached at the CDN for an hour since the table changes only on deploy.
export const GET: RequestHandler = async ({ url, fetch, setHeaders }) => {
	const q = (url.searchParams.get('q') ?? '').trim().slice(0, MAX_Q);
	if (q.length < 2) error(400, 'Query too short');
	const lim = Math.min(20, Math.max(1, Number(url.searchParams.get('limit') ?? 8) || 8));
	const res = await fetch(`${SUPABASE_URL}/rest/v1/rpc/search_entities`, {
		method: 'POST',
		headers: { apikey: SUPABASE_ANON_KEY, authorization: `Bearer ${SUPABASE_ANON_KEY}`, 'content-type': 'application/json' },
		body: JSON.stringify({ q, lim })
	});
	if (!res.ok) {
		console.error('search_entities failed', res.status, await res.text());
		error(502, 'Search is unavailable right now');
	}
	setHeaders({ 'cache-control': 'public, s-maxage=3600, stale-while-revalidate=86400' });
	return json(await res.json());
};
