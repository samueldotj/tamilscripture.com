<script lang="ts">
	// Back and forward through the passages read in this tab (trail.svelte.ts),
	// and the latest ten. In the book rail ('menu') a row of arrows with the
	// list as a dropdown; in the phone chapter menu's Recent tab ('list') the
	// arrows over the list itself. Both end with the full history page.
	import { goto } from '$app/navigation';
	import { trail } from './trail.svelte';

	let { lang, mode = 'menu', onpick }: { lang: 'ta' | 'en'; mode?: 'menu' | 'list'; /** After a pick, e.g. to close the phone menu. */ onpick?: () => void } = $props();

	const ta = $derived(lang === 'ta');
	// The trail lives in sessionStorage: show it only once running in the browser,
	// so the server render and hydration agree.
	let mounted = $state(false);
	$effect(() => {
		mounted = true;
	});
	let open = $state(false);
	let root: HTMLElement | undefined = $state();

	const backLabel = $derived(trail.back ? `${ta ? 'பின்செல்' : 'Back'}: ${trail.back.label}` : ta ? 'பின்செல்' : 'Back');
	const forwardLabel = $derived(trail.forward ? `${ta ? 'முன்செல்' : 'Forward'}: ${trail.forward.label}` : ta ? 'முன்செல்' : 'Forward');
	const recentLabel = $derived(ta ? 'சமீபத்தில் வாசித்தவை' : 'Recently read');
	const langOf = (label: string) => (/[஀-௿]/.test(label) ? 'ta' : 'en');

	function go(url: string | null) {
		open = false;
		onpick?.();
		if (url) goto(url);
	}
	function onDocDown(e: PointerEvent) {
		if (open && root && !root.contains(e.target as Node)) open = false;
	}
	function onKey(e: KeyboardEvent) {
		if (open && e.key === 'Escape') {
			e.stopPropagation();
			open = false;
		}
	}
</script>

<svelte:document onpointerdown={onDocDown} />

{#snippet arrows()}
	<button type="button" class="arrow" disabled={!trail.back} aria-label={backLabel} title={trail.back ? backLabel : undefined} onclick={() => go(trail.step(-1))}>
		<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m9 14-5-5 5-5" /><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11" /></svg>
		{#if mode === 'list'}<span lang={ta ? 'ta' : 'en'}>{ta ? 'பின்' : 'Back'}</span>{/if}
	</button>
	<button type="button" class="arrow" disabled={!trail.forward} aria-label={forwardLabel} title={trail.forward ? forwardLabel : undefined} onclick={() => go(trail.step(1))}>
		{#if mode === 'list'}<span lang={ta ? 'ta' : 'en'}>{ta ? 'முன்' : 'Forward'}</span>{/if}
		<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m15 14 5-5-5-5" /><path d="M20 9H9.5a5.5 5.5 0 0 0 0 11H13" /></svg>
	</button>
{/snippet}

{#snippet items()}
	{#each trail.recent(10) as stop (stop.i)}
		<button type="button" role={mode === 'menu' ? 'menuitem' : undefined} class="item" class:here={stop.i === trail.at} aria-current={stop.i === trail.at ? 'page' : undefined} lang={langOf(stop.label)} onclick={() => go(trail.jump(stop.i))}>{stop.label}</button>
	{/each}
	<a role={mode === 'menu' ? 'menuitem' : undefined} class="all" href="/me/history" lang={ta ? 'ta' : 'en'} onclick={() => go(null)}>{ta ? 'முழு வரலாற்றையும் காண்க' : 'View all history'} →</a>
{/snippet}

{#if mounted && trail.stops.length}
	{#if mode === 'menu'}
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -- Escape closes the menu inside the group -->
		<div class="trail-nav" role="group" aria-label={ta ? 'வாசித்த பகுதிகள்' : 'Reading history'} bind:this={root} onkeydown={onKey}>
			{@render arrows()}
			<button type="button" class="recent" aria-haspopup="menu" aria-expanded={open} onclick={() => (open = !open)} lang={ta ? 'ta' : 'en'}>
				<span>{ta ? 'சமீபம்' : 'Recent'}</span>
				<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg>
			</button>
			{#if open}
				<div class="menu" role="menu" aria-label={recentLabel}>{@render items()}</div>
			{/if}
		</div>
	{:else}
		<div class="trail-list">
			<div class="row" role="group" aria-label={ta ? 'வாசித்த பகுதிகள்' : 'Reading history'}>{@render arrows()}</div>
			<p class="group" lang={ta ? 'ta' : 'en'}>{recentLabel}</p>
			{@render items()}
		</div>
	{/if}
{/if}

<style>
	.trail-nav { position: relative; display: flex; gap: 0.35rem; padding: 0.6rem 1rem; border-bottom: var(--bw) solid var(--line); flex: none; }
	.arrow { display: inline-flex; align-items: center; justify-content: center; gap: 0.4rem; min-width: 40px; height: 40px; padding: 0 0.6rem; border: var(--bw) solid var(--line-2); border-radius: 10px; background: var(--surface); color: var(--ink-2); font: inherit; font-size: 0.92rem; font-weight: 600; cursor: pointer; }
	.arrow [lang='ta'] { font-family: var(--tamil); }
	.arrow:hover:not(:disabled) { color: var(--accent); border-color: var(--accent); }
	.arrow:disabled { opacity: 0.4; cursor: default; }
	.recent { flex: 1; display: inline-flex; align-items: center; justify-content: space-between; gap: 0.4rem; height: 40px; padding: 0 0.75rem; border: var(--bw) solid var(--line-2); border-radius: 10px; background: var(--surface); color: var(--ink); font: inherit; font-size: 0.88rem; font-weight: 600; cursor: pointer; }
	.recent[lang='ta'] { font-family: var(--tamil); }
	.recent[aria-expanded='true'] { border-color: var(--accent); color: var(--accent); }
	/* The latest ten under the row, the width of the rail; "View all" stays in sight at the foot. */
	.menu { position: absolute; z-index: 16; top: calc(100% - 0.2rem); left: 0.6rem; right: 0.6rem; max-height: min(36rem, 70vh); overflow-y: auto; display: grid; padding: 0.35rem; background: var(--surface); border: var(--bw) solid var(--line-2); border-radius: var(--r-l); box-shadow: var(--shadow-lg); }
	.item { font: inherit; font-size: 0.95rem; text-align: left; padding: 0.55rem 0.75rem; min-height: 40px; border: 0; border-radius: 9px; background: none; color: var(--ink); cursor: pointer; }
	.item[lang='ta'] { font-family: var(--tamil); }
	.item:hover, .item:focus-visible { background: var(--surface-2); }
	.item.here { color: var(--accent); font-weight: 700; background: var(--accent-soft); cursor: default; }
	.all { position: sticky; bottom: -0.35rem; background: var(--surface); margin-top: 0.3rem; padding: 0.6rem 0.75rem 0.45rem; border-top: var(--bw) solid var(--line); font-size: 0.88rem; font-weight: 600; color: var(--accent); text-decoration: none; }
	.all[lang='ta'] { font-family: var(--tamil); }
	/* The phone menu's Recent tab. */
	.trail-list { display: grid; gap: 4px; }
	.trail-list .row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 6px; }
	.trail-list .arrow { height: 48px; border-radius: 12px; }
	.trail-list .item { min-height: 46px; font-size: 1rem; border: var(--bw) solid transparent; }
	.trail-list .item.here { border-color: var(--accent); }
	.trail-list .all { position: static; margin-top: 6px; padding: 0.75rem; }
	.group { margin: 6px 0 2px; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); }
	.group[lang='ta'] { font-family: var(--tamil); }
	.arrow:focus-visible, .recent:focus-visible, .item:focus-visible, .all:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
</style>
