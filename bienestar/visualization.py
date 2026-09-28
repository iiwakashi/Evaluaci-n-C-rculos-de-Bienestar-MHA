from __future__ import annotations

from html import escape


COLORS = {
    1: "#E94F4F",
    2: "#F4C400",
    3: "#47AD43",
}


def _circle(score: int, size: str, moment: str) -> str:
    color = COLORS.get(score, "#A3A3A3")
    return (
        f'<span class="wellbeing-circle {size}" style="background:{color}" '
        f'title="{escape(moment)}" aria-label="{escape(moment)}"></span>'
    )


def evolution_html(evolution: list[dict]) -> str:
    cards = []
    for item in evolution:
        entry_name = {1: "Rojo", 2: "Amarillo", 3: "Verde"}.get(item["entry"], "Sin dato")
        exit_name = {1: "Rojo", 2: "Amarillo", 3: "Verde"}.get(item["exit"], "Sin dato")
        cards.append(
            f'<article class="indicator-card" title="{escape(item["change"])}">'
            '<div class="circle-pair">'
            f'{_circle(item["entry"], "entry-circle", f"Entrada: {entry_name}")}'
            f'{_circle(item["exit"], "exit-circle", f"Salida: {exit_name}")}'
            '</div>'
            f'<div class="indicator-label">{escape(item["label"])}</div>'
            '</article>'
        )
    return '<section class="indicator-grid">' + "".join(cards) + "</section>"


def summary_html(metrics: dict[str, int]) -> str:
    net = metrics["net"]
    net_class = "net-positive" if net > 0 else "net-negative" if net < 0 else "net-neutral"
    net_text = f"+{net}" if net > 0 else str(net)
    return f"""
    <section class="summary-section">
      <h2>Resumen total de evolución</h2>
      <div class="summary-grid">
        <div class="metric-card metric-improved"><span>Mejoran</span><strong>{metrics['improved']}</strong></div>
        <div class="metric-card metric-worsened"><span>Empeoran</span><strong>{metrics['worsened']}</strong></div>
        <div class="metric-card metric-unchanged"><span>Siguen igual</span><strong>{metrics['unchanged']}</strong></div>
        <div class="metric-card {net_class}"><span>Resultado neto</span><strong>{net_text}</strong></div>
      </div>
    </section>
    """


APP_CSS = """
<style>
  .block-container {max-width: 1280px; padding-top: 2rem; padding-bottom: 3rem;}
  .app-subtitle {color:#52606d; margin-top:-0.6rem; margin-bottom:1.6rem;}
  .legend {display:flex; flex-wrap:wrap; gap:1rem; align-items:center; margin:.75rem 0 1.5rem; color:#38444d;}
  .legend-item {display:flex; gap:.4rem; align-items:center;}
  .legend-dot {width:15px; height:15px; border-radius:50%; display:inline-block;}
  .moment-legend {margin-left:auto; font-size:.92rem; color:#68747d;}
  .indicator-grid {display:grid; grid-template-columns:repeat(auto-fit,minmax(155px,1fr)); gap:2rem 1.25rem; margin:1rem 0 2.5rem;}
  .indicator-card {min-height:120px; text-align:center; display:flex; flex-direction:column; align-items:center;}
  .circle-pair {height:58px; display:flex; align-items:center; justify-content:center; margin-bottom:.55rem;}
  .wellbeing-circle {display:inline-block; border-radius:50%; box-shadow:0 0 0 3px white;}
  .entry-circle {width:29px; height:29px; z-index:1; margin-right:-6px;}
  .exit-circle {width:48px; height:48px; z-index:2;}
  .indicator-label {font-size:.98rem; line-height:1.18; color:#182026; max-width:185px;}
  .summary-section {border-top:1px solid #d9dde1; padding-top:1.2rem; margin-top:.5rem;}
  .summary-section h2 {font-size:1.25rem; margin-bottom:1rem;}
  .summary-grid {display:grid; grid-template-columns:repeat(4,minmax(135px,1fr)); gap:.8rem;}
  .metric-card {border-radius:14px; color:white; padding:.85rem 1rem; display:flex; justify-content:space-between; align-items:center; min-height:58px;}
  .metric-card span {font-weight:600;}
  .metric-card strong {font-size:1.65rem;}
  .metric-improved {background:#2fa34a;}
  .metric-worsened {background:#e94f4f;}
  .metric-unchanged {background:#7a838b;}
  .net-positive {background:#157a3d;}
  .net-negative {background:#b92727;}
  .net-neutral {background:#46515a;}
  @media (max-width:700px) {
    .summary-grid {grid-template-columns:repeat(2,minmax(130px,1fr));}
    .moment-legend {width:100%; margin-left:0;}
  }
</style>
"""


LEGEND_HTML = """
<div class="legend">
  <span class="legend-item"><i class="legend-dot" style="background:#E94F4F"></i>Rojo</span>
  <span class="legend-item"><i class="legend-dot" style="background:#F4C400"></i>Amarillo</span>
  <span class="legend-item"><i class="legend-dot" style="background:#47AD43"></i>Verde</span>
  <span class="moment-legend">Círculo pequeño: entrada · Círculo grande: salida</span>
</div>
"""
