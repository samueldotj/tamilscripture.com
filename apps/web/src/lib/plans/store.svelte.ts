// Shared state for the /plans pages: the plan catalogue (built in plus
// published community plans), the reader's progress, and which plan and day
// are on screen. Changes show at once and are saved behind (repo.ts).
import { browser } from '$app/environment';
import { loadProgress, publishedPlans, saveProgress, type ProgressMap } from './repo';
import { BUILTIN, fromRow, iso, type Plan, type Progress } from './schedule';

const ACTIVE_KEY = 'readingPlanActive';

function loadActive(): string | null {
	if (!browser) return null;
	try { return localStorage.getItem(ACTIVE_KEY); } catch { return null; }
}

class PlansStore {
	community = $state<Plan[]>([]);
	mine = $state<ProgressMap>({});
	ready = $state(false);
	error = $state('');
	/** The plan on the Today and Stats pages. */
	activeId = $state<string | null>(loadActive());
	/** The day shown on Today; null follows today. */
	day = $state<number | null>(null);
	private signedIn = false;
	private loadedFor: boolean | null = null;

	plans = $derived<Plan[]>([...BUILTIN, ...this.community]);
	byId = $derived(new Map(this.plans.map((p) => [p.id, p])));
	/** Joined plans, in catalogue order (a plan withdrawn by a moderator drops out). */
	joined = $derived(this.plans.filter((p) => this.mine[p.id]));
	active = $derived<Plan | null>(this.joined.find((p) => p.id === this.activeId) ?? this.joined[0] ?? null);

	/** Load once per sign-in state; again after signing in or out. */
	async load(signedIn: boolean) {
		if (this.loadedFor === signedIn) return;
		this.loadedFor = signedIn;
		this.signedIn = signedIn;
		this.error = '';
		const [rows, mine] = await Promise.all([
			publishedPlans().catch(() => []),
			loadProgress(signedIn).catch((e) => {
				this.error = String(e?.message ?? e);
				return {} as ProgressMap;
			})
		]);
		this.community = rows.map(fromRow);
		this.mine = mine;
		this.ready = true;
	}

	progress(id: string): Progress | null {
		const m = this.mine[id];
		return m ? { start: m.start, done: new Set(m.done) } : null;
	}

	pick(id: string) {
		this.activeId = id;
		this.day = null;
		try { localStorage.setItem(ACTIVE_KEY, id); } catch { /* blocked */ }
	}

	private put(id: string, row: ProgressMap[string] | null) {
		const next = { ...this.mine };
		if (row) next[id] = row;
		else delete next[id];
		this.mine = next;
		saveProgress(this.signedIn, id, row).catch((e) => (this.error = String(e?.message ?? e)));
	}

	join(id: string, start: Date) {
		this.put(id, { start: iso(start), done: [] });
		this.pick(id);
	}

	leave(id: string) {
		this.put(id, null);
	}

	setDone(id: string, keys: string[], read: boolean) {
		const m = this.mine[id];
		if (!m) return;
		const done = new Set(m.done);
		for (const k of keys) {
			if (read) done.add(k);
			else done.delete(k);
		}
		this.put(id, { start: m.start, done: [...done] });
	}
}

export const plansStore = new PlansStore();
