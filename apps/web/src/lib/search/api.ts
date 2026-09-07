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

/** Split a query into display tokens for highlighting (quotes removed). */
export function queryTokens(q: string): string[] {
	return q
		.replace(/[“”"]/g, ' ')
		.split(/\s+/)
		.map((t) => t.trim())
		.filter((t) => t.length > 1);
}
