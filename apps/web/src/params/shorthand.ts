import type { ParamMatcher } from '@sveltejs/kit';

// A single path segment that could be a typed reference: contains a letter
// (Latin or Tamil) and is not a reserved top-level path. Actual parsing
// happens in the route, since the wasm parser loads asynchronously.
const reserved = new Set(['api', 'me', 'search', 'about', 'heatmap', 'auth', 'signin']);

export const match: ParamMatcher = (param) =>
	/\p{L}/u.test(param) && !reserved.has(param.toLowerCase()) && param.length <= 64;
