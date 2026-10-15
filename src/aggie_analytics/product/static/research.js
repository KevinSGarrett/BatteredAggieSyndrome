// BAS private national retrospective research browser (BAT-728, Cycle #57 TP57-A01).
// Every value shown is a server record from /api/v1/research (never a client-side estimate or aggregate); every
// string is inserted as text, never as HTML. RETROSPECTIVE_RESEARCH / UNTRUSTED_SHADOW / PIT_NOT_ADMITTED /
// predictive skill NOT_ESTABLISHED.
"use strict";
(() => {
  const API = "/api/v1/research";
  const $ = (id) => document.getElementById(id);
  const GRAINS = ["games", "features", "estimates", "scores", "parameters", "summary", "comparisons"];
  const SELECTORS = ["season", "team", "game", "model", "partition", "slice", "baseline"];
  const state = { profiles: [], profileId: null, detail: null, grain: "games", offset: 0, limit: 50, filters: {},
                  pollTimer: null, lastAction: null, status: null, beforeDetail: null, detailRequest: null };

  // ------------------------------------------------------------------------------------------- request ownership
  // Every asynchronous request captures an immutable context: its channel (profile, results or detail), the channel
  // generation it was issued under, the profile generation and what it asked for. A newer request on the same channel,
  // a grain change, a closed game detail or a profile change advances the generation, so an older answer (success,
  // refusal or transport failure) is dropped before it can change rows, pager, counts, status, Retry, game detail,
  // profile identity, selectors or polling. A results answer renders only under the grain it was requested for.
  const generation = { profile: 0, results: 0, detail: 0 };
  function supersede(channel) {
    generation[channel] += 1;
    if (channel === "profile") { generation.results += 1; generation.detail += 1; }
  }
  function issue(channel, fields) {
    supersede(channel);
    return Object.freeze({ ...fields, channel, generation: generation[channel], profileGeneration: generation.profile });
  }
  function current(ctx) {
    if (generation[ctx.channel] !== ctx.generation || generation.profile !== ctx.profileGeneration) return false;
    if (ctx.channel === "results") return ctx.grain === state.grain && ctx.profileId === state.profileId;
    if (ctx.channel === "detail") return ctx.profileId === state.profileId;
    return true;
  }

  // ------------------------------------------------------------------------------------------- DOM helpers
  function el(tag, text, attrs) {
    const node = document.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = String(text);
    for (const [k, v] of Object.entries(attrs || {})) node.setAttribute(k, v);
    return node;
  }
  function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }
  function rat(v) { return v === null || v === undefined ? "—" : `${v.numerator}/${v.denominator}`; }
  function show(v) { return v === null || v === undefined || v === "" ? "—" : String(v); }
  // The status line belongs to the request context that set it (owner); Retry repeats that request's action.
  function setStatus(kind, text, owner) {
    const s = $("status");
    s.dataset.state = kind;
    s.textContent = text;
    $("retry").hidden = !(kind === "error" || kind === "unavailable" || kind === "verifying");
    state.status = { kind, text, owner: owner || null, retry: state.lastAction };
  }
  // The profile selector stays usable whenever two or more profiles are listed (an unavailable or verifying profile
  // must not trap the user); the other selectors follow the current profile.
  function setEnabled(on) {
    for (const id of [...SELECTORS, "limit", "apply"]) $(id).disabled = !on;
    if (on) applicability();
  }

  // ------------------------------------------------------------------------------------------- HTTP
  async function getJSON(path) {
    let response;
    try {
      response = await fetch(path, { headers: { Accept: "application/json" }, cache: "no-store" });
    } catch (error) {
      return { network: true, status: 0, body: null };
    }
    let body = null;
    try { body = await response.json(); } catch (error) { body = null; }
    return { network: false, status: response.status, body, retryAfter: response.headers.get("Retry-After") };
  }
  function errorCode(result) { return result.body && result.body.error ? result.body.error.code : `HTTP_${result.status}`; }

  // ------------------------------------------------------------------------------------------- profiles
  async function loadProfiles() {
    clearTimeout(state.pollTimer);
    const ctx = issue("profile", {});
    state.lastAction = loadProfiles;
    setStatus("loading", "Loading research profiles…", ctx);
    const result = await getJSON(`${API}/profiles`);
    if (!current(ctx)) return;
    if (result.network) return setStatus("error", "Network error: the research API could not be reached. Retry when the server is available.", ctx);
    if (result.status === 404) {
      setEnabled(false);
      $("profile").disabled = true;
      return setStatus("unconfigured", "Research is unavailable: no research profile is configured on this server.", ctx);
    }
    if (result.status !== 200 || !result.body) return setStatus("error", `Research API error ${errorCode(result)}.`, ctx);
    state.profiles = result.body.profiles || [];
    const select = $("profile");
    clear(select);
    for (const p of state.profiles) select.appendChild(el("option", `${p.display_label} (${p.profile_id})`, { value: p.profile_id }));
    select.disabled = state.profiles.length < 2;
    if (!state.profiles.length) return setStatus("unconfigured", "Research is unavailable: no research profile is configured.", ctx);
    if (!state.profileId || !state.profiles.some((p) => p.profile_id === state.profileId)) state.profileId = state.profiles[0].profile_id;
    select.value = state.profileId;
    return chooseProfile(ctx, result.retryAfter);
  }

  // Retry of a profile detail: a new profile request that supersedes every older answer.
  function reloadProfile() { return chooseProfile(issue("profile", {})); }

  async function chooseProfile(ctx, retryAfter) {
    const profile = state.profiles.find((p) => p.profile_id === state.profileId);
    renderIdentity(profile, null);
    if (profile.state === "VERIFYING" || profile.state === "NOT_STARTED") {
      setEnabled(false);
      setStatus("verifying", `Verifying profile ${profile.profile_id} with the accepted reader (state ${profile.state}); nothing is served until verification completes.`, ctx);
      state.pollTimer = setTimeout(loadProfiles, 1000 * Math.min(Number(retryAfter) || 2, 10));
      return;
    }
    if (profile.state !== "AVAILABLE") {
      setEnabled(false);
      clearResults();
      return setStatus("unavailable", `Profile ${profile.profile_id} is unavailable (${profile.refusal_code || profile.state}); nothing is served.`, ctx);
    }
    state.lastAction = reloadProfile;
    setStatus("loading", "Loading profile…", ctx);
    const result = await getJSON(`${API}/profiles/${encodeURIComponent(profile.profile_id)}`);
    if (!current(ctx)) return;
    if (result.network) return setStatus("error", "Network error while loading the profile.", ctx);
    if (result.status === 503) return handleUnavailable(result, ctx);
    if (result.status !== 200) return setStatus("error", `Profile error ${errorCode(result)}.`, ctx);
    state.detail = result.body;
    renderIdentity(profile, state.detail);
    populateSelectors(state.detail);
    renderAdverse(state.detail.adverse_2023);
    setEnabled(true);
    return loadGrain();
  }

  function handleUnavailable(result, ctx) {
    const code = errorCode(result);
    if (code === "RESEARCH_PROFILE_VERIFYING") {
      setEnabled(false);
      setStatus("verifying", "Verifying the profile with the accepted reader…", ctx);
      state.pollTimer = setTimeout(loadProfiles, 2000);
      return;
    }
    setEnabled(false);
    clearResults();
    setStatus("unavailable", `Profile unavailable (${code}); nothing is served.`, ctx);
  }

  function renderIdentity(profile, detail) {
    const dl = $("identity");
    clear(dl);
    const ids = (detail && detail.verified_identities) || (profile && profile.expected_identities) || {};
    const rows = [["Profile", profile ? profile.profile_id : "—"], ["State", profile ? profile.state : "—"]];
    for (const key of ["database_identity", "content_identity", "database_sha256", "manifest_sha256", "contract_sha256",
                       "history_identity", "population_identity"]) if (ids[key]) rows.push([key, ids[key]]);
    if (detail) {
      const c = detail.coverage;
      rows.push(["Coverage", `${c.games} games · ${c.feature_records} feature records · ${c.estimates} estimates · ${c.scores} scores · ${c.parameters} parameter records`]);
    }
    for (const [k, v] of rows) { dl.appendChild(el("dt", k)); dl.appendChild(el("dd", v, { "data-key": k })); }
    const labels = $("labels");
    const values = (detail && detail.labels) || (profile && profile.labels);
    if (values) {
      clear(labels);
      for (const v of Object.values(values)) labels.appendChild(el("li", v));
    }
    const limits = $("limitations");
    clear(limits);
    for (const line of (detail && detail.limitations) || []) limits.appendChild(el("li", line));
  }

  function populateSelectors(detail) {
    const fill = (id, values, label) => {
      const select = $(id);
      const keep = select.value;
      clear(select);
      if (label !== null) select.appendChild(el("option", label, { value: "" }));
      for (const [value, text] of values) select.appendChild(el("option", text, { value: String(value) }));
      select.value = [...select.options].some((o) => o.value === keep) ? keep : select.options[0].value;
    };
    fill("season", detail.seasons.map((s) => [s, String(s)]), "All seasons");
    fill("model", detail.models.map((m) => [m.model_id, `${m.model_id} (${m.metric_kind === "MARGIN" ? "expected margin only" : "probability"})`]), "All models");
    fill("partition", detail.partitions.map((p) => [p.partition_id, `${p.partition_id} (${p.seasons.join(", ")})`]), "All partitions");
    fill("slice", Object.keys(detail.slices).map((s) => [s, s]), "All slices");
    fill("baseline", detail.models.filter((m) => m.probability_served).map((m) => [m.model_id, m.model_id]), null);
  }

  function applicability() {
    const allowed = state.detail ? state.detail.grains[state.grain].selectors : [];
    for (const id of SELECTORS) $(id).disabled = !allowed.includes(id);
  }

  // ------------------------------------------------------------------------------------------- grains
  function readFilters() {
    const filters = {};
    for (const id of SELECTORS) {
      const node = $(id);
      if (node.disabled) continue;
      const value = node.value.trim();
      if (value) filters[id] = value;
    }
    return filters;
  }

  async function loadGrain() {
    if (!state.detail) { supersede("results"); return; }
    clearTimeout(state.pollTimer);
    const grain = state.grain;
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(state.filters)) {
      if (state.detail.grains[grain].selectors.includes(k) && !(k === "baseline" && v === "NULL_HALF_V1")) params.set(k, v);
    }
    params.set("limit", String(state.limit));
    params.set("offset", String(state.offset));
    const ctx = issue("results", { profileId: state.profileId, grain, query: params.toString() });
    state.lastAction = loadGrain;
    setStatus("loading", `Loading ${grain}…`, ctx);
    $("count").textContent = "";
    const result = await getJSON(`${API}/profiles/${encodeURIComponent(ctx.profileId)}/${ctx.grain}?${ctx.query}`);
    if (!current(ctx)) return;
    if (result.network) { clearResults(); return setStatus("error", "Network error while loading results. Retry when the server is available.", ctx); }
    if (result.status === 503) return handleUnavailable(result, ctx);
    if (result.status !== 200) {
      clearResults();
      return setStatus("error", `Request refused (${errorCode(result)}): ${result.body && result.body.error ? result.body.error.message : ""}`, ctx);
    }
    renderTable(ctx.grain, result.body);
    const doc = result.body;
    if (!doc.total) setStatus("empty", `No ${ctx.grain} match these selectors (0 rows; ${doc.season_scope_state}).`, ctx);
    else setStatus("ready", `Showing ${doc.offset + 1}–${doc.offset + doc.returned} of ${doc.total} ${ctx.grain}.`, ctx);
    $("count").textContent = `total ${doc.total}; returned ${doc.returned}; offset ${doc.offset}; next ${doc.next_offset === null ? "none" : doc.next_offset}`;
    $("prev").disabled = doc.offset === 0;
    $("next").disabled = doc.next_offset === null;
  }

  function clearResults() {
    clear($("results").querySelector("thead"));
    clear($("results").querySelector("tbody"));
    $("count").textContent = "";
    $("prev").disabled = true;
    $("next").disabled = true;
  }

  const COLUMNS = {
    games: ["Game", "Season", "Date", "Team A", "Team B", "Score A–B", "Partition", "Slices"],
    features: ["Game", "View", "Team", "Team prior G (W-L-T)", "Opponent", "Opponent prior G (W-L-T)", "Excluded priors (team/opponent)"],
    estimates: ["Game", "Model", "Orientation", "Team", "Opponent", "Served output", "Sample state"],
    scores: ["Game", "Model", "Season", "Metric", "Brier / abs. error", "Log loss / sq. error", "Label state"],
    parameters: ["Model", "Parameter state", "Fitted", "Output", "Convergence"],
    summary: ["Slice", "Scope", "Model", "Scored games", "Brier mean / MAE", "Log loss mean / RMSE"],
    comparisons: ["Slice", "Scope", "Model", "Baseline", "Scored games", "Brier difference", "Log-loss difference"],
  };

  function gameButton(key) {
    const button = el("button", key, { type: "button", "data-game": key, "aria-label": `Open game ${key}` });
    button.addEventListener("click", () => openGame(key));
    return button;
  }
  function record(r) { return `${r.games} (${r.wins}-${r.losses}-${r.ties})`; }
  // C47 records serve an exact rational with its decimal text; the new models serve a 12-place decimal string
  function probability(r) { return r.probability_decimal || (typeof r.probability === "object" ? rat(r.probability) : r.probability); }
  function cells(grain, r) {
    switch (grain) {
      case "games": return [gameButton(r.game_key), r.season, r.contest_date, `${r.a_name} (${r.a_key})`, `${r.b_name} (${r.b_key})`,
        `${show(r.label.a_points)}–${show(r.label.b_points)}`, r.partition,
        [r.texas_am_target ? "TEXAS_AM" : "", r.first_four_team_games ? "FIRST_FOUR" : "", r.cold_start ? "COLD_START" : ""].filter(Boolean).join(" ") || "—"];
      case "features": return [gameButton(r.contest_key), r.view, `${r.team_name} (${r.team_key})`, record(r.team), `${r.opponent_name} (${r.opponent_key})`, record(r.opponent),
        `${r.excluded_prior_inputs.team.length}/${r.excluded_prior_inputs.opponent.length}`];
      case "estimates": return [gameButton(r.contest_key), r.model_id, r.orientation, r.team_name, r.opponent_name,
        r.output_kind === "EXPECTED_MARGIN_ONLY_NO_PROBABILITY" ? `margin ${r.margin}` : `P(win) ${probability(r)}`,
        show(r.sample_state)];
      case "scores": return [gameButton(r.contest_key), r.model_id, r.season, r.metric_kind,
        r.metric_kind === "MARGIN" ? show(r.absolute_error_decimal) : show(r.brier_decimal),
        r.metric_kind === "MARGIN" ? show(r.squared_error_decimal) : show(r.log_loss), r.label_state];
      case "parameters": return [r.model_id, r.parameter_state, String(r.fitted), r.definition ? (r.definition.output || r.definition.family) : "—",
        r.convergence ? `${r.convergence.state} (${r.convergence.newton_steps} steps)` : "—"];
      case "summary": return [r.slice, r.scope_id, r.model_id, r.scored_games,
        r.metric_kind === "MARGIN" ? show(r.mae_decimal) : show(r.brier_mean_decimal),
        r.metric_kind === "MARGIN" ? show(r.rmse_decimal) : show(r.log_loss_mean)];
      case "comparisons": return [r.slice, r.scope_id, r.model_id, r.baseline_model_id, r.scored_games,
        show(r.brier_mean_difference_decimal), show(r.log_loss_mean_difference)];
      default: return [];
    }
  }

  function renderTable(grain, doc) {
    const table = $("results");
    $("results-caption").textContent = `${grain} (${doc.season_scope_state})`;
    const head = table.querySelector("thead");
    const body = table.querySelector("tbody");
    clear(head);
    clear(body);
    const hr = el("tr");
    for (const name of COLUMNS[grain]) hr.appendChild(el("th", name, { scope: "col" }));
    head.appendChild(hr);
    doc.rows.forEach((r, i) => {
      const tr = el("tr", null, { "data-row": String(doc.offset + i) });
      for (const value of cells(grain, r)) {
        const td = el("td");
        if (value instanceof Node) td.appendChild(value); else td.textContent = show(value);
        tr.appendChild(td);
      }
      body.appendChild(tr);
    });
  }

  // ------------------------------------------------------------------------------------------- game detail
  async function openGame(key) {
    if (!state.profileId) return;
    // the status shown before this game was requested (never another game's), restored if it is closed while pending
    if (!state.status || !state.status.owner || state.status.owner.channel !== "detail") state.beforeDetail = state.status;
    const ctx = issue("detail", { profileId: state.profileId, key });
    state.detailRequest = ctx;
    state.lastAction = () => openGame(key);
    setStatus("loading", `Loading game ${key}…`, ctx);
    const result = await getJSON(`${API}/profiles/${encodeURIComponent(ctx.profileId)}/games/${encodeURIComponent(key)}`);
    if (!current(ctx)) return;
    state.detailRequest = null;
    if (result.network) return setStatus("error", "Network error while loading the game.", ctx);
    if (result.status === 503) return handleUnavailable(result, ctx);
    if (result.status !== 200) return setStatus("error", `Game refused (${errorCode(result)}).`, ctx);
    renderGame(result.body);
    setStatus("ready", `Game ${key} loaded.`, ctx);
    $("detail").hidden = false;
    $("detail").scrollIntoView({ block: "start" });
    $("close-detail").focus();
  }

  // Closing the detail supersedes its pending request; a status that request still owns is restored.
  function closeDetail() {
    const pending = state.detailRequest;
    supersede("detail");
    state.detailRequest = null;
    $("detail").hidden = true;
    if (pending && state.status && state.status.owner === pending && state.beforeDetail) {
      const before = state.beforeDetail;
      state.lastAction = before.retry;
      setStatus(before.kind, before.text, before.owner);
    }
  }

  function table(columns, rows, testid) {
    const t = el("table", null, testid ? { "data-testid": testid } : {});
    const tr = el("tr");
    for (const c of columns) tr.appendChild(el("th", c, { scope: "col" }));
    const thead = el("thead"); thead.appendChild(tr); t.appendChild(thead);
    const tbody = el("tbody");
    for (const row of rows) {
      const r = el("tr");
      for (const value of row) r.appendChild(el("td", show(value)));
      tbody.appendChild(r);
    }
    t.appendChild(tbody);
    return t;
  }

  function renderGame(doc) {
    const body = $("detail-body");
    clear(body);
    const g = doc.game;
    body.appendChild(el("p", `${g.game_key} · ${g.contest_date} · season ${g.season} (${g.partition}, ${g.fit_role}) · site ${g.site}`, { "data-testid": "detail-game" }));
    body.appendChild(el("p", `${g.a_name} (${g.a_key}) ${show(g.label.a_points)} – ${show(g.label.b_points)} ${g.b_name} (${g.b_key}) · label ${g.label.label_state}`, { "data-testid": "detail-label" }));
    for (const feature of doc.features) {
      const section = el("section", null, { class: "lineage", "data-testid": `lineage-${feature.view}` });
      section.appendChild(el("h3", `View ${feature.view}: ${feature.team_name} (${feature.team_key}) prior history; opponent ${feature.opponent_name}`));
      for (const side of ["team", "opponent"]) {
        const block = feature[side];
        section.appendChild(el("p", `${side === "team" ? feature.team_name : feature.opponent_name}: ${record(block)}; points for ${block.points_for_total}, against ${block.points_against_total}; win rate ${rat(block.win_rate)}`));
        section.appendChild(table(["Contributing game", "Date", "Side", "Opponent", "Points for", "Points against", "Result"],
          block.contributing.map((c) => [c.contest_key, c.contest_date, c.side, c.opponent_key, c.points_for, c.points_against, c.result]),
          `contributing-${feature.view}-${side}`));
        section.appendChild(table(["Excluded prior input", "Date", "Opponent", "Reasons"],
          feature.excluded_prior_inputs[side].map((e) => [e.contest_key, e.contest_date, e.opponent_key, e.reasons.join(", ")]),
          `excluded-${feature.view}-${side}`));
      }
      body.appendChild(section);
    }
    body.appendChild(el("h3", "Estimates (both orientations; ridge serves an expected margin only)"));
    body.appendChild(table(["Model", "Orientation", "Team", "Served output", "Sample state"], doc.estimates.map((e) => [
      e.model_id, e.orientation, e.team_name,
      e.output_kind === "EXPECTED_MARGIN_ONLY_NO_PROBABILITY" ? `margin ${e.margin}` : `P(win) ${probability(e)}`,
      e.sample_state]), "detail-estimates"));
    body.appendChild(el("h3", "Game-level scores (one per model, A orientation)"));
    body.appendChild(table(["Model", "Metric", "Brier / abs. error", "Log loss / sq. error", "Score state"], doc.scores.map((s) => [
      s.model_id, s.metric_kind, s.metric_kind === "MARGIN" ? s.absolute_error_decimal : s.brier_decimal,
      s.metric_kind === "MARGIN" ? s.squared_error_decimal : s.log_loss, s.score_state]), "detail-scores"));
  }

  function renderAdverse(adverse) {
    const t = $("adverse-table");
    clear(t.querySelector("thead"));
    clear(t.querySelector("tbody"));
    if (!adverse) return;
    const hr = el("tr");
    for (const c of ["Model", "Scored 2023 games", "Brier mean", "Log loss mean"]) hr.appendChild(el("th", c, { scope: "col" }));
    t.querySelector("thead").appendChild(hr);
    for (const m of adverse.models) {
      const tr = el("tr", null, { "data-model": m.model_id });
      const flagged = adverse.new_probability_references_not_beating_comparator.includes(m.model_id);
      for (const v of [m.model_id + (flagged ? " (does not beat the fixed smoothed comparator)" : ""), m.scored_games, m.brier_mean_decimal, m.log_loss_mean]) {
        const td = el("td", show(v));
        if (flagged) td.className = "adverse-flag";
        tr.appendChild(td);
      }
      t.querySelector("tbody").appendChild(tr);
    }
    $("adverse-note").textContent = `Comparator ${adverse.comparator}; not beaten by: ${adverse.new_probability_references_not_beating_comparator.join(", ") || "none"}. ${adverse.rule}.`;
  }

  // ------------------------------------------------------------------------------------------- events
  function selectTab(grain) {
    state.grain = grain;
    state.offset = 0;
    for (const button of document.querySelectorAll('[role="tab"]')) {
      const on = button.dataset.grain === grain;
      button.setAttribute("aria-selected", on ? "true" : "false");
      button.tabIndex = on ? 0 : -1;
    }
    $("results-panel").setAttribute("aria-labelledby", `tab-${grain}`);
    applicability();
    state.filters = readFilters();
    if (state.detail) loadGrain(); else supersede("results");
  }

  $("filters").addEventListener("submit", (event) => {
    event.preventDefault();
    state.filters = readFilters();
    state.limit = Number($("limit").value);
    state.offset = 0;
    loadGrain();
  });
  $("prev").addEventListener("click", () => { state.offset = Math.max(0, state.offset - state.limit); loadGrain(); });
  $("next").addEventListener("click", () => { state.offset += state.limit; loadGrain(); });
  $("retry").addEventListener("click", () => (state.lastAction || loadProfiles)());
  $("close-detail").addEventListener("click", closeDetail);
  // A profile change invalidates the previous profile's rows, open game detail and every pending answer.
  $("profile").addEventListener("change", (event) => {
    state.profileId = event.target.value;
    state.detail = null;
    state.detailRequest = null;
    $("detail").hidden = true;
    clear($("detail-body"));
    clearResults();
    loadProfiles();
  });
  $("tabs").addEventListener("click", (event) => {
    const button = event.target.closest('[role="tab"]');
    if (button) selectTab(button.dataset.grain);
  });
  $("tabs").addEventListener("keydown", (event) => {
    if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
    const index = GRAINS.indexOf(state.grain);
    const next = GRAINS[(index + (event.key === "ArrowRight" ? 1 : GRAINS.length - 1)) % GRAINS.length];
    selectTab(next);
    $(`tab-${next}`).focus();
    event.preventDefault();
  });
  loadProfiles();
})();
