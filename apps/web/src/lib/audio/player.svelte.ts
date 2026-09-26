// The audio Bible player (docs/feature_audio.md, design 12B): one audio
// element for the whole site, so playback survives navigation. The chapter
// page asks it to play; the bar and the verse chips read its state.
import { goto } from '$app/navigation';
import { chapterUrl, findBook, findVersion } from '$lib/content/manifest';
import { loadAudioTimings, loadChapter } from '$lib/content/load';
import type { Book, ChapterJson, ChapterRef, VersionMeta } from '$lib/content/types';

export interface Track {
	version: VersionMeta;
	book: Book;
	chapter: number;
	src: string;
	/** Duration from the build, until the element knows better. */
	ms: number;
	/** `[verse, ms]` starts when the recording is timed (stage 2), else null. */
	verses: [number, number][] | null;
	prev: ChapterRef | null;
	next: ChapterRef | null;
}

export const RATES = [0.75, 1, 1.25, 1.5, 2] as const;
const RATE_KEY = 'audio-rate';

/** "IRVTAM.JHN.3": which chapter a track or a page is. */
export const trackKey = (version: string, book: string, chapter: number) => `${version}.${book}.${chapter}`;

function readRate(): number {
	try {
		const r = Number(localStorage.getItem(RATE_KEY));
		return (RATES as readonly number[]).includes(r) ? r : 1;
	} catch {
		return 1;
	}
}

class Player {
	track = $state<Track | null>(null);
	playing = $state(false);
	/** Seconds into the track. */
	time = $state(0);
	/** Seconds; the build's figure until the element reports its own. */
	duration = $state(0);
	rate = $state(1);
	loading = $state(false);
	error = $state('');
	/** The chapter page on screen and the version path it uses, so the page can follow the reading. */
	viewing = $state<{ key: string; versionPath: string } | null>(null);

	#el: HTMLAudioElement | null = null;
	#seq = 0;

	get key(): string | null {
		const t = this.track;
		return t ? trackKey(t.version.code, t.book.code, t.chapter) : null;
	}

	/** The verse being read, when the track is timed. */
	get verse(): number | null {
		const v = this.track?.verses;
		if (!v?.length) return null;
		const ms = this.time * 1000;
		let lo = 0, hi = v.length - 1, at = 0;
		while (lo <= hi) {
			const mid = (lo + hi) >> 1;
			if (v[mid][1] <= ms + 1) { at = mid; lo = mid + 1; } else hi = mid - 1;
		}
		return v[at][0];
	}

	/** Position of the current verse among the chapter's timed verses, 1-based. */
	get verseIndex(): number {
		const v = this.track?.verses, n = this.verse;
		return v && n !== null ? v.findIndex(([x]) => x === n) + 1 : 0;
	}

	#element(): HTMLAudioElement {
		if (this.#el) return this.#el;
		const el = new Audio();
		el.preload = 'none';
		el.addEventListener('timeupdate', () => (this.time = el.currentTime));
		el.addEventListener('durationchange', () => { if (isFinite(el.duration)) this.duration = el.duration; });
		el.addEventListener('play', () => (this.playing = true));
		el.addEventListener('pause', () => (this.playing = false));
		el.addEventListener('waiting', () => (this.loading = true));
		el.addEventListener('playing', () => { this.loading = false; this.error = ''; });
		el.addEventListener('canplay', () => (this.loading = false));
		el.addEventListener('ended', () => void this.#advance());
		el.addEventListener('error', () => {
			if (!el.getAttribute('src')) return;
			this.loading = false;
			this.playing = false;
			this.error = 'unavailable';
		});
		this.rate = readRate();
		this.#el = el;
		this.#mediaSession();
		return el;
	}

	/** Start a chapter from its beginning, or from a verse once timings exist. */
	async play(chapter: ChapterJson, version: VersionMeta, book: Book, fromVerse?: number) {
		if (!chapter.audio) return;
		const el = this.#element();
		const seq = ++this.#seq;
		const same = this.key === trackKey(version.code, book.code, chapter.chapter);
		if (!same) {
			this.track = {
				version, book, chapter: chapter.chapter, src: chapter.audio.src, ms: chapter.audio.ms,
				verses: null, prev: chapter.prev, next: chapter.next
			};
			this.time = 0;
			this.duration = chapter.audio.ms / 1000;
			this.error = '';
			el.src = chapter.audio.src;
			el.playbackRate = this.rate;
			this.#metadata();
			if (chapter.audio.timed) {
				loadAudioTimings(fetch, version.code, book.code, chapter.chapter)
					.then((t) => { if (seq === this.#seq && this.track) this.track.verses = t.verses; if (fromVerse) this.playFrom(fromVerse); })
					.catch(() => {});
			}
		}
		if (fromVerse && this.track?.verses) this.playFrom(fromVerse);
		else if (!same) el.currentTime = 0;
		await this.#start(el);
	}

	async #start(el: HTMLAudioElement) {
		this.loading = true;
		try {
			await el.play();
		} catch (e) {
			this.loading = false;
			// A browser that refuses to start without a tap leaves the bar paused.
			if ((e as Error).name !== 'NotAllowedError' && (e as Error).name !== 'AbortError') this.error = 'unavailable';
		}
	}

	/** The toolbar's கேள் button: start this chapter, or pause and resume it if it is the one playing. */
	listen(chapter: ChapterJson, version: VersionMeta, book: Book) {
		if (this.key === trackKey(version.code, book.code, chapter.chapter)) this.toggle();
		else void this.play(chapter, version, book);
	}

	toggle() {
		const el = this.#el;
		if (!el || !this.track) return;
		if (el.paused) void this.#start(el);
		else el.pause();
	}

	seek(seconds: number) {
		const el = this.#el;
		if (!el) return;
		const end = this.duration || el.duration || 0;
		el.currentTime = Math.max(0, Math.min(end ? end - 0.25 : seconds, seconds));
		this.time = el.currentTime;
	}

	skip(delta: number) {
		this.seek(this.time + delta);
	}

	/** Jump to a verse's start (timed tracks only) and keep playing. */
	playFrom(verse: number) {
		const v = this.track?.verses;
		const hit = v?.find(([n]) => n === verse) ?? v?.filter(([n]) => n <= verse).at(-1);
		if (!hit || !this.#el) return;
		this.seek(hit[1] / 1000);
		if (this.#el.paused) void this.#start(this.#el);
	}

	cycleRate() {
		const i = RATES.indexOf(this.rate as (typeof RATES)[number]);
		this.rate = RATES[(i + 1) % RATES.length];
		if (this.#el) this.#el.playbackRate = this.rate;
		try { localStorage.setItem(RATE_KEY, String(this.rate)); } catch { /* private mode */ }
	}

	close() {
		this.#seq++;
		const el = this.#el;
		if (el) {
			el.pause();
			el.removeAttribute('src');
			el.load();
		}
		this.track = null;
		this.playing = false;
		this.loading = false;
		this.error = '';
		this.time = 0;
		if ('mediaSession' in navigator) navigator.mediaSession.metadata = null;
	}

	nextChapter() { void this.#go(this.track?.next ?? null); }
	prevChapter() { void this.#go(this.track?.prev ?? null); }

	/** Continuous play: at the end of a chapter the next one starts, if it has a recording. */
	async #advance() {
		await this.#go(this.track?.next ?? null, true);
	}

	async #go(ref: ChapterRef | null, fromEnd = false) {
		const t = this.track;
		if (!t) return;
		if (!ref) { if (fromEnd) this.playing = false; return; }
		const book = findBook(ref.book);
		const version = findVersion(t.version.code);
		if (!book || !version || !version.books.includes(ref.book)) { if (fromEnd) this.playing = false; return; }
		// The page follows the reading only if it was showing the chapter being read.
		const follow = this.viewing?.key === this.key ? this.viewing.versionPath : null;
		try {
			const next = await loadChapter(fetch, version.code, book.code, ref.chapter);
			if (!next.audio) { this.playing = false; this.error = 'gap'; return; }
			await this.play(next, version, book);
			if (follow) void goto(chapterUrl(follow, book, ref.chapter), { noScroll: false, keepFocus: true });
		} catch {
			this.error = 'unavailable';
		}
	}

	#metadata() {
		const t = this.track;
		if (!t || !('mediaSession' in navigator)) return;
		const name = t.version.lang === 'ta' ? t.book.name_ta : t.book.name_en;
		navigator.mediaSession.metadata = new MediaMetadata({
			title: `${name} ${t.chapter}`,
			artist: t.version.short,
			album: t.version.name,
			artwork: [{ src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png' }]
		});
	}

	#mediaSession() {
		if (!('mediaSession' in navigator)) return;
		const ms = navigator.mediaSession;
		const set = (a: MediaSessionAction, h: MediaSessionActionHandler) => { try { ms.setActionHandler(a, h); } catch { /* unsupported action */ } };
		set('play', () => this.toggle());
		set('pause', () => this.toggle());
		set('seekbackward', (d) => this.skip(-(d.seekOffset ?? 10)));
		set('seekforward', (d) => this.skip(d.seekOffset ?? 10));
		set('seekto', (d) => { if (d.seekTime !== undefined) this.seek(d.seekTime); });
		set('previoustrack', () => this.prevChapter());
		set('nexttrack', () => this.nextChapter());
	}
}

export const player = new Player();
