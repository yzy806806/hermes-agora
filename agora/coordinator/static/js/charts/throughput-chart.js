/* Task Throughput — Bar chart: tasks completed per day/week.
Phase 13.3b: Part of DashboardCharts modular split. */
import { api } from '../api.js';

const MAX_BARS = 30;

export class ThroughputChart {
  constructor(canvas) {
    this.chart = new Chart(canvas.getContext('2d'), {
      type: 'bar',
      data: {
        labels: [],
        datasets: [{
          label: 'Tasks Completed',
          data: [],
          backgroundColor: '#34d399',
          borderColor: '#059669',
          borderWidth: 1,
        }],
      },
      options: chartOpts('Task Throughput'),
    });
  }

  async loadHistory(range = '7d') {
    try {
      const d = await api.get(
        `/metrics/history?metric=task_throughput&range=${range}`
      );
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
    if (ds.labels.length > MAX_BARS) {
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
