/* API Rate Limit Usage — Line chart: TPM per agent.
Phase 13.3b: Part of DashboardCharts modular split. */
import { api } from '../api.js';

const MAX_POINTS = 60;
const PALETTE = [
  '#3b82f6','#8b5cf6','#f59e0b','#ef4444',
  '#34d399','#ec4899','#06b6d4','#f97316',
];

export class RateLimitChart {
  constructor(canvas) {
    this.chart = new Chart(canvas.getContext('2d'), {
      type: 'line',
      data: { labels: [], datasets: [] },
      options: chartOpts('API Rate Limit Usage (TPM)'),
    });
  }

  async loadHistory(range = '7d') {
    try {
      const d = await api.get(
        `/metrics/history?metric=rate_limit_usage&range=${range}`
      );
      if (d?.labels?.length && d.datasets?.length) {
        this.chart.data.labels = d.labels;
        this.chart.data.datasets = d.datasets.map((ds, i) => ({
          ...ds,
          borderColor: PALETTE[i % PALETTE.length],
          backgroundColor: 'transparent',
          tension: 0.3, pointRadius: 2,
        }));
        this.chart.update();
      }
    } catch { /* no history endpoint yet — ok */ }
  }

  pushAgentPoint(label, agentId, tpm) {
    let ds = this.chart.data.datasets.find(d => d.agentId === agentId);
    if (!ds) {
      const idx = this.chart.data.datasets.length;
      ds = {
        agentId, label: agentId.slice(0, 8),
        data: [], borderColor: PALETTE[idx % PALETTE.length],
        backgroundColor: 'transparent', tension: 0.3, pointRadius: 2,
      };
      this.chart.data.datasets.push(ds);
    }
    if (!this.chart.data.labels.includes(label)) {
      this.chart.data.labels.push(label);
      if (this.chart.data.labels.length > MAX_POINTS) {
        this.chart.data.labels.shift();
        this.chart.data.datasets.forEach(s => s.data.shift());
      }
    }
    ds.data.push(tpm);
    this.chart.update('none');
  }

  destroy() { this.chart.destroy(); }
}

function chartOpts(title) {
  return {
    responsive: true, maintainAspectRatio: false,
    plugins: {
      title: { display: true, text: title, color: '#e2e8f0' },
      legend: { labels: { color: '#94a3b8' } },
    },
    scales: {
      x: { ticks: { color: '#94a3b8', maxRotation: 45 } },
      y: { ticks: { color: '#94a3b8' }, beginAtZero: true },
    },
  };
}
