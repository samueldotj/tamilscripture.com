// A person's family tree for the person page: ancestors a few generations up,
// the person with spouses and siblings, and the children with their children.
// Each person file names only parents, partners, siblings and children, so the
// tree is put together from the files of the people around the person.
import { loadPerson } from './load';
import type { Person, Relation } from './types';

type Fetch = typeof fetch;

/** Generations of ancestors to show above the person. */
const UP = 4;
/** At most this many people on one ancestor row. */
const ROW = 6;
/** At most this many children (David has 21). */
const CHILDREN = 24;

export interface Node {
	id: string;
	name_en: string;
	name_ta?: string;
	brief?: string;
}

export interface ChildBranch extends Node {
	/** The child's other parent, when the person had several spouses. */
	other?: Node;
	children: Node[];
}

export interface Family {
	/** Nearest generation first: parents, grandparents, … */
	ancestors: Node[][];
	partners: Node[];
	siblings: Node[];
	children: ChildBranch[];
}

const node = (r: Relation): Node => ({ id: r.id, name_en: r.name_en, name_ta: r.name_ta, brief: r.brief });

function dedupe(nodes: Node[], skip: Set<string>): Node[] {
	const out: Node[] = [];
	for (const n of nodes) {
		if (skip.has(n.id)) continue;
		skip.add(n.id);
		out.push(n);
	}
	return out;
}

/** The person's family, or null when the files name no relatives. Never throws. */
export async function loadFamily(f: Fetch, p: Person): Promise<Family | null> {
	const r = p.relations;
	if (!r.parents?.length && !r.children?.length && !r.partners?.length && !r.siblings?.length) return null;
	const get = (id: string) => loadPerson(f, id).catch(() => null);
	const seen = new Set([p.id]);
	const partners = dedupe((r.partners ?? []).map(node), new Set(seen));
	const siblings = dedupe((r.siblings ?? []).map(node), new Set([p.id, ...partners.map((x) => x.id)]));

	// Children and the first generation up load together; each step up needs the one below it.
	const kids = (r.children ?? []).slice(0, CHILDREN);
	const childFiles = Promise.all(kids.map((c) => get(c.id)));
	const ancestors: Node[][] = [];
	let row = dedupe((r.parents ?? []).map(node), seen).slice(0, ROW);
	for (let g = 0; g < UP && row.length; g++) {
		ancestors.push(row);
		if (g === UP - 1) break;
		const files = await Promise.all(row.map((n) => get(n.id)));
		row = dedupe(files.flatMap((x) => (x?.relations.parents ?? []).map(node)), seen).slice(0, ROW);
	}

	const partnerIds = new Set(partners.map((x) => x.id));
	const files = await childFiles;
	const children: ChildBranch[] = kids.map((c, i) => {
		const file = files[i];
		const other = partners.length > 1 ? file?.relations.parents?.find((x) => partnerIds.has(x.id)) : undefined;
		return {
			...node(c),
			...(other ? { other: node(other) } : {}),
			children: (file?.relations.children ?? []).map(node)
		};
	});
	return { ancestors, partners, siblings, children };
}
