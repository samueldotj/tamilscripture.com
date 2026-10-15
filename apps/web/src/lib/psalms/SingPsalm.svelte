<script lang="ts">
	// "Sing this psalm" on the Psalms explorer's card (docs/feature_psalms_explorer.md §9):
	// the psalm in the 1650 Scottish Psalter. A switch picks the version (C.M. or L.M., or
	// the part of Psalm 119), chips pick its tune, and the tune plays every stanza on
	// organ while the line being sung is lit; the first stanza opens out into all of them.
	import TuneBlock from './TuneBlock.svelte';
	import type { PsalmCard } from './types';

	let { card, ta }: { card: PsalmCard; ta: boolean } = $props();

	let vi = $state(0);
	let ti = $state(0);
	let all = $state(false);
	/** The stanza and line the organ is on. */
	let place = $state<{ stanza: number; line: number } | null>(null);
	let words = $state<HTMLElement>();
	function follow(p: { stanza: number; line: number } | null) {
		place = p;
		if (!p) return;
		if (p.stanza > 0) all = true;
		if (p.line === 0) queueMicrotask(() => words?.querySelectorAll('.stanza')[p.stanza]?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }));
	}
	const v = $derived(card.metrical[vi]);
	const tunes = $derived(v.tunes.map((id) => card.tunes.find((t) => t.id === id)!).filter(Boolean));
	const tune = $derived(tunes[Math.min(ti, tunes.length - 1)]);
	const shown = $derived(all ? v.stanzas : v.stanzas.slice(0, 1));
	const many = $derived(card.metrical.length > 1);
	const parts = $derived(card.metrical.some((x) => x.part));

	function pick(i: number) {
		vi = i;
		ti = 0;
		all = false;
		place = null;
	}
	const versionName = (x: (typeof card.metrical)[number]) => (x.part ? `${x.part}` : x.label);
</script>

<section class="sing" aria-labelledby="sing-title">
	<div class="head">
		<h3 id="sing-title"><span lang={ta ? 'ta' : 'en'}>{ta ? 'பாடுங்கள்' : 'Sing this psalm'}</span><span class="sub">{ta ? 'Sing this psalm' : 'பாடுங்கள்'} · Scottish Psalter, 1650</span></h3>
		{#if many}
			<div class="versions" class:parts role="group" aria-label={parts ? (ta ? 'பகுதி' : 'Part') : ta ? 'பதிப்பு' : 'Version'}>
				{#if parts}<span class="lbl">{ta ? 'பகுதி' : 'Part'}</span>{/if}
				{#each card.metrical as x, i (x.key)}
					<button type="button" class:on={i === vi} aria-pressed={i === vi} onclick={() => pick(i)}>{versionName(x)}</button>
				{/each}
			</div>
		{/if}
	</div>

	<div class="body">
		<div class="music">
			{#if tune}
				{#if tunes.length > 1}
					<div class="tunes" role="group" aria-label={ta ? 'பண்' : 'Tune'}>
						{#each tunes as t, i (t.id)}
							<button type="button" class:on={t === tune} aria-pressed={t === tune} onclick={() => (ti = i)}>{t.name}</button>
						{/each}
					</div>
				{/if}
				{#key tune.id}
					<TuneBlock {tune} {ta} stanzas={v.stanzas.length} lyrics={v.lyrics} onplace={follow} />
				{/key}
				<p class="note">
					{#if v.fallback}
						{ta ? `இந்தச் சங்கீதத்திற்கு மரபுப் பண் இன்னும் இல்லை; இவை ${v.label} அளவுக்குப் பொருந்தும் பண்கள்.` : `No traditional tune is set for this version yet; these fit its metre (${v.label}).`}
					{:else}
						{ta ? 'ஸ்காட்லாந்து சபைகளில் இந்தச் சங்கீதத்துக்குப் பாடப்படும் பண்.' : 'Tunes this psalm is traditionally sung to in Scotland.'}
					{/if}
				</p>
			{:else}
				<p class="note">{ta ? `இந்த அளவுக்கு (${v.label}) பண் இன்னும் சேர்க்கப்படவில்லை.` : `No tune in this metre (${v.label}) has been added yet.`}</p>
			{/if}
		</div>

		<div class="words" lang="en" bind:this={words}>
			{#if v.argument}<p class="argument">{v.argument}</p>{/if}
			{#each shown as stanza, si (si)}
				<p class="stanza">
					{#each stanza as line, li (li)}
						<span class="line" class:indent={line.startsWith('  ')} class:sung={place?.stanza === si && place?.line === li}>{line.trim()}</span>
					{/each}
				</p>
			{/each}
			{#if v.stanzas.length > 1}
				<button type="button" class="more" aria-expanded={all} onclick={() => (all = !all)}>
					{all ? (ta ? 'முதல் பத்தி மட்டும்' : 'First stanza only') : ta ? `எல்லா ${v.stanzas.length} பத்திகளும்` : `All ${v.stanzas.length} stanzas`}
				</button>
			{/if}
		</div>
	</div>
</section>

<style>
	.sing { border-top: var(--bw) solid var(--line); padding: 1.4rem var(--pad, 1.5rem) 1.6rem; display: flex; flex-direction: column; gap: 1rem; }
	.head { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 0.6rem 1rem; }
	h3 { margin: 0; font-size: 1.1rem; font-weight: 600; color: var(--amber); display: flex; gap: 0.6rem; align-items: baseline; flex-wrap: wrap; }
	h3 [lang='ta'] { font-family: var(--tamil); }
	h3 .sub { font-size: 0.82rem; color: var(--muted); font-weight: 600; }
	.versions, .tunes { display: flex; flex-wrap: wrap; gap: 0.35rem; align-items: center; }
	.versions .lbl { font-size: 0.8rem; color: var(--muted); margin-right: 0.2rem; }
	.versions button, .tunes button { min-height: 36px; min-width: 40px; padding: 0.25rem 0.75rem; border: var(--bw) solid var(--line-2); border-radius: 999px; background: var(--surface); color: var(--ink); font: inherit; font-size: 0.85rem; font-weight: 600; cursor: pointer; font-variant-numeric: tabular-nums; }
	.versions.parts button { min-width: 36px; padding: 0.25rem 0.5rem; }
	.versions button:hover, .tunes button:hover { border-color: var(--accent); }
	.versions button.on, .tunes button.on { background: var(--accent); border-color: var(--accent); color: var(--on-accent); }
	.body { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 19rem), 1fr)); gap: 1.4rem; align-items: start; }
	.music { display: flex; flex-direction: column; gap: 0.7rem; }
	.note { margin: 0; font-size: 0.8rem; color: var(--muted); }
	.words { font-size: 1.02rem; line-height: 1.6; color: var(--ink-en); }
	.argument { margin: 0 0 0.6rem; font-style: italic; font-size: 0.9rem; color: var(--muted); }
	.stanza { margin: 0 0 0.9rem; }
	.line { display: block; }
	.line.indent { padding-left: 1.5rem; }
	.line { border-radius: 4px; transition: background-color 0.2s; }
	.line.sung { background: var(--hl); color: var(--ink); }
	@media (prefers-reduced-motion: reduce) { .line { transition: none; } }
	.more { border: 0; background: none; color: var(--accent); font: inherit; font-weight: 600; font-size: 0.9rem; cursor: pointer; padding: 0.3rem 0; text-decoration: underline; text-underline-offset: 3px; }
</style>
