import type { ParamMatcher } from '@sveltejs/kit';

/** A chapter and verse in one segment, `3.16` or `3.16-18`; `3_16` is accepted and redirected. */
export const match: ParamMatcher = (param) => /^[1-9]\d{0,2}[._][1-9]\d{0,2}(-[1-9]\d{0,2})?$/.test(param);
