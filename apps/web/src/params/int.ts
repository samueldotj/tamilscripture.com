import type { ParamMatcher } from '@sveltejs/kit';

export const match: ParamMatcher = (param) => /^[1-9]\d{0,2}$/.test(param);
