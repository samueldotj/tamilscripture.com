<script lang="ts">
	// Verse of the day beside the home page's heading: the verse in the reader's
	// version, with the other language under it.
	import { onMount } from 'svelte';
	import { bookNameIn, companionOf, findBook, findVersion, manifest, verseUrl } from '$lib/content/manifest';
	import { verseOfDay } from './daily';

	let { versionPath, ta }: { versionPath: string; ta: boolean } = $props();

	const id = verseOfDay();
	const [code, ch, v] = id.split('.');
	const book = findBook(code)!;
	const primary = $derived(findVersion(versionPath.split('+')[0]) ?? manifest.versions[0]);
	const second = $derived(companionOf(primary, book.code));
	const href = $derived(verseUrl(versionPath.split('+')[0], book, Number(ch), v));
	const date = $derived.by(() => new Date().toLocaleDateString(ta ? 'ta-IN' : 'en-GB', { day: 'numeric', month: 'long' }));

	let text = $state('');
	let other = $state('');
	let copied = $state(false);

	async function textIn(code: string): Promise<string> {
		const res = await fetch(`/api/verses?${new URLSearchParams({ v: code, ids: id })}`);
		return res.ok ? (((await res.json()) as Record<string, string>)[id] ?? '') : '';
	}
	onMount(async () => {
		try {
			[text, other] = await Promise.all([textIn(primary.code), second ? textIn(second.code) : Promise.resolve('')]);
		} catch { /* offline: the card keeps its reference */ }
	});

	async function share() {
		const url = new URL(href, location.href).href;
		const title = `${bookNameIn(book, primary)} ${ch}:${v}`;
		try {
			if (navigator.share) await navigator.share({ title, text: text ? `${text} — ${title}` : title, url });
			else {
				await navigator.clipboard.writeText(url);
				copied = true;
				setTimeout(() => (copied = false), 2000);
			}
		} catch { /* dismissed */ }
	}
</script>

<aside class="votd" aria-labelledby="votd-h">
	<div class="head">
		<h2 id="votd-h" class="kicker"><span lang="ta">இன்றைய வசனம்</span> · Verse of the day</h2>
		<span class="date" lang={ta ? 'ta' : 'en'}>{date}</span>
	</div>
	{#if text}
		<p class="text" lang={primary.lang}>{text}</p>
	{:else}
		<p class="text placeholder" aria-hidden="true"></p>
	{/if}
	{#if other && second}<p class="other" lang={second.lang}>{other}</p>{/if}
	<div class="foot">
		<a class="ref" href={href} lang={primary.lang}>{bookNameIn(book, primary)} {ch}:{v} →</a>
		<button type="button" class="icon" onclick={share} aria-label={copied ? (ta ? 'இணைப்பு நகலெடுக்கப்பட்டது' : 'Link copied') : ta ? 'பகிர்' : 'Share'}>
			{#if copied}
				<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12l5 5L20 7" /></svg>
			{:else}
				<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 12v7a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-7" /><path d="M12 3v12" /><path d="M7 8l5-5 5 5" /></svg>
			{/if}
		</button>
	</div>
</aside>

<style>
	.votd { display: flex; flex-direction: column; gap: 0.6rem; padding: 1.25rem 1.4rem; border-radius: var(--r-xl); background: var(--hl); border: var(--bw) solid var(--line); min-width: 0; box-sizing: border-box; }
	.head { display: flex; justify-content: space-between; align-items: baseline; gap: 0.5rem 1rem; flex-wrap: wrap; }
	.head .kicker { margin: 0; color: var(--amber); }
	.head .kicker [lang='ta'] { font-family: var(--tamil); letter-spacing: 0.03em; text-transform: none; }
	.date { font-size: 0.82rem; color: var(--muted); }
	.date[lang='ta'] { font-family: var(--tamil); }
	.text { margin: 0; font-size: 1.22rem; line-height: 1.6; font-weight: 600; color: var(--ink); }
	.text[lang='ta'] { font-family: var(--tamil); }
	.placeholder { min-height: 3.9rem; border-radius: var(--r-s); background: linear-gradient(90deg, transparent, rgba(var(--accent-rgb), 0.06), transparent); }
	.other { margin: 0; font-size: 0.92rem; line-height: 1.6; color: var(--ink-2); }
	.other[lang='ta'] { font-family: var(--tamil); }
	.foot { display: flex; align-items: center; gap: 0.5rem; margin-top: 0.2rem; }
	.ref { flex: 1; font-weight: 600; text-decoration: none; min-height: 44px; display: flex; align-items: center; }
	.ref[lang='ta'] { font-family: var(--tamil); }
	.icon { flex: none; width: 44px; height: 44px; border-radius: var(--r); border: var(--bw) solid var(--line-2); background: var(--surface); color: var(--ink-2); display: flex; align-items: center; justify-content: center; cursor: pointer; }
	.icon:hover { border-color: var(--accent); color: var(--accent); }
</style>
