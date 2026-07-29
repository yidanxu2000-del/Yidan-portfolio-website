# Job Copilot

Finds roles worth applying to, works out whether you're actually a fit, tailors
your resume to each one, and drafts a cover letter you can edit by talking to it.
Runs on your machine. Sends nothing unless you approve it, one application at a
time.

Built around one idea: **the bottleneck in a job search isn't sending
applications, it's knowing which ones deserve the effort and making those ones
good.** So this optimises for judgement and quality per application, not volume.

---

## Start here

```bash
cd vibe-coding/job-copilot
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...          # analysis, tailoring, letters
cp config.example.toml config.toml           # then edit it
python3 run.py
```

Open http://127.0.0.1:8765.

**Runs without an API key.** Analysis becomes a weighted scorer — role-title
match, skill overlap, location fit, plus the two deterministic scans below —
capped at 72 so it never reads as a confident verdict. The resume tailor
selects and reorders real bullets from your bank by keyword match; nothing is
rewritten, so there's zero fabrication risk even without a model. The cover
letter without a key is a plain template — that part genuinely needs a model
to write well, so leave it for by-hand editing, or paste postings into a
Claude chat directly (see below).

What free mode can't do: judge whether your *depth* on a requirement is
enough, write in your voice, or catch anything the posting doesn't say in
plain words. Set `ANTHROPIC_API_KEY` when you want that.

Your profile is already seeded from your resume and yidan-xu.com: every role,
every bullet, every project with its case-study link. Nothing to set up before
the first sweep.

## What it does, in order

1. **Sweep sources** — pulls open roles from every board in `config.toml`, drops
   the obvious non-matches, and stores the rest.
2. **Analyse new** — reads each posting against your profile and returns a fit
   score, the requirements assessed one by one against your actual experience,
   the right-to-work stance, the keywords an ATS would screen on, which of your
   projects to lead with, and the risks. Sorted by score.
3. **Draft top 5** — for the strongest matches, reorders and rephrases your
   bullet bank for that posting and writes a cover letter in your voice.
4. **Edit** — the letter has an instruction box. "Cut the third paragraph."
   "Lead with the Xiaomi regulatory work." "Less formal." Every version is kept.
5. **Send** — or don't. Most postings want their own form; the print views are
   there for that. Where there's a real contact, you can send from here.

`python3 run.py sweep` does steps 1 and 2 with no UI, if you want it in a cron job.

---

## Where LinkedIn fits

LinkedIn's User Agreement prohibits automated access, and their Easy Apply flow
is not something to automate — a script applying under your name can get the
account restricted, and mass-applied applications get filtered anyway. So this
tool does not log into LinkedIn and does not auto-apply. Two supported routes:

**Job-alert emails (recommended).** Create job alerts on LinkedIn as normal.
LinkedIn emails you the matches. Set `linkedin.alerts_enabled = true` and this
reads those emails from your own mailbox over IMAP. Nothing touches LinkedIn.
Alert emails carry the title, company and link but not the description, so those
roles arrive flagged — open the posting, paste the description in, then analyse.

For outlook.com with two-factor auth you need an app password, not your account
password: account.microsoft.com/security → App passwords → `JOBCOPILOT_IMAP_PASSWORD`.

**Assisted search (opt-in).** Drives a real browser you're already signed into,
reads the search results you can see, throttled and read-only. Off by default.
Turning it on is your call and carries the account risk described above.

Everything else — the ATS boards, the aggregators, URL fetch, paste — needs
neither.

## The sources that do the real work

Company job boards, read through each ATS's own public JSON API. Documented,
keyless, and meant to be read by machines. Find the token in a careers-page URL:

| URL you see | Put the token under |
|---|---|
| `boards.greenhouse.io/TOKEN` | `greenhouse` |
| `jobs.lever.co/TOKEN` | `lever` |
| `jobs.ashbyhq.com/TOKEN` | `ashby` |
| `apply.workable.com/TOKEN` | `workable` |
| `jobs.smartrecruiters.com/TOKEN` | `smartrecruiters` |
| `TOKEN.recruitee.com` | `recruitee` |

Twenty companies you'd genuinely work for beats any aggregator query. Build that
list once and the sweep becomes worth running daily.

Also available: Remotive, Arbeitnow and Jobicy (open, remote-focused), and Adzuna
for ordinary UK listings (free keys from developer.adzuna.com).

---

## Why the resume tailoring can be trusted

Every bullet the tailor writes must cite the bullet-bank entry it came from, and
that citation shows in the UI under each line. It can compress, reorder,
re-emphasise and match the posting's vocabulary. It cannot add a fact, a metric,
a tool or an outcome that isn't already in your profile — and any bullet whose
citation doesn't resolve to a real bank entry gets flagged in red before you can
miss it.

What it leaves out, it lists under "Left out on purpose", so an omission is a
decision you can see rather than something that quietly vanished.

Same rule for the letter: facts come from the profile, links point at real case
studies on yidan-xu.com, and anything the writer had to guess at is listed for
you to check.

## Documents

The tailored resume and the letter render as A4-styled HTML in `data/out/`, and
the UI links to them. Open, read, print to PDF from the browser. HTML rather than
a generated PDF so the last step stays yours — you can edit the CSS if a line
breaks badly, which matters more to you than to most people using a tool like
this.

For sending, put a PDF in `data/attachments/` and it appears as a tickable
attachment. Recruiters want PDF; don't attach the HTML.

## Sending

Deliberately narrow:

- `send.mode = "review"` (the default) sends nothing, ever.
- `send.mode = "approve"` sends only what you tick the approval box for, one
  application at a time, with a confirm dialog and a daily cap.
- There is no autonomous mode and there shouldn't be. A bad application sent
  under your name to a company you wanted isn't recoverable.
- Attachments are confined to `data/` so a bad path can't read arbitrary files.
- Every send BCCs you by default.

## Where things live

```
config.toml            yours, gitignored
data/jobs.json         every role found
data/analyses.json     the assessments
data/applications.json drafts, contacts, status, sent log
data/profile.json      your profile, once you've saved an edit
data/out/              rendered resumes and letters
data/attachments/      PDFs to attach
```

All of `data/` is gitignored. Nothing about your job search ends up in the repo.

## Tuning it

- **Everything scores 80+** — the prompt is calibrated to be hard to impress, so
  if scores look inflated your target roles are probably too broad. Narrow
  `target_roles` in the profile.
- **Nothing scores above 50** — check `avoid` and `seniority`. If you're aiming
  a level up, say so in `seniority` rather than fighting the scores.
- **Letters read generic** — that's the voice rules doing too little. They're in
  the profile under `voice`; make them more specific and opinionated.
- **Model spend** — `min_score_to_draft` gates the expensive step. Analysis runs
  four at a time and skips anything already scored, so re-sweeping is cheap.
