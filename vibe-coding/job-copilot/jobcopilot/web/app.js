/* Job Copilot UI. Vanilla — nothing to build, nothing to install. */

const state = {
  jobs: [],
  counts: {},
  config: {},
  selected: null,   // { job, analysis, application }
  tab: "analysis",
  filter: "",
  view: "all",
};

const $ = (sel) => document.querySelector(sel);
const esc = (v) =>
  String(v ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/* ---------- transport ---------- */

async function api(path, body) {
  const opts = body === undefined
    ? {}
    : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const res = await fetch(path, opts);
  let data = {};
  try { data = await res.json(); } catch { /* non-JSON error page */ }
  if (!res.ok) throw new Error(data.error || `${res.status} ${res.statusText}`);
  return data;
}

let toastTimer;
function toast(message, kind = "") {
  const el = $("#toast");
  el.className = "toast" + (kind ? ` toast--${kind}` : "");
  el.innerHTML = message;
  el.hidden = false;
  clearTimeout(toastTimer);
  if (kind !== "busy") toastTimer = setTimeout(() => (el.hidden = true), 7000);
}

/** Runs an async action with the button disabled, so a slow sweep can't be double-fired. */
async function busy(button, label, fn) {
  const original = button?.textContent;
  if (button) { button.disabled = true; button.textContent = label; }
  toast(`<span class="spin">◠</span> ${esc(label)}…`, "busy");
  try {
    const out = await fn();
    $("#toast").hidden = true;
    return out;
  } catch (err) {
    toast(esc(err.message), "err");
    throw err;
  } finally {
    if (button) { button.disabled = false; button.textContent = original; }
  }
}

/* ---------- shell ---------- */

async function refresh() {
  const data = await api("/api/state");
  Object.assign(state, data);
  renderBar();
  renderList();
}

function renderBar() {
  const c = state.counts, cfg = state.config;
  $("#stats").innerHTML = `
    <span><b>${c.total ?? 0}</b> roles</span>
    <span><b>${c.analysed ?? 0}</b> scored</span>
    <span><b>${c.drafts ?? 0}</b> drafted</span>
    <span><b>${c.sent ?? 0}</b> sent</span>
    ${c.needs_detail ? `<span class="badge badge--warn">${c.needs_detail} need a description</span>` : ""}`;

  const sending = cfg.send_mode === "approve"
    ? `sending on approval · ${cfg.sent_today}/${cfg.daily_cap} today`
    : "review only — nothing sends";
  $("#engine").textContent = `${cfg.llm_available ? cfg.model : "keyword mode (no API key)"} · ${sending}`;
}

function scoreClass(score) {
  if (score === null || score === undefined) return "";
  if (score >= 65) return "score--strong";
  if (score >= 40) return "score--mid";
  return "score--weak";
}

function visible() {
  const q = state.filter.toLowerCase();
  return state.jobs.filter((j) => {
    if (q && !`${j.company} ${j.title} ${j.location}`.toLowerCase().includes(q)) return false;
    switch (state.view) {
      case "scored": return j.fit_score !== null && j.fit_score !== undefined;
      case "strong": return (j.fit_score ?? 0) >= 65;
      case "drafted": return j.has_draft;
      case "needs_detail": return j.needs_detail;
      case "sent": return j.status === "sent";
      default: return true;
    }
  });
}

function renderList() {
  const rows = visible();
  if (!rows.length) {
    $("#list").innerHTML = `<p class="note" style="padding:16px">No roles match. Sweep your
      sources or add one by hand.</p>`;
    return;
  }
  $("#list").innerHTML = rows.map((j) => {
    const badges = [];
    if (j.needs_detail) badges.push(`<span class="badge badge--warn">needs description</span>`);
    if (j.sponsorship === "excludes") badges.push(`<span class="badge badge--bad">right to work blocks this</span>`);
    if (j.sponsorship === "restricted") badges.push(`<span class="badge badge--warn">check right to work</span>`);
    if (j.sponsorship === "sponsors") badges.push(`<span class="badge badge--good">sponsors</span>`);
    if (j.status && j.status !== "draft") badges.push(`<span class="badge badge--accent">${esc(j.status)}</span>`);
    else if (j.has_draft) badges.push(`<span class="badge">draft ready</span>`);
    if (j.engine === "keyword") badges.push(`<span class="badge">keyword only</span>`);

    return `<button class="card ${state.selected?.job.id === j.id ? "is-active" : ""}" data-id="${j.id}">
      <span class="score ${scoreClass(j.fit_score)}">${j.fit_score ?? "–"}</span>
      <span>
        <span class="card__title">${esc(j.title)}</span>
        <span class="card__company">${esc(j.company || "unknown company")}</span>
        <span class="card__meta">${esc(j.location || "location not stated")} · ${esc(j.source)}</span>
        ${badges.length ? `<span class="card__badges">${badges.join("")}</span>` : ""}
      </span>
    </button>`;
  }).join("");
}

/* ---------- detail ---------- */

async function select(jobId) {
  state.selected = await api(`/api/job?job_id=${encodeURIComponent(jobId)}`);
  renderList();
  renderDetail();
}

function renderDetail() {
  const sel = state.selected;
  if (!sel) return;
  const { job, analysis, application } = sel;
  const score = analysis?.fit_score;

  const tabs = [
    ["analysis", "Analysis"],
    ["resume", "Resume"],
    ["letter", "Cover letter"],
    ["send", "Send"],
  ];

  $("#detail").innerHTML = `
    <div class="dhead">
      <div>
        <h2>${esc(job.title)}</h2>
        <p class="dhead__company">${esc(job.company || "unknown company")}${
          job.location ? ` · ${esc(job.location)}` : ""}</p>
        <p class="dhead__meta">${esc(job.source)}${
          job.url ? ` · <a href="${esc(job.url)}" target="_blank" rel="noreferrer">open posting ↗</a>` : ""}</p>
      </div>
      <div class="dhead__side">
        <span class="dhead__score score ${scoreClass(score)}"
          style="width:64px;height:64px;font-size:22px">${score ?? "–"}</span>
        ${analysis?.verdict ? `<span class="badge">${esc(analysis.verdict)}</span>` : ""}
      </div>
    </div>
    <nav class="tabs">${tabs.map(([id, label]) =>
      `<button class="tab ${state.tab === id ? "is-active" : ""}" data-tab="${id}">${label}</button>`
    ).join("")}</nav>
    <div id="tabbody"></div>`;

  const body = $("#tabbody");
  if (state.tab === "analysis") body.innerHTML = viewAnalysis(job, analysis);
  else if (state.tab === "resume") body.innerHTML = viewResume(application);
  else if (state.tab === "letter") body.innerHTML = viewLetter(application);
  else body.innerHTML = viewSend(job, application);

  if (state.tab === "send") loadPreflight(job.id);
}

function viewAnalysis(job, analysis) {
  const needsDetail = !((job.description || "").trim());
  if (needsDetail) {
    return `
      <div class="callout callout--warn section">
        <strong>No job description yet.</strong>
        <p class="note">${esc(job.extra?.fetch_note ||
          "This came from a source that only gives the title and link — LinkedIn alerts work this way. Open the posting, copy the description, and paste it here.")}</p>
      </div>
      <label class="field">
        <span>Job description</span>
        <textarea id="detail-description" class="input input--area" rows="14"></textarea>
      </label>
      <div class="row row--end">
        <button class="btn btn--primary" data-act="save-detail">Save and analyse</button>
      </div>`;
  }

  if (!analysis) {
    return `<div class="section"><p class="note">Not analysed yet.</p></div>
      <div class="row"><button class="btn btn--primary" data-act="analyse-one">Analyse this role</button></div>
      ${descriptionBlock(job)}`;
  }

  const wa = analysis.work_authorisation || {};
  const waClass = { excludes: "bad", restricted: "warn", sponsors: "good", silent: "", unclear: "warn" }[wa.stance] || "";
  const waLabel = {
    excludes: "Blocks you",
    restricted: "Restricted — check against your status",
    sponsors: "Sponsorship offered",
    silent: "Not mentioned",
    unclear: "Unclear",
  }[wa.stance] || wa.stance;

  return `
    <div class="section">
      <div class="callout ${analysis.fit_score >= 65 ? "callout--good" : analysis.fit_score >= 40 ? "callout--warn" : "callout--bad"}">
        <strong>${esc(analysis.one_line)}</strong>
        ${analysis.role_family || analysis.seniority ? `<p class="note" style="margin-top:6px">
          ${esc(analysis.role_family)}${analysis.seniority ? ` · pitched at ${esc(analysis.seniority)}` : ""}</p>` : ""}
      </div>
    </div>

    ${analysis.angle ? `<div class="section"><h3>The angle</h3>
      <div class="prose"><p>${esc(analysis.angle)}</p></div></div>` : ""}

    ${wa.stance ? `<div class="section"><h3>Right to work</h3>
      <div class="callout ${waClass ? `callout--${waClass}` : ""}">
        <strong>${esc(waLabel)}</strong>
        <p class="note" style="margin-top:4px">${esc(wa.evidence)}</p>
      </div></div>` : ""}

    ${analysis.risks?.length ? `<div class="section"><h3>Risks</h3>
      <ul class="bullets">${analysis.risks.map((r) => `<li>${esc(r)}</li>`).join("")}</ul></div>` : ""}

    ${analysis.must_haves?.length ? `<div class="section"><h3>Their requirements</h3>
      <div class="reqs">${analysis.must_haves.map((r) => `
        <div class="req">
          <span class="req__status req__status--${esc(r.status)}">${esc(r.status)}</span>
          <span><span>${esc(r.requirement)}</span>
            <span class="req__evidence">${esc(r.evidence)}</span></span>
        </div>`).join("")}</div></div>` : ""}

    ${analysis.keywords?.length ? `<div class="section"><h3>Keywords they screen on</h3>
      <div class="chips">${analysis.keywords.map((k) => `<span class="chip">${esc(k)}</span>`).join("")}</div>
      ${analysis.keywords_missing?.length ? `<h3 style="margin-top:14px">No honest match for these</h3>
        <div class="chips">${analysis.keywords_missing.map((k) =>
          `<span class="chip chip--missing">${esc(k)}</span>`).join("")}</div>` : ""}
    </div>` : ""}

    ${analysis.lead_projects?.length ? `<div class="section"><h3>Lead with</h3>
      <div class="chips">${analysis.lead_projects.map((p) => `<span class="chip">${esc(p)}</span>`).join("")}</div></div>` : ""}

    ${analysis.questions_to_ask?.length ? `<div class="section"><h3>Worth asking them</h3>
      <ul class="bullets">${analysis.questions_to_ask.map((q) => `<li>${esc(q)}</li>`).join("")}</ul></div>` : ""}

    <div class="section row">
      <button class="btn btn--primary" data-act="prepare">${
        state.selected.application?.letter ? "Redraft resume and letter" : "Draft resume and letter"}</button>
      <button class="btn" data-act="analyse-one">Re-analyse</button>
      <button class="btn btn--ghost btn--sm" data-act="status" data-status="skipped">Not for me</button>
    </div>
    ${descriptionBlock(job)}`;
}

function descriptionBlock(job) {
  return `<details class="section"><summary class="note" style="cursor:pointer">The posting itself</summary>
    <pre class="input input--area" style="margin-top:10px; white-space:pre-wrap; max-height:420px; overflow:auto">${
      esc(job.description || "")}</pre></details>`;
}

function viewResume(application) {
  const resume = application?.resume;
  if (!resume) {
    return `<div class="section"><p class="note">No tailored resume yet.</p></div>
      <div class="row"><button class="btn btn--primary" data-act="prepare">Draft resume and letter</button></div>`;
  }
  const file = application.files?.resume;
  return `
    ${resume.engine === "keyword" ? `<div class="callout section">
      <strong>Selected by keyword match, not rewritten.</strong>
      <p class="note" style="margin-top:4px">Every word below is exactly as you wrote it — this only picked
        and reordered your own bullets. Set <code>ANTHROPIC_API_KEY</code> to have it rephrased in the
        posting's own language too.</p></div>` : ""}
    ${resume.unsourced?.length ? `<div class="callout callout--bad section">
      <strong>${resume.unsourced.length} bullet(s) cite a source that isn't in your bank.</strong>
      <p class="note" style="margin-top:4px">Read these before sending:</p>
      <ul class="bullets">${resume.unsourced.map((t) => `<li>${esc(t)}</li>`).join("")}</ul></div>` : ""}

    <div class="section"><h3>Headline and summary</h3>
      <div class="prose"><p><strong>${esc(resume.headline)}</strong></p><p>${esc(resume.summary)}</p></div></div>

    <div class="section"><h3>Experience</h3>
      ${(resume.roles || []).map((role) => `
        <div class="role">
          <div class="role__line">
            <span class="role__name">${esc(role.role)} — ${esc(role.company)}</span>
            <span class="role__dates">${esc(role.dates)}</span>
          </div>
          <ul class="bullets">${(role.bullets || []).map((b) =>
            `<li>${esc(b.text)}<span class="bullet__src">${esc(b.source)}</span></li>`).join("")}</ul>
        </div>`).join("")}
    </div>

    ${resume.skills?.length ? `<div class="section"><h3>Skills, in this order</h3>
      <div class="chips">${resume.skills.map((s) => `<span class="chip">${esc(s)}</span>`).join("")}</div></div>` : ""}

    ${resume.keyword_coverage?.length ? `<div class="section"><h3>Now covers</h3>
      <div class="chips">${resume.keyword_coverage.map((k) => `<span class="chip">${esc(k)}</span>`).join("")}</div></div>` : ""}

    ${resume.omitted?.length ? `<div class="section"><h3>Left out on purpose</h3>
      <ul class="bullets">${resume.omitted.map((o) => `<li>${esc(o)}</li>`).join("")}</ul></div>` : ""}

    <div class="section row">
      ${file ? `<a class="btn" href="/out/${esc(file.split(/[\\/]/).pop())}" target="_blank" rel="noreferrer">
        Open print view ↗</a>` : ""}
      <button class="btn" data-act="retailor">Tailor again</button>
    </div>
    <p class="note">The print view is styled for A4 — open it and print to PDF.</p>`;
}

function viewLetter(application) {
  const letter = application?.letter;
  if (!letter) {
    return `<div class="section"><p class="note">No letter yet.</p></div>
      <div class="row"><button class="btn btn--primary" data-act="prepare">Draft resume and letter</button></div>`;
  }
  const file = application.files?.letter;
  return `
    ${letter.engine === "none" ? `<div class="callout callout--warn section">
      Template only — no API key. Rewrite this before it goes anywhere.</div>` : ""}
    ${letter.notes?.length ? `<div class="callout callout--warn section">
      <strong>The writer had to guess at these — check them:</strong>
      <ul class="bullets">${letter.notes.map((n) => `<li>${esc(n)}</li>`).join("")}</ul></div>` : ""}

    <label class="field"><span>Subject</span>
      <input id="letter-subject" class="input" value="${esc(letter.subject)}"></label>
    <label class="field"><span>Body — Markdown, edit freely (v${letter.version ?? 1})</span>
      <textarea id="letter-body" class="input input--area letterbox">${esc(letter.body)}</textarea></label>

    <div class="section row">
      <button class="btn" data-act="save-letter">Save edits</button>
      ${file ? `<a class="btn btn--ghost" href="/out/${esc(file.split(/[\\/]/).pop())}"
        target="_blank" rel="noreferrer">Open print view ↗</a>` : ""}
    </div>

    <div class="section">
      <h3>Or tell it what to change</h3>
      <label class="field">
        <input id="letter-instruction" class="input"
          placeholder="e.g. cut the third paragraph, lead with the Xiaomi regulatory work, less formal">
        <small>Rewrites from the current text, keeps your voice rules, and can't
          introduce anything that isn't in your profile. The previous version is kept.</small>
      </label>
      <div class="row">
        <button class="btn btn--primary" data-act="edit-letter">Revise</button>
      </div>
    </div>

    ${letter.history?.length ? `<details class="section">
      <summary class="note" style="cursor:pointer">${letter.history.length} earlier version(s)</summary>
      ${letter.history.slice().reverse().map((h) => `
        <div class="callout" style="margin-top:10px">
          <p class="note">v${h.version} — asked for: ${esc(h.instruction || "initial draft")}</p>
          <pre style="white-space:pre-wrap; margin-top:8px; font-size:12.5px">${esc(h.body)}</pre>
        </div>`).join("")}
    </details>` : ""}`;
}

function viewSend(job, application) {
  const letter = application?.letter;
  if (!letter) {
    return `<div class="section"><p class="note">Draft a letter first.</p></div>`;
  }
  const contact = application.contact || {};
  return `
    <div id="preflight" class="section"><p class="note">Checking…</p></div>

    <div class="section">
      <h3>Who it goes to</h3>
      <div class="grid2">
        <label class="field"><span>Name (optional)</span>
          <input id="to-name" class="input" value="${esc(contact.name || "")}"></label>
        <label class="field"><span>Email</span>
          <input id="to-email" class="input" type="email"
            value="${esc(contact.email || job.apply_email || "")}" placeholder="hiring@company.com"></label>
      </div>
      <p class="note">Most postings want you to apply on their own form. Use this for
        roles with a named contact, or a direct application address.</p>
    </div>

    <div class="section">
      <h3>Attachments</h3>
      <div id="attachments" class="chips"><span class="note">Loading…</span></div>
      <p class="note" style="margin-top:8px">Drop a PDF resume into
        <code id="attach-dir"></code> and it appears here. Recruiters want PDF, so print
        the tailored resume to PDF and put it there rather than attaching the HTML.</p>
    </div>

    <div class="section">
      <h3>What will be sent</h3>
      <div class="callout">
        <p class="note">Subject</p>
        <p><strong>${esc(letter.subject)}</strong></p>
        <p class="note" style="margin-top:10px">Body</p>
        <pre style="white-space:pre-wrap; font-size:13px; margin-top:4px">${esc(letter.body)}</pre>
      </div>
    </div>

    <div class="section">
      <label class="row" style="gap:8px; align-items:flex-start">
        <input type="checkbox" id="approve" style="margin-top:3px">
        <span>I've read the letter and the resume, and I'm approving this one
          application to <b id="approve-target">this recipient</b>.</span>
      </label>
    </div>

    <div class="row row--end">
      <button class="btn btn--ghost" data-act="status" data-status="sent">Mark as sent by hand</button>
      <button class="btn btn--primary" data-act="send" disabled id="send-btn">Send it</button>
    </div>`;
}

async function loadPreflight(jobId) {
  try {
    const data = await api(`/api/preflight?job_id=${encodeURIComponent(jobId)}`);
    const box = $("#preflight");
    if (!box) return;
    box.innerHTML = data.problems.length
      ? `<div class="callout callout--warn"><strong>Not ready to send:</strong>
          <ul class="bullets">${data.problems.map((p) => `<li>${esc(p)}</li>`).join("")}</ul></div>`
      : `<div class="callout callout--good">Ready. ${data.sent_today}/${data.daily_cap} sent today.</div>`;

    const dir = $("#attach-dir");
    if (dir) dir.textContent = data.attachments_dir;
    const list = $("#attachments");
    if (list) {
      list.innerHTML = data.available_attachments.length
        ? data.available_attachments.map((name) =>
            `<label class="chip"><input type="checkbox" class="attach" value="${esc(name)}"> ${esc(name)}</label>`
          ).join("")
        : `<span class="note">Nothing in the attachments folder yet.</span>`;
    }
    const send = $("#send-btn");
    const approve = $("#approve");
    if (send && approve) {
      const sync = () => {
        const email = $("#to-email")?.value.trim();
        send.disabled = !approve.checked || data.problems.length > 0 || !email;
        const target = $("#approve-target");
        if (target) target.textContent = email || "this recipient";
      };
      approve.addEventListener("change", sync);
      $("#to-email")?.addEventListener("input", sync);
      sync();
    }
  } catch (err) {
    toast(esc(err.message), "err");
  }
}

/* ---------- actions ---------- */

async function handleAction(act, button, dataset) {
  const sel = state.selected;
  const jobId = sel?.job.id;

  switch (act) {
    case "discover": {
      const out = await busy(button, "Sweeping", () => api("/api/discover", {}));
      await refresh();
      toast(`${out.new} new, ${out.updated} updated, ${out.filtered_out} filtered out.` +
        (out.notes.length ? `<br><span class="note">${out.notes.map(esc).join("<br>")}</span>` : ""),
        out.new ? "ok" : "");
      break;
    }
    case "analyse": {
      const out = await busy(button, "Analysing", () => api("/api/analyse", { limit: 25 }));
      await refresh();
      toast(`Scored ${out.analysed} role(s).` +
        (out.errors.length ? `<br><span class="note">${out.errors.map(esc).join("<br>")}</span>` : ""),
        "ok");
      break;
    }
    case "prepare-top": {
      const out = await busy(button, "Drafting", () => api("/api/prepare-top", { limit: 5 }));
      await refresh();
      toast(out.prepared.length
        ? `Drafted ${out.prepared.length}: ${out.prepared.map((p) => esc(p.company)).join(", ")}`
        : "Nothing eligible — analyse some roles first, or lower min_score_to_draft.", "ok");
      break;
    }
    case "add":
      $("#add-dialog").showModal();
      break;

    case "analyse-one":
      await busy(button, "Analysing", () => api("/api/analyse-one", { job_id: jobId }));
      await select(jobId);
      await refresh();
      break;

    case "save-detail": {
      const description = $("#detail-description").value;
      await busy(button, "Saving", async () => {
        await api("/api/job/detail", { job_id: jobId, description });
        await api("/api/analyse-one", { job_id: jobId });
      });
      await select(jobId);
      await refresh();
      break;
    }

    case "prepare":
      await busy(button, "Drafting", () => api("/api/prepare", { job_id: jobId }));
      state.tab = "letter";
      await select(jobId);
      await refresh();
      toast("Resume tailored and letter drafted. Read both before sending.", "ok");
      break;

    case "retailor":
      await busy(button, "Tailoring", () => api("/api/resume/retailor", { job_id: jobId }));
      await select(jobId);
      break;

    case "save-letter":
      await busy(button, "Saving", () => api("/api/letter/save", {
        job_id: jobId,
        subject: $("#letter-subject").value,
        body: $("#letter-body").value,
      }));
      await select(jobId);
      toast("Saved.", "ok");
      break;

    case "edit-letter": {
      const instruction = $("#letter-instruction").value.trim();
      if (!instruction) { toast("Say what to change first.", "err"); return; }
      await busy(button, "Revising", () => api("/api/letter/edit", { job_id: jobId, instruction }));
      await select(jobId);
      toast("Revised. The previous version is kept below.", "ok");
      break;
    }

    case "status":
      await api("/api/application/status", { job_id: jobId, status: dataset.status });
      await select(jobId);
      await refresh();
      break;

    case "send": {
      const to_email = $("#to-email").value.trim();
      const to_name = $("#to-name").value.trim();
      const attachments = [...document.querySelectorAll(".attach:checked")].map((el) => el.value);
      if (!confirm(`Send this application to ${to_email}? This can't be undone.`)) return;
      await busy(button, "Sending", () => api("/api/send", {
        job_id: jobId, to_email, to_name, attachments, approved: true,
      }));
      await select(jobId);
      await refresh();
      toast(`Sent to ${esc(to_email)}.`, "ok");
      break;
    }
  }
}

/* ---------- wiring ---------- */

document.addEventListener("click", (event) => {
  const card = event.target.closest(".card");
  if (card) { select(card.dataset.id); return; }

  const tab = event.target.closest(".tab");
  if (tab) { state.tab = tab.dataset.tab; renderDetail(); return; }

  const actor = event.target.closest("[data-act]");
  if (actor) {
    const act = actor.dataset.act;
    if (["add-url-go", "add-paste-go"].includes(actor.id)) return;
    handleAction(act, actor, actor.dataset).catch(() => {});
  }
});

$("#filter").addEventListener("input", (e) => { state.filter = e.target.value; renderList(); });
$("#view").addEventListener("change", (e) => { state.view = e.target.value; renderList(); });

$("#add-url-go").addEventListener("click", async (event) => {
  const url = $("#add-url").value.trim();
  if (!url) { toast("Paste a URL first.", "err"); return; }
  try {
    const out = await busy(event.target, "Fetching", () => api("/api/job/url", { url }));
    $("#add-dialog").close();
    await refresh();
    await select(out.job.id);
    if (out.job.extra?.needs_detail) {
      toast("Fetched, but the description looks thin — paste it in on the Analysis tab.", "err");
    }
  } catch { /* toast already shown */ }
});

$("#add-paste-go").addEventListener("click", async (event) => {
  const payload = {
    title: $("#add-title").value.trim(),
    company: $("#add-company").value.trim(),
    location: $("#add-location").value.trim(),
    apply_email: $("#add-email").value.trim(),
    description: $("#add-description").value.trim(),
  };
  if (!payload.description) { toast("The description is the part that gets analysed.", "err"); return; }
  try {
    const out = await busy(event.target, "Adding", () => api("/api/job/paste", payload));
    $("#add-dialog").close();
    $("#add-description").value = "";
    await refresh();
    await select(out.job.id);
  } catch { /* toast already shown */ }
});

refresh().catch((err) => toast(esc(err.message), "err"));
