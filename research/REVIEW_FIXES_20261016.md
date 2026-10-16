# Reviewed portfolio construction amendment — 16 October 2026

This is the maintained, executed amendment, using the dated price vintage through **15 October 2026**. Run `python run_reviewed_analysis.py` from the repository root in the documented environment to reproduce it. The runner writes a new output directory; it never overwrites the frozen baseline.

The review fixes three reproducibility defects:

1. The executed amendment was only in ignored output folders. A reviewed copy is now published as `portfolio_construction_amended.ipynb`, separately from the unchanged `portfolio_construction.ipynb` baseline.
2. The earlier runner did not bind the paper protocol, parent protocol and forecast-outcome registry to the recorded freeze before executing. A new read-only integrity cell verifies their exact hashes, pinned source, data and runtime versions before calculations.
3. Hash-chain checks alone accepted an absent journal or deletion of its final entry. The reviewed notebook requires the retained entry count, terminal hash and protocol binding. A later journal or input vintage needs a separately declared review; it must not replace this snapshot silently.

Git attributes now preserve the bytes of hashed code, notebooks and data across checkout platforms. Both frozen protocols and their pinned source remain unchanged. The review adds one executable integrity cell and strengthens the journal read; it does not tune allocations, uncertainty assumptions or transaction costs. All calculation functions remain embedded in the notebook; the new project import performs provenance checks only.

**Interpretation:** this is a retrospective reconstruction, including common-risk controls, prior-only basis diagnostics and gated forecast calibration. The common-risk scenario returned 5.56% versus 5.74% for equal weight over 53 sessions. This does not demonstrate an advantage. There are zero qualifying completed forecast cycles; the 10% forecast and 2% mapping assumptions remain uncalibrated. The separate paper decision is recorded evidence of intent, with no observed outcome in this snapshot.

Earlier dated commentary below describes the baseline or preceding refresh. The final implementation review supersedes its pending-work statements. This opening declaration identifies the additional software fixes, rather than reclassifying earlier research as prospective evidence.
