"""Readable build audit: requirements, review actions, decisions and reconciliation.

Rendering only: every number comes from the `Dataset` and the `Check`s. Times in tables are
local (Europe/Paris), as in the raw files, so a row can be looked up there.
"""

import html
import json

from defile_dataset.report_text import CHECK_TEXT, GROUPS, COLUMNS_FR, COVERAGE_METRICS

import pandas as pd

from defile_dataset.site import SITE_NAME, TIMEZONE, TREKTELLEN_SITE_ID

MAX_TABLE_ROWS = 200
STATUS_COLORS = {"pass": "#1a7f37", "warn": "#9a6700", "fail": "#cf222e"}
CSS = """
:root { --fg:#26312e; --muted:#65716c; --line:#d8dfdc; --soft:#f4f7f5; }
body { font:14px/1.55 -apple-system,"Segoe UI",Arial,sans-serif; color:var(--fg); max-width:1320px; margin:0 auto; padding:24px 24px 60px; }
h1 { font-size:26px; margin:0 0 8px; } h2 { font-size:21px; margin:0 0 10px; } h3 { font-size:16px; }
.audit-group { border-top:0; padding-top:0; } .audit-group > h2 { margin-top:40px; padding-bottom:8px; border-bottom:2px solid #17675b; font-size:25px; }
html[lang=en] .fr, html[lang=fr] .en { display:none; }
th button { font:inherit; font-weight:bold; border:0; background:transparent; color:inherit; cursor:pointer; text-align:left; padding:0; }
.table-controls { display:flex; flex-wrap:wrap; gap:16px; align-items:center; }
section { border-top:1px solid var(--line); margin-top:28px; padding-top:22px; }
a { color:#17675b; } .muted { color:var(--muted); } .action { border-left:3px solid #b58527; padding:6px 12px; }
table { border-collapse:collapse; font-size:12px; margin:12px 0; } th,td { border-bottom:1px solid var(--line); padding:6px 9px; text-align:left; vertical-align:top; }
th[aria-sort=ascending] button::after { content:" ↑"; } th[aria-sort=descending] button::after { content:" ↓"; }
th { background:var(--soft); } tbody tr:nth-child(even) { background:#fafcfb; }
.table-wrap { overflow:auto; max-width:100%; } .badge { display:inline-block; color:white; border-radius:4px; padding:1px 7px; font-size:12px; vertical-align:middle; }
summary { cursor:pointer; color:#17675b; padding:6px 0; } code { background:var(--soft); padding:1px 4px; }
input,select { font:inherit; padding:5px; border:1px solid #adbab3; border-radius:3px; }
.matrix-controls { display:flex; flex-wrap:wrap; gap:14px; align-items:end; } .matrix-controls label { display:flex; flex-direction:column; }
.matrix-controls input[type=number] { width:90px; } .matrix-wrap { overflow:auto; max-height:680px; }
.count-heatmap { border-collapse:separate; border-spacing:2px; } .count-heatmap td { min-width:82px; white-space:nowrap; font-variant-numeric:tabular-nums; }
.count-heatmap th { position:sticky; background:var(--soft); z-index:1; white-space:nowrap; }
.count-heatmap thead th { top:0; } .count-heatmap th:first-child { left:0; min-width:210px; } .count-heatmap thead th:first-child { z-index:2; }
.coverage-figure { margin:16px 0; }
@media(max-width:700px) { body { padding:16px 12px; } }
@media print { input,select { display:none; } }
"""


def _local(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in df.columns:
        if isinstance(df[c].dtype, pd.DatetimeTZDtype):
            df[c] = df[c].dt.tz_convert(TIMEZONE).dt.strftime("%Y-%m-%d %H:%M:%S")
        elif pd.api.types.is_datetime64_any_dtype(df[c]):
            df[c] = df[c].dt.strftime("%Y-%m-%d")
    return df


def _t(en, fr):
    return f'<span class="en">{html.escape(en)}</span><span class="fr">{html.escape(fr)}</span>'


def _table(df: pd.DataFrame, max_rows=MAX_TABLE_ROWS, links=(), audit=False, table_class=None, filter_column='') -> str:
    if df is None or df.empty:
        return '<p class="muted">'+_t('No rows.', 'Aucune ligne.')+'</p>'
    display = _local(df.head(max_rows))
    if filter_column and 'date' in df:
        for column in ('start', 'end', 'sunrise', 'sunset', 'civil_dawn', 'civil_dusk'):
            if column in df:
                local = df[column].head(max_rows).dt.tz_convert(TIMEZONE)
                display[column] = local.dt.strftime('%H:%M')
                different_day = local.dt.tz_localize(None).dt.normalize().ne(df.date.head(max_rows))
                display.loc[different_day, column] = local.loc[different_day].dt.strftime('%m-%d %H:%M')
    out = f'<table class="sortable {table_class or "audit-table"}"><thead><tr>'
    for column in df:
        out += '<th scope="col" aria-sort="none"><button type="button">'+_t(column.replace('_', ' '), COLUMNS_FR.get(column, column.replace('_', ' ')))+'</button></th>'
    out += '</tr></thead><tbody>'
    for position, (_, row) in enumerate(display.iterrows()):
        value = df.iloc[position][filter_column] if filter_column else ''
        out += f'<tr data-filter-value="{value}">'
        for column, value in row.items():
            raw = df.iloc[position][column]
            sort = '' if pd.isna(raw) else str(raw)
            cell = '' if pd.isna(value) else f'{value:.2f}'.rstrip('0').rstrip('.') if isinstance(value, float) else str(value)
            if column not in links:
                cell = html.escape(cell)
            out += f'<td data-sort="{html.escape(sort, quote=True)}">{cell}</td>'
        out += '</tr>'
    out += '</tbody></table>'
    more = len(df)-max_rows
    note = '<p class="muted">'+_t(f'Preview: {max_rows} of {len(df):,} rows. Download the complete table.', f'Aperçu : {max_rows} lignes sur {len(df):,}. Télécharger la table complète.')+'</p>' if more > 0 else ''
    return f'<div class="table-wrap">{out}</div>{note}'


def _badge(status: str) -> str:
    labels = {'pass': ('pass', 'conforme'), 'warn': ('review', 'à revoir'), 'fail': ('fail', 'échec')}
    return f'<span class="badge" style="background:{STATUS_COLORS[status]}">{_t(*labels[status])}</span>'


def _section_reconciliation(comparison, taxonomy_order):
    years = comparison.loc[comparison['report_count'].notna(), 'year']
    data = comparison.astype(object).where(comparison.notna(), None).to_dict('records')
    body = '<p>'+_t('R = report; D = dataset; Δ = D − R. Dataset totals cover the whole year; reports use their published seasons. Percentages use R as the baseline. Blank means missing, zero is a count.', 'R = rapport ; D = données ; Δ = D − R. Les données couvrent l’année entière ; les rapports suivent leurs saisons publiées. Les pourcentages utilisent R comme référence. Vide signifie absent, zéro est un effectif.')+'</p>'
    body += '<form id="count-matrix-form" class="matrix-controls">'
    for field, label, label_fr, options in [
        ('mode','Colour by','Couleur selon',[('difference','Difference','Différence'),('percentage','Percentage difference','Écart en pourcentage'),('report_count','Report count','Effectif du rapport'),('dataset_count','Dataset count','Effectif des données')]),
        ('coverage','Show','Afficher',[('reports','Species/years with report counts','Espèces/années avec effectifs des rapports'),('all','All available species/years','Toutes les espèces/années disponibles')]),
        ('sort','Sort species by','Trier les espèces selon',[('abundance','Abundance','Abondance'),('taxonomy','Taxonomy','Taxonomie')])]:
        # Options cannot contain spans; the language switch replaces their labels.
        body += '<label>'+_t(label,label_fr)+f' <select id="matrix-{field}">'
        for value,en,fr in options:
            body += f'<option value="{value}" data-en="{en}" data-fr="{fr}">{en}</option>'
        body += '</select></label>'
    for field,en,fr,value in [('from','From year','Année de début',years.min()),('to','To year','Année de fin',years.max())]:
        body += '<label>'+_t(en,fr)+f' <input id="matrix-{field}" type="number" value="{value}" min="{comparison.year.min()}" max="{comparison.year.max()}"></label>'
    body += '<label>'+_t('Species','Espèce')+' <input id="matrix-species" type="search"></label></form>'
    body += '<p id="matrix-availability" class="muted"></p><p id="matrix-legend" class="muted"></p><div id="count-matrix" class="matrix-wrap"></div>'
    body += '<p><a href="report_reconciliation.csv">'+_t('Download counts','Télécharger les effectifs')+'</a></p>'
    body += '<script id="annual-counts" type="application/json">'+json.dumps(data, ensure_ascii=False).replace('<', r'\u003c')+'</script>'
    body += '<script id="annual-taxonomy" type="application/json">'+json.dumps(taxonomy_order, ensure_ascii=False).replace('<', r'\u003c')+'</script>'
    return body


def _check_section(check):
    rows = check.rows.copy()
    if check.columns:
        rows = rows.reindex(columns=check.columns)
    links = []
    for field in ('survey_id', 'duplicate_of'):
        if field in rows:
            target = 'edit' if field == 'survey_id' else 'edit_kept_period'
            native_ids = check.rows.get('source_survey_id', rows[field]) if field == 'survey_id' else rows[field]
            rows[target] = [f'<a href="https://www.trektellen.org/count/edit/{html.escape(str(sid)[1:])}" '
                            'target="_blank" rel="noopener">'+_t('Edit count', 'Modifier le comptage')+'</a>' if str(sid).startswith('T') else '' for sid in native_ids]
            links.append(target)
    if 'date' in rows and 'survey_id' in rows:
        rows['view'] = [f'<a href="https://www.trektellen.org/count/view/{TREKTELLEN_SITE_ID}/{pd.Timestamp(date):%Y%m%d}" '
                        'target="_blank" rel="noopener">'+_t('View day', 'Voir la journée')+'</a>' if str(sid).startswith('T') and pd.notna(date) else ''
                        for date,sid in zip(rows.date,rows.survey_id)]
        links.append('view')
    en, fr, detail, detail_fr = CHECK_TEXT.get(check.key, (check.name, check.name, check.detail, check.detail))
    if check.key == 'taxonomy-source':
        en, fr = 'Taxonomy sources', 'Sources taxonomiques'
        detail = check.detail
        detail_fr = check.detail.replace('Taxa named from each checklist:', 'Taxons nommés selon chaque liste :')
    body = f'<section id="{check.key}"><h3>{_t(en,fr)} {_badge(check.status)}</h3><p>{_t(detail,detail_fr)}</p>'
    if check.action and not rows.empty:
        if check.group == 'Historical records':
            action = ('Check the workbook sheet/row and config/attributes/historical_attributes.csv; assign only supported values.', 'Vérifier la feuille/ligne du classeur et config/attributes/historical_attributes.csv ; attribuer seulement les valeurs étayées.')
        elif check.key in ('taxa-in-source-taxa-csv', 'every-bird-taxon-has-an-avibase-id', 'avibase-ids-in-the-checklists'):
            action = ('Review taxonomy/source_taxa.csv against the maintained checklists.', 'Vérifier taxonomy/source_taxa.csv à partir des listes taxonomiques utilisées.')
        elif check.group == 'Coverage and published totals':
            action = ('Check source records and report evidence; record supported decisions in config/audit-settings/interruption-review-notes.csv.', 'Vérifier les sources et rapports ; consigner les décisions étayées dans config/audit-settings/interruption-review-notes.csv.')
        elif check.key.startswith('survey-status-'):
            action = ('Check source remarks; record supported status decisions in config/survey-status/trektellen-survey-status.csv.', 'Vérifier les remarques source ; consigner les statuts étayés dans config/survey-status/trektellen-survey-status.csv.')
        else:
            action = ('Check original records; correct confirmed errors and re-export. Keep legitimate records.', 'Vérifier les données originales ; corriger les erreurs confirmées puis réexporter. Conserver les données légitimes.')
        body += '<p class="action">'+_t(*action)+'</p>'
    if not rows.empty:
        controls = '<div class="table-controls"><label>'+_t('Search rows ', 'Rechercher des lignes ')+'<input class="finding-search" type="search"></label>'
        if check.filter_column:
            unit = ('Night overlap above (min)', 'Chevauchement de nuit supérieur à (min)') if check.filter_column == 'night_minutes' else ('Duration above (h)', 'Durée supérieure à (h)')
            if check.filter_column == 'outside_minutes':
                unit = ('Outside period by more than (min)', 'Écart hors période supérieur à (min)')
            floor = 12 if check.key == 'long-surveys' else 0
            controls += '<label>'+_t(*unit)+f' <input class="finding-threshold" type="number" min="{floor}" step="0.5" value="{check.filter_threshold}"></label>'
        controls += '<span class="visible-count muted" aria-live="polite"></span></div>'
        if check.filter_column:
            controls += '<p class="muted">'+_t('Filters change the view only.', 'Les filtres changent seulement l’affichage.')+'</p>'
        table = _table(rows, max_rows=len(rows) if check.filter_column else MAX_TABLE_ROWS, links=links, filter_column=check.filter_column)
        content = controls+table
        body += '<details><summary>'+_t(f'{len(rows):,} evidence rows', f'{len(rows):,} lignes justificatives')+'</summary>'+content+'</details>'
    if check.file:
        body += f'<p><a href="{check.file}">'+_t('Download complete evidence', 'Télécharger les données complètes')+'</a>'
        if check.file == 'validation_findings.csv':
            body += ' <span class="muted">'+_t('(filter the CSV by test name)', '(filtrer le CSV par nom de contrôle)')+'</span>'
        body += '</p>'
    return body+'</section>'


def _coverage_section(coverage, season):
    data = _local(coverage).astype(object).where(coverage.notna(), None).to_dict('records')
    body = '<section id="yearly-coverage"><h3>'+_t('Coverage by day and year', 'Couverture par jour et par année')+'</h3>'
    body += '<p>'+_t('Final dataset after selection and overlap removal. Choose a metric; hover over the figure for daily values.', 'Données finales après sélection et suppression des chevauchements. Choisir une mesure ; survoler la figure pour les valeurs journalières.')+'</p>'
    body += '<label>'+_t('Metric ', 'Mesure ')+'<select id="coverage-metric">'
    for key, (en, fr, _, _) in COVERAGE_METRICS.items():
        body += f'<option value="{key}" data-en="{en}" data-fr="{fr}">{en}</option>'
    body += '</select></label><p id="coverage-description"></p>'
    body += '<script src="coverage/plotly.min.js"></script><figure class="coverage-figure"><div id="coverage-chart"></div>'
    body += '<figcaption>'+_t('Grey: no recorded value. Pale blue: zero. Large ranges use a logarithmic colour scale; hover values remain actual totals.', 'Gris : aucune valeur renseignée. Bleu pâle : zéro. Les grandes plages utilisent une échelle de couleur logarithmique ; le survol affiche les valeurs réelles.')+'</figcaption></figure>'
    body += '<p><button id="coverage-download" type="button">'+_t('Download figure', 'Télécharger la figure')+'</button> · <a href="daily_coverage.csv">'+_t('Download daily metrics', 'Télécharger les mesures journalières')+'</a></p>'
    for name, values in [('daily-coverage', data), ('coverage-season', season), ('coverage-metrics', COVERAGE_METRICS)]:
        body += f'<script id="{name}" type="application/json">'+json.dumps(values, ensure_ascii=False).replace('<', r'\u003c')+'</script>'
    return body+'</section>'


def render(checks, metadata, comparison=None, taxonomy_order=None, coverage=None, coverage_season=None):
    """Present computed audit results, grouped by research question."""
    body = '<label style="float:right">'+_t('Language ', 'Langue ')+'<select id="report-language"><option value="en">English</option><option value="fr">Français</option></select></label>'
    body += f'<h1>{SITE_NAME} — audit</h1><p class="muted">'+_t('Built ', 'Généré le ')+html.escape(metadata.get('built_at', ''))+'. '+_t('Times: Europe/Paris. Source evidence keeps its original language.', 'Heures : Europe/Paris. Les données source gardent leur langue originale.')+'</p>'
    for group, fr in GROUPS.items():
        body += f'<section class="audit-group"><h2>{_t(group,fr)}</h2>'
        body += ''.join(_check_section(check) for check in checks if check.group == group)
        if group == 'Coverage and published totals':
            if coverage is not None:
                body += _coverage_section(coverage, coverage_season)
            if comparison is not None:
                body += '<section id="published-totals"><h3>'+_t('Published totals and source counts', 'Totaux des rapports et effectifs source')+'</h3><p>'+_t('Review differences against report seasons, taxon mappings and overlap decisions.', 'Examiner les écarts selon les saisons des rapports, les correspondances taxonomiques et les chevauchements.')+'</p>'+_section_reconciliation(comparison, taxonomy_order or {})+'</section>'
        body += '</section>'
    body += '<footer><p class="muted">'+_t('Code tests run separately through pytest.', 'Les tests du code s’exécutent séparément avec pytest.')+' <a href="audit.json">'+_t('Audit inventory', 'Inventaire des contrôles')+'</a> · <a href="README.md">'+_t('Audit file guide', 'Guide des fichiers d’audit')+'</a></p></footer>'
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>Défilé build audit</title><style>{CSS}</style></head>"
        f"<body>{body}" + """
<script>
const language = document.getElementById('report-language');
function filterRows(section) {
  const search = section.querySelector('.finding-search');
  const threshold = section.querySelector('.finding-threshold');
  const rows = [...section.querySelectorAll('tbody tr')];
  rows.forEach(row => {
    row.hidden = (search && !row.textContent.toLowerCase().includes(search.value.toLowerCase())) ||
      (threshold && Number(row.dataset.filterValue) <= Number(threshold.value));
  });
  const count = section.querySelector('.visible-count');
  if (count) count.textContent = `${rows.filter(r => !r.hidden).length} / ${rows.length} `+(language.value === 'fr' ? 'lignes affichées' : 'rows shown');
}
document.querySelectorAll('.table-controls').forEach(controls => {
  const section = controls.closest('section');
  controls.addEventListener('input', () => filterRows(section));
  filterRows(section);
});
function enableSorting(table) {
 table.querySelectorAll('thead th').forEach((th) => {
  th.querySelector('button').addEventListener('click', () => {
    const column = th.cellIndex;
    const ascending = th.getAttribute('aria-sort') !== 'ascending';
    table.querySelectorAll('thead th').forEach(header => header.setAttribute('aria-sort', 'none'));
    th.setAttribute('aria-sort', ascending ? 'ascending' : 'descending');
    const rows = [...table.tBodies[0].rows];
    rows.sort((a,b) => {
      const x = a.cells[column].dataset.sort, y = b.cells[column].dataset.sort;
      if (x === '' || y === '') return x === y ? 0 : x === '' ? 1 : -1;
      const order = Number.isFinite(Number(x)) && Number.isFinite(Number(y)) ? Number(x)-Number(y) : x.localeCompare(y, language.value, {numeric:true});
      return ascending ? order : -order;
    });
    rows.forEach(row => table.tBodies[0].appendChild(row));
  });
 });
}
document.querySelectorAll('table.sortable').forEach(enableSorting);
language.addEventListener('change', () => {
  document.documentElement.lang = language.value;
  document.querySelectorAll('option[data-en]').forEach(option => option.textContent = option.dataset[language.value]);
  document.querySelectorAll('.table-controls').forEach(controls => filterRows(controls.closest('section')));
  if (matrixData) drawMatrix();
  if (coverageData) drawCoverage();
});
let drawCoverage;
const coverageData = document.getElementById('daily-coverage');
if (coverageData) {
  const records = JSON.parse(coverageData.textContent);
  const season = JSON.parse(document.getElementById('coverage-season').textContent);
  const metrics = JSON.parse(document.getElementById('coverage-metrics').textContent);
  const lookup = new Map(records.map(row => [`${row.year}::${row.day_of_year}`, row]));
  const metric = document.getElementById('coverage-metric');
  const chart = document.getElementById('coverage-chart');
  const years = Array.from({length: Math.max(...records.map(r => r.year))-Math.min(...records.map(r => r.year))+1}, (_, i) => Math.min(...records.map(r => r.year))+i);
  const days = Array.from({length: season.end_day_of_year-season.start_day_of_year+1}, (_, i) => season.start_day_of_year+i);
  drawCoverage = () => {
    const fr = language.value === 'fr';
    const label = metrics[metric.value][fr ? 1 : 0];
    document.getElementById('coverage-description').textContent = metrics[metric.value][fr ? 3 : 2];
    const values = years.map(year => days.map(day => lookup.get(`${year}::${day}`)?.[metric.value] ?? null));
    const maximum = Math.max(1, ...values.flat().filter(v => v !== null));
    const logarithmic = maximum > 100;
    const ticks = [0, ...Array.from({length: Math.floor(Math.log10(maximum))+1}, (_, i) => 10**i)];
    const hover = years.map((year, i) => days.map((day, j) => {
      const date = new Date(Date.UTC(year, 0, day)).toISOString().slice(0, 10);
      const value = values[i][j];
      return `${date} · ${fr ? 'jour' : 'day'} ${day}<br>${label}: ${value === null ? '' : value.toLocaleString(fr ? 'fr-FR' : 'en-GB', {maximumFractionDigits: 2})}`;
    }));
    Plotly.react(chart, [{type: 'heatmap', x: days, y: years,
      z: values.map(row => row.map(v => v === null ? null : logarithmic ? Math.log1p(v) : v)),
      text: hover, hovertemplate: '%{text}<extra></extra>', hoverongaps: false,
      zmin: 0, zmax: logarithmic ? Math.log1p(maximum) : maximum,
      colorscale: [[0, '#eff6fb'], [.25, '#bdd7e7'], [.5, '#6baed6'], [.75, '#2171b5'], [1, '#08306b']],
      colorbar: {title: {text: label}, thickness: 14, ...(logarithmic ? {tickvals: ticks.map(Math.log1p), ticktext: ticks.map(v => v.toLocaleString(fr ? 'fr-FR' : 'en-GB'))} : {})}
    }], {height: Math.max(500, years.length*12+100), margin: {l: 65, r: 140, t: 15, b: 65},
      paper_bgcolor: '#ffffff', plot_bgcolor: '#e4e7e5', font: {family: 'system-ui, sans-serif', color: '#273b35'},
      xaxis: {title: {text: fr ? 'Jour de l’année' : 'Day of year'}, range: [season.start_day_of_year-.5, season.end_day_of_year+.5], dtick: 10, showgrid: false},
      yaxis: {title: {text: fr ? 'Année' : 'Year'}, range: [years[years.length-1]+.5, years[0]-.5], dtick: 5, showgrid: false},
      uirevision: 'coverage-season', dragmode: 'zoom'
    }, {responsive: true, displaylogo: false, modeBarButtonsToRemove: ['lasso2d', 'select2d'], toImageButtonOptions: {filename: 'coverage', scale: 2}});
  };
  metric.addEventListener('change', drawCoverage);
  document.getElementById('coverage-download').addEventListener('click', () => Plotly.downloadImage(chart, {format: 'png', filename: `coverage-${metric.value}-${language.value}`, scale: 2}));
  drawCoverage();
}
let drawMatrix;
const matrixData = document.getElementById('annual-counts');
if (matrixData) {
  const counts = JSON.parse(matrixData.textContent);
  const taxonomyOrder = JSON.parse(document.getElementById('annual-taxonomy').textContent);
  const form = document.getElementById('count-matrix-form');
  const mode = document.getElementById('matrix-mode');
  const coverage = document.getElementById('matrix-coverage');
  const sort = document.getElementById('matrix-sort');
  const from = document.getElementById('matrix-from');
  const to = document.getElementById('matrix-to');
  const speciesSearch = document.getElementById('matrix-species');
  const container = document.getElementById('count-matrix');
  const number = value => value === null ? '' : value.toLocaleString(language.value === 'fr' ? 'fr-FR' : 'en-GB');
  const abundance = new Map();
  const reportAbundance = new Map();
  counts.forEach(r => {
    if (r.dataset_count !== null) abundance.set(r.species, (abundance.get(r.species) || 0)+r.dataset_count);
    if (r.report_count !== null) reportAbundance.set(r.species, (reportAbundance.get(r.species) || 0)+r.report_count);
  });
  const total = name => abundance.get(name) ?? reportAbundance.get(name) ?? 0;
  drawMatrix = function() {
    const periodCounts = counts.filter(r => r.year >= Number(from.value) && r.year <= Number(to.value));
    const selected = periodCounts.filter(r => r.species.toLowerCase().includes(speciesSearch.value.toLowerCase()));
    const reported = selected.filter(r => r.report_count !== null);
    const visible = coverage.value === 'reports' ? reported : selected;
    const yearCounts = coverage.value === 'reports' ? periodCounts.filter(r => r.report_count !== null) : periodCounts;
    const years = [...new Set(yearCounts.map(r => r.year))].sort((a,b) => a-b);
    const species = [...new Set(visible.map(r => r.species))].sort((a,b) =>
      (sort.value === 'taxonomy' ? (taxonomyOrder[a] ?? Infinity)-(taxonomyOrder[b] ?? Infinity) : total(b)-total(a)) || a.localeCompare(b));
    const lookup = new Map(selected.map(r => [`${r.species}::${r.year}`, r]));
    const value = r => ['difference','percentage'].includes(mode.value) ?
      (r.report_count === null || r.dataset_count === null || (mode.value === 'percentage' && r.report_count === 0) ? null :
        (r.dataset_count-r.report_count)/(mode.value === 'percentage' ? r.report_count/100 : 1)) : r[mode.value];
    const maximum = Math.max(1, ...selected.map(r => Math.abs(value(r) || 0)));
    const table = document.createElement('table');
    table.className = 'count-heatmap';
    const head = table.createTHead().insertRow();
    [language.value === 'fr' ? 'Espèce / année' : 'Species / year', ...years].forEach(label => {
      const th = head.appendChild(document.createElement('th'));
      th.setAttribute('aria-sort', 'none');
      th.appendChild(document.createElement('button')).textContent = label;
      const report = counts.find(r => r.year === label && r.report_pdf);
      if (report) {
        const link = th.appendChild(document.createElement('div')).appendChild(document.createElement('a'));
        link.href = report.report_pdf;
        link.textContent = 'PDF';
        link.target = '_blank';
        link.rel = 'noopener';
      }
    });
    const body = table.createTBody();
    species.forEach(name => {
      const row = body.insertRow();
      const speciesCell = row.appendChild(document.createElement('th'));
      speciesCell.textContent = name;
      speciesCell.dataset.sort = name;
      years.forEach(year => {
        const cell = row.insertCell();
        const r = lookup.get(`${name}::${year}`) || {report_count:null, dataset_count:null};
        const delta = r.report_count === null || r.dataset_count === null ? null : r.dataset_count-r.report_count;
        const colourValue = value(r);
        cell.dataset.sort = colourValue === null ? '' : String(colourValue);
        if (colourValue !== null) {
          const strength = Math.sqrt(Math.abs(colourValue)/maximum);
          const hue = ['difference','percentage'].includes(mode.value) && colourValue > 0 ? 28 : 210;
          cell.style.backgroundColor = `hsl(${hue}, 65%, ${100-38*strength}%)`;
        }
        [['R',r.report_count,'report_count'],['D',r.dataset_count,'dataset_count'],['Δ',delta,'difference']].forEach(([label,n,key]) => {
          if (n === null) return;
          const line = document.createElement('div');
          const percentage = key === 'difference' && r.report_count !== 0 ?
            ` (${(100*delta/r.report_count).toLocaleString(language.value === 'fr' ? 'fr-FR' : 'en-GB', {minimumFractionDigits:1, maximumFractionDigits:1, signDisplay:'exceptZero'})}%)` : '';
          line.textContent = `${label} ${key === 'difference' && n > 0 ? '+' : ''}${number(n)}${percentage}`;
          if (key === 'report_count' && r.report_pdf) {
            const link = document.createElement('a');
            link.href = r.report_pdf + (r.pdf_page ? `#page=${r.pdf_page}` : '');
            link.textContent = line.textContent;
            link.title = r.pdf_page ? (language.value === 'fr' ? `Ouvrir le PDF, page ${r.pdf_page}` : `Open PDF, page ${r.pdf_page}`) : (language.value === 'fr' ? 'Ouvrir le rapport PDF' : 'Open report PDF');
            link.target = '_blank';
            link.rel = 'noopener';
            line.replaceChildren(link);
          }
          if (key === mode.value || (key === 'difference' && mode.value === 'percentage')) line.style.fontWeight = '700';
          cell.appendChild(line);
        });
        cell.title = language.value === 'fr' ?
          `${name}, ${year} : rapport ${r.report_count === null ? 'absent' : number(r.report_count)}, données ${r.dataset_count === null ? 'absentes' : number(r.dataset_count)}, différence ${number(delta)}` :
          `${name}, ${year}: report ${r.report_count === null ? 'missing' : number(r.report_count)}, dataset ${r.dataset_count === null ? 'missing' : number(r.dataset_count)}, difference ${number(delta)}`;
      });
    });
    container.replaceChildren(table);
    enableSorting(table);
    const fr = language.value === 'fr';
    document.getElementById('matrix-availability').textContent = fr ?
      `${reported.length} effectifs des rapports · ${reported.filter(r => r.dataset_count !== null).length} correspondances. Abondance : somme sur toutes les années. Taxonomie : ordre eBird/Clements ; taxons sans correspondance à la fin.` :
      `${reported.length} report counts · ${reported.filter(r => r.dataset_count !== null).length} matches. Abundance: sum over all years. Taxonomy: eBird/Clements order; unmatched taxa last.`;
    document.getElementById('matrix-legend').textContent = ['difference','percentage'].includes(mode.value) ?
      (fr ? 'Bleu : données plus basses · Blanc : égalité · Orange : données plus hautes' : 'Blue: dataset lower · White: equal · Orange: dataset higher') +
      (mode.value === 'percentage' ? (fr ? ' · Écart relatif au rapport ; indéfini si le rapport vaut zéro' : ' · Relative to report count; undefined when report is zero') : '') :
      (fr ? 'Bleu plus foncé : effectif plus élevé' : 'Darker blue: higher count');
  };
  form.addEventListener('submit', event => event.preventDefault());
  form.addEventListener('input', drawMatrix);
  form.addEventListener('change', drawMatrix);
  drawMatrix();
}
</script></body></html>"""
    )
