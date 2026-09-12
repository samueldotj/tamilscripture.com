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
	offset = 0
): Promise<SearchResponse> {
	const params = new URLSearchParams({ q, v: versions.join(','), offset: String(offset) });
	const res = await fetchFn(`/api/search?${params}`);
	if (!res.ok) throw new Error(`search failed: ${res.status}`);
	return res.json();
}

export async function commonSearches(fetchFn: typeof fetch, lang: 'ta' | 'en'): Promise<string[]> {
	const res = await fetchFn(`/api/common-searches?lang=${lang}`);
	if (!res.ok) return [];
	return res.json();
}

export interface EntityHit {
	id: string;
	type: 'place';
	slug: string;
	name_en: string;
	/** space-joined Tamil forms; the first is the label */
	names_ta: string;
	rank: number;
}

/** Places (later people and articles) matching a query in either script. */
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
