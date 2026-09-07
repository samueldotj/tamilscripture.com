// Server-side access to the same parser. `read` serves the bundled asset in
// every adapter (Vercel, Node), with no filesystem path assumptions.
import { read } from '$app/server';
import wasmUrl from '@tamilscripture/bible-wasm/wasm?url';
import { load, parseReference, referencePath } from '@tamilscripture/bible-wasm';

export async function ready(): Promise<void> {
	await load(read(wasmUrl));
}

export { parseReference, referencePath };
