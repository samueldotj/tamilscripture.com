// Client for /api/search and /api/common-searches.
export interface SearchHit {
	verse_id: string;
	version: string;
	text: string;
	rank: number;
	book_ord: number;
}

export interface SearchResponse {
	query: string;
	exact: boolean;
	versions: string[];
	hits: SearchHit[];
	total: number;
	took_ms: number;
}

export async function search(
	fetchFn: typeof fetch,
	q: string,
	versions: string[],
	offset = 0,
	range: { bookMin: number; bookMax: number; chMin?: number; chMax?: number } | null = null
): Promise<SearchResponse> {
	const params = new URLSearchParams({ q, v: versions.join(','), offset: String(offset) });
	if (range) {
		params.set('bmin', String(range.bookMin));
		params.set('bmax', String(range.bookMax));
		if (range.chMin) params.set('cmin', String(range.chMin));
		if (range.chMax) params.set('cmax', String(range.chMax));
	}
	const res = await fetchFn(`/api/search?${params}`);
	if (!res.ok) throw new Error(`search failed: ${res.status}`);
	return res.json();
}

export async function commonSearches(fetchFn: typeof fetch, lang: 'ta' | 'en'): Promise<string[]> {
	const res = await fetchFn(`/api/common-searches?lang=${lang}`);
	if (!res.ok) return [];
	return res.json();
}

export type EntityType = 'place' | 'person' | 'article';

export interface EntityHit {
	/** `place/damascus`, `person/paul`, `article/eastons/damascus` */
	id: string;
	type: EntityType;
	/** `damascus`, `paul`, `eastons/damascus` */
	slug: string;
	name_en: string;
	/** space-joined Tamil forms; the first is the label */
	names_ta: string;
	rank: number;
}

/** Page for an entity hit. */
export function entityHref(h: Pick<EntityHit, 'type' | 'slug'>): string {
	return h.type === 'article' ? `/dictionary/${h.slug}` : `/${h.type}/${h.slug}`;
}

/** Kind label for an entity hit in the interface language. */
export function entityKind(type: EntityType, lang: 'ta' | 'en'): string {
	const labels = { place: ['இடம்', 'place'], person: ['நபர்', 'person'], article: ['அகராதி', 'dictionary'] } as const;
	return labels[type][lang === 'ta' ? 0 : 1];
}

/** Places, people and dictionary articles matching a query in either script. */
export async function searchEntities(fetchFn: typeof fetch, q: string, limit = 6): Promise<EntityHit[]> {
	if (q.trim().length < 2) return [];
	const res = await fetchFn(`/api/entities/search?${new URLSearchParams({ q: q.trim(), limit: String(limit) })}`);
	if (!res.ok) return [];
	return res.json();
}

/** Tamil label of an entity hit, if any. */
export function entityLabelTa(h: EntityHit): string | undefined {
	return h.names_ta.split(' ').filter(Boolean)[0];
}

/** Split a query into display tokens for highlighting (quotes removed). */
export function queryTokens(q: string): string[] {
	return q
		.replace(/[“”"]/g, ' ')
		.split(/\s+/)
		.map((t) => t.trim())
		.filter((t) => t.length > 1);
}
