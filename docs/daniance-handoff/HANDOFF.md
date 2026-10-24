# Daniance — handoff for rebuilding in Figma

Daniance is a portfolio case study: a web finance dashboard for UK small businesses, with AI that answers money questions by redrawing the cash forecast. It started as a 5-day design home task (originally called BizFinTrack) and is now framed as an independent B2B fintech project, not tied to any company.

**Goal of the rebuild:** small and sharp. Show small-business B2B fintech design ability, with the AI moment as the centrepiece. Build in the author’s Figma education team.

Reference prototypes in this folder:
- `prototypes/daniance-ask.html`: the new Home with the Ask bar and the hiring answer (also published at https://claude.ai/artifact/3g1yyDd6aus6nVYg3Nhsjs)
- `prototypes/bizfintrack-prototype.html`: the earlier full prototype (Home, P&L owner/accountant, Goals, Accounts, Open Banking connect flow). Rename BizFinTrack to Daniance and Revolut accounts to Daniance accounts when reusing.

## 1. File structure (3 pages)

1. **Case study** (1920 wide, dark stage `#0C0D0F`, about 6 sections)
   1. Cover: “Daniance”, one-line positioning, hero = Home with an AI answer, in a thin browser window (traffic lights + URL `app.daniance.com/home`).
   2. Problem: context (5.5m UK private businesses, 5.45m with fewer than 50 people), one key stat (56% decide on incomplete information), one owner quote, then a blue “So the problem is…” box: *Owners have all the numbers spread across their tools, and still can’t quickly tell whether the business is okay this month or what to do next.*
   3. Insight: Xero (JAX) and QuickBooks (Intuit Intelligence) already offer AI chat. They answer what is in the system, not whether the owner can do something. Use `research/xero-jax-chat.webp` (asked “how much money do I have?”, got a list of accounts; note the demo company had no bank connected).
   4. Iteration: V1 AI chat as Home (rejected: owners don’t know what to ask, text answers about money are hard to trust) → V2 one number, Safe to spend from today’s balance (too optimistic: payroll and VAT land before invoices) → V3 answer first, and AI draws its answer onto the cash forecast. Leave dashed placeholders for the author’s paper sketches.
   5. Core experience: Flow “Can I hire someone?” in 4 states (ask → thinking → answer → change start date to February and recalculate). One sticky note per state.
   6. Trust design: shows its working, editable assumptions, data freshness, hand-off to the accountant, stale-data answer.
2. **Prototype**: 5 to 6 screens at 1440×900, nav and top bar fixed, content scrolls. Home (before asking), Thinking, Answer (start 1 Jan, February under buffer), Answer (start 1 Feb), Accountant check view (Tom sees the scenario with a comment), Stale data answer (HSBC not synced). Wire them with prototype links.
3. **Research**: every screenshot in `research/` with its numbers and source link. The case study keeps only core evidence; this page supports every sentence.

## 2. Visual system (keep it light in the case study)

Inspired by Behance B2B dashboards: floating rounded panels on a cool grey canvas, black active nav pill, big page title, KPI strip where the selected tile is brand blue and drives the chart, hatched forecast bars.

- Font: Geist (Regular, Medium, SemiBold). Tabular numbers.
- Colours: canvas `#EEF0F3`, panel `#FFFFFF`, subtle `#F5F6F8`, ink `#121417`, secondary `#5D6570`, tertiary `#8A919B`, border `#E6E8EC` / `#CDD2D9`, brand `#2C46DB`, brand subtle `#ECEFFD`, hatch `#BCC7F6`, positive `#12715B` on `#E4F3EC`, caution `#8F5300` on `#FCF0DA`, risk `#B3261E` on `#FCEAE8`.
- Type: H1 40/48 SemiBold −2%, KPI 32/40 SemiBold, H2 20/28, H3 16/24, body 14/20, caption 12/16.
- Radii: panels 24, cards 20, controls pill (999). 8pt grid. Buttons 44 / 36 tall.
- Layout at 1440: sidebar card 240 wide at x16 y16; top bar card 1152×76 at x272 y16; content at x272 y124, width 1152.
- Status pills always pair colour with a word (Late, Behind, On track).

## 3. Data (keep numbers consistent)

Business: Dan Studio, 4 people, owner Maya Chen, external accountant Tom Price. Today: Thursday 23 October 2026.

- Cash today £24,300 = Daniance Main £13,550 + Daniance Tax £5,350 + HSBC £5,400.
- 30-day forecast events: 28 Oct payroll −£7,200; 1 Nov rent −£2,100; 3 Nov Acme pays +£4,520 (invoice due 11 Oct, Acme usually pays about 3 weeks late); 7 Nov VAT for Jul–Sep −£6,100; 10 Nov Brightside pays +£6,800; 20 Nov subscriptions −£480.
- Lowest point £13,420 on 7 Nov. Buffer £5,000. **Safe to spend £8,420 until 22 Nov.**
- Coming in 30 days £11,320, going out £15,880.
- Hiring scenario: junior designer, £28,000 a year. Monthly cost about £2,680 = salary £2,333 + employer NI £288 (15% above £5,000, 2025/26) + pension £54 (3%). Employment Allowance may reduce employer NI, so “Ask Tom to check”.
- Lowest balance per month, now: Nov £13,420, Dec £15,800, Jan £12,600, Feb £9,900 (Q4 VAT on 7 Feb), Mar £14,200.
- Start 1 Jan: Jan £9,920, Feb £4,540 (under buffer by £460), Mar £6,160. Start 1 Feb: Feb £7,220, Mar £8,840 (always above buffer).
- Other AI answers: “Why is 7 Nov my lowest day?” (payroll and rent first, Acme in on 3 Nov, VAT £6,100 on 7 Nov, Brightside three days later). “What if Acme pays late again?” (if Acme pays 17 Nov, lowest point £8,900 on 7 Nov, safe to spend £3,900).
- P&L Q3 (if reports are shown): income £70,500, costs £55,120, net profit £15,380 (18% less than Q2 £18,760). Profit-to-cash bridge: £15,380 − unpaid invoices £9,320 + VAT collected £7,080 − VAT paid for Apr–Jun £5,860 − loan £1,500 − owner drawings £3,000 = cash +£2,780.

## 4. AI design principles (the story to tell)

- The answer comes first; the Ask bar sits in the middle of Home, under the KPI strip.
- Suggested questions come from the owner’s own data, so the box is never blank.
- The AI shows what it did (steps), gives a one-sentence verdict, then the working (cost table), editable assumptions (chips), and the chart.
- The answer is drawn on the forecast: current bars hatched/light, scenario bars blue, months under the buffer red.
- Actions: Try 1 February, Save as scenario, Ask Tom to check. Big or tax decisions go to the accountant.
- If data is stale, the AI says so before answering.

## 5. Research sources (all screenshots in `research/`)

| File | What it shows | Source |
|---|---|---|
| c-gov.png | 5.5m UK private sector businesses, 5.45m small (2024) | https://www.gov.uk/government/statistics/business-population-estimates-2024/business-population-estimates-for-the-uk-and-regions-2024-statistical-release |
| c-digits-survey.png | 56% decide on incomplete info monthly; 37% need 1–3 days for accurate numbers (2,004 US SMB owners, 2021) | https://www.prnewswire.com/news-releases/survey-finds-majority-of-small-businesses-dont-know-where-their-money-is-being-spent-301399220.html |
| c-xero-survey.png | 50% faced problems from low financial literacy; 16% find interpreting metrics hard (1,021 US owners, 2024) | https://www.xero.com/us/media-releases/survey-small-business-financial-literacy/ |
| c-idea-watchlist.png | Custom budget can’t be shown on dashboard; “wasted my time creating a new budget…” | https://productideas.xero.com/forums/939198-for-small-businesses/suggestions/47762207-account-watchlist-display-a-custom-budget-on-acc |
| c-idea-bs-budget.png | Balance sheet budgets: 225 votes since 2013, Xero suggests a spreadsheet | https://productideas.xero.com/forums/939198-for-small-businesses/suggestions/44960479-reporting-budget-add-budgets-for-balance-sheet |
| c-feed-proactive.png | Accountant: “we miss months of data” when bank feeds break | https://productideas.xero.com/forums/967136-banking-chart-of-accounts/suggestions/50444607-bank-feeds-suggestion-for-proactive-user-notific |
| c-feed-email.png | Email alerts for broken feeds, Gaining support (June 2026) | https://productideas.xero.com/forums/967136-banking-chart-of-accounts/suggestions/51334390-bank-feeds-automated-email-notifications-for-ban |
| c-xero-demo.png | Author’s Xero demo company home screen (bookkeeping tasks, three balances to reconcile) | Author’s own screenshot |
| xero-jax-chat.webp | Xero JAX answer to “how much money do I have?” | Author’s own screenshot |

## 6. Writing voice

First person, plain, positive. Fewer “not X but Y” contrasts, fewer triplets, no defensive disclaimers. Example: “Next: testing with owners” rather than “No heatmaps yet, and I won’t fake them.”

## 7. Figma Plugin API lessons from the first build

- `resize()` on an auto-layout frame can leave the primary axis fixed; set `primaryAxisSizingMode = 'AUTO'` after resizing.
- A horizontal row where every child is FILL height collapses; keep the tallest child HUG.
- Paint opacity is ignored when a colour variable is bound; use a plain solid paint for scrims.
- A failed `use_figma` call rolls back completely; keep calls focused.
- Starter plans have a small monthly MCP quota per team; batch work into few large calls.
- For case study images, export frames with `exportAsync` and place them as image fills instead of rescaling clones.
