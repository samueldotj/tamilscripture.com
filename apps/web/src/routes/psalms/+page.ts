// The Psalms explorer (docs/feature_psalms_explorer.md). A static route, so it wins
// over [book=book] for /psalms; the reader's /psalms/23 is unaffected.
import { loadPsalmsIndex } from '$lib/psalms/load';

export const prerender = false;
export const ssr = true;

export async function load({ fetch }) {
	return { index: await loadPsalmsIndex(fetch) };
}
