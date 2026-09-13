import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/private';
import { SUPABASE_ANON_KEY, SUPABASE_URL } from '$lib/supabase/config';

export const prerender = false;

// POST /api/mod/publish  (Authorization: Bearer <supabase access token>)
// Verifies the caller's session and moderator role with Supabase, then asks
// GitHub to run the export workflow now (feature_dictionary.md §6). The
// fine-grained token lives in the GITHUB_DISPATCH_TOKEN environment variable
// on Vercel, scoped to this repository's Actions; it never reaches the browser.
const REPO = env.GITHUB_REPO || 'samueldotj/tamilscripture.com';

export const POST: RequestHandler = async ({ request, fetch }) => {
	const auth = request.headers.get('authorization') ?? '';
	const token = auth.startsWith('Bearer ') ? auth.slice(7).trim() : '';
	if (!token) error(401, 'Sign in first');

	const userRes = await fetch(`${SUPABASE_URL}/auth/v1/user`, { headers: { apikey: SUPABASE_ANON_KEY, authorization: `Bearer ${token}` } });
	if (!userRes.ok) error(401, 'Session is not valid');
	const user = (await userRes.json()) as { id: string };

	const roleRes = await fetch(`${SUPABASE_URL}/rest/v1/rpc/my_role`, {
		method: 'POST',
		headers: { apikey: SUPABASE_ANON_KEY, authorization: `Bearer ${token}`, 'content-type': 'application/json' },
		body: '{}'
	});
	if (!roleRes.ok || (await roleRes.json()) !== 'moderator') error(403, 'Moderators only');

	if (!env.GITHUB_DISPATCH_TOKEN) error(503, 'Publishing is not configured on this deployment');
	const dispatch = await fetch(`https://api.github.com/repos/${REPO}/dispatches`, {
		method: 'POST',
		headers: {
			accept: 'application/vnd.github+json',
			authorization: `Bearer ${env.GITHUB_DISPATCH_TOKEN}`,
			'x-github-api-version': '2022-11-28',
			'user-agent': 'tamilscripture-publish'
		},
		body: JSON.stringify({ event_type: 'export-overrides', client_payload: { by: user.id } })
	});
	if (dispatch.status !== 204) {
		console.error('repository_dispatch failed', dispatch.status, await dispatch.text());
		error(502, 'GitHub did not accept the request');
	}

	await fetch(`${SUPABASE_URL}/rest/v1/rpc/log_publish`, {
		method: 'POST',
		headers: { apikey: SUPABASE_ANON_KEY, authorization: `Bearer ${token}`, 'content-type': 'application/json' },
		body: '{}'
	}).catch(() => undefined);

	return json({ ok: true, actions: `https://github.com/${REPO}/actions/workflows/export-overrides.yml` });
};
