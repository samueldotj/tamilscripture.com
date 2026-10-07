// "Share as image" (Claude Design handoff, Verse Share Image): a passage drawn on a
// canvas in the Classical style. The preview, the template thumbnails and the
// downloaded PNG are one drawing at different sizes.

export type Template = 'plate' | 'margin' | 'rules' | 'numeral' | 'initial' | 'corner';
export type IconName = 'cross' | 'bible' | 'church' | 'mountain' | 'desert' | 'sea';
export type ImageSize = 'square' | 'story' | 'landscape';
export type ImageTheme = 'light' | 'dark';

export const TEMPLATES: Template[] = ['plate', 'margin', 'rules', 'numeral', 'initial', 'corner'];

/** Lucide paths (24-unit grid): cross, book-open, church, mountain, tree-palm, waves. */
export const ICONS: Record<IconName, string[]> = {
	cross: ['M11 2a2 2 0 0 0-2 2v5H4a2 2 0 0 0-2 2v2c0 1.1.9 2 2 2h5v5c0 1.1.9 2 2 2h2a2 2 0 0 0 2-2v-5h5a2 2 0 0 0 2-2v-2a2 2 0 0 0-2-2h-5V4a2 2 0 0 0-2-2h-2z'],
	bible: ['M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z', 'M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z'],
	church: ['m18 7 4 2v11a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9l4-2', 'M14 22v-4a2 2 0 0 0-2-2a2 2 0 0 0-2 2v4', 'M18 22V5l-6-3-6 3v17', 'M12 7v5', 'M10 9h4'],
	mountain: ['m8 3 4 8 5-5 5 15H2L8 3z'],
	desert: ['M13 8c0-2.76-2.46-5-5.5-5S2 5.24 2 8h2l1-1 1 1h4', 'M13 7.14A5.82 5.82 0 0 1 16.5 6c3.04 0 5.5 2.24 5.5 5h-3l-1-1-1 1h-3', 'M5.89 9.71c-2.15 2.15-2.3 5.47-.35 7.43l4.24-4.25.7-.7.71-.71 2.12-2.12c-1.95-1.96-5.27-1.8-7.42.35z', 'M11 15.5c.5 2.5-.17 4.5-1 6.5h4c2-5.5-.5-12-1-14'],
	sea: ['M2 6c.6.5 1.2 1 2.5 1C7 7 7 5 9.5 5c2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1', 'M2 12c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1', 'M2 18c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1']
};
/** The "auto" icon for a book; any other book gets the open Bible. */
const AUTO_ICON: Record<string, IconName> = { JHN: 'cross', MAT: 'cross', MRK: 'cross', LUK: 'cross', PSA: 'mountain', EXO: 'desert', NUM: 'desert', DEU: 'desert', JON: 'sea', ACT: 'sea', GEN: 'mountain', ISA: 'mountain', ROM: 'church', EPH: 'church', REV: 'church' };
export function autoIcon(book: string): IconName {
	return AUTO_ICON[book] ?? 'bible';
}

export const SIZES: Record<ImageSize, { W: number; H: number }> = { square: { W: 1080, H: 1080 }, story: { W: 1080, H: 1920 }, landscape: { W: 1200, H: 630 } };

const TA = "'Noto Serif Tamil', 'Tamil Fallback', 'Nirmala UI', 'Latha', serif";
const EN = "'Lora', Georgia, serif";
const HEAD = "'Cormorant Garamond', Georgia, serif";
const SANS = "'Noto Sans', sans-serif";
/** The faces the drawing uses; load them before drawing or the canvas falls back. */
export const FACES = ['400 40px "Noto Serif Tamil"', '600 40px "Noto Serif Tamil"', '400 40px Lora', '600 40px "Cormorant Garamond"', '400 40px "Cormorant Garamond"', '700 20px "Noto Sans"'];

export const PALETTE: Record<ImageTheme, { bg: string; text: string; muted: string; accent: string; div: string; wm: number }> = {
	light: { bg: '#f3f2f2', text: '#201f1d', muted: '#605d5d', accent: '#b68235', div: 'rgba(32,31,29,0.18)', wm: 0.11 },
	dark: { bg: '#1f1d1c', text: '#f3f2f2', muted: '#bab6b6', accent: '#e1ad66', div: 'rgba(243,242,242,0.2)', wm: 0.13 }
};
type Colors = (typeof PALETTE)[ImageTheme];

/** One version's text: its verses and its reference line ("யோவான் 3:16 · IRV-TA"). */
export interface Passage {
	lang: string;
	verses: { n: number | string; text: string }[];
	ref: string;
}
export interface DrawOptions {
	W: number;
	H: number;
	template: Template;
	icon: IconName;
	theme: ImageTheme;
	/** One or two passages; the second is set a step smaller. */
	passages: Passage[];
	/** The chapter and verses alone, for the numeral template ("3:16"). */
	chapterVerse: string;
	many: boolean;
}

interface Token { t: string; n: string; w?: number }
type Line = Token[] & { ind?: number };
interface Indent { w: number; lines: number }
interface Block { toks: Token[]; fam: string; lh: number; k: number; ind?: (s: number) => Indent }
interface Laid extends Block { size: number; lines: Line[]; sp: number; h: number }
interface Fit { laid: Laid[]; h: number }

function tokens(verses: Passage['verses'], many: boolean): Token[] {
	const out: Token[] = [];
	verses.forEach((v) => v.text.split(/\s+/).filter(Boolean).forEach((w, i) => out.push({ t: w, n: many && i === 0 ? String(v.n) : '' })));
	return out;
}

function wrap(ctx: CanvasRenderingContext2D, toks: Token[], fam: string, wt: number, size: number, maxW: number, ind: Indent | null) {
	const lines: Line[] = [];
	let line: Line = [];
	let x = 0;
	const lim = () => (ind && lines.length < ind.lines ? maxW - ind.w : maxW);
	const push = () => { line.ind = ind && lines.length < ind.lines ? ind.w : 0; lines.push(line); line = []; x = 0; };
	ctx.font = `${wt} ${size}px ${fam}`;
	const sp = ctx.measureText(' ').width;
	for (const tk of toks) {
		let w = 0;
		if (tk.n) { ctx.font = `700 ${size * 0.42}px ${SANS}`; w += ctx.measureText(tk.n).width + size * 0.1; }
		ctx.font = `${wt} ${size}px ${fam}`;
		w += ctx.measureText(tk.t).width;
		if (line.length && x + sp + w > lim()) push();
		line.push({ ...tk, w });
		x += (line.length > 1 ? sp : 0) + w;
	}
	if (line.length) push();
	return { lines, sp };
}

function firstGrapheme(s: string): string {
	if (typeof Intl !== 'undefined' && Intl.Segmenter) {
		const it = new Intl.Segmenter(undefined, { granularity: 'grapheme' }).segment(s)[Symbol.iterator]().next();
		return it.done ? s : it.value.segment;
	}
	return s.slice(0, 1);
}

/** Steps the type down from `start` until the blocks fit `maxH` (or reach `min`). */
function fitBlocks(ctx: CanvasRenderingContext2D, blocks: Block[], maxW: number, maxH: number, start: number, min: number): Fit {
	let fit: Fit = { laid: [], h: 0 };
	for (let size = start; size >= min; size -= 2) {
		let h = 0;
		const laid = blocks.map((b, i) => {
			const s = size * b.k;
			const r = wrap(ctx, b.toks, b.fam, 400, s, maxW, b.ind ? b.ind(s) : null);
			const bh = r.lines.length * s * b.lh;
			h += bh + (i ? size * 1.1 : 0);
			return { ...b, size: s, lines: r.lines, sp: r.sp, h: bh };
		});
		fit = { laid, h };
		if (h <= maxH || size - 2 < min) break;
	}
	return fit;
}

function drawBlocks(ctx: CanvasRenderingContext2D, fit: Fit, x: number, top: number, maxW: number, align: 'left' | 'center' | 'right', C: Colors) {
	let y = top;
	ctx.textBaseline = 'middle';
	fit.laid.forEach((b, i) => {
		if (i) {
			// short gold hairline between the two versions
			const rx = align === 'center' ? x + maxW / 2 - b.size * 0.6 : align === 'right' ? x + maxW - b.size * 1.2 : x;
			ctx.fillStyle = C.accent;
			ctx.fillRect(rx, y + b.size * 0.5, b.size * 1.2, Math.max(1, b.size * 0.03));
			y += (b.size * 1.1) / b.k;
		}
		b.lines.forEach((ln, li) => {
			const lw = ln.reduce((a, t) => a + (t.w ?? 0), 0) + b.sp * (ln.length - 1);
			let cx = align === 'center' ? x + (maxW - lw) / 2 : align === 'right' ? x + maxW - lw : x + (ln.ind || 0);
			const cy = y + (li + 0.5) * b.size * b.lh;
			for (const t of ln) {
				if (t.n) {
					ctx.font = `700 ${b.size * 0.42}px ${SANS}`;
					ctx.fillStyle = C.accent;
					ctx.fillText(t.n, cx, cy - b.size * 0.3);
					cx += ctx.measureText(t.n).width + b.size * 0.1;
				}
				ctx.font = `400 ${b.size}px ${b.fam}`;
				ctx.fillStyle = C.text;
				ctx.fillText(t.t, cx, cy);
				cx += ctx.measureText(t.t).width + b.sp;
			}
		});
		y += b.h;
	});
}

function drawIcon(ctx: CanvasRenderingContext2D, name: IconName, cx: number, cy: number, size: number, color: string, alpha: number) {
	ctx.save();
	ctx.globalAlpha = alpha;
	ctx.translate(cx - size / 2, cy - size / 2);
	ctx.scale(size / 24, size / 24);
	ctx.lineWidth = 1.6;
	ctx.lineCap = 'round';
	ctx.lineJoin = 'round';
	ctx.strokeStyle = color;
	for (const d of ICONS[name]) ctx.stroke(new Path2D(d));
	ctx.restore();
}

interface RefLine { text: string; fam: string; wt: number; k: number; muted?: boolean }
function refLines(o: DrawOptions): RefLine[] {
	return o.passages.map((p, i) => {
		const line = p.lang === 'ta' ? { text: p.ref, fam: TA, wt: 600, k: 0.86 } : { text: p.ref, fam: HEAD, wt: 600, k: 1 };
		return i ? { ...line, k: line.k * 0.88, muted: true } : line;
	});
}

function drawRef(ctx: CanvasRenderingContext2D, o: DrawOptions, x: number, y: number, size: number, align: CanvasTextAlign, C: Colors): number {
	ctx.textAlign = align;
	ctx.textBaseline = 'alphabetic';
	let yy = y;
	for (const r of refLines(o)) {
		ctx.font = `${r.wt} ${size * r.k}px ${r.fam}`;
		ctx.fillStyle = r.muted ? C.muted : C.accent;
		ctx.fillText(r.text, x, yy);
		yy += size * 1.25;
	}
	ctx.textAlign = 'left';
	return yy - y;
}

export function render(cv: HTMLCanvasElement, o: DrawOptions) {
	const { W, H } = o;
	cv.width = W;
	cv.height = H;
	const ctx = cv.getContext('2d');
	if (!ctx) return;
	const C = PALETTE[o.theme];
	const u = Math.sqrt(W * H) / 1080;
	const m = Math.min(W, H);
	const both = o.passages.length > 1;
	ctx.fillStyle = C.bg;
	ctx.fillRect(0, 0, W, H);
	const blocks: Block[] = o.passages.map((p, i) => ({ toks: tokens(p.verses, o.many), fam: p.lang === 'ta' ? TA : EN, lh: p.lang === 'ta' ? 1.6 : 1.42, k: i ? 0.78 : 1 }));
	const base = (both ? 58 : 66) * u;
	const min = 22 * u;
	if (o.template === 'plate') {
		const p = 64 * u;
		ctx.strokeStyle = C.div;
		ctx.lineWidth = Math.max(1, 1.2 * u);
		ctx.strokeRect(p, p, W - 2 * p, H - 2 * p);
		ctx.strokeStyle = C.accent;
		ctx.globalAlpha = 0.6;
		ctx.lineWidth = Math.max(1, 0.9 * u);
		ctx.strokeRect(p + 10 * u, p + 10 * u, W - 2 * (p + 10 * u), H - 2 * (p + 10 * u));
		ctx.globalAlpha = 1;
		drawIcon(ctx, o.icon, W / 2, H / 2 - 20 * u, m * 0.6, C.accent, C.wm);
		const x = p + 70 * u, maxW = W - 2 * x, top = p + 80 * u, refH = (both ? 2 : 1) * 36 * u + 40 * u, maxH = H - top - p - 70 * u - refH;
		const fit = fitBlocks(ctx, blocks, maxW, maxH, base, min);
		drawBlocks(ctx, fit, x, top + (maxH - fit.h) / 2, maxW, 'center', C);
		ctx.fillStyle = C.accent;
		ctx.fillRect(W / 2 - 24 * u, H - p - refH - 26 * u, 48 * u, Math.max(1, u));
		drawRef(ctx, o, W / 2, H - p - refH + 20 * u, 30 * u, 'center', C);
	} else if (o.template === 'margin') {
		drawIcon(ctx, o.icon, W * 0.86, H * 0.84, m * 0.56, C.accent, C.wm);
		const rx = W * 0.1, top = H * 0.14, bot = H * 0.86;
		ctx.fillStyle = C.accent;
		ctx.fillRect(rx, top, Math.max(1.5, 2 * u), bot - top);
		const x = rx + 44 * u, maxW = W - x - W * 0.1;
		const rh = drawRef(ctx, o, x, top + 26 * u, 28 * u, 'left', C);
		const t = top + rh + 40 * u, maxH = bot - t - 10 * u;
		const fit = fitBlocks(ctx, blocks, maxW, maxH, base, min);
		drawBlocks(ctx, fit, x, t, maxW, 'left', C);
	} else if (o.template === 'rules') {
		const y1 = H * 0.13, y2 = H * 0.87, x = W * 0.1, maxW = W * 0.8;
		drawIcon(ctx, o.icon, W / 2, H / 2, m * 0.6, C.accent, C.wm);
		ctx.fillStyle = C.div;
		ctx.fillRect(x, y1, maxW, Math.max(1, u));
		ctx.fillRect(x, y2, maxW, Math.max(1, u));
		const lines = refLines(o);
		ctx.textBaseline = 'alphabetic';
		ctx.font = `${lines[0].wt} ${28 * u * lines[0].k}px ${lines[0].fam}`;
		ctx.fillStyle = C.accent;
		ctx.textAlign = 'left';
		ctx.fillText(lines[0].text, x, y1 - 22 * u);
		if (lines[1]) {
			ctx.font = `600 ${24 * u}px ${lines[1].fam}`;
			ctx.fillStyle = C.muted;
			ctx.textAlign = 'right';
			ctx.fillText(lines[1].text, x + maxW, y1 - 22 * u);
			ctx.textAlign = 'left';
		}
		const t = y1 + 50 * u, maxH = y2 - 50 * u - t;
		const fit = fitBlocks(ctx, blocks, maxW, maxH, base, min);
		drawBlocks(ctx, fit, x, t + (maxH - fit.h) / 2, maxW, 'left', C);
	} else if (o.template === 'initial') {
		// drop cap: the first grapheme set large in the accent, the opening lines indented around it
		drawIcon(ctx, o.icon, W * 0.8, H * 0.78, m * 0.5, C.accent, C.wm);
		const x = W * 0.11, maxW = W * 0.78, top = H * 0.11;
		const rh = drawRef(ctx, o, x, top + 24 * u, 26 * u, 'left', C);
		ctx.fillStyle = C.div;
		ctx.fillRect(x, top + rh + 18 * u, maxW, Math.max(1, u));
		const first = blocks[0];
		const g = firstGrapheme(first.toks[0]?.t ?? '');
		const rest = (first.toks[0]?.t ?? '').slice(g.length);
		first.toks = rest ? [{ ...first.toks[0], t: rest, n: '' }, ...first.toks.slice(1)] : first.toks.slice(1).map((t, i) => (i ? t : { ...t, n: '' }));
		const capLines = 3;
		let cap: { cs: number; asc: number } | null = null;
		first.ind = (s) => {
			const cs = s * first.lh * capLines * 0.78;
			ctx.font = `600 ${cs}px ${first.fam}`;
			const mt = ctx.measureText(g);
			cap = { cs, asc: mt.actualBoundingBoxAscent || cs * 0.7 };
			return { w: mt.width + s * 0.35, lines: capLines };
		};
		const t = top + rh + 60 * u, maxH = H * 0.9 - t;
		const fit = fitBlocks(ctx, blocks, maxW, maxH, base, min);
		const ty = t + Math.min((maxH - fit.h) / 2, 40 * u);
		const c = cap as { cs: number; asc: number } | null;
		if (c) {
			ctx.font = `600 ${c.cs}px ${first.fam}`;
			ctx.fillStyle = C.accent;
			ctx.textBaseline = 'alphabetic';
			ctx.textAlign = 'left';
			ctx.fillText(g, x, ty + fit.laid[0].size * fit.laid[0].lh * 0.5 - fit.laid[0].size * 0.4 + c.asc);
		}
		drawBlocks(ctx, fit, x, ty, maxW, 'left', C);
	} else if (o.template === 'corner') {
		// the icon bleeds off the lower-left corner; type sets flush right against it
		drawIcon(ctx, o.icon, W * 0.14, H * 0.9, m * 1.05, C.accent, C.wm);
		const x = W * 0.12, maxW = W * 0.78, top = H * 0.1;
		drawRef(ctx, o, x + maxW, top + 24 * u, 26 * u, 'right', C);
		ctx.fillStyle = C.accent;
		ctx.fillRect(x + maxW - 48 * u, top + 24 * u + (both ? 2 : 1) * 32 * u + 6 * u, 48 * u, Math.max(1, u));
		const t = top + 130 * u, maxH = H * 0.8 - t;
		const fit = fitBlocks(ctx, blocks, maxW, maxH, base, min);
		drawBlocks(ctx, fit, x, t + Math.min((maxH - fit.h) / 2, 60 * u), maxW, 'right', C);
	} else {
		// numeral: the chapter and verse set large beneath a rule
		drawIcon(ctx, o.icon, W / 2, H * 0.1, m * 0.72, C.accent, C.wm);
		const x = W * 0.12, maxW = W * 0.76, yr = H * 0.845;
		ctx.fillStyle = C.div;
		ctx.fillRect(x, yr, maxW, Math.max(1, u));
		ctx.textBaseline = 'alphabetic';
		ctx.textAlign = 'right';
		ctx.font = `400 ${96 * u}px ${HEAD}`;
		ctx.fillStyle = C.accent;
		ctx.fillText(o.chapterVerse, x + maxW, yr + 92 * u);
		ctx.textAlign = 'left';
		drawRef(ctx, o, x, yr + 46 * u, 26 * u, 'left', C);
		const t = H * 0.3, maxH = yr - 40 * u - t;
		const fit = fitBlocks(ctx, blocks, maxW, maxH, base, min);
		drawBlocks(ctx, fit, x, t + (maxH - fit.h) / 2, maxW, 'center', C);
	}
}
