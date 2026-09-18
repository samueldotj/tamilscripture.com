// First-party analytics beacon (docs/feature_analytics.md). No cookies and no
// storage: each call sends one small POST to /api/t, which adds location and
// device on the server. Browsers that ask not to be tracked (Global Privacy
// Control, Do Not Track) are not counted, and nothing is sent in development.
import { browser, dev } from '$app/environment';

let firstView = true;

function optedOut(): boolean {
	const nav = navigator as Navigator & { globalPrivacyControl?: boolean };
	return nav.globalPrivacyControl === true || nav.doNotTrack === '1';
}

export function track(
	kind: 'view' | 'verse',
	data: { route?: string | null; verse?: string; lang?: string; user?: string | null; book?: string; chapter?: number } = {}
) {
	if (!browser || dev || optedOut()) return;
	const body = JSON.stringify({
		k: kind,
		p: location.pathname,
		r: data.route ?? undefined,
		v: data.verse,
		l: data.lang,
		u: data.user ?? undefined,
		b: data.book,
		c: data.chapter,
		s: `${screen.width}x${screen.height}`,
		// Only the landing page has a meaningful referrer.
		ref: kind === 'view' && firstView ? document.referrer || undefined : undefined
	});
	if (kind === 'view') firstView = false;
	try {
		if (!navigator.sendBeacon?.('/api/t', new Blob([body], { type: 'application/json' }))) {
			void fetch('/api/t', { method: 'POST', body, keepalive: true, headers: { 'content-type': 'application/json' } }).catch(() => {});
		}
	} catch {
		/* analytics never breaks the page */
	}
}
