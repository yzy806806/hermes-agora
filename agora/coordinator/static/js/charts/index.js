/* DashboardCharts — orchestrator for all Phase 13.3b/c chart modules.
Creates chart instances, loads history, pushes real-time WS updates. */
import { ActivityChart } from './activity-chart.js';
import { ThroughputChart } from './throughput-chart.js';
import { DiscussionChart } from './discussion-chart.js';
import { PipelineChart } from './pipeline-chart.js';
import { RateLimitChart } from './rate-limit-chart.js';

export class DashboardCharts {
  constructor() { this.charts = {}; }

  /** Call after DOM ready with canvas elements in the page. */
  init() {
    const ids = {
      activity: 'chart-activity', throughput: 'chart-throughput',
      discussion: 'chart-discussion', pipeline: 'chart-pipeline',
      rateLimit: 'chart-rate-limit',
    };
    if ($('#' + ids.activity))
      this.charts.activity = new ActivityChart($('#' + ids.activity));
    if ($('#' + ids.throughput))
      this.charts.throughput = new ThroughputChart($('#' + ids.throughput));
    if ($('#' + ids.discussion))
      this.charts.discussion = new DiscussionChart($('#' + ids.discussion));
    if ($('#' + ids.pipeline))
      this.charts.pipeline = new PipelineChart($('#' + ids.pipeline));
    if ($('#' + ids.rateLimit))
      this.charts.rateLimit = new RateLimitChart($('#' + ids.rateLimit));
  }

  /** Load historical data for all charts. */
  async loadHistory(range = '7d') {
    await Promise.allSettled(
      Object.values(this.charts).map(c => c.loadHistory(range))
    );
  }

  /** Push a real-time WS event into the relevant chart. */
  updateFromEvent(msg) {
    const t = msg.type, p = msg.payload || {};
    if (t === 'AGENT_STATUS') this._onAgentStatus(p);
    else if (t === 'TASK_UPDATE') this._onTaskUpdate(p);
    else if (t === 'DISCUSSION_UPDATE') this._onDiscussionUpdate(p);
    else if (t === 'PIPELINE_PHASE_CHANGE') this._onPipelinePhase(p);
  }

  _onAgentStatus(p) {
    if (!this.charts.activity) return;
    const ts = p.timestamp || new Date().toISOString().slice(11, 16);
    const count = p.active_count ?? (p.is_online !== false ? 1 : 0);
    this.charts.activity.pushPoint(ts, count);
  }

  _onTaskUpdate(p) {
    if (!this.charts.throughput) return;
    if (p.status === 'completed' || p.status === 'failed') {
      const day = new Date().toISOString().slice(0, 10);
      this.charts.throughput.pushPoint(day, 1);
    }
  }

  _onDiscussionUpdate(p) {
    if (!this.charts.discussion) return;
    const outcome = p.outcome || p.status;
    if (!outcome) return;
    const labels = this.charts.discussion.chart.data.labels;
    const data = this.charts.discussion.chart.data.datasets[0].data;
    const idx = labels.indexOf(outcome);
    if (idx >= 0) data[idx]++;
    else { labels.push(outcome); data.push(1); }
    this.charts.discussion.chart.update('none');
  }

  _onPipelinePhase(p) {
    if (!this.charts.pipeline) return;
    const sr = p.success_rate;
    if (p.phase === 'completed')
      this.charts.pipeline.setPercent(sr ?? 100);
    else if (p.phase === 'failed')
      this.charts.pipeline.setPercent(sr ?? 0);
  }

  /** Clean up all chart instances. */
  destroy() { Object.values(this.charts).forEach(c => c.destroy()); this.charts = {}; }
}

function $(sel) { return document.querySelector(sel); }
