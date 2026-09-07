// Typed wrapper over the wasm-pack output in ./pkg. Call `load()` once with
// the .wasm bytes or URL; every other function is synchronous afterwards.
import init, {
	parse_reference,
	reference_path,
	suggest_books,
	type InitInput
} from './pkg/bible_wasm.js';

export interface ParsedReference {
	code: string;
	slug: string;
	chapter: number;
	verse: number | null;
	verse_end: number | null;
	id: string;
	display_en: string;
	display_ta: string;
}

export interface BookSuggestion {
	code: string;
	slug: string;
	order: number;
	testament: 'OT' | 'NT';
	chapters: number;
	name_en: string;
	name_ta: string;
}

let ready: Promise<void> | null = null;

/** Initialise the module. `input` is a URL, Response, or the .wasm bytes. */
export function load(input: InitInput | Promise<InitInput>): Promise<void> {
	if (!ready) ready = init({ module_or_path: input }).then(() => undefined);
	return ready;
}

export function isLoaded(): boolean {
	return ready !== null;
}

// The Rust side expects NFC; normalising here keeps the Unicode tables out of the wasm.
const nfc = (s: string) => s.normalize('NFC');

export function parseReference(input: string): ParsedReference | null {
	const s = parse_reference(nfc(input));
	return s == null ? null : (JSON.parse(s) as ParsedReference);
}

export function referencePath(input: string, versionPath: string): string | null {
	return reference_path(nfc(input), versionPath) ?? null;
}

export function suggestBooks(prefix: string, limit = 8): BookSuggestion[] {
	return JSON.parse(suggest_books(nfc(prefix), limit)) as BookSuggestion[];
}
