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
		await ensure();
		const path = referencePath(text, versionPath);
		if (path) {
			suggestions = [];
			value = '';
			input.blur();
			await goto(path);
		} else {
			notFound = true;
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
	<input
		bind:this={input}
		bind:value
		type="search"
		autocomplete="off"
		spellcheck="false"
		enterkeyhint="go"
		aria-label={lang === 'ta' ? 'வசனம் தேடு' : 'Go to reference'}
		aria-invalid={notFound}
		placeholder={lang === 'ta' ? 'யோவா 3:16 · John 3:16' : 'John 3:16 · யோவா 3:16'}
		onfocus={ensure}
		oninput={onInput}
		onkeydown={onKey}
		onblur={() => setTimeout(() => (suggestions = []), 150)}
	/>
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
		<p class="hint" role="status">{lang === 'ta' ? 'இது வசனக் குறிப்பாகத் தெரியவில்லை. எ.கா. யோவா 3:16' : 'Not recognised as a reference. Try John 3:16.'}</p>
	{/if}
</form>

<style>
	.refbox { position: relative; }
	input { width: 100%; font: inherit; font-family: var(--tamil); padding: 0.45rem 0.7rem; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); color: var(--ink); }
	input:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
	input[aria-invalid='true'] { border-color: var(--accent); }
	.suggest { position: absolute; z-index: 10; left: 0; right: 0; top: calc(100% + 4px); margin: 0; padding: 4px; list-style: none; background: var(--surface); border: 1px solid var(--line); border-radius: 6px; box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12); }
	.suggest button { display: flex; gap: 0.6rem; width: 100%; padding: 0.4rem 0.6rem; border: 0; background: none; color: inherit; font: inherit; text-align: left; border-radius: 4px; cursor: pointer; }
	.suggest li.active button, .suggest button:hover { background: var(--accent-soft, rgba(126, 42, 42, 0.08)); }
	.suggest .en { color: var(--muted); font-size: 0.9em; }
	.suggest [lang='ta'] { font-family: var(--tamil); }
	.hint { position: absolute; margin: 4px 0 0; font-size: 0.8rem; color: var(--accent); }
</style>
