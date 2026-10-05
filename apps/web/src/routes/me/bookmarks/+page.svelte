<script lang="ts">
	import { onMount } from 'svelte';
	import { chapterUrl, findBook } from '$lib/content/manifest';
	import { allBookmarks, deleteBookmark, type Bookmark } from '$lib/personal/repo';
	import { settings } from '$lib/settings/store.svelte';

	const ta = $derived(settings.value.uiLang === 'ta');
	let items = $state<Bookmark[]>([]);
	let loading = $state(true);

	onMount(async () => {
		try { items = (await allBookmarks()).filter((b) => findBook(b.book)); } finally { loading = false; }
	});

	function label(b: Bookmark) {
		const book = findBook(b.book)!;
		return `${ta ? book.name_ta : book.name_en} ${b.chapter}:${b.verse}`;
	}
	// Opened in the version it was made in when that is known, else the reader's own.
	const href = (b: Bookmark) => chapterUrl((b.version || settings.value.version).toLowerCase(), findBook(b.book)!, b.chapter, `${b.verse}`);
	async function remove(b: Bookmark) {
		items = items.filter((x) => x.id !== b.id);
		await deleteBookmark(b.id).catch(() => {});
	}
</script>

<svelte:head><title>{ta ? 'குறிகள்' : 'Bookmarks'} · Tamil Scripture</title></svelte:head>

<h1>{ta ? 'குறிகள்' : 'Bookmarks'} <span class="n">{items.length}</span></h1>

{#if loading}
	<p class="muted">…</p>
{:else if !items.length}
	<p class="muted">{ta ? 'குறிகள் இல்லை. வசன எண்ணைத் தொட்டு “குறி” அழுத்துங்கள்.' : 'No bookmarks yet. Tap a verse number and choose Bookmark.'}</p>
{:else}
	<ul>
		{#each items as b (b.id)}
			<li>
				<a class="ref" href={href(b)} lang={ta ? 'ta' : 'en'}>{label(b)}</a>
				<time datetime={b.created_at}>{new Date(b.created_at).toLocaleDateString(ta ? 'ta-IN' : 'en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</time>
				<button type="button" class="ghost" onclick={() => remove(b)} aria-label={ta ? 'குறியை நீக்கு' : 'Remove bookmark'}>✕</button>
			</li>
		{/each}
	</ul>
{/if}

<style>
	h1 { font-family: var(--tamil); font-size: 1.5rem; margin: 0 0 1rem; }
	h1 .n { color: var(--muted); font-size: 1rem; font-weight: 400; }
	ul { list-style: none; padding: 0; margin: 0; max-width: 42rem; }
	li { padding: 0.6rem 0; border-top: 1px solid var(--line); display: flex; align-items: center; gap: 1rem; }
	.ref { font-family: var(--tamil); text-decoration: none; font-weight: 600; flex: 1; }
	time { color: var(--muted); font-size: 0.85rem; }
	.ghost { border: 0; background: none; color: var(--muted); min-width: 40px; min-height: 40px; border-radius: 999px; cursor: pointer; }
	.ghost:hover { background: var(--surface-2); color: var(--ink); }
	.muted { color: var(--muted); }
</style>
