import type { PageLoad } from './$types';
import { loadArticleIndex } from '$lib/entities/load';

// One index page: rendered on first request and cached until the next deploy.
export const prerender = false;
export const config = { isr: { expiration: false } };

export const load: PageLoad = async ({ fetch, url }) => {
	const articles = await loadArticleIndex(fetch).catch(() => []);
	const letters = [...new Set(articles.map((a) => a.title[0]?.toUpperCase() ?? '#'))].sort();
	const letter = url.searchParams.get('l')?.toUpperCase() ?? letters[0] ?? 'A';
	return { articles, letters, letter };
};
