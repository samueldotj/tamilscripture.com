// When a visit becomes engaged (docs/feature_analytics.md A11, §8). One timer,
// two users: the site's own analytics (a `goal` event for every reader, counted
// on /mod/traffic) and the Google Ads conversions for ad visits (ads.ts). Both
// apply the same rules to the same seconds:
//   reader    at least two different pages (not the home page, sign-in or /mod),
//             adding up to two minutes on screen; a page counts once seen for
//             10 s, bringing those seconds with it
//   listener  60 s of the Audio Bible heard
//   atlas     60 s on the atlas pages
//   psalms    60 s in the Psalms explorer
// Page time counts only while the tab is in front; listening counts in the
// background too.
import { browser } from '$app/environment';

export type Engagement = 'reader' | 'listener' | 'atlas' | 'psalms';
export const ENGAGEMENTS: Engagement[] = ['reader', 'listener', 'atlas', 'psalms'];

/** Seconds that make a listen, an atlas or a Psalms visit. */
export const ENGAGED_S = 60;
/** An engaged reader: this many different pages, each seen at least PAGE_MIN_S,
 *  adding up to READER_S on screen. */
export const READER_PAGES = 2;
export const PAGE_MIN_S = 10;
export const READER_S = 120;

/** How far one visit has got. */
export interface Progress {
	/** pages that have counted, up to READER_PAGES */
	pages: string[];
	/** seconds on counted pages */
	read: number;
	atlas: number;
	psalms: number;
	listen: number;
	/** goals already reached */
	done: string[];
}
export function newProgress(): Progress {
	return { pages: [], read: 0, atlas: 0, psalms: 0, listen: 0, done: [] };
}

/** One tick: what the reader was doing for `page` seconds in front and `listen` seconds of audio. */
interface Sample {
	route: string;
	path: string;
	/** seconds on screen on this page in this tab before this tick */
	had: number;
	page: number;
	listen: number;
}

/** The home page, sign-in and moderation pages never count towards an engaged reader. */
function countsAsPage(route: string, path: string): boolean {
	return route !== '' && route !== '/' && !path.startsWith('/signin') && !path.startsWith('/auth/') && !path.startsWith('/mod');
}

/** Add a tick to a visit's progress; returns the goals it reached just now. */
export function advance(p: Progress, s: Sample): Engagement[] {
	if (s.page > 0) {
		const total = s.had + s.page;
		if (countsAsPage(s.route, s.path) && total >= PAGE_MIN_S) {
			p.read += s.had >= PAGE_MIN_S ? s.page : total;
			if (!p.pages.includes(s.path) && p.pages.length < READER_PAGES) p.pages.push(s.path);
		}
		if (s.route.startsWith('/atlas')) p.atlas += s.page;
		if (s.route.startsWith('/psalms')) p.psalms += s.page;
	}
	p.listen += s.listen;
	const reached: Record<Engagement, boolean> = {
		reader: p.pages.length >= READER_PAGES && p.read >= READER_S,
		listener: p.listen >= ENGAGED_S,
		atlas: p.atlas >= ENGAGED_S,
		psalms: p.psalms >= ENGAGED_S
	};
	const now = ENGAGEMENTS.filter((g) => reached[g] && !p.done.includes(g));
	p.done.push(...now);
	return now;
}

/** Something that wants the seconds: returns false once it needs no more. */
export type Watcher = (s: Sample) => boolean;

const watchers = new Set<Watcher>();
let timer: ReturnType<typeof setInterval> | null = null;
let isPlaying: () => boolean = () => false;
let route = '';
let path = '';
/** Seconds in front of each page in this tab. */
const pageSeconds = new Map<string, number>();
let last = 0;
let wasVisible = false;
let wasPlaying = false;

function tick() {
	const now = Date.now();
	// Real elapsed time, as browsers slow timers in background tabs; a long gap
	// on screen is not counted, nor a very long one while playing.
	const dt = last ? (now - last) / 1000 : 0;
	last = now;
	const visible = document.visibilityState === 'visible';
	const playing = isPlaying();
	const page = visible && wasVisible && dt > 0 && dt <= 5 ? dt : 0;
	const listen = playing && wasPlaying && dt > 0 && dt <= 120 ? dt : 0;
	wasVisible = visible;
	wasPlaying = playing;
	if (!page && !listen) return;
	const had = pageSeconds.get(path) ?? 0;
	if (page) pageSeconds.set(path, had + page);
	const s: Sample = { route, path, had, page, listen };
	for (const w of [...watchers]) if (!w(s)) watchers.delete(w);
	if (watchers.size === 0) stop();
}
function stop() {
	if (timer) clearInterval(timer);
	timer = null;
}

/** Start measuring, with the audio player's state. Called once, on the first page. */
export function startEngagement(playing: () => boolean) {
	isPlaying = playing;
}

/** Add a watcher; the timer runs while any is left. */
export function watch(w: Watcher) {
	if (!browser) return;
	watchers.add(w);
	if (!timer) {
		last = 0;
		timer = setInterval(tick, 1000);
	}
}

/** On every navigation: the page being read now. */
export function enterPage(routeId: string | null, pathname: string) {
	route = routeId ?? '';
	path = pathname;
}
