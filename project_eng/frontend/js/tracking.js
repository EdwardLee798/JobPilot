/**
 * 进度管理模块 - 时间线、日历、聊天功能
 * 整合自Func4_StatusTracking
 */

class TrackingManager {
    constructor() {
        this.currentView = 'chat';
        this.currentDate = new Date();
        this.events = [];
        this.jobsData = [];
        this.eventSource = null;
        this.lastDataHash = ''; // 用于检测数据变化
        this.isAnimating = false; // 用于防止日历切换动画冲突

        this.initElements();
        this.bindEvents();
        this.setupCalendar();
        this.loadInitialData(); // 加载初始数据
        this.switchView('chat'); // 初始化为智能助手界面
    }

    initElements() {
        // 视图切换按钮
        this.timelineViewBtn = document.getElementById('timelineViewBtn');
        this.chatViewBtn = document.getElementById('chatViewBtn');

        // 视图面板
        this.timelineViewPanel = document.getElementById('timelineViewPanel');
        this.chatViewPanel = document.getElementById('chatViewPanel');

        // 容器
        this.jobCardsContainer = document.getElementById('jobCardsContainer');
        this.calendarGrid = document.getElementById('calendarGrid');
        this.calendarTitle = document.getElementById('calendarTitle');

        // 聊天元素
        this.trackingChatMessages = document.getElementById('trackingChatMessages');
        this.trackingChatInput = document.getElementById('trackingChatInput');
        this.trackingChatSend = document.getElementById('trackingChatSend');

        // 日历按钮
        this.calendarPrev = document.getElementById('calendarPrev');
        this.calendarNext = document.getElementById('calendarNext');

        // 统计元素
        this.totalJobsEl = document.getElementById('totalJobs');
        this.activeJobsEl = document.getElementById('activeJobs');
        this.terminatedJobsEl = document.getElementById('terminatedJobs');
    }

    bindEvents() {
        // 视图切换
        this.timelineViewBtn?.addEventListener('click', () => this.switchView('timeline'));
        this.chatViewBtn?.addEventListener('click', () => this.switchView('chat'));

        // 聊天发送
        this.trackingChatSend?.addEventListener('click', () => this.sendChatMessage());
        this.trackingChatInput?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendChatMessage();
            }
        });

        // 日历导航
        this.calendarPrev?.addEventListener('click', () => this.prevMonth());
        this.calendarNext?.addEventListener('click', () => this.nextMonth());

        // 日历滚轮
        this.calendarGrid?.addEventListener('wheel', (e) => {
            // 防止动画进行中时触发新的切换
            if (this.isAnimating) {
                e.preventDefault();
                return;
            }
            
            if (e.deltaY < 0) {
                this.animateMonthSwitch('prev');
            } else if (e.deltaY > 0) {
                this.animateMonthSwitch('next');
            }
            e.preventDefault();
        }, { passive: false });
    }

    switchView(view) {
        this.currentView = view;

        if (view === 'timeline') {
            this.timelineViewBtn.classList.add('active');
            this.chatViewBtn.classList.remove('active');
            this.timelineViewPanel.style.display = 'block';
            this.chatViewPanel.style.display = 'none';
            this.connectSSE();
        } else {
            this.chatViewBtn.classList.add('active');
            this.timelineViewBtn.classList.remove('active');
            this.chatViewPanel.style.display = 'block';
            this.timelineViewPanel.style.display = 'none';
            this.disconnectSSE();
            
            // 显示欢迎消息
            this.showWelcomeMessage();
        }
    }

    // 显示欢迎消息
    showWelcomeMessage() {
        // 检查是否已经有欢迎消息
        if (this.trackingChatMessages && this.trackingChatMessages.children.length === 0) {
            const welcomeText = `您好，我是您的职位网申流程管理助手，专注于帮助您高效管理求职申请的各个环节。我可以协助您：

- **记录新的网申流程**：为您新增的职位申请创建跟踪档案。
- **更新申请进度**：记录笔试、面试等关键节点，支持时间规划。
- **查询申请状态**：随时查看某公司或某岗位的当前申请进展。
- **生成排期规划**：根据已知的笔面试安排，为您制定合理的日程计划。

请告诉我您需要哪方面的协助，例如"我想记录一个新的岗位申请"或"我要更新腾讯产品经理的面试进度"，我将为您提供精准支持。`;
            this.renderChatMessage('assistant', welcomeText);
        }
    }

    // SSE连接
    connectSSE() {
        if (this.eventSource) return;

        this.eventSource = new EventSource('/api/tracking/merged_data');
        
        this.eventSource.onmessage = (ev) => {
            try {
                const data = JSON.parse(ev.data);
                if (Array.isArray(data)) {
                    // 计算数据哈希，只在数据变化时更新
                    const dataHash = JSON.stringify(data);
                    if (dataHash !== this.lastDataHash) {
                        this.lastDataHash = dataHash;
                        this.jobsData = data;
                        this.renderTimeline(data);
                        this.processEventsForCalendar(data);
                        this.updateStats(data);
                    }
                }
            } catch (e) {
                console.error('SSE解析失败:', e);
            }
        };

        this.eventSource.onerror = () => {
            console.log('SSE连接断开，尝试重连...');
            this.disconnectSSE();
            setTimeout(() => this.connectSSE(), 3000);
        };
    }

    disconnectSSE() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
    }

    // 加载初始数据（用于显示统计信息）
    loadInitialData() {
        fetch('/api/tracking/jobs')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.jobs) {
                    // 转换为merged_data格式
                    const records = [];
                    data.jobs.forEach(job => {
                        job.statuses.forEach(status => {
                            records.push({
                                job_id: job.job_id,
                                job_title: job.job_title,
                                company_name: job.company_name,
                                job_desc: job.job_desc,
                                status_update: status.status,
                                event_time: status.event_time || -100.0,
                                timestamp: status.timestamp
                            });
                        });
                    });
                    
                    // 更新数据和统计
                    this.jobsData = records;
                    this.processEventsForCalendar(records);
                    this.updateStats(records);
                    // 重新渲染日历以显示事件
                    this.renderCalendar();
                }
            })
            .catch(err => {
                console.error('加载初始数据失败:', err);
            });
    }

    // 渲染时间线
    renderTimeline(records) {
        if (!records || records.length === 0) {
            this.jobCardsContainer.innerHTML = '<div class="empty-state">暂无投递记录</div>';
            return;
        }

        // 按job_id分组
        const groups = {};
        records.forEach(r => {
            const id = r.job_id || '_unknown';
            if (!groups[id]) {
                groups[id] = {
                    job_id: id,
                    company_name: r.company_name || '',
                    job_title: r.job_title || '',
                    job_desc: r.job_desc || '',
                    updates: []
                };
            }
            groups[id].updates.push({
                event_id: r.id,
                status: r.status_update || '',
                ts: r.event_time || r.timestamp
            });
        });

        // 渲染卡片
        this.jobCardsContainer.innerHTML = '';
        Object.values(groups).forEach(g => {
            const card = this.createJobCard(g);
            this.jobCardsContainer.appendChild(card);
        });
    }

    createJobCard(jobData) {
        const card = document.createElement('div');
        card.className = 'job-card';
        card.id = `job-card-${jobData.job_id}`;

        // 卡片头部
        const header = document.createElement('div');
        header.className = 'card-header-section';
        
        const title = document.createElement('h3');
        title.textContent = `${jobData.company_name} — ${jobData.job_title}`;
        header.appendChild(title);

        // 删除整个岗位按钮
        const deleteJobBtn = document.createElement('div');
        deleteJobBtn.className = 'job-card-delete-btn';
        deleteJobBtn.innerHTML = '×';
        deleteJobBtn.title = '删除此岗位';
        deleteJobBtn.onclick = (e) => {
            e.stopPropagation();
            this.deleteJob(jobData.job_id, jobData.company_name, jobData.job_title);
        };
        header.appendChild(deleteJobBtn);

        card.appendChild(header);

        // 时间线
        const timeline = document.createElement('div');
        timeline.className = 'job-timeline';

        const sortedUpdates = jobData.updates.sort((a, b) => {
            const ta = Number(a.ts) || 0;
            const tb = Number(b.ts) || 0;
            // -100 表示流程终止标记，应该排在最后
            if (ta === -100) return 1;
            if (tb === -100) return -1;
            return ta - tb;
        });

        // 检查是否终止
        let isTerminated = false;
        if (sortedUpdates.length > 0) {
            const lastStatus = sortedUpdates[sortedUpdates.length - 1].status || '';
            if (lastStatus.includes('流程终止') || lastStatus.includes('被拒') || lastStatus.includes('拒绝')) {
                isTerminated = true;
                card.classList.add('terminated');
            }
        }

        // 职位描述悬浮提示（仅在未终止时显示）
        if (!isTerminated && jobData.job_desc && jobData.job_desc.trim()) {
            const tooltip = document.createElement('div');
            tooltip.className = 'job-desc-tooltip';
            tooltip.textContent = jobData.job_desc;
            header.appendChild(tooltip);
            header.classList.add('has-desc');
        }

        sortedUpdates.forEach((u, index) => {
            const item = document.createElement('div');
            item.className = 'timeline-item';

            if (index === sortedUpdates.length - 1 && isTerminated) {
                item.classList.add('terminated');
            }

            // 删除按钮（仅对非首个事件显示）
            if (index > 0) {
                const deleteBtn = document.createElement('div');
                deleteBtn.className = 'timeline-delete-btn';
                deleteBtn.innerHTML = '×';
                deleteBtn.title = '删除此事件';
                deleteBtn.onclick = (e) => {
                    e.stopPropagation();
                    this.deleteEvent(u.event_id, jobData.job_id);
                };
                item.appendChild(deleteBtn);
            }

            const dot = document.createElement('div');
            dot.className = 'timeline-dot';
            item.appendChild(dot);

            const content = document.createElement('div');
            content.className = 'timeline-content';

            const date = document.createElement('div');
            date.className = 'timeline-date';
            date.textContent = this.formatTimestamp(u.ts);
            content.appendChild(date);

            const status = document.createElement('div');
            status.className = 'timeline-status';
            status.textContent = u.status;
            content.appendChild(status);

            item.appendChild(content);
            timeline.appendChild(item);
        });

        card.appendChild(timeline);
        return card;
    }

    formatTimestamp(ts) {
        if (!ts || ts == -100.0) return '';
        const n = Number(ts);
        if (!isNaN(n)) {
            const ms = n > 1e12 ? n : n * 1000;
            return new Date(ms).toLocaleString('zh-CN');
        }
        try {
            return new Date(ts).toLocaleString('zh-CN');
        } catch (e) {
            return String(ts);
        }
    }

    // 日历功能
    setupCalendar() {
        // 添加星期标题
        const weekdays = ['日', '一', '二', '三', '四', '五', '六'];
        weekdays.forEach(day => {
            const cell = document.createElement('div');
            cell.className = 'calendar-weekday';
            cell.textContent = day;
            this.calendarGrid.appendChild(cell);
        });
        this.renderCalendar();
    }

    renderCalendar() {
        // 清除现有日期单元格
        const cells = this.calendarGrid.querySelectorAll('.calendar-day');
        cells.forEach(cell => cell.remove());

        const year = this.currentDate.getFullYear();
        const month = this.currentDate.getMonth();

        // 更新标题
        this.calendarTitle.textContent = new Date(year, month).toLocaleString('zh-CN', {
            year: 'numeric',
            month: 'long'
        });

        const firstDay = new Date(year, month, 1).getDay();
        const totalDays = new Date(year, month + 1, 0).getDate();
        const prevMonthDays = new Date(year, month, 0).getDate();

        let date = 1;
        let nextDate = 1;

        for (let i = 0; i < 42; i++) {
            const cell = document.createElement('div');
            cell.className = 'calendar-day';

            if (i < firstDay) {
                const prevDate = prevMonthDays - (firstDay - i - 1);
                cell.innerHTML = `<div class="calendar-date">${prevDate}</div>`;
                cell.classList.add('other-month');
            } else if (date > totalDays) {
                cell.innerHTML = `<div class="calendar-date">${nextDate}</div>`;
                cell.classList.add('other-month');
                nextDate++;
            } else {
                cell.innerHTML = `<div class="calendar-date">${date}</div>`;

                // 今天
                const today = new Date();
                if (date === today.getDate() && month === today.getMonth() && year === today.getFullYear()) {
                    cell.classList.add('today');
                }

                // 事件
                const dayEvents = this.events.filter(e =>
                    e.date.getDate() === date &&
                    e.date.getMonth() === month &&
                    e.date.getFullYear() === year
                );

                if (dayEvents.length > 0) {
                    cell.classList.add('has-events');
                    
                    // 创建悬浮提示
                    const tooltip = document.createElement('div');
                    tooltip.className = 'calendar-event-tooltip';
                    
                    dayEvents.forEach((e, idx) => {
                        const eventItem = document.createElement('div');
                        eventItem.className = 'tooltip-event-item';
                        eventItem.innerHTML = `
                            <strong>${e.company_name}</strong> - ${e.job_title}<br/>
                            <span class="tooltip-event-status">${e.title}</span>
                        `;
                        eventItem.style.cursor = 'pointer';
                        
                        // 为每个事件项添加点击事件
                        eventItem.addEventListener('click', (event) => {
                            event.stopPropagation();
                            if (e.jobId) {
                                this.scrollToCard(e.jobId);
                            }
                        });
                        
                        tooltip.appendChild(eventItem);
                    });
                    
                    cell.appendChild(tooltip);
                    
                    // 日期单元格点击跳转到第一个事件
                    cell.addEventListener('click', () => {
                        const firstEvent = dayEvents[0];
                        if (firstEvent && firstEvent.jobId) {
                            this.scrollToCard(firstEvent.jobId);
                        }
                    });
                }

                date++;
            }

            this.calendarGrid.appendChild(cell);
        }
    }

    processEventsForCalendar(records) {
        this.events = records.filter(r => {
            const status = r.status_update || '';
            const eventTime = r.event_time || '';
            return !status.includes('已申请') && eventTime != -100.0;
        }).map(r => ({
            date: new Date(Number(r.event_time) * 1000),
            title: r.status_update || '',
            jobId: r.job_id,
            job_title: r.job_title || '',
            company_name: r.company_name || ''
        }));
        
        this.renderCalendar();
    }

    prevMonth() {
        this.animateMonthSwitch('prev');
    }

    nextMonth() {
        this.animateMonthSwitch('next');
    }

    animateMonthSwitch(direction) {
        // 防止动画进行中时触发新的切换
        if (this.isAnimating) return;
        
        this.isAnimating = true;
        this.calendarGrid.classList.remove('flip-prev', 'flip-next');
        void this.calendarGrid.offsetWidth;

        const duration = 500;
        if (direction === 'prev') {
            this.calendarGrid.classList.add('flip-prev');
            setTimeout(() => {
                this.currentDate.setMonth(this.currentDate.getMonth() - 1);
                this.renderCalendar();
            }, duration);
        } else {
            this.calendarGrid.classList.add('flip-next');
            setTimeout(() => {
                this.currentDate.setMonth(this.currentDate.getMonth() + 1);
                this.renderCalendar();
            }, duration);
        }

        const self = this;
        this.calendarGrid.addEventListener('animationend', function handler() {
            this.classList.remove('flip-prev', 'flip-next');
            this.removeEventListener('animationend', handler);
            self.isAnimating = false; // 动画结束后重置标志
        });
    }

    scrollToCard(jobId) {
        // 切换到时间线视图
        if (this.currentView !== 'timeline') {
            this.switchView('timeline');
            // 确保时间线已渲染
            if (this.jobsData && this.jobsData.length > 0) {
                this.renderTimeline(this.jobsData);
            }
        }
        
        // 延迟查找卡片，确保DOM已更新
        setTimeout(() => {
            const card = document.getElementById(`job-card-${jobId}`);
            if (card) {
                card.scrollIntoView({ behavior: 'smooth', block: 'center' });
                this.highlightCard(card);
            }
        }, this.currentView !== 'timeline' ? 300 : 0);
    }

    highlightCard(card) {
        const originalBg = card.style.backgroundColor;
        card.style.transition = 'background-color 0.5s';
        card.style.backgroundColor = '#e5ebff';
        setTimeout(() => {
            card.style.backgroundColor = originalBg;
        }, 1000);
    }

    async deleteEvent(eventId, jobId) {
        if (!confirm('确定要删除这个事件吗？')) {
            return;
        }

        try {
            const response = await fetch(`/api/tracking/event/${eventId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('删除失败');
            }

            // 刷新数据
            await this.loadInitialData();
            
            // 显示成功消息
            this.showMessage('事件已删除', 'success');
        } catch (error) {
            console.error('删除事件失败:', error);
            this.showMessage('删除失败，请重试', 'error');
        }
    }

    async deleteJob(jobId, companyName, jobTitle) {
        if (!confirm(`确定要删除「${companyName} — ${jobTitle}」的所有申请记录吗？\n\n此操作将删除该岗位的所有事件记录，且无法恢复。`)) {
            return;
        }

        try {
            const response = await fetch(`/api/tracking/job/${jobId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('删除失败');
            }

            // 刷新数据
            await this.loadInitialData();
            
            // 显示成功消息
            this.showMessage('岗位已删除', 'success');
        } catch (error) {
            console.error('删除岗位失败:', error);
            this.showMessage('删除失败，请重试', 'error');
        }
    }

    showMessage(text, type = 'info') {
        // 创建消息提示
        const msg = document.createElement('div');
        msg.className = `status-message ${type}`;
        msg.textContent = text;
        document.body.appendChild(msg);
        
        setTimeout(() => {
            msg.classList.add('show');
        }, 10);
        
        setTimeout(() => {
            msg.classList.remove('show');
            setTimeout(() => msg.remove(), 300);
        }, 2000);
    }

    // 聊天功能
    sendChatMessage() {
        const message = this.trackingChatInput.value.trim();
        if (!message) return;

        // 显示用户消息
        this.renderChatMessage('user', message);
        this.trackingChatInput.value = '';

        // 显示“正在思考”的状态提示（在对话框外）
        const statusEl = document.getElementById('trackingChatStatus');
        if (statusEl) {
            statusEl.textContent = '助手正在思考...';
            statusEl.className = 'status-message show info';
        }
        
        // 为所有助手头像添加闪烁动画
        const assistantAvatars = document.querySelectorAll('.msg-assistant-tracking .chat-avatar');
        assistantAvatars.forEach(avatar => avatar.classList.add('avatar-thinking'));

        // 创建助手消息容器
        const assistantMsg = this.renderChatMessage('assistant', '');
        const textEl = assistantMsg.querySelector('.chat-text-tracking');

        // 发起SSE请求
        fetch('/api/tracking/chat_stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        })
        .then(response => {
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let isDone = false;
            let isFirstChunk = true;
            let hasToolCalls = false;

            const processStream = ({ done, value }) => {
                if (done) {
                    // 流结束后，清除状态提示和头像动画，并刷新数据
                    if (statusEl) {
                        statusEl.className = 'status-message';
                    }
                    // 移除所有助手头像的闪烁动画
                    const assistantAvatars = document.querySelectorAll('.msg-assistant-tracking .chat-avatar');
                    assistantAvatars.forEach(avatar => avatar.classList.remove('avatar-thinking'));
                    
                    if (isDone) {
                        this.refreshDataAfterChat();
                    }
                    return;
                }

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                lines.forEach(line => {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            
                            if (data.type === 'tool') {
                                // 显示工具调用信息
                                if (isFirstChunk) {
                                    isFirstChunk = false;
                                }
                                
                                if (!hasToolCalls) {
                                    hasToolCalls = true;
                                }
                                
                                // 添加工具调用提示
                                const toolDiv = document.createElement('div');
                                toolDiv.className = 'tool-call-info';
                                toolDiv.textContent = data.message;
                                textEl.appendChild(toolDiv);
                                
                            } else if (data.type === 'char') {
                                // 逐字显示
                                if (isFirstChunk) {
                                    isFirstChunk = false;
                                }
                                
                                // 如果之前有工具调用，添加分隔符
                                if (hasToolCalls && textEl.lastChild?.className === 'tool-call-info') {
                                    const separator = document.createElement('div');
                                    separator.className = 'tool-separator';
                                    textEl.appendChild(separator);
                                    
                                    const resultDiv = document.createElement('div');
                                    resultDiv.className = 'tool-result';
                                    textEl.appendChild(resultDiv);
                                    hasToolCalls = false; // 重置标志
                                }
                                
                                // 追加字符到结果区域
                                const targetEl = textEl.querySelector('.tool-result') || textEl;
                                if (targetEl.nodeType === Node.ELEMENT_NODE && targetEl !== textEl) {
                                    targetEl.textContent += data.char;
                                } else {
                                    textEl.appendChild(document.createTextNode(data.char));
                                }
                                
                            } else if (data.type === 'done') {
                                isDone = true;
                            } else if (data.type === 'error') {
                                textEl.textContent = `错误：${data.message}`;
                                if (statusEl) {
                                    statusEl.textContent = '处理失败';
                                    statusEl.className = 'status-message show error';
                                }
                                // 移除头像动画
                                const assistantAvatars = document.querySelectorAll('.msg-assistant-tracking .chat-avatar');
                                assistantAvatars.forEach(avatar => avatar.classList.remove('avatar-thinking'));
                            }
                        } catch (e) {
                            console.error('解析SSE数据失败:', e);
                        }
                    }
                });

                return reader.read().then(processStream);
            };

            return reader.read().then(processStream);
        })
        .catch(err => {
            textEl.textContent = `发送失败：${err.message}`;
            if (statusEl) {
                statusEl.textContent = '发送失败';
                statusEl.className = 'status-message show error';
            }
            // 移除头像动画
            const assistantAvatars = document.querySelectorAll('.msg-assistant-tracking .chat-avatar');
            assistantAvatars.forEach(avatar => avatar.classList.remove('avatar-thinking'));
        });
    }

    // 对话后刷新数据
    refreshDataAfterChat() {
        // 立即获取最新数据
        fetch('/api/tracking/jobs')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.jobs) {
                    // 转换为merged_data格式
                    const records = [];
                    data.jobs.forEach(job => {
                        job.statuses.forEach(status => {
                            records.push({
                                job_id: job.job_id,
                                job_title: job.job_title,
                                company_name: job.company_name,
                                job_desc: job.job_desc,
                                status_update: status.status,
                                event_time: status.event_time || -100.0,
                                timestamp: status.timestamp
                            });
                        });
                    });
                    
                    // 更新显示
                    this.jobsData = records;
                    this.renderTimeline(records);
                    this.processEventsForCalendar(records);
                    this.updateStats(records);
                }
            })
            .catch(err => {
                console.error('刷新数据失败:', err);
            });
    }

    renderChatMessage(who, text) {
        const msg = document.createElement('div');
        msg.className = `chat-message-tracking msg-${who}-tracking`;

        const avatar = document.createElement('div');
        avatar.className = 'chat-avatar';
        avatar.textContent = who === 'assistant' ? '🤖' : '👤';
        msg.appendChild(avatar);

        if (text || who === 'assistant') {
            const textEl = document.createElement('div');
            textEl.className = 'chat-text-tracking';
            textEl.textContent = text;
            msg.appendChild(textEl);
        }

        this.trackingChatMessages.appendChild(msg);
        this.trackingChatMessages.scrollTop = this.trackingChatMessages.scrollHeight;
        return msg;
    }

    // 更新统计
    updateStats(records) {
        const jobIds = new Set(records.map(r => r.job_id));
        this.totalJobsEl.textContent = jobIds.size;

        // 统计终止和活跃
        const terminated = new Set();
        const active = new Set();

        const grouped = {};
        records.forEach(r => {
            if (!grouped[r.job_id]) grouped[r.job_id] = [];
            grouped[r.job_id].push(r);
        });

        Object.values(grouped).forEach(updates => {
            const lastUpdate = updates[updates.length - 1];
            const status = lastUpdate.status_update || '';
            if (status.includes('流程终止') || status.includes('被拒') || status.includes('拒绝')) {
                terminated.add(lastUpdate.job_id);
            } else {
                active.add(lastUpdate.job_id);
            }
        });

        this.terminatedJobsEl.textContent = terminated.size;
        this.activeJobsEl.textContent = active.size;
    }
}

// 初始化
let trackingManager = null;

document.addEventListener('DOMContentLoaded', () => {
    // 仅在进度管理tab激活时初始化
    const statusTrackingTab = document.getElementById('status-tracking');
    if (statusTrackingTab) {
        const observer = new MutationObserver(() => {
            if (statusTrackingTab.classList.contains('active') && !trackingManager) {
                trackingManager = new TrackingManager();
            }
        });

        observer.observe(statusTrackingTab, {
            attributes: true,
            attributeFilter: ['class']
        });

        // 如果默认激活，立即初始化
        if (statusTrackingTab.classList.contains('active')) {
            trackingManager = new TrackingManager();
        }
    }
});
