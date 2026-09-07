import type { ParamMatcher } from '@sveltejs/kit';
import { findBook } from '$lib/content/manifest';

export const match: ParamMatcher = (param) => findBook(param) !== undefined;
