// Reader settings: persisted in localStorage under "reader", mirrored to
// classes on <html> (see app.html for the pre-paint stamp) and to a `version`
// cookie read by the shorthand redirector. Signed-in sync to `profiles` is M3.
import { browser } from '$app/environment';

export type Format = 'reader' | 'standard' | 'xref';
export type Theme = 'system' | 'light' | 'dark';
export type TamilFont = 'mukta' | 'sans' | 'serif' | 'system';

export interface Settings {
	format: Format;
	tamilFont: TamilFont;
	headings: boolean;
	intro: boolean;
	footnotes: boolean;
	xrefs: boolean;
	/** Tint verses by community highlight count (R-2.3), off by default. */
	heat: boolean;
	/** 1..5, 3 is the default 17px */
	fontSize: number;
	theme: Theme;
	uiLang: 'ta' | 'en';
	version: string;
}

export const DEFAULTS: Settings = {
	format: 'standard',
	tamilFont: 'mukta',
	headings: true,
	intro: true,
	footnotes: true,
	xrefs: true,
	heat: false,
	fontSize: 3,
	theme: 'system',
	uiLang: 'ta',
	version: 'irvtam'
};

const KEY = 'reader';

function read(): Settings {
	if (!browser) return { ...DEFAULTS };
	try {
		const saved = JSON.parse(localStorage.getItem(KEY) || '{}');
		return { ...DEFAULTS, ...saved };
	} catch {
		return { ...DEFAULTS };
	}
}

/** Class list for <html>; kept in sync with the inline script in app.html. */
export function htmlClasses(s: Settings): string[] {
	const c = [`fmt-${s.format}`, `fs-${s.fontSize}`, `tf-${s.tamilFont}`];
	if (!s.headings) c.push('no-headings');
	if (!s.intro) c.push('no-intro');
	if (!s.footnotes) c.push('no-footnotes');
	if (!s.xrefs) c.push('no-xrefs');
	return c;
}

class SettingsStore {
	value = $state<Settings>(read());

	update(patch: Partial<Settings>) {
		this.value = { ...this.value, ...patch };
		this.persist();
	}

	toggle(key: 'headings' | 'intro' | 'footnotes' | 'xrefs' | 'heat') {
		this.update({ [key]: !this.value[key] } as Partial<Settings>);
	}

	private persist() {
		if (!browser) return;
		try {
			localStorage.setItem(KEY, JSON.stringify(this.value));
		} catch {
			/* private mode or blocked storage */
		}
		document.cookie = `version=${this.value.version}; path=/; max-age=31536000; samesite=lax`;
		this.stamp();
	}

	/** Apply classes and theme to <html>. Safe to call repeatedly. */
	stamp() {
		if (!browser) return;
		const html = document.documentElement;
		const keep = [...html.classList].filter(
			(c) => !/^(fmt-|fs-|tf-|no-headings$|no-intro$|no-footnotes$|no-xrefs$)/.test(c)
		);
		html.className = [...keep, ...htmlClasses(this.value)].join(' ');
		if (this.value.theme === 'system') html.removeAttribute('data-theme');
		else html.setAttribute('data-theme', this.value.theme);
	}
}

export const settings = new SettingsStore();
