// The permalink. A presentation shared by link is read here with the public
// key (no session, like /api/verses) so the page arrives with its title for
// link previews; a private one comes back null and the page then asks the
// browser's own session, which is the owner's. Never cached: the owner may
// be editing while the audience opens the link.
import type { PageServerLoad } from './$types';
import { sharedPresentation } from '$lib/present/repo';

export const prerender = false;

export const load: PageServerLoad = async ({ params, fetch, setHeaders }) => {
	setHeaders({ 'cache-control': 'private, no-store' });
	const presentation = await sharedPresentation(fetch, params.slug).catch(() => null);
	return { slug: params.slug, presentation };
};
