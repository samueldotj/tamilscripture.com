import { contentUrl } from './manifest';
import type { ChapterJson, IntroJson, XrefChapter } from './types';

type Fetch = typeof fetch;

async function getJson<T>(fetch: Fetch, path: string): Promise<T> {
	const res = await fetch(contentUrl(path));
	if (!res.ok) throw new Error(`${res.status} loading ${path}`);
	return (await res.json()) as T;
}

export function loadChapter(fetch: Fetch, version: string, book: string, chapter: number) {
	return getJson<ChapterJson>(fetch, `${version}/${book}/${chapter}.json`);
}

export function loadIntro(fetch: Fetch, version: string, book: string) {
	return getJson<IntroJson>(fetch, `${version}/${book}/intro.json`);
}

export function loadXrefs(fetch: Fetch, book: string, chapter: number) {
	return getJson<XrefChapter>(fetch, `xref/${book}/${chapter}.json`);
}
