# Finding 2: the frozen-table entry (t=3, k=1584, v=2, N=64) is
# unsupported as implemented (2026-08-30, grind catch)

Status note for the repository copy (2026-09-05): fixed upstream. The
CAs author diagnosed a constant-row defect in DHHF2CA (2026-08-31)
affecting the chi > 0 rows of powerCTcat, and the CAs GitHub commit
d1c6570 of 2026-09-04 fixed it. The post-fix re-audit in this
directory (mac_powerct_refix.R, data/powerct_refix.csv,
results/powerct_refix_result.txt) builds powerCA(3, 1584, 2) as
64 x 1584 and verifies it in full (EXECUTED_POSTFIX), with the other
13 diagnosed rows passing full verification (1) or 4-window screens
(12). The text below is the finding as written before the fix.

Snapshot row: N=64, Source "Power CT12^3,cT1". The CAs powerCT route
reproduces the size (Ns: powerCT=64, equal to eCAN) and is
route-dominant, so bestCA(3, 1584, 2) serves the array silently.

Established by execution:
1. The built 64 x 1584 array FAILS strength-3 coverage: exactly
   123 of 661,136,784 triples gapped, every missing tuple (1,1,1),
   123 total missing tuples (caverify, full verification).
2. Independent confirmation with plain R (direct any() scan, no
   caverify logic): the reported tuples are truly absent.
3. The array is otherwise healthy: every column balanced (31-33
   ones in 64 rows), no degenerate columns. The 123 gaps touch
   126 distinct columns spread across the full width. A near-miss,
   consistent with a subtle defect in the cover-starter (cT1)
   component or its parameters (catalogue row: Pbase 12, expon 3,
   OAforDHF miscCA(3,6,12), M=5, weights 12/4, 11/1, ..., constr
   TJ + PALEY, chi=1), not a gross construction error.

Not yet established: whether the defect is the CAs implementation,
the catalogue row's parameters, or the published claim itself
(the power-CT/cover-starter literature check pending). Family
blast radius pending: powerct audit script prepared, run after
the grind finishes (both use the same workstation).

Status: second confirmed defective frozen-table entry (after the
three cyclotomy type-3a rows; this one is a different
construction family). Verified-alternative note: Ns shows DWYER=66
at these parameters, so a certified fallback likely exists two
runs larger; to be pinned when the family audit runs.
