// Calendar view for application events
class Calendar {
  constructor() {
    this.currentDate = new Date();
    this.events = [];
    this.grid = document.querySelector('.calendar-grid');
    this.title = document.querySelector('.calendar-title');
    this.setupCalendar();
    this.setupSSE();
  }

  setupSSE() {
    const es = new EventSource('/events');
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data && Array.isArray(data)) {
          this.processEvents(data);
        }
      } catch (e) {
        console.error('Failed parsing calendar SSE data', e);
      }
    };
  }

  processEvents(records) {
    // Filter out events containing "已申请" or "未通过"
    this.events = records.filter(r => {
      const status = r.status_update || '';
      const end = r.event_time || '';
      return !status.includes('已申请') && end != -100.0;
    }).map(r => ({
      // support either `event_time` or `timestamp` coming from server
      date: new Date(Number(r.event_time ?? r.timestamp ?? r.timestamp ?? 0) * 1000),
      title: r.status_update || r.status || '',
      jobId: r.job_id,
      job_title: r.job_title || r.jobTitle || '',
      company_name: r.company_name || r.companyName || ''
    }));
    this.renderCalendar();
  }

  setupCalendar() {
    // Add weekday headers
    const weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    weekdays.forEach(day => {
      const cell = document.createElement('div');
      cell.className = 'calendar-weekday';
      cell.textContent = day;
      this.grid.appendChild(cell);
    });
    this.renderCalendar();
  }

  renderCalendar() {
    // Clear existing calendar cells (except weekday headers)
    const cells = this.grid.querySelectorAll('.calendar-day');
    cells.forEach(cell => cell.remove());

    const year = this.currentDate.getFullYear();
    const month = this.currentDate.getMonth();
    
    // Update calendar title
    this.title.textContent = new Date(year, month).toLocaleString('default', { 
      month: 'long', 
      year: 'numeric' 
    });

    // Get first day of month and total days
    const firstDay = new Date(year, month, 1).getDay();
    const totalDays = new Date(year, month + 1, 0).getDate();
    
    // Get prev month's last days
    const prevMonthDays = new Date(year, month, 0).getDate();
    
    // Create calendar grid
    let date = 1;
    let nextDate = 1;

    // Up to 6 rows needed for a month
    for (let i = 0; i < 42; i++) {
      const cell = document.createElement('div');
      cell.className = 'calendar-day';
      
      if (i < firstDay) {
        // Previous month
        const prevDate = prevMonthDays - (firstDay - i - 1);
        cell.innerHTML = `<div class="calendar-date">${prevDate}</div>`;
        cell.classList.add('other-month');
      } else if (date > totalDays) {
        // Next month
        cell.innerHTML = `<div class="calendar-date">${nextDate}</div>`;
        cell.classList.add('other-month');
        nextDate++;
      } else {
        // Current month
        cell.innerHTML = `<div class="calendar-date">${date}</div>`;
        
        // Check if today
        const today = new Date();
        if (date === today.getDate() && 
            month === today.getMonth() && 
            year === today.getFullYear()) {
          cell.classList.add('today');
        }
        
        // Add events for this date
        const dayEvents = this.events.filter(e => 
          e.date.getDate() === date && 
          e.date.getMonth() === month && 
          e.date.getFullYear() === year
        );
        
        if (dayEvents.length > 0) {
          cell.classList.add('has-events');
          
          // Create hover popup for events
          const eventsHover = document.createElement('div');
          eventsHover.className = 'calendar-events-hover';
          
          dayEvents.forEach(event => {
            const div = document.createElement('div');
            div.className = 'calendar-event';

            // Job/company line
            const meta = document.createElement('div');
            meta.className = 'calendar-event-meta';
            meta.textContent = `${event.job_title || ''} ${event.job_title && event.company_name ? '—' : ''} ${event.company_name || ''}`.trim();
            if (meta.textContent) eventsHover.appendChild(meta);

            // Format the event time if available
            const eventTime = event.date && !isNaN(event.date) ? event.date.toLocaleTimeString('default', {
              hour: '2-digit',
              minute: '2-digit'
            }) : '';

            const text = document.createElement('div');
            text.className = 'calendar-event-text';
            text.textContent = `${eventTime ? (eventTime + ' - ') : ''}${event.title}`;
            eventsHover.appendChild(text);
          });
          
          // Add mouse event listeners for positioning and lifecycle
          let removeTimeout = null;
          const removeHover = () => {
            if (eventsHover.parentNode) eventsHover.parentNode.removeChild(eventsHover);
          };

          cell.addEventListener('mouseenter', (e) => {
            // append popup if not present and show it
            if (!eventsHover.parentNode) document.body.appendChild(eventsHover);
            eventsHover.style.display = 'block';

            // position after appended so we can measure size
            const rect = cell.getBoundingClientRect();
            const hoverRect = eventsHover.getBoundingClientRect();
            let left = rect.left + (rect.width / 2) - (hoverRect.width / 2);
            // clamp to viewport
            left = Math.max(8, Math.min(left, window.innerWidth - hoverRect.width - 8));
            let top = rect.top - 8 - hoverRect.height; // prefer above
            if (top < 8) { // if not enough space above, place below
              top = rect.bottom + 8;
            }
            eventsHover.style.left = `${left}px`;
            eventsHover.style.top = `${top}px`;

            if (removeTimeout) { clearTimeout(removeTimeout); removeTimeout = null; }
          });

          cell.addEventListener('mouseleave', (e) => {
            // give small delay to allow move into popup
            removeTimeout = setTimeout(removeHover, 150);
          });

          eventsHover.addEventListener('mouseenter', () => {
            if (removeTimeout) { clearTimeout(removeTimeout); removeTimeout = null; }
          });
          eventsHover.addEventListener('mouseleave', () => {
            removeHover();
          });
        }
        
        date++;
      }
      
      this.grid.appendChild(cell);
    }
  }

  prevMonth() {
    this.currentDate.setMonth(this.currentDate.getMonth() - 1);
    this.renderCalendar();
  }

  nextMonth() {
    this.currentDate.setMonth(this.currentDate.getMonth() + 1);
    this.renderCalendar();
  }
}

// Initialize calendar
const calendar = new Calendar();