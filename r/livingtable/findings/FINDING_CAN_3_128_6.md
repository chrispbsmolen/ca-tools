# Finding: THREE frozen-table entries sourced "Cyclotomy (Colbourn)"
# are unsupported, all type 3a (updated 2026-08-30 after the full
# catalogue audit; originally the single q=127 finding of 2026-08-29)

Status note for the repository copy (2026-09-05): fixed upstream. The
CAs GitHub commit ae81661 of 2026-09-04 switched these three
CYCLOTOMYcat rows to type 4a (sizes vq + v: 768, 43,240, 48,552).
The type-4a arrays were checked in this directory (mac_4a_q127.R:
full verification at q=127; mac_4a_check.R: 48 caverify windows each
at q=2161 and q=2311, all pass; logs in results/). The text below is
the finding as written before the fix.

## Update, full-catalogue audit (workstation, 213 rows, audit2)

210 of 213 CYCLOTOMYcat rows pass (16 fully certified, 194 pass a
50-column screen). THREE fail, ALL type 3a, all matching
frozen-table rows sourced "Cyclotomy (Colbourn)", all winning the
size comparison in Ns so bestCA serves each broken array silently:

  t=3 k=128  v=6   N=762    q=127   (FULL verification failure)
  t=3 k=2162 v=20  N=43220  q=2161  (screen failure, proof of defect)
  t=3 k=2312 v=21  N=48531  q=2311  (screen failure, proof of defect)

A screen failure is proof (a subset of a covering array's columns
must itself cover). The type-3a pattern suggests one shared cause,
likely the 3a precondition failing at these q while the catalogue
row was inherited from the frozen tables unchecked (the CAs
documentation notes the checks "take a long time for large cases").

## Closure (follow-up, 2026-08-30): isolated and repaired

Multi-window screens (first 50, last 50, two random 50s) on all
194 giant rows: ZERO new failures. The defect is confirmed
isolated to exactly the three type-3a rows above. Repairs, all via
the type-3b sibling at the same q:

  q=127:  CA(792; 3, 128, 6)     FULLY VERIFIED
  q=2161: 43,600 x 2162 (v=20)   all four windows pass (screen-grade)
  q=2311: 48,951 x 2312 (v=21)   all four windows pass (screen-grade)

Structural confirmation: each repair costs exactly v(v-1) rows
over the failing type-3a size (30, 380, 420), one consistent
formula, so the 3b route is behaving lawfully at all three q.
Audit artifacts: data/cyclotomy_audit2.csv, data/cyclotomy_screen4.csv,
result logs in results/. The finding is COMPLETE: three
frozen-table entries unsupported by their cited source, cause
pattern named, blast radius measured (3 of 213), every repair in
hand at the strongest feasible tier. Remaining open item: the
Colbourn (2010) paper check (paywalled), which decides erratum
versus transcription slip.

# Original finding (t=3, k=128, v=6), triple-certified 2026-08-29

## The claim under examination

The frozen Colbourn tables (November 2024 snapshot, via
colbournBigFrame in CAs 0.24) record CAN(3, 128, 6) <= 762 with
Source "Cyclotomy (Colbourn)". The CAs CYCLOTOMYcat maps this to
cyc(127, 6, type="3a"), 762 = 6 x 127 rows, k = q + 1 = 128.

## What was established, each point by execution

1. The constructed type-3a array (762 x 128) FAILS strength-3
   coverage: 5,334 of 341,376 projections gapped, 32,004 missing
   tuples. caverify and CAs::coverage() agree EXACTLY.
2. The failure is not the primitive root: all 36 primitive roots
   of GF(127) were tried; none yields a covering array.
3. The failure is not a generator slip: the CAs condition checker
   checkcond3a(3, 6, 127) returns FALSE, the type-3a precondition
   provably does not hold there. The checker discriminates
   correctly: TRUE on control rows (3,4,53) and (4,2,23) whose
   arrays verify.
4. The blast radius is one row: 14 of 15 cheaply-verifiable
   CYCLOTOMYcat rows pass, including six other type-3a rows.
   Full-catalogue audit script run on the workstation (audit2).
5. The repair: type 3b at the same q builds a 792 x 128 array
   that VERIFIES (zero gaps; its checker condition is FALSE, but
   the conditions are sufficient, not necessary, and the array
   itself is checked). So cyclotomy legitimately achieves 792
   there, not 762.

## Current best verifiable state at (3, 128, 6)

VERIFIED: 792 (cyc(127, 6, type="3b"), array in hand, full
caverify pass). The recorded 762 has, at present, no verifiable
support: its cited construction fails its own precondition and
fails coverage under every primitive. Best other implemented
route: 1054 (CK doubling).

## What is NOT yet established

Whether Colbourn (2010) itself claims 762 at these parameters
(the paper is paywalled from the sandbox; the CAs documentation
already notes "various mistakes were found in tables of Colbourn (2010)"), and
whether any non-cyclotomy source in the literature attains 762 or
less. Until those are checked, this is stated as "the table
entry's cited support is invalid and the best verifiable value is
792", NOT as "CAN(3,128,6) = 792" and NOT as "the table is wrong
by 30".

## Practical consequences

- CAs users calling bestCA(3, 128, 6) today silently receive a
  non-covering array (the broken 762 route wins the size
  comparison). One catalogue row is the fix (762/3a -> 792/3b).
  (Since fixed upstream via type 4a, see the status note above.)
- First live demonstration of the living-table mission: the
  frozen record carries at least one entry whose citation cannot
  support it, found by systematically executing and verifying
  the record. The 969 other MATCH entries passed the same
  treatment where run (438 executed-verified so far, this the
  only failure).
