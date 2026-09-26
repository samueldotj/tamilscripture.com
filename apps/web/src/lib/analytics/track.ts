// First-party analytics beacon (docs/feature_analytics.md). No cookies and no
// storage: events are queued in memory and sent to /api/t in one small POST
// when the tab is hidden or closed (or the queue fills), and the server adds
// location and device. One request per visit rather than one per event keeps
// the site's edge requests and function calls down. Browsers that ask not to
// be tracked (Global Privacy Control, Do Not Track) are not counted, and
// nothing is sent in development.
import { browser, dev } from '$app/environment';

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

function optedOut(): boolean {
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

export interface TrackData {
	route?: string | null;
	verse?: string;
	lang?: string;
	user?: string | null;
	book?: string;
	chapter?: number;
	/** audio: play, next, jump, end or time */
	action?: 'play' | 'next' | 'jump' | 'end' | 'time';
	/** audio: the recording's version code */
	version?: string;
	/** audio: seconds listened, for `time` */
	amount?: number;
}

export function track(kind: 'view' | 'verse' | 'audio', data: TrackData = {}) {
	if (!browser || dev || optedOut()) return;
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
		s: `${screen.width}x${screen.height}`,
		// Only the landing page has a meaningful referrer.
		ref: kind === 'view' && firstView ? document.referrer || undefined : undefined
	});
	if (kind === 'view') firstView = false;
	if (queue.length >= MAX_BATCH) flush();
}
