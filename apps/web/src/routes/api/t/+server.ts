import type { RequestHandler } from './$types';
import { SUPABASE_ANON_KEY, SUPABASE_URL } from '$lib/supabase/config';
import { dev } from '$app/environment';

export const prerender = false;

// POST /api/t — one analytics event (docs/feature_analytics.md §2). Adds what
// only the server knows (location from Vercel's edge headers, device from the
// user agent, the client address) and hands it to Postgres, which hashes the
// address, user agent and user id with the day's salt and stores no raw value.
// Always answers 204: a beacon has nobody to read an error.

// "Cubot" is a phone brand, not a crawler.
const BOTS = /(?<!cu)bot|crawl|spider|slurp|bingpreview|facebookexternalhit|embedly|headless|lighthouse|pagespeed|preview|monitor|uptime|curl|wget|python|axios|node-fetch|go-http|java\//i;

function device(ua: string): 'mobile' | 'tablet' | 'desktop' {
	if (/iPad|Tablet|PlayBook|Silk|(Android(?!.*Mobile))/i.test(ua)) return 'tablet';
	if (/Mobi|iPhone|iPod|Android|Opera Mini|IEMobile/i.test(ua)) return 'mobile';
	return 'desktop';
}
function os(ua: string): string {
	if (/Windows/i.test(ua)) return 'Windows';
	if (/iPhone|iPad|iPod/i.test(ua)) return 'iOS';
	if (/Android/i.test(ua)) return 'Android';
	if (/CrOS/i.test(ua)) return 'ChromeOS';
	if (/Mac OS X|Macintosh/i.test(ua)) return 'macOS';
	if (/Linux/i.test(ua)) return 'Linux';
	return 'Other';
}
function browser(ua: string): string {
	if (/Edg\//i.test(ua)) return 'Edge';
	if (/OPR\/|Opera/i.test(ua)) return 'Opera';
	if (/SamsungBrowser/i.test(ua)) return 'Samsung Internet';
	if (/Firefox|FxiOS/i.test(ua)) return 'Firefox';
	if (/Chrome|CriOS/i.test(ua)) return 'Chrome';
	if (/Safari/i.test(ua)) return 'Safari';
	return 'Other';
}
/** Best-effort per-address limit inside one function instance (phase A6):
 *  60 events a minute. The database caps a visitor at 600 a day as well. */
const WINDOW_MS = 60_000;
const PER_WINDOW = 60;
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
function str(v: unknown, max: number): string | null {
	return typeof v === 'string' && v.length > 0 ? v.slice(0, max) : null;
}

export const POST: RequestHandler = async ({ request, getClientAddress, url, fetch }) => {
	// Always 204, but the x-analytics header says what happened, so a failure
	// is visible when testing: stored, skipped:<why> or error:<status>.
	const done = (outcome: string) => new Response(null, { status: 204, headers: { 'x-analytics': outcome } });
	const ua = request.headers.get('user-agent') ?? '';
	if (!ua || BOTS.test(ua)) return done('skipped:bot');
	// A prefetch is not a visit.
	const purpose = request.headers.get('sec-purpose') ?? request.headers.get('purpose') ?? '';
	if (/prefetch|prerender/i.test(purpose)) return done('skipped:prefetch');
	let body: Record<string, unknown>;
	try {
		const text = await request.text();
		if (text.length > 2000) return done('skipped:size');
		body = JSON.parse(text);
	} catch {
		return done('skipped:body');
	}
	// The referring site's host, only when it is another site.
	let referrer: string | null = null;
	const ref = str(body.ref, 500);
	if (ref) {
		try {
			const host = new URL(ref).hostname.replace(/^www\./, '');
			if (host && host !== url.hostname.replace(/^www\./, '') && !host.endsWith('tamilscripture.com')) referrer = host;
		} catch {
			/* not a URL */
		}
	}
	let ip = '';
	try {
		ip = getClientAddress();
	} catch {
		/* not available in every adapter */
	}
	// Load testing (scripts/analytics-load.mjs) exercises everything but the
	// limiter and the write, and only on a development server.
	const dryRun = dev && request.headers.get('x-analytics-dry-run') === '1';
	if (!dryRun && limited(ip || ua)) return done('skipped:limited');
	const args = {
		p_kind: body.k === 'verse' ? 'verse' : 'view',
		p_path: str(body.p, 200),
		p_route: str(body.r, 200),
		p_verse: str(body.v, 20),
		p_ip: ip,
		p_ua: ua.slice(0, 400),
		p_user: str(body.u, 40),
		p_country: header(request, 'x-vercel-ip-country'),
		p_region: header(request, 'x-vercel-ip-country-region'),
		p_city: header(request, 'x-vercel-ip-city'),
		p_device: device(ua),
		p_os: os(ua),
		p_browser: browser(ua),
		p_screen: str(body.s, 12),
		p_referrer: referrer,
		p_lang: str(body.l, 2),
		p_book: str(body.b, 3),
		p_chapter: typeof body.c === 'number' && Number.isInteger(body.c) ? body.c : null
	};
	if (!args.p_path) return done('skipped:path');
	if (dryRun) return done('dry-run');
	try {
		const res = await fetch(`${SUPABASE_URL}/rest/v1/rpc/track`, {
			method: 'POST',
			headers: { apikey: SUPABASE_ANON_KEY, authorization: `Bearer ${SUPABASE_ANON_KEY}`, 'content-type': 'application/json' },
			body: JSON.stringify(args)
		});
		if (!res.ok) {
			console.error('track failed', res.status, await res.text());
			return done(`error:${res.status}`);
		}
	} catch (e) {
		console.error('track failed', e);
		return done('error:fetch');
	}
	return done('stored');
};
