// The passage last opened in the reader, kept in this browser for everyone
// (signed in or not), so the home page can offer "Continue reading" (R-10.6).
import { browser } from '$app/environment';

export interface LastRead {
	/** Reader path of the version(s), e.g. `irvtam` or `irvtam+bsb`. */
	versions: string;
	book: string;
	chapter: number;
	at: number;
}

const KEY = 'lastRead';

export function saveLastRead(r: Omit<LastRead, 'at'>) {
	if (!browser) return;
	try {
		localStorage.setItem(KEY, JSON.stringify({ ...r, at: Date.now() }));
	} catch { /* storage full or blocked */ }
}

export function loadLastRead(): LastRead | null {
	if (!browser) return null;
	try {
		const r = JSON.parse(localStorage.getItem(KEY) || 'null');
		return r && typeof r.book === 'string' && typeof r.chapter === 'number' && typeof r.versions === 'string' ? r : null;
	} catch {
		return null;
	}
}
