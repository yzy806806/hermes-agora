/* Discussion Metrics — Pie chart: motion outcomes (consensus/deadlock/timeout).
Phase 13.3b: Part of DashboardCharts modular split. */
import { api } from '../api.js';

const COLORS = ['#34d399', '#f87171', '#fbbf24', '#3b82f6', '#8b5cf6'];

export class DiscussionChart {
  constructor(canvas) {
    this.chart = new Chart(canvas.getContext('2d'), {
      type: 'doughnut',
      data: {
        labels: ['Consensus', 'Deadlock', 'Timeout', 'Open'],
        datasets: [{
          data: [0, 0, 0, 0],
          backgroundColor: COLORS.slice(0, 4),
          borderColor: '#1e293b',
          borderWidth: 2,
        }],
      },
      options: chartOpts('Motion Outcomes'),
    });
  }

  async loadHistory(range = '7d') {
    try {
      const d = await api.get(
        `/metrics/history?metric=discussion_outcomes&range=${range}`
      );
      if (d?.labels?.length) {
        this.chart.data.labels = d.labels;
        this.chart.data.datasets[0].data = d.datasets[0].data;
        this.chart.data.datasets[0].backgroundColor =
          COLORS.slice(0, d.labels.length);
        this.chart.update();
      }
    } catch { /* no history endpoint yet — ok */ }
  }

  updateData(labels, values) {
    this.chart.data.labels = labels;
    this.chart.data.datasets[0].data = values;
    this.chart.data.datasets[0].backgroundColor =
      COLORS.slice(0, labels.length);
    this.chart.update('none');
  }

  destroy() { this.chart.destroy(); }
}

function chartOpts(title) {
  return {
    responsive: true, maintainAspectRatio: false,
    plugins: {
      title: { display: true, text: title, color: '#e2e8f0' },
      legend: { position: 'bottom', labels: { color: '#94a3b8' } },
    },
  };
}
