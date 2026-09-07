/* tslint:disable */
/* eslint-disable */

/**
 * Parse a reference in English or Tamil. Returns a JSON object or `null`.
 */
export function parse_reference(input: string): string | undefined;

/**
 * Canonical site path for a reference under a version path such as `irvtam`
 * or `irvtam+bsb`. Returns `null` if the input is not a reference.
 */
export function reference_path(input: string, version_path: string): string | undefined;

/**
 * Books whose names or abbreviations start with the typed text, as a JSON array.
 */
export function suggest_books(prefix: string, limit: number): string;

export type InitInput = RequestInfo | URL | Response | BufferSource | WebAssembly.Module;

export interface InitOutput {
    readonly memory: WebAssembly.Memory;
    readonly parse_reference: (a: number, b: number) => [number, number];
    readonly reference_path: (a: number, b: number, c: number, d: number) => [number, number];
    readonly suggest_books: (a: number, b: number, c: number) => [number, number];
    readonly __wbindgen_externrefs: WebAssembly.Table;
    readonly __wbindgen_malloc: (a: number, b: number) => number;
    readonly __wbindgen_realloc: (a: number, b: number, c: number, d: number) => number;
    readonly __wbindgen_free: (a: number, b: number, c: number) => void;
    readonly __wbindgen_start: () => void;
}

export type SyncInitInput = BufferSource | WebAssembly.Module;

/**
 * Instantiates the given `module`, which can either be bytes or
 * a precompiled `WebAssembly.Module`.
 *
 * @param {{ module: SyncInitInput }} module - Passing `SyncInitInput` directly is deprecated.
 *
 * @returns {InitOutput}
 */
export function initSync(module: { module: SyncInitInput } | SyncInitInput): InitOutput;

/**
 * If `module_or_path` is {RequestInfo} or {URL}, makes a request and
 * for everything else, calls `WebAssembly.instantiate` directly.
 *
 * @param {{ module_or_path: InitInput | Promise<InitInput> }} module_or_path - Passing `InitInput` directly is deprecated.
 *
 * @returns {Promise<InitOutput>}
 */
export default function __wbg_init (module_or_path?: { module_or_path: InitInput | Promise<InitInput> } | InitInput | Promise<InitInput>): Promise<InitOutput>;
