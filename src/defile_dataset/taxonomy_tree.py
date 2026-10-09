"""The taxon hierarchy (`parent_taxon_id`) as an HTML tree section of the audit report, with
records and birds.

A group's "sp." or slash taxon holds the birds identified only that far; its total adds every
taxon beneath it, so selecting "harrier sp." reads as all harriers.
"""

import html

import pandas as pd

MAIN_CATEGORY = "normal"

CSS = """
#taxonomy { --bar:#9fcfc5; }
#taxonomy .controls { display:flex; gap:12px; align-items:center; margin:16px 0; flex-wrap:wrap; }
#taxonomy button, #taxonomy input { font:inherit; padding:4px 10px; }
#taxonomy .head, #taxonomy summary, #taxonomy .leaf { display:grid; grid-template-columns:minmax(0,1fr) 90px 90px 110px 110px; gap:8px; align-items:baseline; padding:2px 6px; border-bottom:1px solid var(--line); }
#taxonomy .head { font-weight:bold; background:var(--soft); }
#taxonomy .num { text-align:right; font-variant-numeric:tabular-nums; } #taxonomy .own { color:var(--muted); }
#taxonomy details > details, #taxonomy details > .leaf { margin-left:20px; }
#taxonomy summary { cursor:pointer; list-style:none; } #taxonomy summary::-webkit-details-marker { display:none; }
#taxonomy summary .name::before { content:"▸ "; color:var(--muted); } #taxonomy details[open] > summary .name::before { content:"▾ "; }
#taxonomy summary .name { font-weight:bold; } #taxonomy .leaf .name { padding-left:16px; }
#taxonomy .rank { color:var(--muted); font-size:12px; margin-left:6px; }
#taxonomy .bar { display:block; height:4px; background:var(--bar); margin-top:2px; }
#taxonomy [hidden] { display:none !important; }
"""

SCRIPT = """
(() => {
const root = document.getElementById('taxonomy');
const all = open => root.querySelectorAll('details').forEach(d => d.open = open);
root.querySelector('#taxonomy-expand').onclick = () => all(true);
root.querySelector('#taxonomy-collapse').onclick = () => { all(false); root.querySelectorAll('.top').forEach(d => d.open = true); };
root.querySelector('#taxonomy-find').oninput = e => {
  const q = e.target.value.trim().toLowerCase();
  const nodes = [...root.querySelectorAll('.node')];
  nodes.forEach(n => { n.hidden = false; n.dataset.hit = ''; });
  if (!q) return;
  nodes.forEach(n => { n.dataset.hit = n.querySelector('.name').textContent.toLowerCase().includes(q) ? '1' : ''; });
  nodes.forEach(n => {
    n.hidden = !(n.dataset.hit || n.querySelector('.node[data-hit="1"]') || n.parentElement.closest('.node[data-hit="1"]'));
    if (!n.hidden && n.tagName === 'DETAILS') n.open = true;
  });
};
})();
"""


def tree_stats(taxa: pd.DataFrame, count: pd.DataFrame) -> pd.DataFrame:
    """`taxa` plus own and total (with all descendants) `records` and `birds`."""
    rows = count.groupby("taxon_id").size().rename("records")
    main = count[count["count_category"].eq(MAIN_CATEGORY)]
    birds = main.groupby("taxon_id")["count"].sum().rename("birds")
    t = taxa.set_index("taxon_id").join(rows).join(birds)
    t[["records", "birds"]] = t[["records", "birds"]].fillna(0).astype(int)
    t = t.rename(columns={"records": "own_records", "birds": "own_birds"})
    t["total_records"], t["total_birds"] = t["own_records"], t["own_birds"]
    # Roll each taxon into its parent, deepest first, so totals sum nicely up the tree.
    parent = t["parent_taxon_id"]
    depth = {}

    def level(i):
        if i not in depth:
            p = parent.get(i)
            depth[i] = 0 if pd.isna(p) else level(p) + 1
        return depth[i]

    for i in sorted(t.index, key=level, reverse=True):
        p = parent[i]
        if pd.notna(p):
            t.loc[p, ["total_records", "total_birds"]] += t.loc[
                i, ["total_records", "total_birds"]
            ].to_numpy()
    return t


def tree_section(taxa: pd.DataFrame, count: pd.DataFrame) -> str:
    """The report section: a collapsible tree, own and total records and birds per taxon."""
    t = tree_stats(taxa, count)
    children = t.groupby("parent_taxon_id").groups
    biggest = max(int(t["total_birds"].max()), 1)

    def cells(i, own_only=False):
        r = t.loc[i]
        return (
            f'<span class="num">{r.total_records:,}</span><span class="num own">{r.own_records:,}</span>'
            f'<span class="num">{r.total_birds:,}</span><span class="num own">{r.own_birds:,}</span>'
        )

    def label(i):
        r = t.loc[i]
        width = 100 * r.total_birds / biggest
        return (
            f'<span class="name">{html.escape(r.english_name)}<span class="rank">{html.escape(r.taxon_rank)}</span>'
            f'<span class="bar" style="width:{width:.1f}%"></span></span>'
        )

    def node(i, top=False):
        kids = sorted(
            children.get(i, []), key=lambda k: (-t.loc[k, "total_birds"], t.loc[k, "english_name"])
        )
        if not kids:
            return f'<div class="leaf node">{label(i)}{cells(i)}</div>'
        inner = "".join(node(k) for k in kids)
        return (
            f'<details class="node{" top" if top else ""}"{" open" if top else ""}>'
            f"<summary>{label(i)}{cells(i)}</summary>{inner}</details>"
        )

    roots = sorted(t.index[t["parent_taxon_id"].isna()], key=lambda k: -t.loc[k, "total_birds"])
    body = "".join(node(i, top=True) for i in roots)
    grand = int(t.loc[roots, "total_birds"].sum())
    head = (
        '<div class="head"><span>Taxon</span><span class="num">Records</span><span class="num">of which own</span>'
        '<span class="num">Birds</span><span class="num">of which own</span></div>'
    )
    return (
        f'<section id="taxonomy"><style>{CSS}</style><h2>Taxon hierarchy</h2>'
        '<p class="muted">Each taxon sits under its smallest enclosing group (<code>parent_taxon_id</code> in '
        "<code>taxonomy.csv</code>, curated in <code>taxonomy/parent_taxa.csv</code>). "
        "<b>Records</b> are rows of <code>count.csv</code>; <b>birds</b> are the main-direction counts "
        "(<code>count_category = normal</code>). The first figure of each pair adds every taxon beneath; the grey one is the "
        f"taxon's own, identified only to that level. Total over all roots: {grand:,} birds.</p>"
        '<div class="controls"><button id="taxonomy-expand">Expand all</button><button id="taxonomy-collapse">Collapse all</button>'
        '<input id="taxonomy-find" type="search" placeholder="Find a taxon"></div>'
        f"{head}{body}<script>{SCRIPT}</script></section>"
    )
