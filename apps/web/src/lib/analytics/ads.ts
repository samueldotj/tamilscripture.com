// Google Ads conversions (docs/feature_analytics.md §8). Google's tag is loaded
// only for a visit that came from one of our ads: the landing URL carries a click
// id (gclid, gbraid or wbraid), which is remembered here for 30 days so that what
// the visitor does later in that window can be credited to the ad. Ordinary
// readers never load the tag and get no Google cookies. Browsers that ask not to
// be tracked are skipped, and so are visitors in Europe (judged by time zone),
// where the tag's cookies would need a consent prompt the site does not have.
//
// Five goals, each its own conversion action in Google Ads and each reported at
// most once per ad click, with nothing about the visitor or what they read:
//   signup    an account created in this window
//   reader    reading on: at least two different pages (not the home page),
//             adding up to two minutes; a page seen under 10 s does not count
//   listener  60 s of the Audio Bible heard
//   atlas     60 s on the atlas pages
//   psalms    60 s in the Psalms explorer
// Page time counts only while the tab is in front; listening counts in the
// background too. Set PUBLIC_GOOGLE_ADS_ID (AW-…) and a label per goal
// (PUBLIC_GOOGLE_ADS_LABEL_SIGNUP, _READER, _LISTENER, _ATLAS, _PSALMS); a goal
// without a label is not tracked.
import { browser, dev } from '$app/environment';
import { env } from '$env/dynamic/public';
import type { User } from '@supabase/supabase-js';
import { optedOut } from './track';

export type Goal = 'signup' | 'reader' | 'listener' | 'atlas' | 'psalms';
const GOALS: Goal[] = ['signup', 'reader', 'listener', 'atlas', 'psalms'];

const KEY = 'ads-click';
const WINDOW_MS = 30 * 24 * 3600 * 1000;
/** An account created this recently counts as a sign-up rather than a returning sign-in. */
const NEW_ACCOUNT_MS = 30 * 60 * 1000;
/** Seconds that make a listen, an atlas or a Psalms visit. */
export const ENGAGED_S = 60;
/** An engaged reader: this many different pages, each seen at least PAGE_MIN_S,
 *  adding up to READER_S on screen. */
export const READER_PAGES = 2;
export const PAGE_MIN_S = 10;
export const READER_S = 120;

const adsId = () => env.PUBLIC_GOOGLE_ADS_ID || '';
function label(goal: Goal): string {
	return (env as Record<string, string | undefined>)[`PUBLIC_GOOGLE_ADS_LABEL_${goal.toUpperCase()}`] || '';
}

/** What one ad click has led to so far, kept in localStorage across pages and reloads. */
type Click = { at: number; sent: Goal[]; pages: string[]; read: number; atlas: number; psalms: number; listen: number };

type Gtag = (...args: unknown[]) => void;
let gtag: Gtag | null = null;
let timer: ReturnType<typeof setInterval> | null = null;
let isPlaying: () => boolean = () => false;
let route = '';
let path = '';
/** Seconds in front of each page in this tab. */
const pageSeconds = new Map<string, number>();

function inEurope(): boolean {
	try {
		const tz = Intl.DateTimeFormat().resolvedOptions().timeZone ?? '';
		return /^Europe\//.test(tz) || /^Atlantic\/(Azores|Canary|Faroe|Madeira|Reykjavik)$/.test(tz);
	} catch {
		return false;
	}
}

function allowed(): boolean {
	return browser && !dev && !!adsId() && !optedOut() && !inEurope();
}

function readClick(): Click | null {
	try {
		const raw = localStorage.getItem(KEY);
		if (!raw) return null;
		const c = JSON.parse(raw) as Partial<Click>;
		if (typeof c.at === 'number' && Date.now() - c.at < WINDOW_MS) {
			return { at: c.at, sent: c.sent ?? [], pages: c.pages ?? [], read: c.read ?? 0, atlas: c.atlas ?? 0, psalms: c.psalms ?? 0, listen: c.listen ?? 0 };
		}
		localStorage.removeItem(KEY);
	} catch {
		/* storage blocked, or an unreadable value: no ad attribution */
	}
	return null;
}

function saveClick(c: Click) {
	try {
		localStorage.setItem(KEY, JSON.stringify(c));
	} catch {
		/* ignore */
	}
}

function load() {
	if (gtag) return;
	const w = window as unknown as { dataLayer: unknown[] };
	w.dataLayer = w.dataLayer || [];
	gtag = function () {
		// gtag.js expects the arguments object itself, not an array.
		w.dataLayer.push(arguments);
	};
	const s = document.createElement('script');
	s.async = true;
	s.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(adsId())}`;
	document.head.appendChild(s);
	gtag('js', new Date());
	gtag('config', adsId());
}

/** Goals that have a label and have not been reported for this click. */
function pending(c: Click): Goal[] {
	return GOALS.filter((g) => label(g) && !c.sent.includes(g));
}

/** Report a goal once for this click. */
function send(c: Click, goal: Goal) {
	if (c.sent.includes(goal) || !label(goal)) return;
	load();
	gtag!('event', 'conversion', { send_to: `${adsId()}/${label(goal)}` });
	c.sent.push(goal);
}

/** The home page, sign-in and moderation pages never count towards an engaged reader. */
function countsAsPage(r: string, p: string): boolean {
	return r !== '' && r !== '/' && !p.startsWith('/signin') && !p.startsWith('/auth/') && !p.startsWith('/mod');
}

let last = 0;
let wasVisible = false;
let wasPlaying = false;
function tick() {
	const c = readClick();
	if (!c || pending(c).length === 0) return stop();
	const now = Date.now();
	// Real elapsed time, as browsers slow timers in background tabs; a long gap
	// is not counted.
	const dt = last ? (now - last) / 1000 : 0;
	last = now;
	const visible = document.visibilityState === 'visible';
	const playing = isPlaying();
	const before = JSON.stringify(c);

	if (visible && wasVisible && dt > 0 && dt <= 5) {
		if (countsAsPage(route, path)) {
			const had = pageSeconds.get(path) ?? 0;
			const s = had + dt;
			pageSeconds.set(path, s);
			// A page joins once seen for PAGE_MIN_S, bringing the time it already had.
			if (s >= PAGE_MIN_S) {
				c.read += had >= PAGE_MIN_S ? dt : s;
				if (!c.pages.includes(path) && c.pages.length < READER_PAGES) c.pages.push(path);
			}
			if (c.pages.length >= READER_PAGES && c.read >= READER_S) send(c, 'reader');
		}
		if (route.startsWith('/atlas')) {
			c.atlas += dt;
			if (c.atlas >= ENGAGED_S) send(c, 'atlas');
		}
		if (route.startsWith('/psalms')) {
			c.psalms += dt;
			if (c.psalms >= ENGAGED_S) send(c, 'psalms');
		}
	}
	if (playing && wasPlaying && dt > 0 && dt <= 120) {
		c.listen += dt;
		if (c.listen >= ENGAGED_S) send(c, 'listener');
	}
	wasVisible = visible;
	wasPlaying = playing;
	if (JSON.stringify(c) !== before) saveClick(c);
}

function start() {
	if (timer) return;
	last = 0;
	timer = setInterval(tick, 1000);
}
function stop() {
	if (timer) clearInterval(timer);
	timer = null;
}

/** On the first page of a visit: remember an ad click, load the tag and start watching. */
export function adsLanding(url: URL, playing: () => boolean) {
	isPlaying = playing;
	if (!allowed()) return;
	const fromAd = ['gclid', 'gbraid', 'wbraid'].some((p) => url.searchParams.has(p));
	// A new ad click starts over: Google counts each goal once per click.
	if (fromAd) saveClick({ at: Date.now(), sent: [], pages: [], read: 0, atlas: 0, psalms: 0, listen: 0 });
	const c = readClick();
	if (!c) return;
	load();
	if (pending(c).length) start();
}

/** On every navigation: the page being read now. */
export function adsPage(routeId: string | null, pathname: string) {
	route = routeId ?? '';
	path = pathname;
}

/** When someone is signed in: report a new account, if they came from an ad. */
export function adsSignup(user: User | null) {
	if (!user || !allowed()) return;
	const c = readClick();
	if (!c || c.sent.includes('signup')) return;
	const age = Date.now() - new Date(user.created_at).getTime();
	// A few minutes of slack either way for a device clock that is off.
	if (!(age > -5 * 60 * 1000 && age < NEW_ACCOUNT_MS)) return;
	send(c, 'signup');
	saveClick(c);
}
