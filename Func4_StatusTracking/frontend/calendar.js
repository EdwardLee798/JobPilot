// Calendar view for application events
class Calendar {
    // 支持滚轮切换月份并加翻页动画
    bindWheelMonthSwitch() {
      const calendarGrid = this.grid;
      calendarGrid.addEventListener('wheel', (e) => {
        if (e.deltaY < 0) {
          this.animateMonthSwitch('prev');
        } else if (e.deltaY > 0) {
          this.animateMonthSwitch('next');
        }
        e.preventDefault();
      }, { passive: false });
    }

    animateMonthSwitch(direction) {
      const calendarGrid = this.grid;
      // 移除现有动画类
      calendarGrid.classList.remove('flip-prev', 'flip-next');
      // 强制重绘
      void calendarGrid.offsetWidth;
      // 添加动画类
      const duration = 400;
      if (direction === 'prev') {
        calendarGrid.classList.add('flip-prev');
        setTimeout(() => { this.prevMonth(); }, duration);
      } else {
        calendarGrid.classList.add('flip-next');
        setTimeout(() => { this.nextMonth(); }, duration);
      }
      // 动画结束后移除类
      calendarGrid.addEventListener('animationend', function handler() {
        calendarGrid.classList.remove('flip-prev', 'flip-next');
        calendarGrid.removeEventListener('animationend', handler);
      });
    }
  constructor() {
    this.currentDate = new Date();
    this.events = [];
    this.grid = document.querySelector('.calendar-grid');
    this.title = document.querySelector('.calendar-title');
    this.setupCalendar();
    this.setupSSE();
    this.bindWheelMonthSwitch();
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
          
          // Add click event to scroll to the job card
          cell.addEventListener('click', () => {
            // Get the first event's job_id for this day
            const firstEvent = dayEvents[0];
            if (firstEvent && firstEvent.jobId) {
              // Switch to timeline view if not already there
              const timelineView = document.getElementById('timeline-view');
              if (timelineView.style.display === 'none') {
                // Trigger timeline button click to switch views
                document.getElementById('btn-timeline').click();
                // Wait for view switch animation before scrolling
                setTimeout(() => {
                  this.scrollToCard(firstEvent.jobId);
                }, 150);
              } else {
                this.scrollToCard(firstEvent.jobId);
              }
            }
          });
          
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

  prevMonth(withAnim = false) {
    if (withAnim) {
      this.animateMonthSwitch('prev');
    } else {
      this.currentDate.setMonth(this.currentDate.getMonth() - 1);
      this.renderCalendar();
    }
  }

  nextMonth(withAnim = false) {
    if (withAnim) {
      this.animateMonthSwitch('next');
    } else {
      this.currentDate.setMonth(this.currentDate.getMonth() + 1);
      this.renderCalendar();
    }
  }

  scrollToCard(jobId) {
    const targetCard = document.getElementById(`job-card-${jobId}`);
    if (targetCard) {
      targetCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
      // Add a brief highlight effect
      targetCard.style.transition = 'background-color 0.5s';
      const originalBg = targetCard.style.backgroundColor;
      targetCard.style.backgroundColor = '#e0effe';
      setTimeout(() => {
        targetCard.style.backgroundColor = originalBg;
      }, 1000);
    }
  }
}

// Initialize calendar
const calendar = new Calendar();

// 覆盖按钮点击事件，带动画
window.addEventListener('DOMContentLoaded', () => {
  const navBtns = document.querySelectorAll('.calendar-nav button');
  if (navBtns.length >= 2) {
    navBtns[0].onclick = () => calendar.prevMonth(true);
    navBtns[1].onclick = () => calendar.nextMonth(true);
  }
});