## Broader early-warning test — declared 18 October 2026

**Question.** Does issuer credit and funding information warn of equity stress earlier or more reliably than price-only and broad-credit signals, when every signal is scored on the same eligible issuer-sessions?

**What was declared, and when (UTC, 18 October 2026).** All times come from the files themselves.

| Time | Step | File |
|---|---|---|
| 11:10 | Protocol frozen: universe, targets, signals, periods, tests and success criteria | `research/credit_funding/early_warning_protocol_20261018.json` |
| 11:12 | Bond-identifier searches; abbreviated search terms added for seven issuers before any outcome | `data/early_warning_20261018/search_amendment.json` |
| 11:14 | Mechanical bond selection from FINRA metadata only. Version 2 replaced version 1, which preferred rarely traded Reg S twins; v1 is kept | `selection.json`, `selection_superseded_v1.json` |
| 11:17 | Equity identity and coverage checks; SATS, WBD and PARA excluded with reasons | `equity_quality.json` |
| 11:25 | All 1,801 evidence files pinned | `manifest.json` |
| 11:27 | Development phase (2022-2023) recorded once | `early_warning_development_receipt_20261018.json` |
| 11:31 | Holdout phase (2024 to 16 Oct 2026) recorded once | `early_warning_holdout_receipt_20261018.json` |

No threshold, horizon, universe member or signal definition changed after any outcome was computed. Bond histories and equity prices were downloaded only after the selection was written. Both phases ran on the same calculation module (SHA-256 `1442478b…`), recorded in each receipt.

**Universe.** 38 US-listed issuers in capital-intensive, debt-funded sectors (cable, telecom, towers, data centres, semiconductors, storage, energy, airlines, cruise, autos, casinos, power, steel), two mature cloud contrasts (AMZN, META) and four convertible-funded growth issuers (RIVN, LCID, PLUG, RUN). The seven issuers examined on 17-18 October (CRWV, APLD, IREN, NBIS, CORZ, ORCL, EQIX) are excluded: they are development evidence only.

**Target.** Nonoverlapping equity stress episodes: the first close at least 20% below the prior 60-session high, ending on recovery to 90% of that high or after 60 sessions. A warning must come 1 to 20 sessions before onset. Alarms on the onset day, or during an episode already under way, are reported separately and never counted as warnings. A secondary target applies the same rule to performance relative to SPY.

**Signals.** P1 is a daily fall of 5% or more and P2 a 10% drawdown from the 60-session high. B1 is ICE BofA US high-yield OAS and B2 the Moody's Baa-Treasury spread. I0 is the earlier frozen raw-yield rule and I1 the same rule applied to G-spreads (yield minus the interpolated Treasury curve). I2 adds an excess-over-index condition. F1 and F2 are funding watch and funding gap from 10-Q and 10-K filings. E1 and E2 combine P2 with I1 and F2. Each signal is dated by when its data was actually public: TRACE and ICE values the next session, filings the first close after SEC acceptance.

**Data and its limits.**

- **Bond prices:** FINRA TRACE end-of-day last sale for up to four straight fixed-coupon bonds per issuer, from one exact legal borrower. These are current-vintage downloads; the historical delivery times of these prints are unknown.
- **No OAS:** G-spreads are not option-adjusted. No free issuer OAS history was found.
- **Convertibles** are excluded from every spread, because their prices carry equity optionality.
- **Not pooled:** different legal borrowers are never combined to reach the two-bond quorum.
- **Guarantees and collateral:** FINRA metadata has no guarantor or collateral fields, so these are recorded as UNVERIFIED.
- **Equity and curve data:** prices are Yahoo adjusted closes in their current vintage. The Treasury curve and spread indices come from FRED in its current vintage. FRED serves ICE indices only from October 2023, so B1 is unavailable in development.
- **Funding data:** SEC XBRL company facts and the submissions index. Acceptance timestamps set when each filing becomes usable. These were added in a separate dated addendum after the author authorised a contact email at 12:30 UTC (see *Funding addendum* below). Restricted cash, undrawn facilities and financing proceeds are recorded but never counted as cash. SATS has no SEC CIK in the current ticker map.

<!-- notebook-intro-end -->

### Findings

**1. The earlier four-of-six result carries no evidence of skill.** Using each issuer's own ordinary-day rate of a 10% interim loss within 20 sessions (APLD 75%, IREN 77%, NBIS 60%, CORZ 65%, ORCL 45%, EQIX 1%), four or more hits out of six would happen by chance about 41% of the time.

**2. The issuer credit rule never fired in the untouched holdout.** Across 10,804 issuer-sessions on which price, broad-credit and issuer-credit signals were all evaluable (26 of the 31 bond-eligible issuers had any evaluable coverage, 2024 to 16 October 2026), the G-spread rule I1 produced zero alarms. The raw-yield rule I0 produced one, a false alarm. The verdict under the frozen criteria is **INCONCLUSIVE_LOW_POWER**: there is too little issuer-credit activity to score, and certainly no demonstrated improvement. The closest approach was Caesars on 9 April 2025, when its second-widest bond widened 97 bp, during the tariff sell-off and not before it.

**3. Broad credit stress arrived with equity stress, not before it.** The high-yield OAS rule fired on one date, 9 April 2025. Because it is market-wide, that one date appears as 16 issuer alarms on the identical sample. Eleven of them fell inside episodes already under way, five were false alarms, and none was an advance hit. This is one event, not sixteen pieces of evidence.

**4. Price-only signals beat random timing, partly by construction.** On the same sessions, P1 and P2 had precision of 24% and 23% against a base rate of 12%. Within-issuer circular-shift permutation tests gave p = 0.001 and 0.0035. These tests compare against random alarm timing, not against simply being in a drawdown. P2 fires at a 10% fall from the same 60-session high that defines the 20% target, so part of its edge is mechanical. Each warned 23 of 43 episodes, with a median lead of 9 to 10 sessions. They are still noisy: P2 raised about two false alarms per 250 issuer-sessions, and three of four price alarms were not followed by an episode. The SPY-relative target gives the same ordering, with P2 at 30% precision against a 14% base rate.

**5. Development (2022-2023) showed the same pattern.** On each issuer's own bond coverage (the common sample is empty in development), all six issuer-credit alarm onsets fired during episodes already under way. None was an advance hit. They were coincident, not leading.

### What this does and does not show

- This is retrospective evidence on current-vintage data. It is not prospective validation, and nothing here changes portfolio weights or the prospective paper journal.
- Zero issuer alarms means the frozen rule (100 bp over a 20-observation median, persisting three observations, on two bonds) is too insensitive for 2024-26 conditions in these issuers. It does not prove that issuer spreads carry no information. A more sensitive rule would need a new declaration and new untouched data, because these holdout dates have now been seen.
- Coverage is uneven. TRACE prints for many high-yield bonds are too sparse for the four-day gap rule. For AAL, CLF, DVN and part of APA, the selection still chose Reg S international CUSIPs because no registered or 144A twin appeared in the search, and those rarely print. Several issuers (STX, APA, DVN, AAL, CLF, SBAC) have little or no evaluable issuer-credit coverage, and they stay unknown, not "no warning".
- The main holdout used the three-family sample `common_no_funding`; the funding addendum then scored the declared four-family primary sample. Both are reported.

### Funding addendum (declared 12:32 UTC, scored after the main holdout)

The funding rules F1, F2 and E2 were frozen at 11:10 with everything else. They are scored here without change on the declared primary sample: sessions where the price, broad-credit, issuer-credit and funding signals are all evaluable. The parser was corrected before any filing was parsed. The SEC download began 23 seconds before the declaration was written, but nothing was read until 12:34 (`funding_addendum/declaration.json`). The declaration's parser hash covers the parsing logic; the manifest's hash also covers the I/O helpers appended afterwards. The holdout price episodes had already been seen, so this addendum cannot be tuned, but it is not blind to the episode set.

- **Coverage:** 2,234 periodic filings in the ledger, 781 of them accepted inside the panel (June 2021 onward). Older filings map onto the first panel session, but they are superseded and stale before the development period starts, so they affect no scored number. Unknown states come from missing debt tags (292), missing cash-flow tags (85) and trailing twelve-month totals that cannot be built (186). A missing cash tag leaves the funding watch known and makes only the funding gap unknown.
- **Holdout result on the declared primary sample** (7,685 issuer-sessions, 37 episodes, base rate 14.5%):
  - The funding watch F1 fired 28 times, with 3 hits and 18 false alarms. Its precision of 14% equals the base rate (permutation p = 0.68).
  - The funding gap F2 fired 5 times with no hits.
  - Price alarms filtered by funding or credit state (E2) fired 6 times with no hits.
  - On the same sessions, the price signals P1 and P2 had precision of 28% and 24% (p = 0.002 and 0.029).
- **Verdict under the frozen criteria:** funding information is **NOT_ESTABLISHED** as an improvement, and issuer credit stays **INCONCLUSIVE_LOW_POWER**.
- **One post-hoc lead, which is not a declared test.** On each issuer's own funding coverage, a wider sample that includes convertible-funded issuers, price alarms during an active funding gap were right more often than price alarms alone. Holdout: 13 of 29 (45%) against 61 of 209 (29%). Development: 14 of 21 (67%) against 53 of 137 (39%).
  - In the holdout the gain is not significant. The issuer-bootstrap 90% interval runs from −5 to +35 points, and the permutation p is 0.16.
  - It is also concentrated. Lucid supplies 6 of the 13 holdout hits. In development, 11 of the 14 hits are cruise lines in 2022, which is one sector shock, so the development p of 0.009 is not independent evidence.
  - Because the issuer-credit rule never fired in the holdout, E2 there is simply "price alarm during an active funding gap".
  - It was chosen after reading the receipts, so it can only be validated prospectively or on new issuers. It is saved separately in `early_warning_funding_posthoc_20261018.json`.

### Independent review notes (after the holdout run)

An independent read-only review found no blocking error. Timing, sample identity, episode logic and every number above were checked against the receipts. It raised non-blocking points, which are disclosed here instead of rerunning the recorded phases:

- **Recall counts alarm days that fall inside an earlier episode.** This contradicts the in-episode rule. It explains why B1 shows one "warned" episode with zero hits, and why development I0/I1 show two warned episodes. Precision, the decision metric, is unaffected.
- **The permutation statistic is computed within the period, on issuers with at least 81 eligible sessions.** Its observed precision is 24.4% and 23.6%, slightly different from the table.
- **Development alarms in late December 2023 can be scored against January 2024 onsets.** These are price outcomes only and do not touch any rule.
- **I2 treats a missing high-yield value as "no excess" rather than unknown.** I2 never had an I1 alarm to filter, so this has no effect here.
- **The bootstrap resamples issuers with no eligible sessions.** This widens intervals slightly.
- **The SEC parser has edge cases to fix before the funding arm is scored:** 52/53-week years, a tag mismatch between YTD and annual values, multi-line capex, and amended filings for older periods. The parser has not yet run on real data.
- **The consolidated-subsidiary condition is enforced only by a declared exclusion list.** It is not checked against the filings.

### What would be needed to go further

1. Test the post-hoc funding-gap filter prospectively, or on issuers and dates not used here, with its rule frozen first.
2. Obtain issuer and peer OAS with dated vintages. This likely means a licensed source, which needs approval.
3. Obtain historical guarantor, collateral and legal-borrower mappings, for example from indentures.
4. Run any new, more sensitive spread rule prospectively, or on a later period nobody has examined.
