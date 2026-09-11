<script lang="ts">
	import { settings, type Format, type TamilFont, type Theme } from '$lib/settings/store.svelte';
	import { manifest } from '$lib/content/manifest';

	let { open = $bindable(false) }: { open?: boolean } = $props();
	const s = $derived(settings.value);
	const ta = $derived(s.uiLang === 'ta');

	const formats: { id: Format; ta: string; en: string; hint: string }[] = [
		{ id: 'reader', ta: 'வாசிப்பு', en: 'Reader', hint: 'no verse numbers' },
		{ id: 'standard', ta: 'நிலையான', en: 'Standard', hint: 'like a printed Bible' },
		{ id: 'xref', ta: 'ஒரு வரி', en: 'Verse per line', hint: 'one verse per line' }
	];
	const toggles: { key: 'headings' | 'intro' | 'footnotes' | 'xrefs' | 'heat'; ta: string; en: string }[] = [
		{ key: 'headings', ta: 'பகுதித் தலைப்புகள்', en: 'Section headings' },
		{ key: 'intro', ta: 'புத்தக முன்னுரை', en: 'Book introductions' },
		{ key: 'footnotes', ta: 'குறிப்பு எண்கள்', en: 'Footnote markers' },
		{ key: 'xrefs', ta: 'ஒப்புவசனங்கள்', en: 'Cross-references' },
		{ key: 'heat', ta: 'சமூக அடிக்கோட்டு வெப்பம்', en: 'Community highlight heat' }
	];
	const fonts = $derived<{ id: TamilFont; label: string }[]>([
		{ id: 'mukta', label: 'Mukta Malar' },
		{ id: 'sans', label: 'Noto Sans' },
		{ id: 'serif', label: 'Noto Serif' },
		{ id: 'system', label: ta ? 'சாதனம்' : 'System' }
	]);
	const themes: { id: Theme; ta: string; en: string }[] = [
		{ id: 'system', ta: 'சாதனம்', en: 'System' },
		{ id: 'light', ta: 'காகிதம்', en: 'Paper' },
		{ id: 'dark', ta: 'இரவு', en: 'Night' }
	];

	function onKey(e: KeyboardEvent) {
		if (e.key === 'Escape') open = false;
	}
</script>

{#if open}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="backdrop" onclick={() => (open = false)} onkeydown={onKey}></div>
	<div class="panel" role="dialog" tabindex="-1" aria-modal="true" aria-label={ta ? 'வாசிப்பு அமைப்பு' : 'Reading settings'} onkeydown={onKey}>
		<header>
			<button class="back" type="button" onclick={() => (open = false)} aria-label={ta ? 'மூடு' : 'Close'}>‹</button>
			<h2><span lang="ta">வாசிப்பு அமைப்பு</span> <span class="sub">Reading</span></h2>
		</header>

		<section>
			<h3 class="kicker"><span lang="ta">எழுத்து அளவு</span> · Text size</h3>
			<div class="card size">
				<p class="sample" lang="ta">ஆதியிலே தேவன் வானத்தையும் பூமியையும் படைத்தார்.</p>
				<div class="slider">
					<span class="a small" aria-hidden="true">A</span>
					<input type="range" min="1" max="5" step="1" value={s.fontSize} aria-label={ta ? 'எழுத்து அளவு' : 'Text size'} aria-valuetext={`${s.fontSize} / 5`} oninput={(e) => settings.update({ fontSize: Number((e.currentTarget as HTMLInputElement).value) })} />
					<span class="a big" aria-hidden="true">A</span>
				</div>
			</div>
		</section>

		<section>
			<h3 class="kicker"><span lang="ta">வடிவம்</span> · Format</h3>
			<div class="seg" role="radiogroup">
				{#each formats as f (f.id)}
					<button type="button" role="radio" aria-checked={s.format === f.id} class:on={s.format === f.id} onclick={() => settings.update({ format: f.id })} title={f.hint} lang={ta ? 'ta' : 'en'}>
						{ta ? f.ta : f.en}
					</button>
				{/each}
			</div>
		</section>

		<section>
			<h3 class="kicker"><span lang="ta">காட்டு</span> · Show</h3>
			<div class="card list">
				{#each toggles as t (t.key)}
					<div class="row">
						<span class="labels">
							<span class="t" lang="ta">{t.ta}</span>
							<span class="d">{t.en}</span>
						</span>
						<button type="button" role="switch" class="switch" aria-checked={s[t.key]} aria-label={ta ? t.ta : t.en} onclick={() => settings.toggle(t.key)}><span class="knob"></span></button>
					</div>
				{/each}
			</div>
		</section>

		<section>
			<h3 class="kicker"><span lang="ta">தமிழ் எழுத்துரு</span> · Tamil typeface</h3>
			<div class="tiles" role="radiogroup">
				{#each fonts as f (f.id)}
					<button type="button" role="radio" aria-checked={s.tamilFont === f.id} class="tile font-{f.id}" class:on={s.tamilFont === f.id} onclick={() => settings.update({ tamilFont: f.id })}>
						<span class="glyph" lang="ta">அகர</span>
						<span class="fname">{f.label}</span>
					</button>
				{/each}
			</div>
		</section>

		<section>
			<h3 class="kicker"><span lang="ta">தோற்றம்</span> · Appearance</h3>
			<div class="tiles three" role="radiogroup">
				{#each themes as t (t.id)}
					<button type="button" role="radio" aria-checked={s.theme === t.id} class="tile" class:on={s.theme === t.id} onclick={() => settings.update({ theme: t.id })}>
						<span class="swatch {t.id}" aria-hidden="true"></span>
						<span class="fname" lang={ta ? 'ta' : 'en'}>{ta ? t.ta : t.en}</span>
					</button>
				{/each}
			</div>
		</section>

		<section>
			<h3 class="kicker"><span lang="ta">இயல்புநிலை மொழிபெயர்ப்பு</span> · Default version</h3>
			<select class="field" value={s.version} onchange={(e) => settings.update({ version: (e.currentTarget as HTMLSelectElement).value })}>
				{#each manifest.versions as v (v.code)}
					<option value={v.code.toLowerCase()}>{v.short} · {v.name_native}</option>
				{/each}
			</select>
		</section>

		<button type="button" class="chip primary done" onclick={() => (open = false)}><span lang="ta">வாசிப்புக்குத் திரும்பு</span><span class="sep">·</span>Back to reading</button>
	</div>
{/if}

<style>
	.backdrop { position: fixed; inset: 0; background: var(--scrim); z-index: 20; }
	.panel { position: fixed; z-index: 21; top: 0; right: 0; bottom: 0; width: min(26rem, 100%); overflow-y: auto; background: var(--bg); border-left: var(--bw) solid var(--line); padding: 0.9rem 1.25rem 1.5rem; box-shadow: var(--shadow-lg); display: grid; gap: 1.25rem; align-content: start; }
	header { display: flex; align-items: center; gap: 0.75rem; padding-bottom: 0.9rem; border-bottom: var(--bw) solid var(--line); }
	.back { width: 44px; height: 44px; border-radius: 999px; border: var(--bw) solid var(--line-2); background: var(--surface); color: var(--ink-2); font-size: 1.3rem; line-height: 1; cursor: pointer; }
	h2 { font-size: 1.25rem; margin: 0; font-weight: 600; }
	h2 [lang='ta'] { font-family: var(--tamil); }
	h2 .sub { font-size: 0.78rem; color: var(--muted); font-weight: 400; margin-left: 0.2rem; }
	section { display: grid; gap: 0.7rem; }
	h3 { margin: 0; }
	h3 [lang='ta'] { font-family: var(--tamil); letter-spacing: 0.04em; }
	.card { padding: 1.1rem; }
	.sample { margin: 0 0 1rem; font-family: var(--tamil); font-size: 1.3rem; line-height: 1.8; }
	.slider { display: flex; align-items: center; gap: 0.9rem; }
	.a { font-weight: 700; color: var(--ink-2); }
	.a.small { font-size: 0.95rem; }
	.a.big { font-size: 1.55rem; color: var(--ink); }
	input[type='range'] { flex: 1; accent-color: var(--accent); height: 28px; margin: 0; cursor: pointer; }
	.seg { display: flex; gap: 0.35rem; background: var(--surface-3); border-radius: 14px; padding: 5px; }
	.seg button { flex: 1; border: 0; border-radius: 10px; padding: 0.65rem 0.3rem; background: transparent; color: var(--muted); font-weight: 600; font-size: 0.9rem; cursor: pointer; min-height: 44px; }
	.seg button[lang='ta'] { font-family: var(--tamil); }
	.seg button.on { background: var(--surface); color: var(--ink); box-shadow: 0 1px 2px rgba(28, 26, 24, 0.1); }
	.list { padding: 0; overflow: hidden; }
	.row { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: 0.85rem 1.1rem; }
	.row + .row { border-top: var(--bw) solid var(--line); }
	.labels { display: grid; line-height: 1.3; }
	.labels .t { font-family: var(--tamil); font-weight: 600; font-size: 0.98rem; }
	.labels .d { font-size: 0.78rem; color: var(--muted); }
	.switch { position: relative; flex: none; width: 52px; height: 30px; border-radius: 999px; border: 0; background: var(--line-2); cursor: pointer; padding: 0; transition: background 0.15s; }
	.switch[aria-checked='true'] { background: var(--accent); }
	.knob { position: absolute; top: 3px; left: 3px; width: 24px; height: 24px; border-radius: 999px; background: var(--surface); box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2); transition: transform 0.15s; }
	.switch[aria-checked='true'] .knob { transform: translateX(22px); }
	.tiles { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.6rem; }
	.tiles.three { grid-template-columns: repeat(3, 1fr); }
	.tile { display: grid; gap: 0.5rem; justify-items: center; padding: 0.8rem 0.4rem; border: var(--bw) solid var(--line-2); border-radius: var(--r-l); background: var(--surface); color: var(--ink-2); cursor: pointer; }
	.tile.on { border: 2px solid var(--accent); background: var(--accent-soft); color: var(--ink); }
	.glyph { font-size: 1.35rem; line-height: 1.2; color: var(--ink); }
	.font-mukta .glyph { font-family: var(--tamil-mukta); }
	.font-sans .glyph { font-family: var(--tamil-sans); }
	.font-serif .glyph { font-family: var(--tamil-serif); }
	.font-system .glyph { font-family: 'Tamil Fallback', 'Nirmala UI', 'Latha', sans-serif; }
	.fname { font-size: 0.74rem; font-weight: 600; text-align: center; }
	.fname[lang='ta'] { font-family: var(--tamil); font-size: 0.85rem; }
	.swatch { display: block; width: 100%; height: 34px; border-radius: var(--r-s); border: 1px solid var(--line-2); }
	.swatch.light { background: #FBF7F0; }
	.swatch.dark { background: #1B1D22; border-color: #4A505C; }
	.swatch.system { background: linear-gradient(100deg, #FBF7F0 50%, #1B1D22 50%); }
	select.field { padding: 0.75rem 0.95rem; }
	.done { min-height: 56px; border-radius: var(--r-l); font-size: 1rem; gap: 0.5rem; }
	.done .sep { opacity: 0.7; }
	@media (max-width: 400px) {
		.tiles { grid-template-columns: repeat(2, 1fr); }
		.tiles.three { grid-template-columns: repeat(3, 1fr); }
	}
</style>
