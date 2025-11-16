// Connect to SSE endpoint and render merged CSV records
const statusEl = document.getElementById('status');
const container = document.getElementById('container');

function formatTs(ts) {
  if (!ts) return '';
  // try numeric
  const n = Number(ts);
  if (!isNaN(n)) {
    // Handle Unix timestamps (seconds) vs JavaScript timestamps (milliseconds)
    const ms = n > 1e12 ? n : n * 1000;
    return new Date(ms).toLocaleString();
  }
  // fallback raw
  try { return new Date(ts).toLocaleString(); } catch (e) { return String(ts); }
}

function render(records) {
  container.innerHTML = '';
  if (!records || records.length === 0) {
    container.innerHTML = '<div class="card">No application status found yet.</div>';
    return;
  }

  // group by job_id
  const groups = {};
  records.forEach(r => {
    const id = (r.job_id === undefined || r.job_id === null) ? '_unknown' : r.job_id;
    if (!groups[id]) groups[id] = { job_id: id, company_name: r.company_name || '', job_title: r.job_title || '', updates: [] };
    if (r.event_time == -100.0) {
      groups[id].updates.push({ status: r.status_update || '', ts: r.timestamp || '' });
    } else {
      groups[id].updates.push({ status: r.status_update || '', ts: r.event_time || '' });
    }
  });

  Object.values(groups).forEach(g => {
    const card = document.createElement('div');
    card.className = 'card';
    
    // Title
    const h = document.createElement('h3');
    h.textContent = `${g.company_name} — ${g.job_title}`;
    card.appendChild(h);

    // Timeline container
    const timeline = document.createElement('div');
    timeline.className = 'timeline';

    // Sort updates by timestamp
    const sortedUpdates = g.updates.sort((a, b) => {
      const ta = Number(a.ts) || 0;
      const tb = Number(b.ts) || 0;
      return ta - tb;
    });

    // Create timeline items
    sortedUpdates.forEach(u => {
      const item = document.createElement('div');
      item.className = 'timeline-item';
      
      const dot = document.createElement('div');
      dot.className = 'timeline-dot';
      item.appendChild(dot);

      const content = document.createElement('div');
      content.className = 'timeline-content';
      
      const date = document.createElement('div');
      date.className = 'timeline-date';
      date.textContent = formatTs(u.ts);
      content.appendChild(date);

      const status = document.createElement('div');
      status.className = 'timeline-status';
      status.textContent = u.status;
      content.appendChild(status);

      item.appendChild(content);
      timeline.appendChild(item);
    });

    card.appendChild(timeline);
    container.appendChild(card);
  });
}

function connect() {
  const es = new EventSource('/events');
  es.onopen = () => { statusEl.textContent = 'Connected — listening for updates'; };
  es.onmessage = (ev) => {
    try {
      const data = JSON.parse(ev.data);
      if (data && Array.isArray(data)) {
        render(data);
      } else if (data && data.error) {
        statusEl.textContent = `Error from server: ${data.error}`;
      }
    } catch (e) {
      console.error('Failed parsing SSE data', e, ev.data);
    }
  };
  es.onerror = (e) => {
    statusEl.textContent = 'Disconnected — retrying…';
  };
}

connect();
