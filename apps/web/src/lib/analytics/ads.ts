// Google Ads conversions (docs/feature_analytics.md §8). Google's tag is loaded
// only for a visit that came from one of our ads: the landing URL carries a click
// id (gclid, gbraid or wbraid), which is remembered here for 30 days so that what
// the visitor does later in that window can be credited to the ad. Ordinary
// readers never load the tag and get no Google cookies. Browsers that ask not to
// be tracked are skipped, and so are visitors in Europe (judged by time zone),
// where the tag's cookies would need a consent prompt the site does not have.
//
// Five goals, each its own conversion action in Google Ads and each reported at
// most once per ad click, with nothing about the visitor or what they read: a
// sign-up (an account created in this window), and the four engagements of
// engagement.ts (reader, listener, atlas, psalms), whose rules /mod/traffic
// shares. Progress is kept with the click, so it carries across pages and
// reloads. Set PUBLIC_GOOGLE_ADS_ID (AW-…) and a label per goal
// (PUBLIC_GOOGLE_ADS_LABEL_SIGNUP, _READER, _LISTENER, _ATLAS, _PSALMS); a goal
// without a label is not tracked.
import { browser, dev } from '$app/environment';
import { env } from '$env/dynamic/public';
import type { User } from '@supabase/supabase-js';
import { optedOut } from './track';
import { advance, ENGAGEMENTS, newProgress, watch, type Engagement, type Progress } from './engagement';

export type Goal = 'signup' | Engagement;
const GOALS: Goal[] = ['signup', ...ENGAGEMENTS];

const KEY = 'ads-click';
const WINDOW_MS = 30 * 24 * 3600 * 1000;
/** An account created this recently counts as a sign-up rather than a returning sign-in. */
const NEW_ACCOUNT_MS = 30 * 60 * 1000;

const adsId = () => env.PUBLIC_GOOGLE_ADS_ID || '';
function label(goal: Goal): string {
	return (env as Record<string, string | undefined>)[`PUBLIC_GOOGLE_ADS_LABEL_${goal.toUpperCase()}`] || '';
}

/** One ad click: when, the goals reported for it, and the visit's progress. */
type Click = { at: number; sent: Goal[]; progress: Progress };

type Gtag = (...args: unknown[]) => void;
let gtag: Gtag | null = null;

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
			return { at: c.at, sent: c.sent ?? [], progress: { ...newProgress(), ...c.progress } };
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

/** Engagement goals that have a label and have not been reported for this click. */
function pending(c: Click): Goal[] {
	return GOALS.filter((g) => g !== 'signup' && label(g) && !c.sent.includes(g));
}

/** Report a goal once for this click. */
function send(c: Click, goal: Goal) {
	if (c.sent.includes(goal) || !label(goal)) return;
	load();
	gtag!('event', 'conversion', { send_to: `${adsId()}/${label(goal)}` });
	c.sent.push(goal);
}

/** On the first page of a visit: remember an ad click, load the tag and watch for engagement. */
export function adsLanding(url: URL) {
	if (!allowed()) return;
	const fromAd = ['gclid', 'gbraid', 'wbraid'].some((p) => url.searchParams.has(p));
	// A new ad click starts over: Google counts each goal once per click.
	if (fromAd) saveClick({ at: Date.now(), sent: [], progress: newProgress() });
	const first = readClick();
	if (!first) return;
	load();
	if (!pending(first).length) return;
	watch((s) => {
		// Read and write the click on every tick: another tab may share it.
		const c = readClick();
		if (!c) return false;
		for (const g of advance(c.progress, s)) send(c, g);
		saveClick(c);
		return pending(c).length > 0;
	});
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
