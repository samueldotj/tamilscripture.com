import type { PageLoad } from './$types';
import { search, commonSearches, searchEntities } from '$lib/search/api';
import { DEFAULT_VERSION, findVersion, manifest } from '$lib/content/manifest';

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

	if (q.length < 2) {
		const common = await commonSearches(fetch, primary.lang).catch(() => []);
		return { q, scope, primary, versions, offset, result: null, entities: [], common, error: null };
	}
	// Entity cards ride alongside the first page of verse hits.
	const entitiesPromise = offset === 0 ? searchEntities(fetch, q, 6).catch(() => []) : Promise.resolve([]);
	try {
		const [result, entities] = await Promise.all([search(fetch, q, versions, offset), entitiesPromise]);
		return { q, scope, primary, versions, offset, result, entities, common: [], error: null };
	} catch (e) {
		const entities = await entitiesPromise;
		return { q, scope, primary, versions, offset, result: null, entities, common: [], error: (e as Error).message };
	}
};
