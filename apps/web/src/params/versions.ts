import type { ParamMatcher } from '@sveltejs/kit';
import { findVersion } from '$lib/content/manifest';

/** One version code, or two joined by `+` for dual display, case-insensitive. */
export const match: ParamMatcher = (param) => {
	const parts = param.split('+');
	return parts.length <= 2 && parts.every((p) => findVersion(p) !== undefined);
};
