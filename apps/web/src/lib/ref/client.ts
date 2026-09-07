// Browser-side access to the reference parser. The wasm is fetched lazily on
// first use (about 40 kB) so it never delays the reader.
import wasmUrl from '@tamilscripture/bible-wasm/wasm?url';
import { load, parseReference, referencePath, suggestBooks } from '@tamilscripture/bible-wasm';

export async function ready(): Promise<void> {
	await load(fetch(wasmUrl));
}

export { parseReference, referencePath, suggestBooks };
