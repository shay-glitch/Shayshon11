# ShippingToGo - IIA R&D application - gap review (Claude)

Date: 28.9.2026. Reviewed: "ShippingToGo - תוכנית מלאה לרשות החדשנות" (Hebrew plan, 24.9) against "IIA - ONE BRAIN handoff" (24.9).
Role per ONE BRAIN section 7: consistency check, IIA rule check, final review. Nothing here is submitted anywhere.

## A. Hard blockers (the application cannot win, or cannot be filed, until these close)

1. IP chain of title. Founder invention assignments name ShippingToGo US, Inc., not Shipping To Go Ltd. Signed assignment or licence to the Israeli company is needed before filing. Owner: Shay + lawyer (draft already exists in Drive).
2. OnRoute FZCO (Dubai, owned by Lior). The plan says UAE penetration runs through Lior's relationships. IIA-funded know-how must stay in the Israeli company. The application must state clearly that OnRoute receives no licence or transfer of funded know-how, and disclose it as a related party. Otherwise it reads as planned know-how transfer abroad.
3. FY2025 numbers conflict: USD 3.25m / 38.4% vs signed report showing 3,088,061. Finance (Shira) must name the governing audited statements. One number everywhere.
4. Track not chosen: general R&D Fund vs Early Growth. Early Growth needs Finance sign-off on the four gates.
5. Matching finance. The company funds 50-80% of the budget. Need bank statements / cash runway / investor commitment showing it can carry its share for 12 months.

## B. Consistency conflicts between the two documents (must be one version)

| Topic | Hebrew plan | ONE BRAIN | Fix |
|---|---|---|---|
| Work packages | 9 WPs (incl. WP9 pilot, 20 UAE customers) | 5 WPs | Use the 5-WP structure. WP9 is sales, not R&D; move it to "commercialisation plan". |
| Budget | NIS 4.5-5.5m, table sums ~NIS 3.9m, salaries estimated | NIS ~3m illustration, payroll-based only | Rebuild from Shira's payroll x R&D share. Drop the "expand to 4.5-5.5m" line. |
| Kobi | 100% R&D | "Kobi confirms %" | CTO also runs production; 100% will be challenged. Claim what Git/timesheets support. |
| Ops staff (Avi, Hani, Gal, Tzofia, Ummer, Bar) | 30-60% R&D each | only logged R&D hours | Ops people as annotators is a red flag for the reviewer. Keep only Hodaya/Bar with a defined labelling task and hour logs. Bar may have left; confirm. |
| R&D abroad | "we'll set it at 40% to pass" | 200-06 prior approval + cap | Delete that sentence. Abroad R&D needs a 200-06 request with a justification (skills not available in Israel). Confirm location/status of Darshan, Mobeen, Slava, Ilia. |

## C. What the reviewer (בודק מקצועי) scores, and where we are weak

1. Technological uncertainty. Needs its own section: what we do not know how to do yet and why it is hard (HS accuracy with refusal threshold, scarce Arabic shipping data, mixed-language descriptions, heterogeneous carrier rate formats). Right now it is scattered.
2. State of the art and competitors. Missing entirely. Must name existing solutions (e.g. Zonos Classify, Avalara, Easyship, Shippo, Flexport, generic LLMs) and state what they cannot do that our data-trained, HE/EN/AR, closed-loop model can. Without this, "no one has this" will be marked down.
3. Unsourced figures. "Accuracy 78% today", "~100K invoice PDFs", "COGS down 60%", "API cost down 70%", "WER < 12%", "UAE market USD 1.0-1.4B". Each needs a source or must be labelled a target/estimate.
4. In-house vs third party contradiction. Budget line "GPU / Vertex / OpenAI" undercuts the "replace third-party AI" story. Split: training compute (eligible) vs API run cost (explain as baseline/benchmark only).
5. Measurable milestones. Every WP needs one numeric acceptance test with baseline measured now (use ONE BRAIN table). Measure baselines before filing so numbers are real.
6. Team capability. CVs for every R&D person, plus proof of past delivery (the live AI features: HS estimator, AWB intake, FedEx invoice comparison). Screenshots / Git evidence from Codex.
7. Economic impact in Israel. Jobs added in Israel, export revenue, royalties plan. Reviewer wants to see funded R&D staying and growing in Israel.

## D. Missing attachments / forms

- Online form (RND_Request) - draft by Instinct, not yet read back by Codex.
- Signed declaration and authorisation (הצהרה והרשאה), authorised-signatory affidavit (תצהיר מורשה חתימה).
- Shareholder table and cap table, certificate of incorporation.
- Audited financials FY2023-FY2025 (the governing set) + 2026 management P&L.
- Official IIA budget Excel, reconciled to payroll.
- 200-06 request for any R&D abroad.
- Signed IP / employment / contractor agreements for every claimed person.
- CVs for all R&D staff.
- Letter of intent / customer interest from UAE (without inventing revenue).
- Timesheet system in place from the first day of the filing month (costs only count from then).

## E. Cleanup of the Hebrew plan before anyone outside sees it

- Remove chat residue: "כפי שביקשת", "כפי שצוין בהודעה הקודמת", "בהצלחה! שי (Instinct)", "כבר הוצאנו הרבה - כפי שציינת".
- Remove "נגדיר אותם כ-40% כדי לעבור חלק".
- No em dashes, no AI boilerplate (ONE BRAIN section 8).
- Do not describe know-how as owned by Shipping To Go Ltd until A1 is signed.

## F. Order of work

1. Shira: governing FY2025 numbers + payroll per person. 2. Kobi: location/status of engineers, R&D %, baselines for each WP KPI. 3. Lawyer: IP assignment signed; OnRoute disclosure. 4. Claude: rewrite narrative on the 5-WP structure with sections C1-C2-C7. 5. Codex: Git evidence + tech spec. 6. Instinct: forms, Excel, attachments. 7. Lior + Kobi approve. 8. Shay submits in October.
