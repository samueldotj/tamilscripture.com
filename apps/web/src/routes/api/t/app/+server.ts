import type { RequestHandler } from './$types';
import { json } from '@sveltejs/kit';
import { SUPABASE_ANON_KEY, SUPABASE_URL } from '$lib/supabase/config';

export const prerender = false;

// POST /api/t/app — a batch of stats events from the Android app (tamilscripture.app
// design §12). The app queues events on the phone and sends up to 500 at a time with
// a random install id; this adds location from Vercel's edge headers and hands the
// batch to track_app_batch(), which validates every event, hashes the install id with
// the day's salt and drops events it has already stored (by event id).
//
// Answers {accepted: [ids]}: every event in a batch Postgres has processed, including
// ones it skipped as invalid or over the daily cap, so the phone never resends them.
// Any other answer (limited, error) makes the phone keep its queue and retry later.

const MAX_EVENTS = 500;
const MAX_BYTES = 600 * MAX_EVENTS;

/** Best-effort per-address limit inside one function instance: 20 batches a minute. */
const WINDOW_MS = 60_000;
const PER_WINDOW = 20;
const recent = new Map<string, { start: number; n: number }>();
function limited(key: string): boolean {
	const now = Date.now();
	if (recent.size > 5000) recent.clear();
	const r = recent.get(key);
	if (!r || now - r.start > WINDOW_MS) {
		recent.set(key, { start: now, n: 1 });
		return false;
	}
	r.n += 1;
	return r.n > PER_WINDOW;
}

function header(req: Request, name: string): string | null {
	const v = req.headers.get(name);
	if (!v) return null;
	try {
		return decodeURIComponent(v);
	} catch {
		return v;
	}
}

export const POST: RequestHandler = async ({ request, getClientAddress, fetch }) => {
	let ip = '';
	try {
		ip = getClientAddress();
	} catch {
		/* not available in every adapter */
	}
	if (limited(ip || 'unknown')) return json({ error: 'limited' }, { status: 429, headers: { 'retry-after': '60' } });

	let batch: Record<string, unknown>;
	try {
		const text = await request.text();
		if (text.length > MAX_BYTES) return json({ error: 'size' }, { status: 413 });
		batch = JSON.parse(text);
	} catch {
		return json({ error: 'body' }, { status: 400 });
	}
	if (!batch || typeof batch !== 'object' || !Array.isArray(batch.events)) return json({ error: 'body' }, { status: 400 });
	const events = (batch.events as unknown[]).filter((e): e is Record<string, unknown> => !!e && typeof e === 'object').slice(0, MAX_EVENTS);
	const ids = events.map((e) => e.id).filter((id): id is string => typeof id === 'string');

	try {
		const res = await fetch(`${SUPABASE_URL}/rest/v1/rpc/track_app_batch`, {
			method: 'POST',
			headers: { apikey: SUPABASE_ANON_KEY, authorization: `Bearer ${SUPABASE_ANON_KEY}`, 'content-type': 'application/json' },
			body: JSON.stringify({
				p: { ...batch, events },
				p_country: header(request, 'x-vercel-ip-country'),
				p_region: header(request, 'x-vercel-ip-country-region'),
				p_city: header(request, 'x-vercel-ip-city')
			})
		});
		if (!res.ok) {
			console.error('track_app_batch failed', res.status, await res.text());
			return json({ error: 'store' }, { status: 502 });
		}
		const stored = await res.json();
		return json({ accepted: ids, stored });
	} catch (e) {
		console.error('track_app_batch failed', e);
		return json({ error: 'store' }, { status: 502 });
	}
};
