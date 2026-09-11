<script lang="ts">
	// Permanent book rail for wide screens (design 3A): OT/NT switch, every
	// book as a row, and the current book expanded into an inline chapter grid
	// so moving anywhere in the Bible costs no page change first.
	import { chapterUrl, manifest } from '$lib/content/manifest';
	import type { Book, VersionMeta } from '$lib/content/types';

	let {
		versions,
		book,
		chapter,
		lang
	}: { versions: VersionMeta[]; book: Book; chapter?: number; lang: 'ta' | 'en' } = $props();

	const ta = $derived(lang === 'ta');
	const versionPath = $derived(versions.map((v) => v.code.toLowerCase()).join('+'));
	const available = $derived(new Set(versions[0].books));
	const ot = manifest.books.filter((b) => b.testament === 'OT');
	const nt = manifest.books.filter((b) => b.testament === 'NT');

	// Start on the current book so the server render already shows it expanded,
	// then follow the page: switch testament and expand the book on navigation.
	// svelte-ignore state_referenced_locally
	let testament = $state<'OT' | 'NT'>(book.testament);
	// svelte-ignore state_referenced_locally
	let expanded = $state(book.code);
	let list: HTMLDivElement | undefined = $state();
	$effect(() => {
		testament = book.testament;
		expanded = book.code;
	});
	$effect(() => {
		// Keep the current book in view inside the rail without scrolling the page.
		void expanded;
		const el = list?.querySelector<HTMLElement>(`[data-book="${book.code}"]`);
		if (list && el) list.scrollTop = Math.max(0, el.offsetTop - list.clientHeight / 3);
	});
	const books = $derived(testament === 'OT' ? ot : nt);
</script>

<nav class="rail" aria-label={ta ? 'புத்தகங்கள்' : 'Books'}>
	<div class="seg" role="tablist" aria-label={ta ? 'ஏற்பாடு' : 'Testament'}>
		<button type="button" role="tab" aria-selected={testament === 'OT'} class:on={testament === 'OT'} onclick={() => (testament = 'OT')}><span lang="ta">பழைய</span> <span class="short">OT</span></button>
		<button type="button" role="tab" aria-selected={testament === 'NT'} class:on={testament === 'NT'} onclick={() => (testament = 'NT')}><span lang="ta">புதிய</span> <span class="short">NT</span></button>
	</div>
	<div class="list" bind:this={list}>
		{#each books as b (b.code)}
			{@const current = b.code === book.code}
			{@const open = expanded === b.code}
			<div class="book" data-book={b.code}>
				<button type="button" class="row" class:current aria-expanded={open} aria-current={current ? 'page' : undefined} disabled={!available.has(b.code)} onclick={() => (expanded = open ? '' : b.code)}>
					<span class="name" lang={ta ? 'ta' : 'en'}>{ta ? b.name_ta : b.name_en}</span>
					<span class="alt" lang={ta ? 'en' : 'ta'}>{ta ? b.name_en : b.name_ta}</span>
				</button>
				{#if open}
					<ol class="grid" aria-label={ta ? `${b.name_ta} அதிகாரங்கள்` : `${b.name_en} chapters`}>
						{#each Array.from({ length: b.chapters }, (_, i) => i + 1) as c (c)}
							<li><a href={chapterUrl(versionPath, b, c)} class:on={current && c === chapter} aria-current={current && c === chapter ? 'page' : undefined}>{c}</a></li>
						{/each}
					</ol>
				{/if}
			</div>
		{/each}
	</div>
</nav>

<style>
	.rail { display: flex; flex-direction: column; height: 100%; background: var(--rail); border-right: var(--bw) solid var(--line); }
	.seg { display: flex; gap: 0.35rem; padding: 1rem; border-bottom: var(--bw) solid var(--line); flex: none; }
	.seg button { flex: 1; border: 0; border-radius: 10px; padding: 0.55rem 0.3rem; background: transparent; color: var(--muted); font-weight: 600; font-size: 0.82rem; cursor: pointer; min-height: 40px; }
	.seg button [lang='ta'] { font-family: var(--tamil); }
	.seg button .short { font-weight: 500; }
	.seg button.on { background: var(--surface); color: var(--ink); box-shadow: 0 1px 2px rgba(28, 26, 24, 0.08); }
	.list { flex: 1; overflow-y: auto; padding: 0.5rem 0.6rem 1.5rem; position: relative; scrollbar-width: thin; }
	.row { display: flex; align-items: baseline; justify-content: space-between; gap: 0.6rem; width: 100%; padding: 0.65rem 0.85rem; border: 0; border-radius: 10px; background: transparent; color: var(--ink); text-align: left; cursor: pointer; }
	.row:hover { background: var(--surface); }
	.row:disabled { opacity: 0.4; cursor: default; }
	.row .name { font-size: 1rem; line-height: 1.3; }
	.row .name[lang='ta'] { font-family: var(--tamil); }
	.row .alt { font-size: 0.72rem; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
	.row .alt[lang='ta'] { font-family: var(--tamil); }
	.row.current { background: var(--accent); color: var(--on-accent); }
	.row.current .name { font-weight: 600; }
	.row.current .alt { color: var(--on-accent); opacity: 0.8; }
	.grid { list-style: none; margin: 0; padding: 0.6rem 0.85rem 0.9rem; display: grid; grid-template-columns: repeat(6, 1fr); gap: 0.35rem; }
	.grid a { display: block; text-align: center; padding: 0.4rem 0; border-radius: var(--r-s); background: var(--surface); border: 1px solid var(--line); color: var(--ink-2); font-size: 0.8rem; text-decoration: none; font-variant-numeric: tabular-nums; }
	.grid a:hover { border-color: var(--accent); color: var(--accent); }
	.grid a.on { background: var(--accent); border-color: var(--accent); color: var(--on-accent); font-weight: 700; }
</style>
