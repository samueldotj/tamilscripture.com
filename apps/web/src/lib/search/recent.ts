// The reader's recent searches and references, newest first, kept in this
// browser only (R-5.7). Nothing leaves the device.
import { browser } from '$app/environment';

const KEY = 'recentSearches';
const MAX = 8;

export function loadRecent(): string[] {
	if (!browser) return [];
	try {
		const list = JSON.parse(localStorage.getItem(KEY) || '[]');
		return Array.isArray(list) ? list.filter((s): s is string => typeof s === 'string') : [];
	} catch {
		return [];
	}
}

function store(list: string[]) {
	try {
		localStorage.setItem(KEY, JSON.stringify(list));
	} catch { /* storage full or blocked */ }
}

export function addRecent(text: string) {
	const q = text.trim().replace(/\s+/g, ' ');
	if (!browser || !q || q.length > 120) return;
	store([q, ...loadRecent().filter((s) => s.toLowerCase() !== q.toLowerCase())].slice(0, MAX));
}

export function clearRecent() {
	if (browser) store([]);
}

/** Recent entries matching what is being typed: empty input gives the latest few. */
export function matchRecent(typed: string, limit: number): string[] {
	const t = typed.trim().toLowerCase();
	const list = loadRecent();
	if (!t) return list.slice(0, limit);
	return list.filter((s) => s.toLowerCase().includes(t) && s.toLowerCase() !== t).slice(0, limit);
}
