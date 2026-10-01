import type { PageLoad } from './$types';
import { search, commonSearches, searchEntities } from '$lib/search/api';
import { DEFAULT_VERSION, findVersion, manifest, matchBooks, uiLangOf } from '$lib/content/manifest';
import type { BrowseRow } from '../api/dictionary/browse/+server';
import { parseSearchRange } from '$lib/search/range';
import { isRomanised, romanToTamil } from '$lib/search/romanised';

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
	// Romanised Tamil (R-5.4): "anbu" read as அன்பு when the primary version is Tamil,
	// unless the reader asked for the words as typed (lit=1).
	const roman = primary.lang === 'ta' && !url.searchParams.has('lit') && isRomanised(q) ? romanToTamil(q) : '';
	const tamilVersions = versions.filter((c) => findVersion(c)?.lang === 'ta');

	// A book of that name is the likeliest thing meant, so it heads the page.
	const books = q.length >= 2 ? matchBooks(q) : [];

	if (q.length < 2) {
		const common = await commonSearches(fetch, uiLangOf(primary.lang)).catch(() => []);
		return { q, scope, primary, versions, offset, range, result: null, entities: [], books, words: [] as BrowseRow[], common, error: null, widened: false, shown: q, fromRoman: false, romanOffer: '' };
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
		// An English word against a Tamil version (or the other way round) finds
		// nothing in that version alone, so such a query searches every version
		// from the start; any other query widens to every version if it finds nothing.
		const all = manifest.versions.map((v) => v.code);
		const crossScript = scope === 'version' && /[஀-௿]/.test(q) !== (primary.lang === 'ta');
		const canWiden = scope === 'version' && !crossScript;
		const canRoman = !!roman && tamilVersions.length > 0;
		let [result, entities] = await Promise.all([
			search(fetch, q, crossScript ? all : versions, offset, range, canWiden || canRoman),
			entitiesPromise
		]);
		const words = await wordsPromise;
		let widened = crossScript && result.total > 0;
		if (result.total === 0 && canWiden) {
			const wider = await search(fetch, q, all, offset, range, canRoman).catch(() => null);
			if (wider && wider.total > 0) {
				result = wider;
				widened = true;
			}
		}
		// Romanised Tamil: used when the words as typed find nothing anywhere ("anbu");
		// otherwise ("god", which would read as கொட) the English results stand and the
		// Tamil reading is only offered as a link.
		let shown = q;
		let fromRoman = false;
		let romanOffer = '';
		if (canRoman) {
			if (result.total === 0) {
				const tamil = await search(fetch, roman, tamilVersions, offset, range).catch(() => null);
				if (tamil && tamil.total > 0) {
					result = tamil;
					shown = roman;
					fromRoman = true;
					widened = false;
				}
			} else {
				romanOffer = roman;
			}
		}
		return { q, scope, primary, versions, offset, range, result, entities, books, words, common: [], error: null, widened, shown, fromRoman, romanOffer };
	} catch (e) {
		const entities = await entitiesPromise;
		return { q, scope, primary, versions, offset, range, result: null, entities, books, words: await wordsPromise, common: [], error: (e as Error).message, widened: false, shown: q, fromRoman: false, romanOffer: '' };
	}
};
