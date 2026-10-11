// Loaders for the Psalms explorer: static files under /content/{build}/entities/psalms/.
import { contentUrl } from '$lib/content/manifest';
import type { PsalmCard, PsalmsIndex } from './types';

type Fetch = typeof fetch;

export async function loadPsalmsIndex(fetch: Fetch): Promise<PsalmsIndex> {
	const res = await fetch(contentUrl('entities/psalms/index.json'));
	if (!res.ok) throw new Error(`${res.status} loading psalms/index.json`);
	return (await res.json()) as PsalmsIndex;
}

const cards = new Map<number, Promise<PsalmCard>>();
/** One psalm's card, fetched once per session. */
export function loadPsalmCard(fetch: Fetch, n: number): Promise<PsalmCard> {
	let p = cards.get(n);
	if (!p) {
		p = fetch(contentUrl(`entities/psalms/${n}.json`)).then((r) => {
			if (!r.ok) throw new Error(`${r.status} loading psalms/${n}.json`);
			return r.json() as Promise<PsalmCard>;
		});
		p.catch(() => cards.delete(n));
		cards.set(n, p);
	}
	return p;
}
