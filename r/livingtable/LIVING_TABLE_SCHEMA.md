# Living table: dependency graph schema (Phase 1 draft)

Note for the repository copy: this is the original design note of
2026-08-29. The edge file it describes is data/ca_edges.csv; the
engine as built uses the recipe-level files data/ca_edges_v2.csv,
data/engine_nodes.csv and data/engine_links.csv (see README.md and
PIPELINE.md). The ca_table.csv it refers to is not part of this
directory.

Design principle on record (2026-08-29): built for
future growth and usage. Append-only everywhere, plain text
formats, nothing a future maintainer needs special tooling to
extend.

## Nodes

A node is a parameter point (t, k, v) with its current best-known
state. The existing ca_table.csv rows ARE the nodes; no new node
file is needed. Node identity: (t, k, v). Node state: best N,
tier (CITED / VERIFIED / ...), source tag, stamps. The reserved lb
columns take certified lower bounds when that wing opens.

## Edges (new file: ca_edges.csv, append-only)

One row per derivation claim:

  child_t, child_k, child_v, child_N   the derived entry
  construction                         family name (from the
                                       inventory's controlled list)
  params                               construction parameters as
                                       key=value pairs, semicolonless
                                       (e.g. "split=k1*k2" style)
  ing1_t, ing1_k, ing1_v, ing1_N       first ingredient (blank for
  ing2_t, ing2_k, ing2_v, ing2_N       leaves; second blank when
                                       unary)
  confidence                           EXECUTED (construction run,
                                       output verified by caverify)
                                       / ARITHMETIC (size relation
                                       checked, array not built)
                                       / CLAIMED (tag says so,
                                       nothing checked yet)
  stamp_date, stamp_note               provenance of the edge itself

Every edge starts CLAIMED (from the Source tag), gets upgraded to
ARITHMETIC when a size reproduction pins the ingredients, and to
EXECUTED when the construction runs and the output verifies.
Upgrades are new rows (append-only); the highest confidence row
for an edge is current, matching the table's tier convention.

## Leaves

Entries whose source is a search or an external repository (SA,
tabu, IPOG, CPHF discoveries, Dwyer/NIST/TJ files) are leaves: no
ingredient columns, confidence EXECUTED when the actual array is
in the collection and verified, CLAIMED otherwise. Leaves need no
propagation, only re-verification and replacement when the
campaign beats them.

## Propagation (Phase 3 contract, recorded now for the schema)

Two modes, both to be built:

- Graph mode: an improved node triggers re-evaluation of every
  descendant along edges, depth-first with cycle guard (the
  construction DAG should be acyclic; a cycle is a data error the
  engine reports, never follows).
- Sweep mode: recompute best-known for ALL nodes from scratch
  using the full recipe set. Feasibility note from Phase 1: the CAs Ns
  machinery already evaluates every implemented construction and
  catalogue for one (t, k, v) in milliseconds-to-seconds, so a
  full sweep over 13,641 nodes is hours, not months. Sweep mode is
  the correctness anchor (no missed cascade); graph mode is the
  fast incremental path and the explanation layer (why did this
  entry improve). They must agree; disagreement is a bug in one
  of them and the sweep wins until resolved.

## Controlled vocabulary

The construction column takes values from construction_families
(the inventory file), extended append-only. Free-text goes in
stamp_note, never in construction.
