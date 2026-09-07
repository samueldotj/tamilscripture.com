// Community highlight counts (R-2.x). Fetched from the CDN-cached API.
export type BookHeat = Record<string, Record<string, number>>; // chapter → verse → users
export type AllHeat = Record<string, Record<string, number>>; // book → chapter → users

const cache = new Map<string, Promise<BookHeat>>();

export function bookHeat(fetchFn: typeof fetch, slug: string): Promise<BookHeat> {
	if (!cache.has(slug)) {
		cache.set(
			slug,
			fetchFn(`/api/heat/${slug}.json`).then((r) => (r.ok ? r.json() : {})).catch(() => ({}))
		);
	}
	return cache.get(slug)!;
}

export function allHeat(fetchFn: typeof fetch): Promise<AllHeat> {
	return fetchFn('/api/heat/all.json').then((r) => (r.ok ? r.json() : {})).catch(() => ({}));
}

/** Quantile bucket 1..4 for a value among the given values (0 when absent). */
export function bucket(value: number | undefined, values: number[]): number {
	if (!value || !values.length) return 0;
	const sorted = [...values].sort((a, b) => a - b);
	const rank = sorted.findIndex((v) => v >= value) / sorted.length;
	return rank < 0.25 ? 1 : rank < 0.5 ? 2 : rank < 0.75 ? 3 : 4;
}
