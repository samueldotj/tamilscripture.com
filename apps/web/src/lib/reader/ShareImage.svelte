<script lang="ts">
	// The "Share as image" picker on the single-verse page (Claude Design handoff, Verse
	// Share Image): a live preview with six templates, an icon, a size, the versions
	// and a light or dark ground, then download, share or copy the PNG.
	import { onMount } from 'svelte';
	import { track, type ShareAction } from '$lib/analytics/track';
	import { autoIcon, FACES, ICONS, PALETTE, render, SIZES, TEMPLATES, type DrawOptions, type IconName, type ImageSize, type ImageTheme, type Passage, type Template } from './verse-image';

	let { passages, version, book, slug, chapter, verses, ta }: {
		/** The versions shown on the page, in order: one or two. */
		passages: Passage[];
		/** The first version's code, for the traffic page. */
		version: string;
		book: string;
		/** For the file name ("john-3-16.png"). */
		slug: string;
		chapter: number;
		verses: string;
		ta: boolean;
	} = $props();

	let template = $state<Template>('plate');
	let size = $state<ImageSize>('square');
	let icon = $state<IconName | 'auto'>('auto');
	let theme = $state<ImageTheme>('light');
	/** Which versions go in the image: 'both', or the index of one. */
	let pick = $state<'both' | 0 | 1>('both');
	let fonts = $state(false);
	let toast = $state('');
	let canvas = $state<HTMLCanvasElement>();
	const thumbs = $state<Partial<Record<Template, HTMLCanvasElement>>>({});

	const t = $derived(ta
		? { preview: 'முன்னோட்டம்', template: 'வடிவம்', icon: 'சின்னம்', size: 'அளவு', lang: 'மொழி', theme: 'தோற்றம்', download: 'பதிவிறக்கு', share: 'பகிர்', copy: 'நகல்', auto: 'தானாக', light: 'வெளிச்சம்', dark: 'இரவு', square: 'சதுரம்', story: 'ஸ்டேட்டஸ்', landscape: 'கிடை', copied: 'படம் நகலெடுக்கப்பட்டது', saved: 'படம் பதிவிறக்கப்பட்டது', noCopy: 'நகலெடுக்க முடியவில்லை', label: 'படமாகப் பகிர்',
			icons: { cross: 'சிலுவை', bible: 'வேதாகமம்', church: 'ஆலயம்', mountain: 'மலை', desert: 'பாலைவனம்', sea: 'கடல்' }, tpl: { plate: 'தகடு', margin: 'ஓரம்', rules: 'கோடுகள்', numeral: 'எண்', initial: 'முதலெழுத்து', corner: 'மூலை' } }
		: { preview: 'Preview', template: 'Template', icon: 'Icon', size: 'Size', lang: 'Language', theme: 'Theme', download: 'Download', share: 'Share', copy: 'Copy', auto: 'Auto', light: 'Light', dark: 'Dark', square: 'Square', story: 'Status', landscape: 'Landscape', copied: 'Image copied', saved: 'Image downloaded', noCopy: 'Could not copy', label: 'Share as image',
			icons: { cross: 'Cross', bible: 'Bible', church: 'Church', mountain: 'Mountain', desert: 'Desert', sea: 'Sea' }, tpl: { plate: 'Plate', margin: 'Margin', rules: 'Rules', numeral: 'Numeral', initial: 'Initial', corner: 'Corner' } });

	/** A version's language as the picker names it: Tamil and English by name, others by version. */
	function langName(p: Passage, i: number): string {
		if (p.lang === 'ta') return ta ? 'தமிழ்' : 'Tamil';
		if (p.lang === 'en') return 'English';
		return p.ref.split(' · ').pop() ?? `${i + 1}`;
	}
	const langs = $derived(passages.length > 1
		? [{ k: 0 as const, label: langName(passages[0], 0) }, { k: 'both' as const, label: `${langName(passages[0], 0)} + ${langName(passages[1], 1)}` }, { k: 1 as const, label: langName(passages[1], 1) }]
		: []);

	const many = $derived(verses.includes('-'));
	function opts(extra: Partial<DrawOptions> = {}): DrawOptions {
		const sz = SIZES[size];
		return {
			W: sz.W, H: sz.H, template, theme,
			icon: icon === 'auto' ? autoIcon(book) : icon,
			passages: pick === 'both' ? passages.slice(0, 2) : [passages[pick] ?? passages[0]],
			chapterVerse: `${chapter}:${verses.replace('-', '–')}`,
			many,
			...extra
		};
	}

	// The faces and the drawing wait until the picker nears the screen, so the verse page
	// costs nothing extra for a reader who never scrolls to it.
	let box = $state<HTMLElement>();
	onMount(() => {
		const io = new IntersectionObserver(async (entries) => {
			if (!entries.some((e) => e.isIntersecting)) return;
			io.disconnect();
			try { await Promise.all(FACES.map((f) => document.fonts.load(f, 'அ Ab'))); } catch { /* draw with fallbacks */ }
			fonts = true;
		}, { rootMargin: '400px' });
		if (box) io.observe(box);
		return () => io.disconnect();
	});

	$effect(() => {
		if (!fonts) return;
		const o = opts();
		if (canvas) render(canvas, o);
		for (const k of TEMPLATES) {
			const c = thumbs[k];
			if (c) render(c, { ...o, template: k, W: Math.round(o.W / 4), H: Math.round(o.H / 4) });
		}
	});

	let toastTimer: ReturnType<typeof setTimeout> | undefined;
	function flash(msg: string) {
		toast = msg;
		clearTimeout(toastTimer);
		toastTimer = setTimeout(() => (toast = ''), 1800);
	}
	function blob(): Promise<Blob> {
		return new Promise((res, rej) => {
			const cv = document.createElement('canvas');
			render(cv, opts());
			cv.toBlob((b) => (b ? res(b) : rej(new Error('no image'))), 'image/png');
		});
	}
	const fileName = $derived(`${slug}-${chapter}-${verses}.png`);
	/** An image that went out, for the moderators' traffic page (docs/feature_analytics.md A9). */
	function counted(action: ShareAction) {
		track('share', { action, verse: `${book}.${chapter}.${verses.split("-")[0]}`, book, chapter, version: version.toUpperCase(), lang: ta ? 'ta' : 'en', detail: `${template}.${size}.${theme}` });
	}
	function save(b: Blob) {
		const a = document.createElement('a');
		a.href = URL.createObjectURL(b);
		a.download = fileName;
		a.click();
		setTimeout(() => URL.revokeObjectURL(a.href), 2000);
		flash(t.saved);
		counted('download');
	}
	async function download() {
		save(await blob());
	}
	async function shareImage() {
		const b = await blob();
		const f = new File([b], fileName, { type: 'image/png' });
		if (navigator.canShare?.({ files: [f] })) { try { await navigator.share({ files: [f], title: passages[0].ref }); counted('sheet'); } catch { /* cancelled */ } }
		else save(b);
	}
	async function copyImage() {
		try {
			await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob() })]);
			flash(t.copied);
			counted('copy');
		} catch { flash(t.noCopy); }
	}

	const sizeIcons: Record<ImageSize, [string, string]> = { square: ['14px', '14px'], story: ['10px', '17px'], landscape: ['19px', '10px'] };
	const SPARKLE = ['M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z'];
	const iconKeys = Object.keys(ICONS) as IconName[];
</script>

<section id="image" class="picker" aria-label={t.label} lang={ta ? 'ta' : 'en'} bind:this={box}>
	<div class="col">
		<div class="head">
			<span class="kicker">{t.preview}</span>
			<span class="dims">{SIZES[size].W} × {SIZES[size].H}</span>
		</div>
		<div class="stage">
			<canvas bind:this={canvas} class="preview {size}" aria-label={t.preview}></canvas>
		</div>
		<div class="actions">
			<button type="button" class="chip primary" onclick={download}>
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><path d="m7 10 5 5 5-5"></path><path d="M12 15V3"></path></svg>
				{t.download}
			</button>
			<button type="button" class="chip" onclick={shareImage}>
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><path d="m8.59 13.51 6.83 3.98M15.41 6.51l-6.82 3.98"></path></svg>
				{t.share}
			</button>
			<button type="button" class="chip" onclick={copyImage}>
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"></rect><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"></path></svg>
				{t.copy}
			</button>
			{#if toast}<span class="toast" role="status">{toast}</span>{/if}
		</div>
	</div>

	<div class="col controls">
		<div class="group">
			<span class="kicker">{t.template}</span>
			<div class="templates">
				{#each TEMPLATES as k (k)}
					<button type="button" class="opt tpl" class:on={template === k} aria-pressed={template === k} onclick={() => (template = k)}>
						<span class="thumb"><canvas bind:this={thumbs[k]} aria-hidden="true"></canvas></span>
						<span>{t.tpl[k]}</span>
					</button>
				{/each}
			</div>
		</div>

		<div class="group">
			<span class="kicker">{t.icon}</span>
			<div class="row">
				{#each [{ k: 'auto' as const, paths: SPARKLE, label: t.auto }, ...iconKeys.map((k) => ({ k, paths: ICONS[k], label: t.icons[k] }))] as o (o.k)}
					<button type="button" class="opt" class:on={icon === o.k} aria-pressed={icon === o.k} title={o.label} onclick={() => (icon = o.k)}>
						<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{#each o.paths as d (d)}<path {d}></path>{/each}</svg>
						<span>{o.label}</span>
					</button>
				{/each}
			</div>
		</div>

		<div class="trio">
			<div class="group">
				<span class="kicker">{t.size}</span>
				<div class="row">
					{#each Object.keys(SIZES) as ImageSize[] as k (k)}
						<button type="button" class="opt" class:on={size === k} aria-pressed={size === k} onclick={() => (size = k)}>
							<span class="frame" aria-hidden="true" style:width={sizeIcons[k][0]} style:height={sizeIcons[k][1]}></span>
							<span>{t[k]}</span>
						</button>
					{/each}
				</div>
			</div>
			{#if langs.length}
				<div class="group">
					<span class="kicker">{t.lang}</span>
					<div class="row">
						{#each langs as o (o.k)}
							<button type="button" class="opt" class:on={pick === o.k} aria-pressed={pick === o.k} onclick={() => (pick = o.k)}>{o.label}</button>
						{/each}
					</div>
				</div>
			{/if}
			<div class="group">
				<span class="kicker">{t.theme}</span>
				<div class="row">
					{#each ['light', 'dark'] as ImageTheme[] as k (k)}
						<button type="button" class="opt" class:on={theme === k} aria-pressed={theme === k} onclick={() => (theme = k)}>
							<span class="swatch" aria-hidden="true" style:background={PALETTE[k].bg}></span>
							<span>{t[k]}</span>
						</button>
					{/each}
				</div>
			</div>
		</div>
	</div>
</section>

<style>
	.picker { scroll-margin-top: 6rem; margin-top: 1.25rem; background: var(--surface); border: var(--bw) solid var(--line); border-radius: var(--r-xl); padding: 1.1rem 1.2rem 1.2rem; display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 17rem), 1fr)); gap: 1.25rem 1.5rem; }
	.col { display: flex; flex-direction: column; gap: 0.8rem; min-width: 0; }
	.controls { gap: 1.1rem; }
	.head { display: flex; align-items: baseline; justify-content: space-between; gap: 0.75rem; }
	.dims { font-family: var(--sans); font-size: 0.76rem; color: var(--muted); font-variant-numeric: tabular-nums; }
	.stage { display: flex; justify-content: center; background: var(--surface-2); border-radius: var(--r); padding: 1rem; }
	.preview { display: block; width: 100%; height: auto; max-width: 400px; box-shadow: var(--shadow); }
	.preview.story { max-width: 260px; }
	.preview.landscape { max-width: 100%; }
	.actions { display: flex; flex-wrap: wrap; gap: 0.5rem; position: relative; }
	.toast { position: absolute; bottom: calc(100% + 0.5rem); left: 0; background: var(--ink); color: var(--bg); font-size: 0.85rem; padding: 0.4rem 0.8rem; border-radius: var(--r-s); white-space: nowrap; font-family: var(--tamil); }
	.actions .toast:lang(en) { font-family: var(--sans); }

	.group { display: grid; gap: 0.5rem; }
	.row { display: flex; flex-wrap: wrap; gap: 0.5rem; }
	.trio { display: grid; grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr)); gap: 1rem 1.25rem; }
	.templates { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0.5rem; }

	.opt { display: inline-flex; align-items: center; justify-content: center; gap: 0.4rem; min-height: 42px; padding: 0.5rem 0.75rem; border: var(--bw) solid var(--line-2); border-radius: 11px; background: var(--surface); color: var(--ink); font-family: var(--tamil); font-weight: 600; font-size: 0.88rem; cursor: pointer; white-space: nowrap; }
	.opt:lang(en) { font-family: var(--sans); }
	.opt:hover { border-color: var(--accent); }
	.opt.on { border-color: var(--accent); background: var(--accent-soft); color: var(--accent); }
	.tpl { flex-direction: column; gap: 0.35rem; padding: 0.4rem 0.3rem 0.45rem; font-size: 0.8rem; min-height: 44px; white-space: normal; }
	.thumb { display: flex; align-items: center; justify-content: center; width: 100%; aspect-ratio: 1; background: var(--surface-2); border-radius: 6px; overflow: hidden; }
	.thumb canvas { display: block; max-width: 100%; max-height: 100%; width: auto; height: auto; }
	.frame { display: block; border: 1.5px solid currentColor; border-radius: 2px; }
	.swatch { display: block; width: 14px; height: 14px; border-radius: 50%; border: 1px solid var(--line-2); }
</style>
