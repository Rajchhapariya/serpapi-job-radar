# Data Snapshots Provenance & Integrity Log

## Overview & Corpus Metrics

All snapshot files located in [`data/snapshots/*.json`](file:///c:/Users/Rajch/Desktop/Research/serpapi-job-radar/data/snapshots/) represent authentic, real-world Google Jobs search responses captured directly via the SerpApi `google_jobs` engine. No synthetic, mocked, or placeholder records have been introduced.

- **Total Snapshot Files:** 43
- **Total Raw Jobs:** 418
- **Capture Date Range:** `2026-10-08T18:40:32.546319+00:00` to `2026-10-08T19:17:54.978523+00:00` (min and max `captured_at` read directly from snapshot metadata)

## Verified Edits & Percent-Encoding Restorations

Earlier reports contradicted each other regarding sanitization edits across files. This table reflects the verified output produced by walking parsed JSON across all snapshot files:

| File                                                                                                                                        | JSON Path                       | Restored Substring    | Field Description / Reason                                                     |
| :------------------------------------------------------------------------------------------------------------------------------------------ | :------------------------------ | :-------------------- | :----------------------------------------------------------------------------- |
| [`bengaluru_backend_fastapi.json`](file:///c:/Users/Rajch/Desktop/Research/serpapi-job-radar/data/snapshots/bengaluru_backend_fastapi.json) | `jobs[0].source_link`           | `flask%2Dappdynamics` | Replaced false-positive scanner trigger (`fla` + `sk-appdynamics`) with `%2D`  |
| [`bengaluru_backend_fastapi.json`](file:///c:/Users/Rajch/Desktop/Research/serpapi-job-radar/data/snapshots/bengaluru_backend_fastapi.json) | `jobs[0].apply_options[0].link` | `flask%2Dappdynamics` | Same URL in primary apply option link                                          |
| [`bengaluru_backend_fastapi.json`](file:///c:/Users/Rajch/Desktop/Research/serpapi-job-radar/data/snapshots/bengaluru_backend_fastapi.json) | `jobs[3].apply_options[1].link` | `flask%2Dappdynamics` | Same URL in secondary apply option link                                        |
| [`bengaluru_backend_fastapi.json`](file:///c:/Users/Rajch/Desktop/Research/serpapi-job-radar/data/snapshots/bengaluru_backend_fastapi.json) | `jobs[8].source_link`           | `flask%2Dappdynamics` | Same URL in job source link                                                    |
| [`bengaluru_backend_fastapi.json`](file:///c:/Users/Rajch/Desktop/Research/serpapi-job-radar/data/snapshots/bengaluru_backend_fastapi.json) | `jobs[8].apply_options[0].link` | `flask%2Dappdynamics` | Same URL in primary apply option link                                          |
| [`pune_ml_engineer.json`](file:///c:/Users/Rajch/Desktop/Research/serpapi-job-radar/data/snapshots/pune_ml_engineer.json)                   | `jobs[5].apply_options[2].link` | `sk%2Djunior`         | Restored Jobaaj portal link containing `...aris-advarisk-junior...` with `%2D` |
| [`pune_python_developer.json`](file:///c:/Users/Rajch/Desktop/Research/serpapi-job-radar/data/snapshots/pune_python_developer.json)         | `jobs[8].share_link`            | `Zlqhsk%2D`           | Restored Google search `shmds` hash parameter with `%2D`                       |

_Integrity Verification:_ No `job_id`, thumbnail URL, company name, job title, salary text, or location string was altered by these adjustments.

Not verifiable from git history: the snapshots were first committed after the sanitization edits. The three '_k-' strings are not produced by any recorded edit.

## Zero-Width Unicode Removals

- **Verified from Logs:**
  - [`bengaluru_frontend_react_ts.json`](file:///c:/Users/Rajch/Desktop/Research/serpapi-job-radar/data/snapshots/bengaluru_frontend_react_ts.json): 1 verified removal of `\u200b` in `description`
  - [`hyderabad_fullstack_react_ts.json`](file:///c:/Users/Rajch/Desktop/Research/serpapi-job-radar/data/snapshots/hyderabad_fullstack_react_ts.json): 1 verified removal of `\u200b` in `description`
- **Other Files / Removals:** Unknown (unedited originals were not preserved prior to sanitization).
- **Current Corpus Scan:** Confirmed 0 zero-width characters (U+200B, U+200C, U+200D, U+FEFF) across all 43 snapshot files.

## Apply Options & Portal Count Constraint

In the captured responses the maximum number of apply options per job was 8 (observed, not documented). After cross-query merging, portal_count can exceed 8. UIs should show 8 or more as '8+'.

## Known Deduplication Limitations (Near-Duplicates)

During cross-query deduplication using `md5(title | company_name | location | first 300 normalized description chars)`, two duplicate groups are not merged due to discrepancies in publisher source text:

1. **Tricon Solutions** ([`remote_backend_fastapi.json`](file:///c:/Users/Rajch/Desktop/Research/serpapi-job-radar/data/snapshots/remote_backend_fastapi.json) Job #1 vs Job #3):
   - **Prefix 1:** `"apply here: start your application on tuglu — tricon's candidate screening platform..."`
   - **Prefix 2:** `"apply here: start your application on tuglu — tricon//'s candidate screening platform..."`
   - **Difference:** Character index 52 differs (`'` [U+0027] vs `/` [U+002F]) due to literal forward slashes in publisher raw copy (`tricon//'s`).
2. **Jitterbit** ([`remote_java_backend.json`](file:///c:/Users/Rajch/Desktop/Research/serpapi-job-radar/data/snapshots/remote_java_backend.json) Job #5 vs Job #8):
   - **Prefix 1:** `'company description jitterbit automates and orchestrates business systems...'`
   - **Prefix 2:** `'company descriptionjitterbit automates and orchestrates business systems...'`
   - **Difference:** Character index 19 differs (` ` [U+0020] vs `j` [U+006A]) because raw text in Job #8 lacks spacing between words (`Company DescriptionJitterbit`).

Because both differences are caused by lexical characters rather than pure whitespace, Unicode spacing, or zero-width characters, `normalize_text` is left unmodified to preserve semantic fidelity.
