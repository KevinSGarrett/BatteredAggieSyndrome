const $ = (id) => document.getElementById(id);
const pct = (v) => Number.isFinite(v) ? `${(v * 100).toFixed(1)}%` : "—";
const num = (v) => Number.isFinite(v) ? Number(v).toFixed(1) : "—";
const renderList = (items) => items && items.length ? `<ul>${items.map(x => `<li>${escapeHtml(JSON.stringify(x))}</li>`).join("")}</ul>` : "<span>Not published for this snapshot.</span>";
const escapeHtml = (s) => String(s).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));

async function initGames() {
  const response = await fetch('/api/v1/games');
  const payload = await response.json();
  $('game').innerHTML = payload.games.map(g => `<option value="${escapeHtml(g.game_id)}">${escapeHtml(g.game_id)}</option>`).join('');
  if (payload.games.length) loadForecast();
}

async function loadForecast() {
  const game = $('game').value;
  const lane = $('lane').value;
  if (!game) return;
  const response = await fetch(`/api/v1/games/${encodeURIComponent(game)}/forecast?market_lane=${encodeURIComponent(lane)}`);
  if (!response.ok) {
    $('warningBox').classList.remove('hidden');
    $('warningBox').textContent = `No eligible ${lane} snapshot is currently published for this game.`;
    return;
  }
  const p = await response.json();
  $('warningBox').classList.toggle('hidden', !p.warnings.length);
  $('warningBox').textContent = p.warnings.join(' • ');
  $('freshness').textContent = `${p.freshness.state} · as-of ${p.snapshot.forecast_cutoff}`;
  $('win').textContent = pct(p.forecast.win_probability);
  $('loss').textContent = pct(p.forecast.loss_probability);
  $('margin').textContent = num(p.forecast.expected_margin);
  $('score').textContent = `${num(p.forecast.expected_team_score)} – ${num(p.forecast.expected_opponent_score)}`;
  $('bas').innerHTML = renderList(Object.entries(p.bas).map(([severity, probability]) => ({severity, probability: pct(probability)})));
  $('uncertainty').innerHTML = renderList(p.uncertainty);
  $('availability').innerHTML = renderList(p.explainability.availability);
  $('matchup').innerHTML = renderList(p.explainability.matchup_drivers);
  $('analogs').innerHTML = renderList(p.explainability.historical_analogs);
  $('comparison').textContent = JSON.stringify(p.explainability.comparison_context, null, 2);
  $('lineage').textContent = JSON.stringify(p.lineage, null, 2);
}

$('load').addEventListener('click', loadForecast);
$('lane').addEventListener('change', loadForecast);
initGames().catch(err => {
  $('warningBox').classList.remove('hidden');
  $('warningBox').textContent = `Dashboard initialization failed: ${err}`;
});
