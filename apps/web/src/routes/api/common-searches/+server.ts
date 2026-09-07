import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { SUPABASE_ANON_KEY, SUPABASE_URL } from '$lib/supabase/config';

export const prerender = false;

// GET /api/common-searches?lang=ta → ["அன்பு", ...] from the nightly view.
export const GET: RequestHandler = async ({ url, fetch, setHeaders }) => {
	const lang = url.searchParams.get('lang') === 'en' ? 'en' : 'ta';
	const res = await fetch(
		`${SUPABASE_URL}/rest/v1/common_searches?select=query&lang=eq.${lang}&order=count_30d.desc&limit=10`,
		{ headers: { apikey: SUPABASE_ANON_KEY, authorization: `Bearer ${SUPABASE_ANON_KEY}` } }
	);
	setHeaders({ 'cache-control': 'public, s-maxage=3600, stale-while-revalidate=86400' });
	if (!res.ok) return json([]);
	const rows = (await res.json()) as { query: string }[];
	return json(rows.map((r) => r.query));
};
