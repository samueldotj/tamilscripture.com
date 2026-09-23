import { findVersion } from './manifest';

/** The page's language for `<html lang>`: the first version's on reader pages, Tamil elsewhere. */
export function pageLang(versions: string | undefined): string {
	const first = versions?.split('+')[0];
	return (first && findVersion(first)?.lang) || 'ta';
}
