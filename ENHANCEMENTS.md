# Summary exports and snapshot comparisons

Backup: `backup/pre-enhancements-2026-09-26` (baseline `6543fb0`). Schedule and existing whale rules are unchanged.

New outputs: `latest/summary.json` (no chart arrays) and `latest/probability-snapshots.json` (up to four days, 100 snapshots per outcome). Existing dashboard and market detail paths are retained. Summary upload follows detail uploads. R2 credentials now need object read permission as well as write permission to continue snapshots across GitHub runners.

The same outcome token and price source must match. Select the latest snapshot at or before 24 hours before the current collection, no more than `CHANGE_MAX_GAP_HOURS` (default 6) before that target. Delta is `100 * (current probability - prior probability)`, in percentage points. Missing history/source mismatch => null. At least two suitably timed successful collections are needed; daily schedule jitter can mean no eligible comparison on a particular run.

The export records price provenance, comparison time/price, source resolution text and which outcome supplies the existing chart. Monetary fields preserve precision in millions; missing values are null rather than manufactured zero. This does not alter the existing trade-notional anomaly algorithm.

The existing past-end trade retrieval cap remains; its limitations are disclosed in the dashboard methods page. `count_24h` is a legacy fetched-sample count; consumers should use `whale.latest.time` to decide whether a signal is actually recent.

Test: `python -m unittest discover -s tests -v`. No network required. Run the existing collection action after deploying, or await its daily schedule. To roll back, revert the enhancement commit on main; do not delete historical R2 objects. The dashboard supports prior exports.
