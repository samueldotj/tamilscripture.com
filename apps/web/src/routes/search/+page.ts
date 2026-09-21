import type { PageLoad } from './$types';
import { search, commonSearches, searchEntities } from '$lib/search/api';
import { DEFAULT_VERSION, findVersion, manifest, matchBooks } from '$lib/content/manifest';

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

	// A book of that name is the likeliest thing meant, so it heads the page.
	const books = q.length >= 2 ? matchBooks(q) : [];

	if (q.length < 2) {
		const common = await commonSearches(fetch, primary.lang).catch(() => []);
		return { q, scope, primary, versions, offset, result: null, entities: [], books, common, error: null, widened: false };
	}
	// Entity cards ride alongside the first page of verse hits.
	const entitiesPromise = offset === 0 ? searchEntities(fetch, q, 6).catch(() => []) : Promise.resolve([]);
	try {
		let [result, entities] = await Promise.all([search(fetch, q, versions, offset), entitiesPromise]);
		// An English word against a Tamil version (or the other way round) finds
		// nothing in that version alone; look in every version rather than stop.
		let widened = false;
		if (result.total === 0 && scope === 'version') {
			const all = manifest.versions.map((v) => v.code);
			const wider = await search(fetch, q, all, offset).catch(() => null);
			if (wider && wider.total > 0) {
				result = wider;
				widened = true;
			}
		}
		return { q, scope, primary, versions, offset, result, entities, books, common: [], error: null, widened };
	} catch (e) {
		const entities = await entitiesPromise;
		return { q, scope, primary, versions, offset, result: null, entities, books, common: [], error: (e as Error).message, widened: false };
	}
};
