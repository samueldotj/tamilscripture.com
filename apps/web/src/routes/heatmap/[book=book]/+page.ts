import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import { findBook } from '$lib/content/manifest';

export const prerender = false;
export const config = { isr: { expiration: 3600 } };

export const load: PageLoad = ({ params }) => {
	const book = findBook(params.book)!;
	if (params.book !== book.slug) redirect(301, `/heatmap/${book.slug}`);
	return { book };
};
