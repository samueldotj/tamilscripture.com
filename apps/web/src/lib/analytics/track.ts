// First-party analytics beacon (docs/feature_analytics.md). No cookies and no
// storage: events are queued in memory and sent to /api/t in one small POST
// when the tab is hidden or closed (or the queue fills), and the server adds
// location and device. One request per visit rather than one per event keeps
// the site's edge requests and function calls down. Browsers that ask not to
// be tracked (Global Privacy Control, Do Not Track) are not counted, and
// nothing is sent in development.
import { browser, dev } from '$app/environment';
import { advance, ENGAGEMENTS, newProgress, watch, type Engagement } from './engagement';

/** The server accepts at most this many events in one request. */
export const MAX_BATCH = 20;

let firstView = true;
let queue: Record<string, unknown>[] = [];
let listening = false;
/** Called just before a batch is sent, so a module can add what it has pending
 *  (the audio player's listening time). */
const beforeFlush: (() => void)[] = [];
export function onFlush(fn: () => void) {
	beforeFlush.push(fn);
}

export function optedOut(): boolean {
	const nav = navigator as Navigator & { globalPrivacyControl?: boolean };
	return nav.globalPrivacyControl === true || nav.doNotTrack === '1';
}

function flush() {
	for (const fn of beforeFlush) {
		try {
			fn();
		} catch {
			/* analytics never breaks the page */
		}
	}
	if (queue.length === 0) return;
	const body = JSON.stringify(queue);
	queue = [];
	try {
		if (!navigator.sendBeacon?.('/api/t', new Blob([body], { type: 'application/json' }))) {
			void fetch('/api/t', { method: 'POST', body, keepalive: true, headers: { 'content-type': 'application/json' } }).catch(() => {});
		}
	} catch {
		/* analytics never breaks the page */
	}
}

function listen() {
	if (listening) return;
	listening = true;
	// visibilitychange is the last event mobile browsers reliably fire; pagehide covers desktop closes.
	document.addEventListener('visibilitychange', () => {
		if (document.visibilityState === 'hidden') flush();
	});
	addEventListener('pagehide', flush);
}

/** ?utm_source=whatsapp on the landing URL: a tag for links shared where no
 *  referrer is sent (WhatsApp on iOS, email clients, printed QR codes). A click
 *  on one of our Google ads (gclid, gbraid, wbraid) is tagged google-ads, so paid
 *  visits are told apart from Google search on /mod/traffic. */
function utmSource(): string | undefined {
	try {
		const q = new URLSearchParams(location.search);
		const ad = ['gclid', 'gbraid', 'wbraid'].some((p) => q.has(p));
		return q.get('utm_source') || (ad ? 'google-ads' : undefined);
	} catch {
		return undefined;
	}
}

export interface TrackData {
	route?: string | null;
	verse?: string;
	lang?: string;
	user?: string | null;
	book?: string;
	chapter?: number;
	/** audio: play, next, jump, end or time; share: link, large, download, sheet or copy;
	 *  goal: reader, listener, atlas or psalms */
	action?: 'play' | 'next' | 'jump' | 'end' | 'time' | ShareAction | Engagement;
	/** audio: the recording's version code; share: the first version shown */
	version?: string;
	/** audio: seconds listened, for `time` */
	amount?: number;
	/** share: an image's template, size and theme (plate.square.light) */
	detail?: string;
}
/** link and large: the reader's share menu; download, sheet and copy: "Share as image". */
export type ShareAction = 'link' | 'large' | 'download' | 'sheet' | 'copy';

export function track(kind: 'view' | 'verse' | 'audio' | 'share' | 'goal', data: TrackData = {}) {
	if (!browser || dev || optedOut()) return;
	// The moderators' own pages are not the site's traffic.
	if (location.pathname === '/mod' || location.pathname.startsWith('/mod/')) return;
	listen();
	queue.push({
		k: kind,
		p: location.pathname,
		r: data.route ?? undefined,
		v: data.verse,
		l: data.lang,
		u: data.user ?? undefined,
		b: data.book,
		c: data.chapter,
		a: data.action,
		vr: data.version,
		n: data.amount,
		d: data.detail,
		s: `${screen.width}x${screen.height}`,
		// Only the landing page has a meaningful referrer; e marks it, so a
		// landing with no referrer counts as a direct visit.
		...(kind === 'view' && firstView ? { e: 1, ref: document.referrer || undefined, us: utmSource() } : {})
	});
	if (kind === 'view') firstView = false;
	if (queue.length >= MAX_BATCH) flush();
}

/** Engagement (A11): one `goal` event the first time in this visit (this tab)
 *  a reader reads on, listens, or spends a minute on the atlas or the Psalms
 *  explorer. Kept in memory only, like the rest of the beacon. */
export function watchEngagement() {
	if (!browser || dev || optedOut()) return;
	const p = newProgress();
	watch((s) => {
		for (const g of advance(p, s)) track('goal', { action: g });
		return p.done.length < ENGAGEMENTS.length;
	});
}
