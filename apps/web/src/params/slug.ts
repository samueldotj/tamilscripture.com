import type { ParamMatcher } from '@sveltejs/kit';

/** Entity and journey ids: lowercase ASCII words joined by hyphens. */
export const match: ParamMatcher = (param) => /^[a-z0-9]+(-[a-z0-9]+)*$/.test(param) && param.length <= 80;
