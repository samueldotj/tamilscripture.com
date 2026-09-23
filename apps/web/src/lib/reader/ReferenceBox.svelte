<script lang="ts">
	import { goto } from '$app/navigation';
	import { ready, referencePath, suggestBooks } from '$lib/ref/client';
	import type { BookSuggestion } from '@tamilscripture/bible-wasm';
	import { entityHref, entityKind, entityLabelTa, searchEntities, type EntityHit } from '$lib/search/api';
	import { addRecent, clearRecent, matchRecent } from '$lib/search/recent';

	let { versionPath, lang = 'ta' }: { versionPath: string; lang?: 'ta' | 'en' } = $props();

	let value = $state('');
	let loaded = $state(false);
	let books = $state<BookSuggestion[]>([]);
	let places = $state<EntityHit[]>([]);
	/** Recent searches (R-5.7): the latest on an empty box, matches while typing. */
	let recent = $state<string[]>([]);
	let active = $state(-1);
	let notFound = $state(false);
	let input: HTMLInputElement;
	let placeTimer: ReturnType<typeof setTimeout> | undefined;
	let placeSeq = 0;

	type Item = { kind: 'recent'; q: string } | { kind: 'book'; book: BookSuggestion } | { kind: 'place'; place: EntityHit };
	const items = $derived<Item[]>([
		...recent.map((q) => ({ kind: 'recent' as const, q })),
		...books.map((b) => ({ kind: 'book' as const, book: b })),
		...places.map((p) => ({ kind: 'place' as const, place: p }))
	]);
	function hide() {
		books = [];
		places = [];
		recent = [];
	}
	function onFocus() {
		ensure();
		if (!value.trim()) recent = matchRecent('', 6);
	}

	async function ensure() {
		if (!loaded) {
			await ready();
			loaded = true;
		}
	}

	async function onInput() {
		notFound = false;
		const text = value;
		recent = matchRecent(text, text.trim() ? 3 : 6);
		await ensure();
		// Suggest books only while the user is still typing letters.
		const bookPart = text.replace(/^\s*[1-3]\s*/, '').split(/\d/)[0].trim();
		books = bookPart.length >= 1 && !/\d/.test(text) ? suggestBooks(text, 5) : [];
		active = -1;
		// Places, people and articles: debounced lookup in either script, four rows.
		clearTimeout(placeTimer);
		const seq = ++placeSeq;
		if (text.trim().length >= 2 && !/\d/.test(text)) {
			placeTimer = setTimeout(async () => {
				const hits = await searchEntities(fetch, text, 4).catch(() => []);
				if (seq === placeSeq && value === text) places = hits;
			}, 180);
		} else {
			places = [];
		}
	}

	async function submit(text = value) {
		const trimmed = text.trim();
		if (!trimmed) return;
		addRecent(trimmed);
		await ensure();
		// A Strong's number ("G26", "H430") opens the concordance for it.
		if (/^[HG]\d{1,4}[A-Za-z]?$/i.test(trimmed)) {
			const res = await fetch(`/api/dictionary/browse?${new URLSearchParams({ t: 'strongs', q: trimmed })}`).catch(() => null);
			const first = res?.ok ? ((await res.json()).rows?.[0] as { href: string } | undefined) : undefined;
			if (first) {
				value = '';
				hide();
				input.blur();
				await goto(first.href);
				return;
			}
		}
		const path = referencePath(trimmed, versionPath);
		hide();
		input.blur();
		if (path) {
			value = '';
			await goto(path);
		} else {
			// Not a reference: search the words in the current primary version.
			const v = versionPath.split('+')[0].toUpperCase();
			await goto(`/search?${new URLSearchParams({ q: trimmed, v })}`);
		}
	}

	function pick(item: Item) {
		if (item.kind === 'recent') {
			value = item.q;
			submit(item.q);
		} else if (item.kind === 'book') {
			value = (lang === 'ta' ? item.book.name_ta : item.book.name_en) + ' ';
			hide();
			input.focus();
		} else {
			value = '';
			hide();
			input.blur();
			goto(entityHref(item.place));
		}
	}

	function onKey(e: KeyboardEvent) {
		if (e.key === 'ArrowDown' && items.length) {
			e.preventDefault();
			active = (active + 1) % items.length;
		} else if (e.key === 'ArrowUp' && items.length) {
			e.preventDefault();
			active = (active - 1 + items.length) % items.length;
		} else if (e.key === 'Enter') {
			e.preventDefault();
			if (active >= 0) pick(items[active]);
			else submit();
		} else if (e.key === 'Escape') {
			hide();
			input.blur();
		}
	}
	function close() {
		setTimeout(hide, 150);
	}
</script>

<form class="refbox" role="search" onsubmit={(e) => { e.preventDefault(); submit(); }}>
	<svg class="icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7.5" /><path d="m20.5 20.5-4.2-4.2" /></svg>
	<input
		bind:this={input}
		bind:value
		class="field"
		type="search"
		autocomplete="off"
		spellcheck="false"
		enterkeyhint="go"
		aria-label={lang === 'ta' ? 'வசனம், பெயர் அல்லது சொல் தேடு' : 'Go to a reference, a name, or search a word'}
		aria-invalid={notFound}
		placeholder={lang === 'ta' ? 'யோவான் 3:16 · புத்தகம், பெயர், சொல்' : 'John 3:16 · book, name, word'}
		onfocus={onFocus}
		oninput={onInput}
		onkeydown={onKey}
		onblur={close}
	/>
	<kbd class="kbd" aria-hidden="true">Ctrl K</kbd>
	{#if items.length}
		<ul class="suggest" role="listbox">
			{#if recent.length}
				<li class="group" role="presentation">
					<span lang={lang}>{lang === 'ta' ? 'சமீபத்தியவை' : 'Recent'}</span>
					<button type="button" class="clear" onmousedown={(e) => { e.preventDefault(); clearRecent(); recent = []; }} lang={lang}>{lang === 'ta' ? 'அழி' : 'Clear'}</button>
				</li>
			{/if}
			{#each items as item, i (item.kind === 'recent' ? `r-${item.q}` : item.kind === 'book' ? `b-${item.book.code}` : `p-${item.place.id}`)}
				<li role="option" aria-selected={i === active} class:active={i === active}>
					<button type="button" onmousedown={(e) => { e.preventDefault(); pick(item); }}>
						{#if item.kind === 'recent'}
							<svg class="pin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>
							<span class="q">{item.q}</span>
						{:else if item.kind === 'book'}
							<span lang="ta">{item.book.name_ta}</span> <span class="en">{item.book.name_en}</span>
						{:else}
							{@const ta = entityLabelTa(item.place)}
							<svg class="pin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
								{#if item.place.type === 'place'}<path d="M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/>
								{:else if item.place.type === 'person'}<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>
								{:else}<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21.5z"/><path d="M4 19a2.5 2.5 0 0 1 2.5-2.5H20"/>{/if}
							</svg>
							{#if ta}<span lang="ta">{ta}</span>{/if} <span class="en">{item.place.name_en}</span>
							<span class="kind" lang={lang}>{entityKind(item.place.type, lang)}</span>
						{/if}
					</button>
				</li>
			{/each}
		</ul>
	{/if}
	{#if notFound}
		<p class="hint" role="status">{lang === 'ta' ? 'எ.கா. யோவா 3:16' : 'e.g. John 3:16'}</p>
	{/if}
</form>

<style>
	.refbox { position: relative; }
	.icon { position: absolute; left: 1rem; top: 50%; transform: translateY(-50%); color: var(--muted); pointer-events: none; }
	input { min-height: 46px; padding: 0.7rem 4.4rem 0.7rem 2.7rem; border-radius: 14px; font-size: 0.95rem; }
	input::-webkit-search-cancel-button { -webkit-appearance: none; }
	input[aria-invalid='true'] { border-color: var(--amber); }
	.kbd { position: absolute; right: 0.8rem; top: 50%; transform: translateY(-50%); font: 600 0.68rem var(--sans); color: var(--muted); border: 1px solid var(--line); border-radius: var(--r-s); padding: 2px 7px; pointer-events: none; }
	.suggest { position: absolute; z-index: 10; left: 0; right: 0; top: calc(100% + 6px); margin: 0; padding: 6px; list-style: none; background: var(--surface); border: var(--bw) solid var(--line-2); border-radius: 14px; box-shadow: var(--shadow); }
	.suggest button { display: flex; gap: 0.6rem; align-items: baseline; width: 100%; padding: 0.55rem 0.75rem; border: 0; background: none; color: inherit; font: inherit; text-align: left; border-radius: var(--r-s); cursor: pointer; }
	.suggest li.active button, .suggest button:hover { background: var(--accent-soft); }
	.suggest .en { color: var(--muted); font-size: 0.85em; }
	.suggest [lang='ta'] { font-family: var(--tamil); font-weight: 600; }
	.suggest .pin { color: var(--accent); align-self: center; flex: none; }
	.suggest .q { font-family: var(--tamil), var(--sans); }
	.suggest .group { display: flex; align-items: center; justify-content: space-between; padding: 0.25rem 0.75rem 0.1rem; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); }
	.suggest .group [lang='ta'] { font-family: var(--tamil); letter-spacing: 0.02em; text-transform: none; font-weight: 600; }
	.suggest .group .clear { width: auto; padding: 0.2rem 0.4rem; font-size: 0.75rem; font-weight: 600; color: var(--accent); text-transform: none; letter-spacing: 0; }
	.suggest .kind { margin-left: auto; font-size: 0.7rem; color: var(--muted); border: 1px solid var(--line); border-radius: 999px; padding: 0 0.45rem; font-weight: 500; }
	.hint { position: absolute; margin: 4px 0 0 1rem; font-size: 0.8rem; color: var(--amber); }
	@media (max-width: 720px) {
		.kbd { display: none; }
		input { padding-right: 1rem; }
	}
</style>
