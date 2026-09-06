# Living table: pipeline manifest

Every artifact in this directory, the script that produces it, and
the order to run them. All scripts run with Rscript from this
directory (r/livingtable/); they read and write their CSV files in
data/ and their stdout logs are kept in results/ (paths adjusted for
the repository layout, see README.md). Requirements: R with packages
CAs (>= 0.24, GitHub version) and caverify (>= 0.2.0) installed.
Nothing depends on any cloud environment. Stage 1 scripts are not
shipped, so their outputs are records rather than reproducible
artifacts; stages 2 to 5 rerun from here.

## Stage 1: inventory and measurement of the frozen record

1. tag_inventory.R -> data/construction_families.csv
   Clusters the 2,287 Source tags of colbournBigFrame (13,641
   entries, shipped inside CAs) into construction families.
   (The script is not shipped here; its output is.)
2. make_inventory.R -> construction_inventory.csv
   Bins the top families by implementation status in CAs.
   (Neither the script nor the output is shipped here.)
3. phase2_chunk.R [lo] [hi] -> repro_*.csv, merged into
   data/ca_reproduction.csv
   The full-table reproduction sweep: for every snapshot entry,
   asks Ns(t,k,v) whether any implemented route reproduces the
   recorded N. Statuses: MATCH / BETTER / GAP / NOIMPL / ERR.
   (The chunk script and chunk files are not shipped; the merged
   data/ca_reproduction.csv is.)

## Stage 2: certification and defect handling

4. verify_better.R -> data/better_verified.csv
   Constructs and fully verifies the feasible BETTER entries
   (rows where implemented routes beat the frozen record).
5. mac_grind.R [cost_cap] [workers] -> data/edge_executed_progress.csv
   The certification grind over all MATCH entries: build via
   bestCA, verify via ca_verify, checkpointed, resumable.
   Followed by mac_finish2.R (subprocess per row, hard timeout,
   worker finish_one.R) and mac_finish3.R (screen-tier retry of
   the timeout pile, memory guard), which also maintain
   data/edge_screen_progress.csv. Log: results/mac_finish3_result.txt.
6. mac_cyclotomy_audit2.R and mac_cyclotomy_followup.R ->
   data/cyclotomy_audit2.csv, data/cyclotomy_screen4.csv (logs in
   results/)
   Family audit that isolated the three type-3a defects; the
   followup added multi-window screens and the 3b repairs.
   mac_4a_check.R and mac_4a_q127.R check the type-4a repair
   (logs in results/).
7. mac_powerct_audit.R [workers] -> powerct_audit.csv (not shipped:
   the family audit was interrupted before completion, see
   README.md; 14 rows diagnosed by the CAs author as affected by a
   DHHF2CA defect are skipped by the script). mac_powerct_refix.R
   (worker powerct_one.R) re-audits those 14 rows after the CAs
   GitHub fix of 2026-09-04 -> data/powerct_refix.csv,
   results/powerct_refix_result.txt.
8. Findings: findings/FINDING_CAN_3_128_6.md (cyclotomy, three
   entries), findings/FINDING_POWERCT_3_1584_2.md (powerCT).

## Stage 3: the dependency graph (the engine's substrate)

9.  parse_recipes.R -> data/recipe_ingredients.csv
    Parses the executable code strings of DPcat, PCAcat,
    CYCLOTOMYcat, PALEYcat, ColbournKeriCombis into per-recipe
    ingredient call lists. 1,539 recipes, zero parse failures.
    (Originally run inline on 2026-08-30; the script reproduces it.)
10. ingredient_dims.R -> data/ingredient_dims.csv
    Executes each of the 876 unique ingredient calls (inside the
    CAs namespace where needed) and records N, k, level range.
11. build_edges_v2.R -> data/ca_edges_v2.csv
    Joins 9 and 10: 4,324 ingredient edges over 1,304 recipes,
    all dimensions measured.
    (data/ca_edges.csv is the earlier stage-1-level edge seed from
    the sweep's route matches; v2 supersedes it for the
    recipe-bearing catalogues.)

## Stage 4: the engine (design in LIVING_TABLE_SCHEMA.md)

The propagation engine has two contracted modes. Sweep mode:
recompute best-known for all nodes through Ns-style evaluation,
the correctness anchor, brute-force feasible in hours. Graph
mode: incremental propagation along ca_edges_v2 when an
ingredient improves, the fast path and explanation layer. They
must agree; disagreement is a bug and sweep wins. Every array an
engine produces is verified by caverify before it is stamped
(tier EXECUTED), sizes-only recomputations are tier ARITHMETIC.

12. engine_closure.R -> data/engine_nodes.csv, data/engine_links.csv
    (recipe nodes and recipe-to-recipe links, from 9).
13. engine_depquery.R, engine_walker.R, engine_substitute.R,
    engine_sweep.R: the query, walk, substitute and sweep organs
    (see each header).
14. mac_sweep.R -> data/sweep_agreement.csv, results/mac_sweep_result.txt
    Two-mode agreement test (baseline sweep, swap sweep, graph cascade).
15. mac_engine_demo.R -> data/engine_demo_diff.csv,
    results/engine_demo_result.txt
    Live propagation with every rebuilt array verified, plus the
    change-and-restore replay.
16. engine_coverage.R -> data/engine_coverage.csv
    Coverage accounting of all 13,641 entries.

## Stage 5: the ARITHMETIC tier (size laws over the unresolved entries)

Size laws recovered from the Source tags of the UNRESOLVED entries,
calibrated on every row of each family in the frozen table (the
recorded N must equal the law applied to the recorded sizes of the
named ingredients, eCAN(t, w, v) from the table itself), admitted
only where exact, and wired as an engine organ. Every size in this
tier is a claim derived from claims; nothing in it is verified, and
it is counted apart from the verified tiers. Each script tees its
log to results/<script>_result.txt; run in this order.

17. arith_measure.R -> results/arith_measure_result.txt
    The ceiling, the 9,007 UNRESOLVED entries by tag family (6,397
    in formula-bearing families).
18. Family calibrations, each -> data/<script>.csv:
    arith_formula_power.R (Power CT and Power N-CT, also writes
    data/arith_power_Mtable.csv, the fitted N-CT hash family
    table); arith_formula_dp.R (the direct product law on the
    executed DPcat recipes, reads the stage 3 substrate) and
    arith_formula_dp_table.R (the law on the frozen table);
    arith_probe_powerCZ.R (Power CZ, size law not recovered);
    arith_formula_small.R (Derive, Add 1 factor, Chateauneuf-Kreher
    doubling, perfect hash family); arith_families_probe.R (Add a
    factor, a recorded blind search with nothing admitted, the
    terminal families); arith_formula_addn.R (Add n factors for
    every n, superseding the Add rows of the small and probe csvs);
    arith_formula_mc.R (Martirosyan-Colbourn); arith_formula_fuse.R
    (every tag with a trailing fuse suffix, whole table; supersedes
    the probe's classification on fused rows whose base is in the
    table); arith_formula_cmtw.R (Colbourn-Martirosyan-TVT-Walker,
    strength 3 admitted, strength 4 open with the pure-CAN forms
    tested); arith_formula_mtvt.R (Martirosyan-TVT, even and odd k);
    arith_families_tail.R (the last 39 rows outside the
    paper-blocked families, 8 heterogeneous hash family rows
    admitted, 5 postop bound-only, 26 terminal).
19. arith_tally.R -> data/arith_tally.csv
    The arithmetic tier of every UNRESOLVED entry, ARITHMETIC 4,401,
    ARITH_INFERRED 149, ARITH_ABOVE 10, ARITH_BELOW 0,
    ARITH_BOUND_ONLY 13, TERMINAL_CLAIMED 700, ARITH_OPEN 2,901,
    NOT_ATTEMPTED 833.
20. arith_laws.R (sourced) and arith_engine.R identity ->
    data/arith_edges.csv, results/arith_engine_identity_result.txt
    The law evaluators and the engine organ; the identity run
    requires the frozen record to reproduce itself (4,401 of 4,401)
    and writes the arithmetic edges (10,328 distinct entry-to-lookup
    edges, 1,902 answering rows).
21. arith_engine.R demo -> data/arith_cascade.csv,
    results/arith_engine_demo_result.txt
    Propagation of the 17 verified improvements of
    data/better_verified.csv through the tier, graph and sweep
    modes iterated to closure and required to agree (closure two
    entries, both from CA(3, 12, 14)). arith_engine.R propagate
    file.csv does the same for a user-supplied improvements file ->
    data/arith_cascade_<file>.csv.
22. arith_coverage_republish.R -> data/engine_coverage_v2.csv,
    results/arith_coverage_republish_result.txt
    The coverage accounting over all 13,641 entries with the
    arithmetic tier counted apart (entries with a handle 9,035,
    66.2 percent).

## Provenance note

The published table itself (ca_table.csv, append-only, tiered) is
kept separately from this directory (the ca-tools table area, not
part of r/livingtable/); this directory is the engine workshop. Machine outputs here were produced on either a
cloud sandbox or the author's workstation; every number that matters
is reproducible by rerunning the scripts above against CAs and
caverify.
