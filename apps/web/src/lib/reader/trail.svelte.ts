// The reader's own back/forward trail: the passages visited in this tab, in
// order, with a cursor. The reader's ‹ › buttons walk it; the browser's own
// back and forward are recognised when they land on the neighbouring entry.
// Kept per tab in sessionStorage, so it survives reloads but not new tabs.
import { browser } from '$app/environment';

export type Stop = { url: string; label: string };

const KEY = 'reader-trail';
const MAX = 50;

function read(): { stops: Stop[]; at: number } {
	if (!browser) return { stops: [], at: -1 };
	try {
		const saved = JSON.parse(sessionStorage.getItem(KEY) || 'null');
		if (saved && Array.isArray(saved.stops) && typeof saved.at === 'number') return saved;
	} catch {
		/* blocked storage or a bad value */
	}
	return { stops: [], at: -1 };
}

class Trail {
	stops = $state<Stop[]>([]);
	at = $state(-1);
	/** The entry a ‹ or › press is heading for, until the page arrives. */
	private heading: number | null = null;

	constructor() {
		const saved = read();
		this.stops = saved.stops;
		this.at = saved.at;
	}

	get back(): Stop | null {
		return this.at > 0 ? this.stops[this.at - 1] : null;
	}
	get forward(): Stop | null {
		return this.at >= 0 && this.at < this.stops.length - 1 ? this.stops[this.at + 1] : null;
	}

	/** Where to go for ‹ (-1) or › (+1); the caller navigates there. */
	step(dir: -1 | 1): string | null {
		return this.jump(this.at + dir);
	}

	/** Where entry `to` is (the history menu's pick); the caller navigates there. */
	jump(to: number): string | null {
		if (to < 0 || to >= this.stops.length || to === this.at) return null;
		this.heading = to;
		return this.stops[to].url;
	}

	/** The latest `n` entries, newest first, with their places in the trail. */
	recent(n: number): (Stop & { i: number })[] {
		return this.stops.map((s, i) => ({ ...s, i })).slice(-n).reverse();
	}

	/** A reader page arrived. `replace` keeps one entry for reading on into the next chapter. */
	visit(url: string, label: string, replace = false) {
		const stops = this.stops;
		const h = this.heading;
		this.heading = null;
		if (h !== null && stops[h]?.url === url) {
			this.at = h;
		} else if (stops[this.at]?.url === url) {
			// a reload, or the same page again
		} else if (stops[this.at - 1]?.url === url) {
			this.at -= 1; // the browser's back
		} else if (stops[this.at + 1]?.url === url) {
			this.at += 1; // the browser's forward
		} else if (replace && this.at >= 0) {
			this.stops = [...stops.slice(0, this.at), { url, label }];
		} else {
			const kept = stops.slice(Math.max(0, this.at + 2 - MAX), this.at + 1);
			this.stops = [...kept, { url, label }];
			this.at = this.stops.length - 1;
		}
		this.save();
	}

	private save() {
		try {
			sessionStorage.setItem(KEY, JSON.stringify({ stops: this.stops, at: this.at }));
		} catch {
			/* private mode or blocked storage */
		}
	}
}

export const trail = new Trail();
