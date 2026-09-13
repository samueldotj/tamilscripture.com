import type { PageLoad } from './$types';
import { loadArticleIndex } from '$lib/entities/load';

// One index page: rendered on first request and cached until the next deploy.
export const prerender = false;
export const config = { isr: { expiration: false } };

export const load: PageLoad = async ({ fetch, url }) => {
	const articles = await loadArticleIndex(fetch).catch(() => []);
	const letters = [...new Set(articles.map((a) => a.title[0]?.toUpperCase() ?? '#'))].sort();
	const letter = url.searchParams.get('l')?.toUpperCase() ?? letters[0] ?? 'A';
	const source = url.searchParams.get('s') ?? 'all';
	const counts: Record<string, number> = {};
	for (const a of articles) counts[a.source] = (counts[a.source] ?? 0) + 1;
	return { articles, letters, letter, source, counts };
};
