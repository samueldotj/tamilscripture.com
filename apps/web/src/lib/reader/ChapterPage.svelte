<script lang="ts">
	import { afterNavigate, goto } from '$app/navigation';
	import Chapter from './Chapter.svelte';
	import ActionBar from './ActionBar.svelte';
	import Picker from './Picker.svelte';
	import { chapterUrl, findBook } from '$lib/content/manifest';
	import type { ChapterPageData } from '$lib/content/chapter-load';
	import { settings } from '$lib/settings/store.svelte';

	let { data }: { data: ChapterPageData } = $props();

	const primary = $derived(data.versions[0]);
	const ui = $derived(settings.value.uiLang);
	const isTamil = $derived(ui === 'ta');
	const bookName = $derived(primary.lang === 'ta' ? data.book.name_ta : data.book.name_en);
	const versionPath = $derived(data.versions.map((v) => v.code.toLowerCase()).join('+'));
	const rangeLabel = $derived(
		data.range ? `${data.range.start}${data.range.end !== data.range.start ? `-${data.range.end}` : ''}` : ''
	);
	const title = $derived(`${bookName} ${data.chapter}${rangeLabel ? `:${rangeLabel}` : ''} · ${primary.short}`);

	// Description: the selected verses if any, else the chapter opening.
	const description = $derived.by(() => {
		const segs = data.chapters[0].blocks.flatMap((b) => (b.type === 'para' ? b.segments : []));
		const picked = data.range
			? segs.filter((s) => {
					const n = Number(s.id?.split('.')[2]);
					return n >= data.range!.start && n <= data.range!.end;
				})
			: segs;
		return picked.map((s) => s.text).join(' ').slice(0, 200);
	});

	const prev = $derived(data.chapters[0].prev);
	const next = $derived(data.chapters[0].next);
	function navUrl(ref: { book: string; chapter: number } | null) {
		if (!ref) return null;
		const b = findBook(ref.book);
		return b ? chapterUrl(versionPath, b, ref.chapter) : null;
	}
	const testamentName = $derived(
		data.book.testament === 'OT'
			? isTamil ? 'பழைய ஏற்பாடு' : 'Old Testament'
			: isTamil ? 'புதிய ஏற்பாடு' : 'New Testament'
	);

	// Selection: starts from the URL range (resolving bridges), then follows taps.
	function idsFromRange(): Set<string> {
		const ids = new Set<string>();
		if (!data.range) return ids;
		const bridges = data.chapters[0].bridges ?? {};
		for (let v = data.range.start; v <= data.range.end; v++) {
			const id = `${data.book.code}.${data.chapter}.${v}`;
			ids.add(bridges[id] ?? id);
		}
		return ids;
	}
	let selected = $state<Set<string>>(new Set());
	$effect(() => {
		// Reset when the passage changes.
		void data.canonical;
		selected = idsFromRange();
	});
	function toggle(id: string) {
		const s = new Set(selected);
		if (s.has(id)) s.delete(id); else s.add(id);
		selected = s;
	}

	afterNavigate(() => {
		if (!data.range) return;
		const first = document.getElementById(`${data.book.code}.${data.chapter}.${data.range.start}`)
			?? document.querySelector(`[data-verse="${[...idsFromRange()][0]}"]`);
		first?.scrollIntoView({ block: 'start' });
	});

	// Swipe between chapters on touch screens; arrow keys on desktop.
	let touchX = 0, touchY = 0;
	function touchStart(e: TouchEvent) { touchX = e.touches[0].clientX; touchY = e.touches[0].clientY; }
	function touchEnd(e: TouchEvent) {
		const dx = e.changedTouches[0].clientX - touchX;
		const dy = e.changedTouches[0].clientY - touchY;
		if (Math.abs(dx) > 70 && Math.abs(dy) < 50) {
			const target = dx < 0 ? navUrl(next) : navUrl(prev);
			if (target) goto(target);
		}
	}
	function onKey(e: KeyboardEvent) {
		const t = e.target as HTMLElement | null;
		if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT')) return;
		if (e.key === 'ArrowRight' && navUrl(next)) goto(navUrl(next)!);
		else if (e.key === 'ArrowLeft' && navUrl(prev)) goto(navUrl(prev)!);
		else if (e.key === 'Escape' && selected.size) selected = new Set();
	}
</script>

<svelte:window onkeydown={onKey} />

<svelte:head>
	<title>{title} · Tamil Scripture</title>
	<meta name="description" content={description} />
	<link rel="canonical" href={`https://www.tamilscripture.com${data.canonical}`} />
	<meta property="og:title" content={title} />
	<meta property="og:description" content={description} />
	<meta property="og:type" content="article" />
	<meta property="og:url" content={`https://www.tamilscripture.com${data.canonical}`} />
	{@html `<script type="application/ld+json">${JSON.stringify({
		'@context': 'https://schema.org',
		'@type': 'BreadcrumbList',
		itemListElement: [
			{ '@type': 'ListItem', position: 1, name: 'Bible', item: 'https://www.tamilscripture.com/' },
			{ '@type': 'ListItem', position: 2, name: data.book.name_en, item: `https://www.tamilscripture.com${chapterUrl(versionPath, data.book)}` },
			{ '@type': 'ListItem', position: 3, name: `${data.book.name_en} ${data.chapter}`, item: `https://www.tamilscripture.com${chapterUrl(versionPath, data.book, data.chapter)}` }
		]
	})}</script>`}
</svelte:head>

<!-- svelte-ignore a11y_no_static_element_interactions -- swipe is a shortcut for the prev/next links below -->
<div class="reader" ontouchstart={touchStart} ontouchend={touchEnd}>
	<nav class="crumbs" aria-label="Breadcrumb">
		<a href="/">Bible</a>
		<span aria-hidden="true">›</span>
		<span>{testamentName}</span>
		<span aria-hidden="true">›</span>
		<a href={chapterUrl(versionPath, data.book)}>{bookName}</a>
		<span aria-hidden="true">›</span>
		{#if data.range}
			<a href={chapterUrl(versionPath, data.book, data.chapter)}>{data.chapter}</a>
			<span aria-hidden="true">›</span>
			<span aria-current="page">{rangeLabel}</span>
		{:else}
			<span aria-current="page">{data.chapter}</span>
		{/if}
	</nav>

	<div class="pager">
		{#if navUrl(prev)}<a href={navUrl(prev)} rel="prev">‹ {isTamil ? 'முந்தைய' : 'Previous'}</a>{:else}<span></span>{/if}
		<Picker versions={data.versions} book={data.book} chapter={data.chapter} lang={ui} />
		{#if navUrl(next)}<a href={navUrl(next)} rel="next">{isTamil ? 'அடுத்த' : 'Next'} ›</a>{:else}<span></span>{/if}
	</div>

	<h1 lang={primary.lang}>{bookName} {data.chapter}</h1>

	{#if data.chapters.length === 1}
		<Chapter chapter={data.chapters[0]} lang={primary.lang} {selected} onselect={toggle} />
	{:else}
		<div class="dual">
			{#each data.chapters as ch, i (ch.version)}
				<section aria-label={data.versions[i].name}>
					<h2 class="version-head">{data.versions[i].short}</h2>
					<Chapter chapter={ch} lang={data.versions[i].lang} {selected} onselect={toggle} />
				</section>
			{/each}
		</div>
	{/if}

	<div class="pager bottom">
		{#if navUrl(prev)}<a href={navUrl(prev)} rel="prev">‹ {isTamil ? 'முந்தைய' : 'Previous'}</a>{:else}<span></span>{/if}
		<span></span>
		{#if navUrl(next)}<a href={navUrl(next)} rel="next">{isTamil ? 'அடுத்த' : 'Next'} ›</a>{:else}<span></span>{/if}
	</div>

	<footer class="attribution">
		{#each data.versions as v (v.code)}
			<p><a href={v.source_url} rel="license">{v.attribution}</a></p>
		{/each}
	</footer>
</div>

<ActionBar {selected} chapter={data.chapters[0]} book={data.book} {versionPath} versionShort={primary.short} lang={ui} onclear={() => (selected = new Set())} />

<style>
	.crumbs { display: flex; gap: 0.5rem; flex-wrap: wrap; font-size: 0.9rem; color: var(--muted); margin: 0 0 1rem; }
	.crumbs a { color: inherit; }
	.pager { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 1rem; margin: 0 0 1rem; }
	.pager a:last-child { text-align: right; }
	.pager.bottom { margin-top: 2rem; }
	h1 { font-family: var(--serif); font-weight: 600; font-size: 1.8rem; margin: 0 0 1rem; }
	h1[lang='ta'] { font-family: var(--tamil); }
	.dual { display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; }
	@media (max-width: 720px) { .dual { grid-template-columns: 1fr; } }
	.version-head { font-size: 0.8rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); margin: 0 0 0.5rem; }
	.attribution { margin-top: 3rem; font-size: 0.8rem; color: var(--muted); border-top: 1px solid var(--line); padding-top: 1rem; }
	.attribution a { color: inherit; }
</style>
