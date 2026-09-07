<script lang="ts">
	import { onMount } from 'svelte';
	import { chapterUrl, findBook } from '$lib/content/manifest';
	import { allNotes, type Note } from '$lib/personal/repo';
	import { settings } from '$lib/settings/store.svelte';

	const ta = $derived(settings.value.uiLang === 'ta');
	let items = $state<Note[]>([]);
	let q = $state('');
	let loading = $state(true);
	let timer: ReturnType<typeof setTimeout> | undefined;

	async function load() { try { items = await allNotes(q); } finally { loading = false; } }
	onMount(load);
	function onInput() { clearTimeout(timer); timer = setTimeout(load, 400); }

	function label(n: Note) {
		const b = findBook(n.book)!;
		return `${ta ? b.name_ta : b.name_en} ${n.chapter}:${n.verse_start}${n.verse_end !== n.verse_start ? `-${n.verse_end}` : ''}`;
	}
	function href(n: Note) {
		return chapterUrl(settings.value.version, findBook(n.book)!, n.chapter, n.verse_end !== n.verse_start ? `${n.verse_start}-${n.verse_end}` : `${n.verse_start}`);
	}
</script>

<svelte:head><title>{ta ? 'குறிப்புகள்' : 'Notes'} · Tamil Scripture</title></svelte:head>

<div class="head">
	<h1>{ta ? 'குறிப்புகள்' : 'Notes'} <span class="n">{items.length}</span></h1>
	<input type="search" bind:value={q} oninput={onInput} placeholder={ta ? 'குறிப்புகளில் தேடு' : 'Search notes'} aria-label={ta ? 'குறிப்புகளில் தேடு' : 'Search notes'} />
</div>

{#if loading}
	<p class="muted">…</p>
{:else if !items.length}
	<p class="muted">{q ? (ta ? 'பொருந்தும் குறிப்புகள் இல்லை.' : 'No matching notes.') : (ta ? 'குறிப்புகள் இல்லை. வசன எண்ணைத் தொட்டு “குறிப்பு” அழுத்துங்கள்.' : 'No notes yet. Tap a verse number and choose Note.')}</p>
{:else}
	<ul>
		{#each items as n (n.id)}
			<li>
				<a class="ref" href={href(n)} lang={ta ? 'ta' : 'en'}>{label(n)}</a>
				<time datetime={n.updated_at}>{new Date(n.updated_at).toLocaleDateString(ta ? 'ta-IN' : 'en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</time>
				<p lang={ta ? 'ta' : 'en'}>{n.body}</p>
			</li>
		{/each}
	</ul>
{/if}

<style>
	.head { display: flex; flex-wrap: wrap; gap: 1rem; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
	h1 { font-family: var(--tamil); font-size: 1.5rem; margin: 0; }
	h1 .n { color: var(--muted); font-size: 1rem; font-weight: 400; }
	input { font: inherit; font-family: var(--tamil); padding: 0.5rem 0.8rem; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); color: inherit; min-width: 14rem; }
	ul { list-style: none; padding: 0; margin: 0; max-width: 42rem; }
	li { padding: 0.8rem 0; border-top: 1px solid var(--line); display: grid; grid-template-columns: 1fr auto; gap: 0.2rem 1rem; }
	.ref { font-family: var(--tamil); text-decoration: none; font-weight: 600; }
	time { color: var(--muted); font-size: 0.85rem; }
	li p { grid-column: 1 / -1; margin: 0; white-space: pre-wrap; font-family: var(--tamil); line-height: 1.7; }
	.muted { color: var(--muted); }
</style>
