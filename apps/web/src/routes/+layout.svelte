<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { afterNavigate } from '$app/navigation';
	import { track } from '$lib/analytics/track';
	import ReferenceBox from '$lib/reader/ReferenceBox.svelte';
	import SettingsPanel from '$lib/reader/SettingsPanel.svelte';
	import MobileMenu from '$lib/reader/MobileMenu.svelte';
	import VersePreview from '$lib/reader/VersePreview.svelte';
	import { chrome } from '$lib/chrome.svelte';
	import { goto } from '$app/navigation';
	import { tick } from 'svelte';
	import { bookNameIn, manifest } from '$lib/content/manifest';
	import { pageLang } from '$lib/content/page-lang';
	import type { Book, VersionMeta } from '$lib/content/types';
	import { settings } from '$lib/settings/store.svelte';
	import { session } from '$lib/supabase/session.svelte';
	import { dev } from '$app/environment';
	import { inject } from '@vercel/analytics';

	let { children } = $props();
	let settingsOpen = $state(false);
	let menuOpen = $state(false);
	// Header height feeds the sticky rail/panel offsets of the reader layout.
	let headerH = $state(0);
	// Chapter pages run edge to edge so the reader can lay out its own columns;
	// so does the presentation editor (design 11A) with its three columns.
	const wide = $derived((page.route.id?.includes('[chapter=int]') ?? false) || page.route.id === '/present/[slug=slug]/edit');
	// Map pages (design 9A): the map is the page, edge to edge under the header,
	// with its attribution on the map itself, so the site footer steps aside.
	const bleed = $derived(page.route.id === '/atlas/explore' || page.route.id === '/atlas/[journey=slug]');
	// The presenter (design 11A) is a screen, not a page: no header, no footer.
	const bare = $derived(page.route.id === '/present/[slug=slug]');

	// Keep the reader's current version(s) when jumping by reference.
	const versionPath = $derived(page.params.versions ?? settings.value.version);
	// hooks.server.ts sets <html lang> on the first load; keep it right across navigations.
	$effect(() => {
		document.documentElement.lang = pageLang(page.params.versions);
	});
	const ui = $derived(settings.value.uiLang);
	const signinHref = $derived(`/signin?next=${encodeURIComponent(page.url.pathname)}`);

	// One page view per navigation, including the first load (docs/feature_analytics.md).
	afterNavigate((nav) => {
		if (nav.from) inApp = true;
		chrome.hidden = false;
		chapterMenu = false;
		searchOpen = false;
		// Chapter pages carry their book and chapter, for the reading insight on /mod/traffic.
		const d = page.data as { book?: { code?: string }; chapter?: number };
		track('view', { route: page.route.id, lang: ui, user: session.user?.id, book: d.book?.code, chapter: typeof d.chapter === 'number' ? d.chapter : undefined });
	});

	// ---- Phone header (design 10A): one 56px bar that slides away while reading ----
	let chapterMenu = $state(false);
	let searchOpen = $state(false);
	let inApp = false;
	const pd = $derived(page.data as { book?: Book; chapter?: number; versions?: VersionMeta[] });
	const curBook = $derived(pd.book && typeof pd.book === 'object' && 'slug' in pd.book ? pd.book : undefined);
	const curChapter = $derived(curBook && typeof pd.chapter === 'number' ? pd.chapter : undefined);
	const curVersions = $derived(Array.isArray(pd.versions) ? pd.versions : undefined);
	const pillLang = $derived(curVersions?.[0]?.lang ?? ui);
	const pillTitle = $derived(
		curBook ? `${bookNameIn(curBook, curVersions?.[0] ?? pillLang)}${curChapter ? ` ${curChapter}` : ''}` : 'தமிழ் வேதாகமம்'
	);
	const pillVersion = $derived(
		curVersions?.map((v) => v.short).join(' + ') ??
			manifest.versions.find((v) => v.code.toLowerCase() === versionPath.split('+')[0].toLowerCase())?.short ??
			''
	);
	const isHome = $derived(page.route.id === '/');

	function back() {
		if (inApp) history.back();
		else goto(curBook && curChapter ? `/${versionPath}/${curBook.slug}` : '/');
	}
	async function toggleSearch() {
		searchOpen = !searchOpen;
		chapterMenu = false;
		if (searchOpen) {
			await tick();
			focusSearch();
		}
	}

	// Scrolling down past the bar hides it; any scroll up, or reaching the top, shows it.
	let lastY = 0;
	function onScroll() {
		const y = window.scrollY;
		const dy = y - lastY;
		if (Math.abs(dy) < 6) return;
		lastY = y;
		if (!matchMedia('(max-width: 720px)').matches || chapterMenu || searchOpen || settingsOpen) {
			chrome.hidden = false;
			return;
		}
		chrome.hidden = dy > 0 && y > 80;
	}
	// A tap on the text (not on a control) brings the bars back.
	function onPageTap(e: MouseEvent) {
		if (!chrome.hidden) return;
		const t = e.target as HTMLElement | null;
		if (t?.closest('a, button, input, select, textarea, label, [role="button"], [role="dialog"]')) return;
		chrome.hidden = false;
	}

	onMount(() => {
		settings.stamp();
		session.start();
		inject({ mode: dev ? 'development' : 'production' });
	});

	function focusSearch() {
		document.querySelector<HTMLInputElement>('input[type=search]')?.focus();
	}
	function onKey(e: KeyboardEvent) {
		// Ctrl/Cmd+K from anywhere, "/" outside text fields.
		if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
			e.preventDefault();
			focusSearch();
			return;
		}
		const t = e.target as HTMLElement | null;
		if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT')) return;
		if (e.key === '/') {
			e.preventDefault();
			focusSearch();
		}
	}
</script>

<svelte:window onkeydown={onKey} onscroll={onScroll} />

<!-- One preview image for every shared link; pages add their own title and description. -->
<svelte:head>
	<meta property="og:image" content="https://www.tamilscripture.com/og-default.png" />
	<meta property="og:image:width" content="1200" />
	<meta property="og:image:height" content="630" />
	<meta name="twitter:card" content="summary_large_image" />
</svelte:head>

{#if !bare}
<header class="site" class:hidden={chrome.hidden} class:searching={searchOpen} bind:clientHeight={headerH}>
	<div class="bar">
		{#if isHome}
			<span class="m-only m-icon" aria-hidden="true"></span>
		{:else}
			<button type="button" class="m-only m-icon back" aria-label={ui === 'ta' ? 'பின்செல்' : 'Back'} onclick={back}>
				<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 5l-7 7 7 7"/></svg>
			</button>
		{/if}
		<button type="button" class="m-only pill" class:open={chapterMenu} aria-expanded={chapterMenu} aria-haspopup="dialog" onclick={() => { chapterMenu = !chapterMenu; searchOpen = false; }}>
			<span class="t" lang={curBook ? pillLang : 'ta'}>{pillTitle}</span>
			{#if pillVersion}<span class="v">{pillVersion}</span>{/if}
			<span class="caret" aria-hidden="true">{chapterMenu ? '▴' : '▾'}</span>
		</button>
		<button type="button" class="m-only m-icon" aria-label={ui === 'ta' ? 'தேடு' : 'Search'} aria-expanded={searchOpen} onclick={toggleSearch}>
			{#if searchOpen}
				<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>
			{:else}
				<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L20 20"/></svg>
			{/if}
		</button>
		<button type="button" class="m-only m-icon" aria-label={ui === 'ta' ? 'வாசிப்பு அமைப்பு' : 'Reading settings'} aria-expanded={settingsOpen} onclick={() => { settingsOpen = true; chapterMenu = false; }}>
			<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg>
		</button>
		<a class="brand" href="/">
			<span class="ta" lang="ta">தமிழ் வேதாகமம்</span>
			<span class="en">Tamil Bible</span>
		</a>
		<div class="ref"><ReferenceBox {versionPath} lang={ui} /></div>
		<div class="tools">
			<div class="lang" role="group" aria-label={ui === 'ta' ? 'இடைமுக மொழி' : 'Interface language'}>
				<button type="button" lang="ta" class:on={ui === 'ta'} aria-pressed={ui === 'ta'} onclick={() => settings.update({ uiLang: 'ta' })}>த</button>
				<button type="button" lang="en" class:on={ui === 'en'} aria-pressed={ui === 'en'} onclick={() => settings.update({ uiLang: 'en' })}>EN</button>
			</div>
			{#if session.ready && session.signedIn}
				<div class="user">
					<button class="avatar" type="button" aria-label={ui === 'ta' ? 'கணக்கு' : 'Account'} aria-expanded={menuOpen} onclick={() => (menuOpen = !menuOpen)}>
						{(session.user?.email ?? '?').slice(0, 1).toUpperCase()}
					</button>
					{#if menuOpen}
						<!-- svelte-ignore a11y_no_static_element_interactions -->
						<div class="menu" role="menu" tabindex="-1" onmouseleave={() => (menuOpen = false)}>
							<span class="who">{session.user?.email}</span>
							<a role="menuitem" href="/me/history" onclick={() => (menuOpen = false)}>{ui === 'ta' ? 'வரலாறு' : 'History'}</a>
							<a role="menuitem" href="/me/highlights" onclick={() => (menuOpen = false)}>{ui === 'ta' ? 'அடிக்கோடுகள்' : 'Highlights'}</a>
							<a role="menuitem" href="/me/notes" onclick={() => (menuOpen = false)}>{ui === 'ta' ? 'குறிப்புகள்' : 'Notes'}</a>
							<a role="menuitem" href="/me/presentations" onclick={() => (menuOpen = false)}>{ui === 'ta' ? 'விளக்கக்காட்சிகள்' : 'Presentations'}</a>
							<a role="menuitem" href="/me/account" onclick={() => (menuOpen = false)}>{ui === 'ta' ? 'கணக்கு' : 'Account'}</a>
							<button role="menuitem" type="button" onclick={() => { menuOpen = false; session.signOut(); }}>{ui === 'ta' ? 'வெளியேறு' : 'Sign out'}</button>
						</div>
					{/if}
				</div>
			{:else}
				<a class="chip signin" href={signinHref}>{ui === 'ta' ? 'உள்நுழை' : 'Sign in'}</a>
			{/if}
			<button class="chip gear" type="button" aria-label={ui === 'ta' ? 'அமைப்புகள்' : 'Settings'} aria-expanded={settingsOpen} onclick={() => (settingsOpen = !settingsOpen)}>
				<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg>
			</button>
		</div>
	</div>
</header>
{/if}

<SettingsPanel bind:open={settingsOpen} />
<VersePreview />
<MobileMenu bind:open={chapterMenu} lang={ui} book={curBook} chapter={curChapter} versions={curVersions} {versionPath} {signinHref} top={headerH} onsettings={() => (settingsOpen = true)} />

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -- a tap on the text is a shortcut; the bars also return on scroll up -->
<main class="page" class:wide class:bleed class:bare onclick={onPageTap} style={headerH ? `--header-h: ${headerH}px` : undefined}>
	{@render children()}
</main>

{#if !bleed && !bare}
<footer class="site-foot">
	<a href="/about">{ui === 'ta' ? 'பற்றி' : 'About'}</a>
	<a href="/licences">{ui === 'ta' ? 'உரிமங்கள்' : 'Licences'}</a>
	<a href="/atlas">{ui === 'ta' ? 'வேதாகம வரைபடம்' : 'Atlas'}</a>
	<a href="/dictionary">{ui === 'ta' ? 'அகராதி' : 'Dictionary'}</a>
	<a href="/heatmap">{ui === 'ta' ? 'வெப்ப வரைபடம்' : 'Heatmap'}</a>
</footer>
{/if}

<style>
	.site { border-bottom: var(--bw) solid var(--line); background: var(--bg); position: sticky; top: 0; z-index: 5; transition: transform 0.22s ease; }
	.m-only { display: none; }
	.bar { display: flex; align-items: center; flex-wrap: wrap; gap: 0.75rem 1.5rem; max-width: 74rem; margin: 0 auto; padding: 0.8rem 1.5rem; }
	.brand { display: flex; flex-direction: column; text-decoration: none; color: inherit; line-height: 1.15; flex: none; }
	.brand .ta { font-family: var(--tamil); font-weight: 600; font-size: 1.3rem; color: var(--ink); }
	.brand .en { font-size: 0.66rem; color: var(--muted); letter-spacing: 0.08em; text-transform: uppercase; }
	.ref { flex: 1 1 16rem; max-width: 32rem; margin: 0 auto; }
	.tools { display: flex; align-items: center; gap: 0.75rem; flex: none; margin-left: auto; }
	.lang { display: inline-flex; border: var(--bw) solid var(--line-2); border-radius: var(--r); overflow: hidden; background: var(--surface); }
	.lang button { border: 0; padding: 0 0.85rem; min-height: 42px; background: var(--surface); color: var(--ink-2); font-weight: 600; font-size: 0.88rem; cursor: pointer; }
	.lang button[lang='ta'] { font-family: var(--tamil); font-size: 1rem; }
	.lang button.on { background: var(--accent); color: var(--on-accent); }
	.signin { min-height: 42px; }
	.user { position: relative; flex: none; }
	.avatar { width: 42px; height: 42px; border-radius: 999px; border: var(--bw) solid var(--line-2); background: var(--surface); color: var(--accent); font-weight: 700; cursor: pointer; }
	.avatar:hover { border-color: var(--accent); }
	.menu { position: absolute; right: 0; top: calc(100% + 8px); min-width: 13rem; background: var(--surface); border: var(--bw) solid var(--line-2); border-radius: var(--r-l); box-shadow: var(--shadow); padding: 0.5rem; display: grid; z-index: 30; }
	.menu .who { font-size: 0.75rem; color: var(--muted); padding: 0.4rem 0.7rem; overflow: hidden; text-overflow: ellipsis; }
	.menu a, .menu button { text-align: left; padding: 0.6rem 0.7rem; border: 0; background: none; color: inherit; text-decoration: none; border-radius: var(--r-s); cursor: pointer; font-family: var(--tamil); font-weight: 600; }
	.menu a:hover, .menu button:hover { background: var(--accent-soft); }
	.gear { width: 42px; height: 42px; min-height: 42px; padding: 0; color: var(--ink-2); }
	.gear:hover { color: var(--accent); }
	/* Sticky offsets for the reader columns. The fallback matches the one-row
	   header (46px search field + 0.8rem padding each side + border) so the
	   measured value only fine-tunes it and nothing jumps after hydration. */
	.page { --header-h: 4.4rem; max-width: 74rem; margin: 0 auto; padding: 1.5rem 1.5rem 4rem; }
	.page.wide, .page.bleed, .page.bare { max-width: none; padding: 0; }
	.site-foot { max-width: 74rem; margin: 0 auto; padding: 1.2rem 1.5rem 2.5rem; display: flex; flex-wrap: wrap; gap: 1.5rem; font-size: 0.85rem; color: var(--muted); border-top: var(--bw) solid var(--line); font-family: var(--tamil); }
	.site-foot a { color: inherit; text-decoration: none; }
	.site-foot a:hover { color: var(--accent); }
	/* Phones (design 10A): back, chapter pill, search in one 56px bar. Language,
	   sign-in and settings live in the chapter menu's footer. */
	@media (max-width: 720px) {
		.bar { padding: 6px 10px 8px; gap: 8px 4px; flex-wrap: wrap; }
		.brand, .tools { display: none; }
		.m-only { display: flex; }
		.m-icon { width: 40px; height: 44px; flex: none; align-items: center; justify-content: center; border: 0; border-radius: 999px; background: none; color: var(--ink-2); cursor: pointer; padding: 0; }
		.m-icon:hover { background: var(--surface-2); }
		.pill { flex: 1; min-width: 0; height: 44px; align-items: center; justify-content: center; gap: 8px; padding: 0 16px; border-radius: 999px; background: var(--surface); border: var(--bw) solid var(--line-2); color: var(--ink); cursor: pointer; }
		.pill.open { background: var(--accent-soft); border-color: var(--accent); }
		.pill .t { font-family: var(--sans); font-size: 1.05rem; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
		.pill .t[lang='ta'] { font-family: var(--tamil); font-size: 1.12rem; }
		.pill .v { font-size: 0.75rem; color: var(--muted); white-space: nowrap; flex: none; }
		.pill .caret { font-size: 0.7rem; color: var(--muted); margin-left: -4px; flex: none; }
		.pill.open .v, .pill.open .caret { color: var(--accent); }
		.ref { display: none; order: 3; flex-basis: 100%; max-width: none; }
		.site.searching .ref { display: block; }
		.site { z-index: 20; }
		.site.hidden { transform: translateY(-100%); }
		.page:not(.wide):not(.bleed), .site-foot { padding-left: 1rem; padding-right: 1rem; }
	}
	@media (prefers-reduced-motion: reduce) {
		.site { transition: none; }
	}
</style>
