import type { ParamMatcher } from '@sveltejs/kit';

/** Strong's numbers as TIPNR writes them: H or G, digits, an optional letter (H0085, G3972G). */
export const match: ParamMatcher = (param) => /^[HG]\d{1,5}[A-Za-z]?$/.test(param);
