import type { PageLoad } from './$types';
import type { BrowseRow, BrowseType } from '../api/dictionary/browse/+server';

// The alphabetical index is merged on the server (design 7A): one letter at a
// time, so the page never downloads the 2 MB of entity indexes.
export const prerender = false;
export const config = { isr: { expiration: false } };

export const load: PageLoad = async ({ fetch, url }) => {
	const type = (url.searchParams.get('t') ?? 'all') as BrowseType;
	const letter = url.searchParams.get('l') ?? '';
	const lang = url.searchParams.get('lang') === 'en' ? 'en' : 'ta';
	const source = url.searchParams.get('s') ?? '';
	const res = await fetch(`/api/dictionary/browse?${new URLSearchParams({ t: type, l: letter, lang, s: source })}`);
	const data = res.ok
		? ((await res.json()) as { letters: string[]; letter: string; rows: BrowseRow[]; total: number })
		: { letters: [], letter: '', rows: [], total: 0 };
	return { ...data, type, lang, source };
};
