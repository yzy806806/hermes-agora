/* Agent Activity Timeline — Line chart: active agents over time.
Phase 13.3b: Part of DashboardCharts modular split. */
import { api } from '../api.js';

const MAX_POINTS = 60;

export class ActivityChart {
  constructor(canvas) {
    this.chart = new Chart(canvas.getContext('2d'), {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: 'Active Agents',
          data: [],
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59,130,246,0.15)',
          fill: true, tension: 0.3,
          pointRadius: 2,
        }],
      },
      options: chartOpts('Active Agents Over Time'),
    });
  }

  async loadHistory(range = '7d') {
    try {
      const d = await api.get(`/metrics/history?metric=agent_activity&range=${range}`);
      if (d?.labels?.length) {
        this.chart.data.labels = d.labels;
        this.chart.data.datasets[0].data = d.datasets[0].data;
        this.chart.update();
      }
    } catch { /* no history endpoint yet — ok */ }
  }

  pushPoint(label, value) {
    const ds = this.chart.data;
    ds.labels.push(label);
    ds.datasets[0].data.push(value);
    if (ds.labels.length > MAX_POINTS) {
      ds.labels.shift();
      ds.datasets[0].data.shift();
    }
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
