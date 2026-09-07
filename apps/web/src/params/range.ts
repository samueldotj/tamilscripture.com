import type { ParamMatcher } from '@sveltejs/kit';

/** `16` or `16-18` */
export const match: ParamMatcher = (param) => /^[1-9]\d{0,2}(-[1-9]\d{0,2})?$/.test(param);
