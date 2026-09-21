import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { SUPABASE_ANON_KEY, SUPABASE_URL } from '$lib/supabase/config';
import { manifest } from '$lib/content/manifest';

export const prerender = false;

const MAX = 60;

// GET /api/verses?v=IRVTAM&ids=GEN.17.5,GEN.17.9
// The text of up to 60 verses in one version, from the public verse_search
// table, for lists that name verses without their text (the concordance).
export const GET: RequestHandler = async ({ url, fetch, setHeaders }) => {
	const version = (url.searchParams.get('v') ?? 'IRVTAM').toUpperCase();
	if (!manifest.versions.some((v) => v.code === version)) error(400, 'Unknown version');
	const ids = (url.searchParams.get('ids') ?? '')
		.split(',')
		.map((s) => s.trim())
		.filter((s) => /^[1-3A-Z]{3}\.\d{1,3}\.\d{1,3}$/.test(s))
		.slice(0, MAX);
	if (!ids.length) return json({});

	const params = new URLSearchParams({ select: 'verse_id,text', version: `eq.${version}`, verse_id: `in.(${ids.join(',')})` });
	const res = await fetch(`${SUPABASE_URL}/rest/v1/verse_search?${params}`, {
		headers: { apikey: SUPABASE_ANON_KEY, authorization: `Bearer ${SUPABASE_ANON_KEY}` }
	});
	if (!res.ok) {
		console.error('verses failed', res.status, await res.text());
		error(502, 'Verses are unavailable right now');
	}
	const rows = (await res.json()) as { verse_id: string; text: string }[];
	// The text only changes with a new Bible build, so it caches well.
	setHeaders({ 'cache-control': 'public, max-age=3600, s-maxage=86400' });
	return json(Object.fromEntries(rows.map((r) => [r.verse_id, r.text])));
};
