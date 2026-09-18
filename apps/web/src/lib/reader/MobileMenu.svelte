<script lang="ts">
	// The phone chapter menu (design 10A): opened from the chapter pill in the
	// one-row header. Book, chapter and version tabs, with language, sign-in and
	// settings in its footer row so they no longer take header space.
	import { tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { chapterUrl, manifest } from '$lib/content/manifest';
	import type { Book, VersionMeta } from '$lib/content/types';
	import { settings } from '$lib/settings/store.svelte';
	import { session } from '$lib/supabase/session.svelte';

	let {
		open = $bindable(false),
		lang,
		book,
		chapter,
		versions,
		versionPath,
		signinHref,
		top,
		onsettings
	}: {
		open?: boolean;
		lang: 'ta' | 'en';
		book?: Book;
		chapter?: number;
		/** The versions of the chapter being read, primary first. */
		versions?: VersionMeta[];
		versionPath: string;
		signinHref: string;
		/** Distance from the top of the viewport, below the header. */
		top: number;
		onsettings: () => void;
	} = $props();

	const ta = $derived(lang === 'ta');
	type Tab = 'book' | 'chapter' | 'version';
	let tab = $state<Tab>('book');
	// The book whose chapters the chapter tab shows: the one being read until another is tapped.
	let picked = $state<Book | undefined>(undefined);
	let grid: HTMLDivElement | undefined = $state();

	const primaryCode = $derived((versions?.[0]?.code ?? versionPath.split('+')[0]).toUpperCase());
	const primaryMeta = $derived(manifest.versions.find((v) => v.code === primaryCode) ?? manifest.versions[0]);
	const secondary = $derived(versions?.[1]?.code ?? '');
	const chaptersBook = $derived(picked ?? book);
	const ot = manifest.books.filter((b) => b.testament === 'OT');
	const nt = manifest.books.filter((b) => b.testament === 'NT');

	$effect(() => {
		if (!open) return;
		picked = book;
		tab = 'book';
		void tick().then(() => {
			const el = grid?.querySelector<HTMLElement>('[aria-current="page"]');
			if (grid && el) grid.scrollTop = Math.max(0, el.offsetTop - grid.clientHeight / 3);
		});
	});

	function close() {
		open = false;
	}
	function pickBook(b: Book) {
		picked = b;
		tab = 'chapter';
	}
	function pickVersion(code: string) {
		const b = book ?? chaptersBook;
		if (!b) {
			settings.update({ version: code.toLowerCase() });
			close();
			return;
		}
		const rest = (versions ?? []).slice(1).map((v) => v.code).filter((v) => v !== code);
		close();
		goto(chapterUrl([code, ...rest].map((x) => x.toLowerCase()).join('+'), b, chapter));
	}
	function pickCompare(code: string) {
		if (!book) return;
		close();
		goto(chapterUrl((code ? [primaryCode, code] : [primaryCode]).map((x) => x.toLowerCase()).join('+'), book, chapter));
	}
	function onKey(e: KeyboardEvent) {
		if (open && e.key === 'Escape') close();
	}
	const name = (b: Book) => (ta ? b.name_ta : b.name_en);
</script>

<svelte:window onkeydown={onKey} />

{#if open}
	<button type="button" class="scrim" aria-label={ta ? 'மூடு' : 'Close'} onclick={close}></button>
	<div class="menu" role="dialog" aria-label={ta ? 'புத்தகம், அதிகாரம், மொழிபெயர்ப்பு' : 'Book, chapter and version'} style="--top: {top}px">
		<div class="tabs" role="tablist">
			<button type="button" role="tab" aria-selected={tab === 'book'} class:on={tab === 'book'} lang="ta" onclick={() => (tab = 'book')}>{ta ? 'புத்தகம்' : 'Book'}</button>
			<button type="button" role="tab" aria-selected={tab === 'chapter'} class:on={tab === 'chapter'} disabled={!chaptersBook} onclick={() => (tab = 'chapter')}>{ta ? 'அதிகாரம்' : 'Chapter'}</button>
			<button type="button" role="tab" aria-selected={tab === 'version'} class:on={tab === 'version'} class="ver" onclick={() => (tab = 'version')}>{primaryMeta.short}</button>
		</div>

		<div class="body" bind:this={grid}>
			{#if tab === 'book'}
				{#each [[ot, ta ? 'பழைய ஏற்பாடு' : 'Old Testament'], [nt, ta ? 'புதிய ஏற்பாடு' : 'New Testament']] as [list, label] (label)}
					<p class="group">{label}</p>
					<div class="books">
						{#each list as Book[] as b (b.code)}
							<button type="button" class="cell" lang={ta ? 'ta' : 'en'} class:current={b.code === chaptersBook?.code} aria-current={b.code === book?.code ? 'page' : undefined} disabled={!primaryMeta.books.includes(b.code)} onclick={() => pickBook(b)}>{name(b)}</button>
						{/each}
					</div>
				{/each}
			{:else if tab === 'chapter' && chaptersBook}
				<p class="group" lang={ta ? 'ta' : 'en'}>{name(chaptersBook)}</p>
				<div class="chapters">
					{#each Array.from({ length: chaptersBook.chapters }, (_, i) => i + 1) as c (c)}
						{@const here = chaptersBook.code === book?.code && c === chapter}
						<a class="cell num" class:current={here} aria-current={here ? 'page' : undefined} href={chapterUrl(versionPath, chaptersBook, c)} onclick={close}>{c}</a>
					{/each}
				</div>
			{:else}
				<p class="group">{ta ? 'மொழிபெயர்ப்பு' : 'Version'}</p>
				<div class="versions">
					{#each manifest.versions as v (v.code)}
						<button type="button" class="cell ver-row" class:current={v.code === primaryCode} disabled={!!book && !v.books.includes(book.code)} onclick={() => pickVersion(v.code)}>
							<strong>{v.short}</strong> <span lang={v.lang}>{v.name_native}</span>
						</button>
					{/each}
				</div>
				{#if book}
					<p class="group">{ta ? 'ஒப்பிடு' : 'Compare with'}</p>
					<div class="versions">
						<button type="button" class="cell ver-row" class:current={!secondary} onclick={() => pickCompare('')}>{ta ? 'ஒப்பீடு இல்லை' : 'No comparison'}</button>
						{#each manifest.versions.filter((v) => v.code !== primaryCode) as v (v.code)}
							<button type="button" class="cell ver-row" class:current={v.code === secondary} disabled={!v.books.includes(book.code)} onclick={() => pickCompare(v.code)}>
								<strong>{v.short}</strong> <span lang={v.lang}>{v.name_native}</span>
							</button>
						{/each}
					</div>
				{/if}
			{/if}
		</div>

		<div class="foot">
			<div class="lang" role="group" aria-label={ta ? 'இடைமுக மொழி' : 'Interface language'}>
				<button type="button" lang="ta" class:on={ta} aria-pressed={ta} onclick={() => settings.update({ uiLang: 'ta' })}>த</button>
				<button type="button" lang="en" class:on={!ta} aria-pressed={!ta} onclick={() => settings.update({ uiLang: 'en' })}>EN</button>
			</div>
			{#if session.ready && session.signedIn}
				<a class="wide-btn" href="/me/account" onclick={close}>{ta ? 'கணக்கு' : 'Account'}</a>
			{:else}
				<a class="wide-btn" href={signinHref} onclick={close}>{ta ? 'உள்நுழை' : 'Sign in'}</a>
			{/if}
			<button type="button" class="gear" aria-label={ta ? 'அமைப்புகள்' : 'Settings'} onclick={() => { close(); onsettings(); }}>
				<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg>
			</button>
		</div>
		{#if session.ready && session.signedIn}
			<nav class="mine" aria-label={ta ? 'என் பக்கங்கள்' : 'My pages'}>
				<a href="/me/history" onclick={close}>{ta ? 'வரலாறு' : 'History'}</a>
				<a href="/me/highlights" onclick={close}>{ta ? 'அடிக்கோடுகள்' : 'Highlights'}</a>
				<a href="/me/notes" onclick={close}>{ta ? 'குறிப்புகள்' : 'Notes'}</a>
				<button type="button" onclick={() => { close(); session.signOut(); }}>{ta ? 'வெளியேறு' : 'Sign out'}</button>
			</nav>
		{/if}
	</div>
{/if}

<style>
	/* The page stays visible but dimmed behind the menu, as in the design. */
	.scrim { position: fixed; inset: 0; z-index: 18; border: 0; padding: 0; background: color-mix(in srgb, var(--bg) 62%, transparent); cursor: default; }
	.menu { position: fixed; z-index: 19; left: 12px; right: 12px; top: calc(var(--top) + 8px); max-height: calc(100dvh - var(--top) - 24px); display: flex; flex-direction: column; gap: 14px; padding: 16px; background: var(--surface); border: var(--bw) solid var(--line-2); border-radius: var(--r-2xl); box-shadow: var(--shadow-lg); }
	.tabs { display: flex; gap: 8px; flex: none; }
	.tabs button { flex: 1; height: 48px; border-radius: 14px; border: var(--bw) solid var(--line-2); background: none; color: var(--ink-2); font-family: var(--tamil); font-size: 1rem; font-weight: 600; cursor: pointer; }
	.tabs button.ver { font-family: var(--sans); font-size: 0.94rem; font-weight: 700; }
	.tabs button.on { background: var(--accent); border-color: var(--accent); color: var(--on-accent); }
	.tabs button:disabled { opacity: 0.45; cursor: default; }
	.body { position: relative; overflow-y: auto; min-height: 0; overscroll-behavior: contain; scrollbar-width: none; display: grid; gap: 8px; align-content: start; }
	.group { margin: 6px 0 0; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); font-family: var(--tamil); }
	.group:first-child { margin-top: 0; }
	.books { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
	.chapters { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px; }
	.versions { display: grid; gap: 8px; }
	.cell { min-height: 50px; border-radius: 12px; border: var(--bw) solid var(--line-2); background: none; color: var(--ink); display: flex; align-items: center; justify-content: center; padding: 0 6px; font-family: var(--tamil); font-size: 1.02rem; text-align: center; text-decoration: none; cursor: pointer; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.cell[lang='en'] { font-family: var(--sans); font-size: 0.92rem; }
	.cell.num { font-family: var(--sans); font-variant-numeric: tabular-nums; font-size: 1rem; }
	.cell.current { background: var(--accent-soft); border-color: var(--accent); font-weight: 600; }
	.cell:disabled { opacity: 0.4; cursor: default; }
	.ver-row { justify-content: flex-start; gap: 0.6rem; padding: 0 14px; font-family: var(--sans); font-size: 0.95rem; }
	.ver-row strong { color: var(--accent); font-size: 0.8rem; letter-spacing: 0.06em; }
	.ver-row [lang='ta'] { font-family: var(--tamil); }
	.foot { display: flex; align-items: center; gap: 10px; padding-top: 14px; border-top: var(--bw) solid var(--line-2); flex: none; }
	.lang { display: flex; border: var(--bw) solid var(--line-2); border-radius: 12px; overflow: hidden; flex: none; }
	.lang button { border: 0; padding: 0 14px; height: 44px; background: none; color: var(--ink-2); font-weight: 600; font-size: 0.88rem; cursor: pointer; }
	.lang button[lang='ta'] { font-family: var(--tamil); font-size: 1rem; }
	.lang button.on { background: var(--accent); color: var(--on-accent); }
	.wide-btn { flex: 1; height: 44px; border-radius: 12px; border: var(--bw) solid var(--line-2); display: flex; align-items: center; justify-content: center; font-family: var(--tamil); font-size: 1rem; font-weight: 600; color: var(--ink); text-decoration: none; }
	.gear { width: 44px; height: 44px; border-radius: 12px; border: var(--bw) solid var(--line-2); background: none; color: var(--ink-2); display: flex; align-items: center; justify-content: center; cursor: pointer; flex: none; }
	.mine { display: flex; flex-wrap: wrap; gap: 6px 14px; flex: none; font-family: var(--tamil); font-size: 0.92rem; }
	.mine a, .mine button { color: var(--accent); text-decoration: none; border: 0; background: none; padding: 4px 0; font: inherit; font-weight: 600; cursor: pointer; }
	.cell:focus-visible, .tabs button:focus-visible, .lang button:focus-visible, .wide-btn:focus-visible, .gear:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
</style>
