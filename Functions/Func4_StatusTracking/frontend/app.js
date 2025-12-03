// Timeline + Chat frontend logic
const statusEl = document.getElementById('status');
const container = document.getElementById('container');
const timelineView = document.getElementById('timeline-view');
const chatView = document.getElementById('chat-view');

const btnTimeline = document.getElementById('btn-timeline');
const btnChat = document.getElementById('btn-chat');

const chatMessagesEl = document.getElementById('chat-messages');
const chatInputEl = document.getElementById('chat-input');
const chatSendBtn = document.getElementById('chat-send');

let eventSource = null;

function formatTs(ts) {
  if (!ts) return '';
  const n = Number(ts);
  if (!isNaN(n)) {
    const ms = n > 1e12 ? n : n * 1000;
    return new Date(ms).toLocaleString();
  }
  try { return new Date(ts).toLocaleString(); } catch (e) { return String(ts); }
}

function render(records) {
  container.innerHTML = '';
  if (!records || records.length === 0) {
    container.innerHTML = '<div class="card">No application status found yet.</div>';
    return;
  }

  const groups = {};
  records.forEach(r => {
    const id = (r.job_id === undefined || r.job_id === null) ? '_unknown' : r.job_id;
    if (!groups[id]) groups[id] = { job_id: id, company_name: r.company_name || '', job_title: r.job_title || '', job_desc: r.job_desc || '', updates: [] };
    if (r.event_time == -100.0) {
      groups[id].updates.push({ status: r.status_update || '', ts: r.timestamp || '' });
    } else {
      groups[id].updates.push({ status: r.status_update || '', ts: r.event_time || '' });
    }
  });

  Object.values(groups).forEach(g => {
    const card = document.createElement('div');
    card.className = 'card';
    card.id = `job-card-${g.job_id}`;

    const cardHeader = document.createElement('div');
    cardHeader.className = 'card-header';

    const h = document.createElement('h3');
    h.textContent = `${g.company_name} — ${g.job_title}`;
    cardHeader.appendChild(h);

    // Add job description tooltip if available
    if (g.job_desc && g.job_desc.trim()) {
      const tooltip = document.createElement('div');
      tooltip.className = 'job-desc-tooltip';
      tooltip.textContent = g.job_desc;
      cardHeader.appendChild(tooltip);
      cardHeader.classList.add('has-desc');
    }

    card.appendChild(cardHeader);

    const timeline = document.createElement('div');
    timeline.className = 'timeline';

    // 按时间升序排序
    const sortedUpdates = g.updates.sort((a, b) => {
      const ta = Number(a.ts) || 0;
      const tb = Number(b.ts) || 0;
      return ta - tb;
    });

    // 检查最后一个update是否为终止
    let cardTerminated = false;
    if (sortedUpdates.length > 0) {
      const lastStatus = sortedUpdates[sortedUpdates.length - 1].status || '';
      if (lastStatus.includes('流程终止') || lastStatus.includes('被拒') || lastStatus.includes('拒绝')) {
        cardTerminated = true;
        card.classList.add('terminated');
      }
    }

    sortedUpdates.forEach((u, index) => {
      const item = document.createElement('div');
      item.className = 'timeline-item';

      // Check if this is the last item and if it's a termination status
      if (index === sortedUpdates.length - 1) {
        const isTerminated = u.status && (u.status.includes('流程终止') || u.status.includes('被拒') || u.status.includes('拒绝'));
        if (isTerminated) {
          item.classList.add('terminated');
        }
      }

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
  if (eventSource) return; // already connected
  eventSource = new EventSource('/events');
  eventSource.onopen = () => { statusEl.textContent = 'Connected — listening for updates'; };
  eventSource.onmessage = (ev) => {
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
  eventSource.onerror = () => {
    statusEl.textContent = 'Disconnected — retrying…';
  };
}

function disconnect() {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
}

function showTimeline() {
  timelineView.style.display = '';
  chatView.style.display = 'none';
  btnTimeline.classList.add('active');
  btnChat.classList.remove('active');
  connect();
}

function showChat() {
  timelineView.style.display = 'none';
  chatView.style.display = '';
  btnTimeline.classList.remove('active');
  btnChat.classList.add('active');
  disconnect();
}

function renderChatMessage(who, text) {
  const el = document.createElement('div');
  el.className = 'chat-message ' + (who === 'user' ? 'msg-user' : 'msg-assistant');
  const whoEl = document.createElement('div');
  whoEl.className = 'chat-who';
  // Icon is set via CSS background-image
  el.appendChild(whoEl);

  if (text && text.trim() !== '') {
    const textEl = document.createElement('div');
    textEl.className = 'chat-text';
    // Use innerText to preserve line breaks
    textEl.innerText = text;
    el.appendChild(textEl);
  }

  chatMessagesEl.appendChild(el);
  chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
  return el;
}

// stream-based chat using native EventSource (SSE GET)
function sendChatStream(message) {
  renderChatMessage('user', message);
  const assistantEl = renderChatMessage('assistant', '');
  const textEl = assistantEl.querySelector('.chat-text');

  chatSendBtn.disabled = true;
  chatInputEl.disabled = true;

  // encode message into query param
  const url = `/api/chat_stream?message=${encodeURIComponent(message)}`;
  const es = new EventSource(url);

  // Add initial loading indicator
  let loadingEl = null;
  let isFirstChunk = true;
  let currentChunkDiv = null;
  let allChunks = [];

  async function typeText(text, targetDiv) {
    // Split by words and whitespace, preserving both
    const segments = text.split(/(\s+)/);
    
    for (const segment of segments) {
      if (segment.length === 0) continue;
      
      // Type character by character
      for (let i = 0; i < segment.length; i++) {
        targetDiv.innerText += segment[i];
        chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
        // Adjust speed: faster for non-whitespace
        await new Promise(resolve => setTimeout(resolve, segment.trim() ? 20 : 5));
      }
    }
  }

  function showLoading() {
    if (loadingEl) return;
    loadingEl = document.createElement('div');
    loadingEl.className = 'chat-loading';
    for (let i = 0; i < 3; i++) {
      const dot = document.createElement('div');
      dot.className = 'chat-loading-dot';
      loadingEl.appendChild(dot);
    }
    assistantEl.appendChild(loadingEl);
    assistantEl.classList.add('loading');
    chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
  }
  function hideLoading() {
    if (loadingEl && loadingEl.parentNode) {
      loadingEl.remove();
      loadingEl = null;
    }
    assistantEl.classList.remove('loading');
  }

  es.onopen = () => {
    // connection opened, show initial loading
    showLoading();
  };

  es.onmessage = (ev) => {
    try {
      const obj = JSON.parse(ev.data);
      if (obj.type === 'delta') {
        if (obj.content && obj.content.trim() !== '') {
          // Skip the first chunk, don't display it
          if (isFirstChunk) {
            isFirstChunk = false;
            hideLoading();
            showLoading();
            return;
          }
          
          // Remove loading before adding content
          hideLoading();
          
          // Create a new div for each chunk and display immediately
          const chunkDiv = document.createElement('div');
          chunkDiv.className = 'chat-text';
          chunkDiv.innerText = obj.content; // Display full content immediately
          assistantEl.appendChild(chunkDiv);
          
          // Store reference to this chunk
          allChunks.push({ text: obj.content, div: chunkDiv });
          
          // Show loading again for next chunk
          showLoading();

          // Keep scroll at the bottom
          chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
        }
      } else if (obj.type === 'tool_calls') {
        const note = document.createElement('div');
        note.className = 'chat-note';
        note.textContent = `Calling tools: ${Array.isArray(obj.calls) ? obj.calls.join(', ') : String(obj.calls)}`;
        assistantEl.appendChild(note);
      } else if (obj.type === 'done') {
        // stream finished
        hideLoading();
        
        // Now apply typing effect only to the last chunk
        if (allChunks.length > 0) {
          const lastChunk = allChunks[allChunks.length - 1];
          const lastDiv = lastChunk.div;
          const lastText = lastChunk.text;
          
          // Clear the last div and retype it
          lastDiv.innerText = '';
          typeText(lastText, lastDiv).then(() => {
            es.close();
            chatSendBtn.disabled = false;
            chatInputEl.disabled = false;
          });
        } else {
          es.close();
          chatSendBtn.disabled = false;
          chatInputEl.disabled = false;
        }
      } else if (obj.type === 'error') {
        hideLoading();
        const errorDiv = document.createElement('div');
        errorDiv.className = 'chat-text';
        errorDiv.textContent = `Error: ${obj.error}`;
        assistantEl.appendChild(errorDiv);
        es.close();
        chatSendBtn.disabled = false;
        chatInputEl.disabled = false;
      }
    } catch (e) {
      console.error('Failed to parse SSE data', e, ev.data);
    }
  };

  es.onerror = (e) => {
    // treat as end/error
    hideLoading();
    chatSendBtn.disabled = false;
    chatInputEl.disabled = false;
    try { es.close(); } catch (e) {}
  };

  // allow external cancellation by returning the EventSource
  return es;
}

// Typing queue + animator: append chunks sequentially and reveal characters
function enqueueTypingChunk(assistantEl, textEl, chunk) {
  if (!assistantEl._queue) assistantEl._queue = [];
  assistantEl._queue.push(chunk);
  if (assistantEl._typing) return;
  assistantEl._typing = true;

  // create or reuse cursor
  let cursor = assistantEl._cursor;
  if (!cursor) {
    cursor = document.createElement('span');
    cursor.className = 'typing-cursor';
    cursor.textContent = '|';
    assistantEl._cursor = cursor;
  }
  // ensure cursor at end
  textEl.appendChild(cursor);

  async function runQueue() {
    while (assistantEl._queue && assistantEl._queue.length) {
      const nextChunk = assistantEl._queue.shift();
      if (!nextChunk) continue;
      // create a span for this chunk so we can reveal progressively
      const span = document.createElement('span');
      span.className = 'typing-chunk';
      // insert before cursor so cursor stays at end
      textEl.insertBefore(span, cursor);

      // reveal characters one by one; speed adapts to chunk length
      const total = nextChunk.length;
      // target total duration between min and max (ms)
      const minDur = 180; // for tiny chunk
      const maxDur = 1200; // for large chunk
      const targetDur = Math.min(maxDur, Math.max(minDur, total * 30));
      const interval = Math.max(6, Math.floor(targetDur / Math.max(1, total)));

      for (let i = 0; i < total; i++) {
        span.textContent += nextChunk[i];
        // update assistant previous text cache
        assistantEl._prevText = (assistantEl._prevText || '') + nextChunk[i];
        // keep scroll at bottom
        chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
        await new Promise(r => setTimeout(r, interval));
      }
      // small pause between chunks
      await new Promise(r => setTimeout(r, 40));
    }
    // done typing
    assistantEl._typing = false;
    // remove cursor
    if (assistantEl._cursor && assistantEl._cursor.parentNode) assistantEl._cursor.remove();
  }

  runQueue().catch(err => {
    console.error('Typing animation error', err);
    assistantEl._typing = false;
    if (assistantEl._cursor && assistantEl._cursor.parentNode) assistantEl._cursor.remove();
  });
}

// wire up UI
btnTimeline.addEventListener('click', showTimeline);
btnChat.addEventListener('click', showChat);
chatSendBtn.addEventListener('click', () => {
  const v = chatInputEl.value.trim();
  if (!v) return;
  chatInputEl.value = '';
  sendChatStream(v);
});
chatInputEl.addEventListener('keydown', (e) => { if (e.key === 'Enter') chatSendBtn.click(); });

// start on chat view by default
showChat();
