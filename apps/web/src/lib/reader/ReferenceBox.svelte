<script lang="ts">
	import { goto } from '$app/navigation';
	import { ready, referencePath, suggestBooks } from '$lib/ref/client';
	import type { BookSuggestion } from '@tamilscripture/bible-wasm';

	let { versionPath, lang = 'ta' }: { versionPath: string; lang?: 'ta' | 'en' } = $props();

	let value = $state('');
	let loaded = $state(false);
	let suggestions = $state<BookSuggestion[]>([]);
	let active = $state(-1);
	let notFound = $state(false);
	let input: HTMLInputElement;

	async function ensure() {
		if (!loaded) {
			await ready();
			loaded = true;
		}
	}

	async function onInput() {
		notFound = false;
		await ensure();
		// Suggest books only while the user is still typing letters.
		const bookPart = value.replace(/^\s*[1-3]\s*/, '').split(/\d/)[0].trim();
		suggestions = bookPart.length >= 1 && !/\d/.test(value) ? suggestBooks(value, 6) : [];
		active = -1;
	}

	async function submit(text = value) {
		const trimmed = text.trim();
		if (!trimmed) return;
		await ensure();
		const path = referencePath(trimmed, versionPath);
		suggestions = [];
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

	function pick(b: BookSuggestion) {
		value = (lang === 'ta' ? b.name_ta : b.name_en) + ' ';
		suggestions = [];
		input.focus();
	}

	function onKey(e: KeyboardEvent) {
		if (e.key === 'ArrowDown' && suggestions.length) {
			e.preventDefault();
			active = (active + 1) % suggestions.length;
		} else if (e.key === 'ArrowUp' && suggestions.length) {
			e.preventDefault();
			active = (active - 1 + suggestions.length) % suggestions.length;
		} else if (e.key === 'Enter') {
			e.preventDefault();
			if (active >= 0) pick(suggestions[active]);
			else submit();
		} else if (e.key === 'Escape') {
			suggestions = [];
			input.blur();
		}
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
		aria-label={lang === 'ta' ? 'வசனம் அல்லது சொல் தேடு' : 'Go to a reference or search a word'}
		aria-invalid={notFound}
		placeholder={lang === 'ta' ? 'யோவான் 3:16 · புத்தகம், வசனம், சொல்' : 'John 3:16 · book, verse, word'}
		onfocus={ensure}
		oninput={onInput}
		onkeydown={onKey}
		onblur={() => setTimeout(() => (suggestions = []), 150)}
	/>
	<kbd class="kbd" aria-hidden="true">Ctrl K</kbd>
	{#if suggestions.length}
		<ul class="suggest" role="listbox">
			{#each suggestions as b, i (b.code)}
				<li role="option" aria-selected={i === active} class:active={i === active}>
					<button type="button" onmousedown={(e) => { e.preventDefault(); pick(b); }}>
						<span lang="ta">{b.name_ta}</span> <span class="en">{b.name_en}</span>
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
	.hint { position: absolute; margin: 4px 0 0 1rem; font-size: 0.8rem; color: var(--amber); }
	@media (max-width: 720px) {
		.kbd { display: none; }
		input { padding-right: 1rem; }
	}
</style>
