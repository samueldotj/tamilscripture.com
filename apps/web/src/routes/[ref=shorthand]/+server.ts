import { error, redirect } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { ready, referencePath } from '$lib/ref/server';
import { DEFAULT_VERSION } from '$lib/content/manifest';

// /jn3.16, /John%203:16, /யோவா3 → 302 to the canonical chapter or verse URL
// in the reader's default version (the cookie is added in M1.16; until then
// the site default).
export const GET: RequestHandler = async ({ params, cookies, setHeaders }) => {
	await ready();
	const version = (cookies.get('version') ?? DEFAULT_VERSION).toLowerCase();
	const path = referencePath(decodeURIComponent(params.ref), version);
	if (!path) error(404, 'Not a Bible reference');
	setHeaders({ 'cache-control': 'public, max-age=86400' });
	redirect(302, path);
};
