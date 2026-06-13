/* Pipeline Success Rate — Gauge: % of pipelines that succeed.
Phase 13.3b: Part of DashboardCharts modular split. */
import { api } from '../api.js';

export class PipelineChart {
  constructor(canvas) {
    this.chart = new Chart(canvas.getContext('2d'), {
      type: 'doughnut',
      data: {
        labels: ['Succeeded', 'Failed'],
        datasets: [{
          data: [0, 100],
          backgroundColor: ['#34d399', '#475569'],
          borderColor: '#1e293b',
          borderWidth: 2,
        }],
      },
      options: gaugeOpts(),
    });
    this._centerText = null;
  }

  async loadHistory(range = '7d') {
    try {
      const d = await api.get(
        `/metrics/history?metric=pipeline_success&range=${range}`
      );
      if (d?.datasets?.[0]?.data?.length) {
        const pct = d.datasets[0].data.at(-1);
        this.setPercent(pct);
      }
    } catch { /* no history endpoint yet — ok */ }
  }

  setPercent(pct) {
    pct = Math.max(0, Math.min(100, pct));
    this.chart.data.datasets[0].data = [pct, 100 - pct];
    this.chart.data.datasets[0].backgroundColor =
      pct >= 80 ? ['#34d399', '#475569']
      : pct >= 50 ? ['#fbbf24', '#475569']
      : ['#f87171', '#475569'];
    this.chart.update('none');
  }

  destroy() { this.chart.destroy(); }
}

function gaugeOpts() {
  return {
    responsive: true, maintainAspectRatio: false,
    rotation: -90, circumference: 180,
    cutout: '75%',
    plugins: {
      title: {
        display: true, text: 'Pipeline Success Rate',
        color: '#e2e8f0',
      },
      legend: { display: false },
    },
  };
}
