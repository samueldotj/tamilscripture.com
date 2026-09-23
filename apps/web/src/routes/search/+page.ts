import type { PageLoad } from './$types';
import { search, commonSearches, searchEntities } from '$lib/search/api';
import { DEFAULT_VERSION, findVersion, manifest, matchBooks } from '$lib/content/manifest';
import type { BrowseRow } from '../api/dictionary/browse/+server';
import { parseSearchRange } from '$lib/search/range';

export const prerender = false;
export const ssr = true;

export const load: PageLoad = async ({ url, fetch }) => {
	const q = (url.searchParams.get('q') ?? '').trim();
	const scope = url.searchParams.get('scope') ?? 'version';
	const primary = findVersion(url.searchParams.get('v') ?? DEFAULT_VERSION) ?? findVersion(DEFAULT_VERSION)!;
	const versions =
		scope === 'all'
			? manifest.versions.map((v) => v.code)
			: scope === 'lang'
				? manifest.versions.filter((v) => v.lang === primary.lang).map((v) => v.code)
				: [primary.code];
	const offset = Number(url.searchParams.get('offset') ?? 0) || 0;
	const range = parseSearchRange(url.searchParams.get('in'), url.searchParams.get('ch'));

	// A book of that name is the likeliest thing meant, so it heads the page.
	const books = q.length >= 2 ? matchBooks(q) : [];

	if (q.length < 2) {
		const common = await commonSearches(fetch, primary.lang).catch(() => []);
		return { q, scope, primary, versions, offset, range, result: null, entities: [], books, words: [] as BrowseRow[], common, error: null, widened: false };
	}
	// Entity cards ride alongside the first page of verse hits.
	const entitiesPromise = offset === 0 ? searchEntities(fetch, q, 6).catch(() => []) : Promise.resolve([]);
	// Hebrew and Greek words: a Strong's number, the word, its transliteration or its meaning.
	const wordsPromise: Promise<BrowseRow[]> =
		offset === 0
			? fetch(`/api/dictionary/browse?${new URLSearchParams({ t: 'strongs', q })}`)
					.then((r) => (r.ok ? r.json() : { rows: [] }))
					.then((d) => (d.rows as BrowseRow[]).slice(0, 8))
					.catch(() => [])
			: Promise.resolve([]);
	try {
		let [result, entities] = await Promise.all([search(fetch, q, versions, offset, range), entitiesPromise]);
		const words = await wordsPromise;
		// An English word against a Tamil version (or the other way round) finds
		// nothing in that version alone; look in every version rather than stop.
		let widened = false;
		if (result.total === 0 && scope === 'version') {
			const all = manifest.versions.map((v) => v.code);
			const wider = await search(fetch, q, all, offset, range).catch(() => null);
			if (wider && wider.total > 0) {
				result = wider;
				widened = true;
			}
		}
		return { q, scope, primary, versions, offset, range, result, entities, books, words, common: [], error: null, widened };
	} catch (e) {
		const entities = await entitiesPromise;
		return { q, scope, primary, versions, offset, range, result: null, entities, books, words: await wordsPromise, common: [], error: (e as Error).message, widened: false };
	}
};
