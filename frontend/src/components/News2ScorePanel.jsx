import React from 'react';
import { Activity, Gauge, Heart, ShieldAlert, Thermometer, Wind } from 'lucide-react';
import { Sparkline } from './Sparkline';
import { NEWS2_BANDS } from '../utils/news2';

const PARAMETER_ICONS = {
  rr: Wind,
  spo2: Activity,
  bp_sys: Gauge,
  hr: Heart,
  acvpu: ShieldAlert,
  temperature: Thermometer,
};

const PARAMETER_COLORS = {
  rr: '#22d3ee',
  spo2: '#38bdf8',
  bp_sys: '#a78bfa',
  hr: '#fb7185',
  acvpu: '#f59e0b',
  temperature: '#fbbf24',
};

function pointClass(points) {
  if (points >= 3) return 'is-high';
  if (points > 0) return 'is-medium';
  return 'is-low';
}

export function News2Badge({ news2, showLabel = true }) {
  if (!news2) return null;
  const breakdown = news2.breakdown.map((item) => `${item.label}: +${item.points}`).join(', ');
  return (
    <span
      className={`news2-badge news2-badge-${news2.color}`}
      title={`NEWS2 ${news2.score} — ${news2.level}. ${breakdown || 'No scoring parameters.'}`}
    >
      <ShieldAlert size={11} />
      <span>NEWS2 {news2.score}</span>
      {showLabel && <span className="news2-badge-label">{news2.shortLevel}</span>}
    </span>
  );
}

export function News2ScorePanel({ news2, trends = {} }) {
  if (!news2) return null;

  return (
    <section className={`news2-panel news2-panel-${news2.color}`} aria-label="NEWS2 clinical risk score">
      <div className="news2-panel-top">
        <div className="news2-panel-identity">
          <span className={`news2-panel-icon news2-panel-icon-${news2.color}`}>
            <ShieldAlert size={20} />
          </span>
          <div>
            <div className="news2-panel-eyebrow">National Early Warning Score</div>
            <h3 className="news2-panel-title">
              NEWS2 <strong>{news2.score}</strong>
              <span className={`news2-risk-pill is-${news2.color}`}>{news2.shortLevel} risk</span>
            </h3>
            <p className="news2-panel-action">{news2.action}</p>
          </div>
        </div>

        <div className={`news2-score-dial is-${news2.color}`} aria-hidden="true">
          <span className="score-num">{news2.score}</span>
          <span className="score-label">of 20</span>
        </div>
      </div>

      <div className="news2-band-scale" aria-label="NEWS2 risk bands">
        {NEWS2_BANDS.map((band) => (
          <span
            key={band.key}
            className={`news2-band-chip is-${band.key} ${news2.band.key === band.key ? 'is-active' : ''}`}
          >
            <span className="news2-band-dot" />
            <strong>{band.short}</strong>
            <span>{band.range}</span>
          </span>
        ))}
      </div>

      <div className="news2-parameter-grid">
        {news2.parameters.map((parameter) => {
          const Icon = PARAMETER_ICONS[parameter.key] || Activity;
          const trend = trends[parameter.key];
          return (
            <article key={parameter.key} className={`news2-parameter-card ${pointClass(parameter.points)}`}>
              <div className="news2-parameter-top">
                <span className="news2-parameter-name">
                  <Icon size={14} />
                  {parameter.label}
                </span>
                <span className={`news2-point-chip ${pointClass(parameter.points)}`}>
                  {parameter.points} {parameter.points === 1 ? 'pt' : 'pts'}
                </span>
              </div>
              <div className="news2-parameter-reading">
                {parameter.valueText}
                <span className="news2-parameter-target">Target {parameter.target}</span>
              </div>
              {trend ? (
                <>
                  <Sparkline
                    data={trend.series}
                    color={PARAMETER_COLORS[parameter.key]}
                    label={`${parameter.label} 24-hour trend`}
                    className="news2-sparkline"
                  />
                  <div
                    className={`news2-param-trend ${
                      trend.worsening ? 'is-worse' : trend.trend === 'stable' ? 'is-stable' : 'is-better'
                    }`}
                  >
                    <span aria-hidden="true">
                      {trend.trend === 'stable' ? '→' : trend.trend === 'up' ? '↑' : '↓'}
                    </span>
                    {trend.summary}
                  </div>
                </>
              ) : (
                <div className="news2-param-trend is-stable">
                  <span aria-hidden="true">→</span>
                  No 24h series
                </div>
              )}
            </article>
          );
        })}
      </div>

      <p className="news2-panel-footnote">
        NEWS2 is validated decision support, not a diagnosis. Escalate alongside clinical judgement and local policy.
      </p>
    </section>
  );
}

export default News2ScorePanel;
