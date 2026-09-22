// A small Markdown reader for notes: headings, paragraphs, bold, italics,
// inline code, quotes, bullet and numbered lists (nested by indentation),
// links and rules. It produces a tree that Markdown.svelte renders as
// elements, so no HTML string is ever built from user text and nothing needs
// sanitising. Anything it does not know stays literal text. Line breaks inside
// a paragraph are kept, as people writing sermon notes expect.

export type Inline =
	| { t: 'text'; s: string }
	| { t: 'strong'; c: Inline[] }
	| { t: 'em'; c: Inline[] }
	| { t: 'code'; s: string }
	| { t: 'link'; href: string; c: Inline[] }
	| { t: 'br' };

export type Block =
	| { t: 'h'; level: 1 | 2 | 3; c: Inline[] }
	| { t: 'p'; c: Inline[] }
	| { t: 'quote'; c: Block[] }
	| { t: 'list'; ordered: boolean; items: Block[][] }
	| { t: 'hr' };

const SAFE_HREF = /^(https?:\/\/|\/|#|mailto:)/i;

export function parseMarkdown(src: string): Block[] {
	return parseBlocks(src.replace(/\r\n?/g, '\n').split('\n'));
}

type Item = { indent: number; ordered: boolean; text: string };

function parseBlocks(lines: string[]): Block[] {
	const out: Block[] = [];
	let para: string[] = [];
	const flush = () => {
		if (para.length) out.push({ t: 'p', c: parseInlines(para.join('\n')) });
		para = [];
	};
	for (let i = 0; i < lines.length; i++) {
		const line = lines[i];
		if (!line.trim()) { flush(); continue; }
		let m: RegExpMatchArray | null;
		if ((m = line.match(/^\s{0,3}(#{1,3})\s+(.*?)\s*#*\s*$/))) {
			flush();
			out.push({ t: 'h', level: m[1].length as 1 | 2 | 3, c: parseInlines(m[2]) });
			continue;
		}
		if (/^\s{0,3}([-*_])(\s*\1){2,}\s*$/.test(line)) {
			flush();
			out.push({ t: 'hr' });
			continue;
		}
		if (/^\s{0,3}>/.test(line)) {
			flush();
			const inner: string[] = [];
			while (i < lines.length && /^\s{0,3}>/.test(lines[i])) inner.push(lines[i].replace(/^\s{0,3}>\s?/, '')), i++;
			i--;
			out.push({ t: 'quote', c: parseBlocks(inner) });
			continue;
		}
		if (listItem(line)) {
			flush();
			const items: Item[] = [];
			while (i < lines.length) {
				const it = listItem(lines[i]);
				if (it) items.push(it);
				else if (lines[i].trim() && items.length && /^\s+/.test(lines[i])) items[items.length - 1].text += '\n' + lines[i].trim();
				else break;
				i++;
			}
			i--;
			out.push(...buildLists(items));
			continue;
		}
		para.push(line.trim());
	}
	flush();
	return out;
}

function listItem(line: string): Item | null {
	const m = line.match(/^(\s*)(?:([-*+•])|(\d{1,3})[.)])\s+(.*)$/);
	if (!m) return null;
	return { indent: m[1].replace(/\t/g, '  ').length, ordered: m[3] !== undefined, text: m[4] };
}

/** Items at one indentation form a list; deeper items nest inside the item before them. */
function buildLists(items: Item[]): Block[] {
	const blocks: Block[] = [];
	let i = 0;
	const base = items[0]?.indent ?? 0;
	while (i < items.length) {
		const ordered = items[i].ordered;
		const list: Block = { t: 'list', ordered, items: [] };
		while (i < items.length && items[i].ordered === ordered && items[i].indent <= base) {
			const item: Block[] = [{ t: 'p', c: parseInlines(items[i].text) }];
			i++;
			const start = i;
			while (i < items.length && items[i].indent > base) i++;
			if (i > start) item.push(...buildLists(items.slice(start, i)));
			list.items.push(item);
		}
		blocks.push(list);
		if (i < items.length && items[i].indent > base) i++; // a stray deeper item without a parent: skip it
	}
	return blocks;
}

export function parseInlines(text: string): Inline[] {
	const out: Inline[] = [];
	let buf = '';
	const push = () => { if (buf) out.push({ t: 'text', s: buf }); buf = ''; };
	let i = 0;
	while (i < text.length) {
		const ch = text[i];
		if (ch === '\n') { push(); out.push({ t: 'br' }); i++; continue; }
		if (ch === '\\' && i + 1 < text.length && /[\\`*_[\]()#>-]/.test(text[i + 1])) { buf += text[i + 1]; i += 2; continue; }
		if (ch === '`') {
			const end = text.indexOf('`', i + 1);
			if (end > i + 1) { push(); out.push({ t: 'code', s: text.slice(i + 1, end) }); i = end + 1; continue; }
		}
		if (ch === '[') {
			const close = matching(text, i, '[', ']');
			if (close > 0 && text[close + 1] === '(') {
				const end = matching(text, close + 1, '(', ')');
				const href = end > 0 ? text.slice(close + 2, end).trim() : '';
				if (end > 0 && SAFE_HREF.test(href)) {
					push();
					out.push({ t: 'link', href, c: parseInlines(text.slice(i + 1, close)) });
					i = end + 1;
					continue;
				}
			}
		}
		if (text.startsWith('**', i) || text.startsWith('__', i)) {
			const mark = text.slice(i, i + 2);
			const end = text.indexOf(mark, i + 2);
			if (end > i + 2 && !/\s/.test(text[i + 2]) && !/\s/.test(text[end - 1])) {
				push();
				out.push({ t: 'strong', c: parseInlines(text.slice(i + 2, end)) });
				i = end + 2;
				continue;
			}
		}
		if ((ch === '*' || ch === '_') && (ch === '*' || i === 0 || /[\s(]/.test(text[i - 1]))) {
			const end = text.indexOf(ch, i + 1);
			if (end > i + 1 && !/\s/.test(text[i + 1]) && !/\s/.test(text[end - 1]) && (ch === '*' || end + 1 >= text.length || /[\s.,;:!?)]/.test(text[end + 1]))) {
				push();
				out.push({ t: 'em', c: parseInlines(text.slice(i + 1, end)) });
				i = end + 1;
				continue;
			}
		}
		buf += ch;
		i++;
	}
	push();
	return out;
}

/** Index of the bracket closing the one at `from`, or -1. */
function matching(text: string, from: number, open: string, close: string): number {
	let depth = 0;
	for (let i = from; i < text.length; i++) {
		if (text[i] === '\\') { i++; continue; }
		if (text[i] === open) depth++;
		else if (text[i] === close && --depth === 0) return i;
	}
	return -1;
}

/** The plain words of a Markdown text, for previews and thumbnails. */
export function plainText(src: string, max = 160): string {
	const text = src
		.replace(/`([^`]*)`/g, '$1')
		.replace(/\[([^\]]*)\]\([^)]*\)/g, '$1')
		.replace(/^\s{0,3}(#{1,3}\s+|>\s?|[-*+•]\s+|\d{1,3}[.)]\s+)/gm, '')
		.replace(/(\*\*|__|[*_])/g, '')
		.replace(/\s+/g, ' ')
		.trim();
	return text.length > max ? text.slice(0, max).replace(/\s\S*$/, '') + '…' : text;
}
