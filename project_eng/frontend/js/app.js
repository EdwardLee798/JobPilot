// 全局变量
let currentResumeId = null;
let generatedResumeId = null;

// API基础URL
const API_BASE = '/api';

// 工具函数
function showMessage(elementId, message, type = 'info') {
    const el = document.getElementById(elementId);
    el.textContent = message;
    el.className = `status-message show ${type}`;
    
    // 如果是简历聊天的状态消息且显示“思考中”，为助手头像添加闪烁动画
    if (elementId === 'chatStatus' && message.includes('思考')) {
        const assistantAvatars = document.querySelectorAll('.msg-assistant .chat-avatar');
        assistantAvatars.forEach(avatar => avatar.classList.add('avatar-thinking'));
    } else if (elementId === 'chatStatus') {
        // 其他情况移除闪烁动画
        const assistantAvatars = document.querySelectorAll('.msg-assistant .chat-avatar');
        assistantAvatars.forEach(avatar => avatar.classList.remove('avatar-thinking'));
    }
    
    setTimeout(() => {
        el.classList.remove('show');
    }, 5000);
}

function formatDate(timestamp) {
    const date = new Date(timestamp * 1000);
    return date.toLocaleString('zh-CN');
}

// Tab切换
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const tabId = btn.dataset.tab;

        // 更新按钮状态
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        // 更新内容显示
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(tabId).classList.add('active');

        // 加载对应Tab的数据
        if (tabId === 'resume-parser') {
            loadResumeList();
        } else if (tabId === 'resume-optimizer') {
            loadResumeOptions();
        } else if (tabId === 'auto-apply') {
            loadResumeOptions();
        } else if (tabId === 'status-tracking') {
            loadJobList();
        }
    });
});

// ========== 简历解析 ==========

const uploadBtn = document.getElementById('uploadBtn');
if (uploadBtn) {
    uploadBtn.addEventListener('click', async () => {
        const fileInput = document.getElementById('resumeFile');
        const file = fileInput.files[0];

        if (!file) {
            showMessage('uploadStatus', '请选择文件', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        try {
            showMessage('uploadStatus', '正在上传和解析...', 'info');
            const response = await fetch(`${API_BASE}/resume/upload`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                showMessage('uploadStatus', '解析成功！', 'success');
                currentResumeId = result.resume_id;
                loadResumeList();
                displayResumeDetail(result.data);
            } else {
                showMessage('uploadStatus', result.error || '解析失败', 'error');
            }
        } catch (error) {
            showMessage('uploadStatus', '上传失败: ' + error.message, 'error');
        }
    });
}

async function loadResumeList() {
    try {
        const response = await fetch(`${API_BASE}/resume/list`);
        const result = await response.json();

        if (result.success) {
            const listEl = document.getElementById('resumeList');
            if (result.resumes.length === 0) {
                listEl.innerHTML = '<p>暂无简历，请先上传</p>';
                return;
            }

            listEl.innerHTML = result.resumes.map(resume => `
                <div class="resume-item" data-id="${resume.resume_id}">
                    <h4>${resume.name || '未命名'}</h4>
                    <p>${resume.headline || '暂无描述'}</p>
                    <p style="font-size: 0.85em; color: #999;">
                        上传时间: ${formatDate(resume.timestamp)}
                    </p>
                </div>
            `).join('');

            // 添加点击事件
            document.querySelectorAll('.resume-item').forEach(item => {
                item.addEventListener('click', () => {
                    loadResumeDetail(item.dataset.id);
                });
            });
        }
    } catch (error) {
        console.error('加载简历列表失败:', error);
    }
}

async function loadResumeDetail(resumeId) {
    try {
        const response = await fetch(`${API_BASE}/resume/parse/${resumeId}`);
        const result = await response.json();

        if (result.success) {
            currentResumeId = resumeId;
            displayResumeDetail(result.data);
        }
    } catch (error) {
        console.error('加载简历详情失败:', error);
    }
}

function displayResumeDetail(data) {
    const detailEl = document.getElementById('resumeDetail');
    const sectionEl = document.getElementById('resumeDetailSection');

    sectionEl.style.display = 'block';

    detailEl.innerHTML = `
        <h4>基本信息</h4>
        <p><strong>姓名:</strong> ${data.name || '-'}</p>
        <p><strong>标题:</strong> ${data.headline || '-'}</p>
        <p><strong>邮箱:</strong> ${data.contacts?.email || '-'}</p>
        <p><strong>电话:</strong> ${data.contacts?.phone || '-'}</p>

        <h4>教育背景</h4>
        ${data.education?.map(edu => `
            <p><strong>${edu.school}</strong> - ${edu.degree} in ${edu.major}</p>
        `).join('') || '<p>无</p>'}

        <h4>工作经历</h4>
        ${data.experience?.map(exp => `
            <p><strong>${exp.name}</strong> (${exp.period})</p>
            <p style="margin-left: 20px;">${exp.description || '-'}</p>
        `).join('') || '<p>无</p>'}

        <h4>技能</h4>
        <p>${data.skills?.join(', ') || '无'}</p>
    `;
}

// ========== 简历优化 ==========

async function loadResumeOptions() {
    try {
        const response = await fetch(`${API_BASE}/resume/list`);
        const result = await response.json();

        if (result.success) {
            const options = result.resumes.map(r =>
                `<option value="${r.resume_id}">${r.name || '未命名'} - ${r.headline || ''}</option>`
            ).join('');

            document.getElementById('optimizeResumeSelect').innerHTML =
                '<option value="">-- 请选择简历 --</option>' + options;
            document.getElementById('applyResumeSelect').innerHTML =
                '<option value="">-- 请选择简历 --</option>' + options;
        }
    } catch (error) {
        console.error('加载简历选项失败:', error);
    }
}

const analyzeBtn = document.getElementById('analyzeBtn');
if (analyzeBtn) {
    analyzeBtn.addEventListener('click', async () => {
        const resumeId = document.getElementById('optimizeResumeSelect').value;
        const jdText = document.getElementById('jdText').value.trim();

        if (!resumeId || !jdText) {
            showMessage('optimizeStatus', '请选择简历并输入JD', 'error');
            return;
        }

        try {
            showMessage('optimizeStatus', '正在分析匹配度...', 'info');

            const response = await fetch(`${API_BASE}/optimize/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ resume_id: resumeId, jd_text: jdText })
            });

            const result = await response.json();

            if (result.success) {
                showMessage('optimizeStatus', '分析完成！', 'success');
                displayMatchResult(result.data);
            } else {
                showMessage('optimizeStatus', result.error || '分析失败', 'error');
            }
        } catch (error) {
            showMessage('optimizeStatus', '分析失败: ' + error.message, 'error');
        }
    });
}

function displayMatchResult(data) {
    const resultEl = document.getElementById('matchResult');
    const sectionEl = document.getElementById('matchResultSection');

    sectionEl.style.display = 'block';

    const experiences = data.experience || [];
    resultEl.innerHTML = `
        <h4>匹配经历 (按相关度排序)</h4>
        ${experiences.map((exp, idx) => `
            <div style="margin-bottom: 20px; padding: 15px; background: #f9f9f9; border-radius: 6px;">
                <p><strong>${idx + 1}. ${exp.name}</strong></p>
                <p style="color: #667eea;">匹配度: ${(exp.match_score * 100).toFixed(1)}%</p>
                <p style="margin-top: 10px;">${exp.description || '-'}</p>
            </div>
        `).join('') || '<p>无匹配经历</p>'}
    `;
}

const generateBtn = document.getElementById('generateBtn');
if (generateBtn) {
    generateBtn.addEventListener('click', async () => {
        const resumeId = document.getElementById('optimizeResumeSelect').value;
        const jdText = document.getElementById('jdText').value.trim();

        if (!resumeId || !jdText) {
            showMessage('optimizeStatus', '请选择简历并输入JD', 'error');
            return;
        }

        try {
            showMessage('optimizeStatus', '正在生成优化简历，请稍候...', 'info');

            const response = await fetch(`${API_BASE}/optimize/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ resume_id: resumeId, jd_text: jdText, language: 'zh' })
            });

            const result = await response.json();

            if (result.success) {
                showMessage('optimizeStatus', '简历生成成功！', 'success');
                generatedResumeId = result.generated_id;
                document.getElementById('generatedSection').style.display = 'block';
            } else {
                showMessage('optimizeStatus', result.error || '生成失败', 'error');
            }
        } catch (error) {
            showMessage('optimizeStatus', '生成失败: ' + error.message, 'error');
        }
    });
}

const downloadBtn = document.getElementById('downloadBtn');
if (downloadBtn) {
    downloadBtn.addEventListener('click', () => {
        if (generatedResumeId) {
            window.open(`${API_BASE}/optimize/download/${generatedResumeId}`, '_blank');
        }
    });
}

// ========== 自动投递 ==========

// 检查服务状态
async function checkServiceStatus() {
    try {
        const response = await fetch(`${API_BASE}/apply/status`);
        const result = await response.json();

        const statusEl = document.getElementById('serviceStatus');
        if (result.status === 'running') {
            statusEl.textContent = '✅ 服务运行中';
            statusEl.style.background = '#d4edda';
            statusEl.style.color = '#155724';
            document.getElementById('startServiceBtn').disabled = true;
            document.getElementById('stopServiceBtn').disabled = false;
        } else {
            statusEl.textContent = '⚠️ 服务未启动';
            statusEl.style.background = '#fff3cd';
            statusEl.style.color = '#856404';
            document.getElementById('startServiceBtn').disabled = false;
            document.getElementById('stopServiceBtn').disabled = true;
        }
    } catch (error) {
        console.error('检查服务状态失败:', error);
    }
}

// 启动服务
const startServiceBtn = document.getElementById('startServiceBtn');
if (startServiceBtn) {
    startServiceBtn.addEventListener('click', async () => {
        try {
            showMessage('applyStatus', '正在启动Java服务，请稍候（约15-30秒）...', 'info');
            document.getElementById('startServiceBtn').disabled = true;

            const response = await fetch(`${API_BASE}/apply/start-service`, {
                method: 'POST'
            });

            const result = await response.json();

            if (result.success) {
                showMessage('applyStatus', '服务启动成功！', 'success');
                checkServiceStatus();
            } else {
                showMessage('applyStatus', result.error || '启动失败', 'error');
                document.getElementById('startServiceBtn').disabled = false;
            }
        } catch (error) {
            showMessage('applyStatus', '启动失败: ' + error.message, 'error');
            document.getElementById('startServiceBtn').disabled = false;
        }
    });
}

// 停止服务（停止Java服务并关闭浏览器）
const stopServiceBtn = document.getElementById('stopServiceBtn');
if (stopServiceBtn) {
    stopServiceBtn.addEventListener('click', async () => {
        if (!confirm('确定要停止服务吗？这将停止投递任务、关闭浏览器窗口并停止Java服务（需要约10秒，请耐心等待）。')) {
            return;
        }

        try {
            showMessage('applyStatus', '正在停止服务（约需10秒）...', 'info');

            const response = await fetch(`${API_BASE}/apply/stop-service`, {
                method: 'POST'
            });

            const result = await response.json();

            if (result.success) {
                showMessage('applyStatus', '服务已停止', 'success');
                document.getElementById('startServiceBtn').disabled = false;
                document.getElementById('stopServiceBtn').disabled = true;
                stopProgressPolling();
                checkServiceStatus();
            } else {
                showMessage('applyStatus', result.error || '停止失败', 'error');
            }
        } catch (error) {
            showMessage('applyStatus', '停止失败: ' + error.message, 'error');
        }
    });
}

// 检查状态按钮
const checkServiceBtn = document.getElementById('checkServiceBtn');
if (checkServiceBtn) {
    checkServiceBtn.addEventListener('click', () => {
        checkServiceStatus();
    });
}

// 启动投递
const startApplyBtn = document.getElementById('startApplyBtn');
if (startApplyBtn) {
    startApplyBtn.addEventListener('click', async () => {
        const resumeId = document.getElementById('applyResumeSelect').value;
        const platform = document.getElementById('platformSelect').value;
        const keywords = document.getElementById('keywords').value;
        const cities = document.getElementById('cities').value;

        if (!resumeId) {
            showMessage('applyStatus', '请选择简历', 'error');
            return;
        }

        try {
            showMessage('applyStatus', '正在配置并启动自动投递...', 'info');

            const response = await fetch(`${API_BASE}/apply/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    resume_id: resumeId,
                    platform: platform,
                    keywords: keywords,
                    cities: cities,
                    max_count: 50
                })
            });

            const result = await response.json();

            if (result.success) {
                showMessage('applyStatus', result.message + '（浏览器窗口将自动打开）', 'success');
                document.getElementById('startApplyBtn').disabled = true;
                document.getElementById('stopApplyBtn').disabled = false;
                document.getElementById('applyProgressSection').style.display = 'block';
                startProgressPolling();
            } else {
                showMessage('applyStatus', result.error || '启动失败', 'error');
                if (result.help) {
                    showMessage('applyStatus', result.help, 'info');
                }
            }
        } catch (error) {
            showMessage('applyStatus', '启动失败: ' + error.message, 'error');
        }
    });
}

// 停止投递
const stopApplyBtn = document.getElementById('stopApplyBtn');
if (stopApplyBtn) {
    stopApplyBtn.addEventListener('click', async () => {
    if (!confirm('确定要停止当前投递任务吗？')) {
        return;
    }

    try {
        showMessage('applyStatus', '正在停止投递...', 'info');

        const platform = document.getElementById('platformSelect').value;
        const response = await fetch(`${API_BASE}/apply/stop`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ platform: platform })
        });

        const result = await response.json();

        if (result.success) {
            showMessage('applyStatus', '投递已停止', 'success');
            document.getElementById('startApplyBtn').disabled = false;
            document.getElementById('stopApplyBtn').disabled = true;
            stopProgressPolling();
        } else {
            showMessage('applyStatus', result.error || '停止失败', 'error');
        }
    } catch (error) {
        showMessage('applyStatus', '停止失败: ' + error.message, 'error');
    }
    });
}

// 进度轮询
let progressInterval = null;

async function updateProgress() {
    try {
        const response = await fetch(`${API_BASE}/apply/progress`);
        const result = await response.json();

        if (result.success && result.progress) {
            const p = result.progress;
            document.getElementById('completedCount').textContent = p.completed || 0;
            document.getElementById('failedCount').textContent = p.failed || 0;
            document.getElementById('currentJob').textContent = p.current || '-';
        }
    } catch (error) {
        console.error('获取进度失败:', error);
    }
}

function startProgressPolling() {
    if (progressInterval) return;
    progressInterval = setInterval(updateProgress, 3000); // 每3秒更新一次
    updateProgress(); // 立即更新一次
}

function stopProgressPolling() {
    if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
    }
}

// 页面加载时检查服务状态
if (document.getElementById('serviceStatus')) {
    checkServiceStatus();
}

// ========== 进度管理 ==========

async function loadJobList() {
    try {
        const response = await fetch(`${API_BASE}/tracking/jobs`);
        const result = await response.json();

        if (result.success) {
            displayJobList(result.jobs);
            loadStats();
        }
    } catch (error) {
        console.error('加载职位列表失败:', error);
    }
}

function displayJobList(jobs) {
    const listEl = document.getElementById('jobList');

    if (jobs.length === 0) {
        listEl.innerHTML = '<p>暂无投递记录</p>';
        return;
    }

    listEl.innerHTML = jobs.map(job => {
        const latestStatus = job.statuses[job.statuses.length - 1];
        return `
            <div class="job-item">
                <div class="job-header">
                    <div class="job-info">
                        <h4>${job.job_title}</h4>
                        <p>${job.company_name}</p>
                    </div>
                    <span class="job-status status-applied">${latestStatus?.status || '已申请'}</span>
                </div>
                <div class="job-timeline">
                    ${job.statuses.map(s => `
                        <div class="timeline-item">
                            <p><strong>${s.status}</strong></p>
                            <p class="timeline-time">${s.event_time || formatDate(new Date(s.timestamp).getTime() / 1000)}</p>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }).join('');
}

async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/tracking/stats`);
        const result = await response.json();

        if (result.success) {
            document.getElementById('totalJobs').textContent = result.stats.total;
        }
    } catch (error) {
        console.error('加载统计失败:', error);
    }
}

const refreshBtn = document.getElementById('refreshBtn');
if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
        loadJobList();
    });
}

// 添加投递模态框
const modal = document.getElementById('addJobModal');
const addJobBtn = document.getElementById('addJobBtn');
const modalCancelBtn = document.getElementById('modalCancelBtn');
const closeBtn = document.querySelector('.close');

if (addJobBtn && modal) {
    addJobBtn.addEventListener('click', () => {
        modal.classList.add('show');
    });
}

if (modalCancelBtn && modal) {
    modalCancelBtn.addEventListener('click', () => {
        modal.classList.remove('show');
    });
}

if (closeBtn && modal) {
    closeBtn.addEventListener('click', () => {
        modal.classList.remove('show');
    });
}

const addJobForm = document.getElementById('addJobForm');
if (addJobForm) {
    addJobForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const data = {
            job_title: document.getElementById('modalJobTitle').value,
            company_name: document.getElementById('modalCompany').value,
            job_desc: document.getElementById('modalJobDesc').value,
            tracking_method: document.getElementById('modalTracking').value
        };

        try {
            const response = await fetch(`${API_BASE}/tracking/job`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (result.success) {
                modal.classList.remove('show');
                document.getElementById('addJobForm').reset();
                loadJobList();
            } else {
                alert(result.error || '添加失败');
            }
        } catch (error) {
            alert('添加失败: ' + error.message);
        }
    });
}

// 初始化
loadResumeList();

// ========== 对话式简历生成 ==========

let chatSessionId = null;
let chatCompletionPercentage = 0;

// 模式切换
const uploadModeBtn = document.getElementById('uploadModeBtn');
const chatModeBtn = document.getElementById('chatModeBtn');

if (uploadModeBtn && chatModeBtn) {
    uploadModeBtn.addEventListener('click', () => {
        uploadModeBtn.classList.add('active');
        chatModeBtn.classList.remove('active');
        document.getElementById('uploadMode').style.display = 'block';
        document.getElementById('chatMode').style.display = 'none';
    });

    chatModeBtn.addEventListener('click', () => {
        chatModeBtn.classList.add('active');
        uploadModeBtn.classList.remove('active');
        document.getElementById('chatMode').style.display = 'block';
        document.getElementById('uploadMode').style.display = 'none';

        // 如果还没有会话，自动启动
        if (!chatSessionId) {
            startChatSession();
        }
    });
}

// 启动对话会话
async function startChatSession() {
    try {
        showMessage('chatStatus', '正在启动智能助手...', 'info');

        const response = await fetch(`${API_BASE}/resume/interactive/start`, {
            method: 'POST'
        });

        const result = await response.json();

        if (result.success) {
            chatSessionId = result.session_id;
            addChatMessage('assistant', result.question);
            showMessage('chatStatus', '已启动对话，请开始回答问题', 'success');
            document.getElementById('chatInput').focus();
        } else {
            showMessage('chatStatus', result.error || '启动失败', 'error');
        }
    } catch (error) {
        showMessage('chatStatus', '启动失败: ' + error.message, 'error');
    }
}

// 添加聊天消息
function addChatMessage(role, text, typewriter = false) {
    const messagesEl = document.getElementById('chatMessages');
    const messageEl = document.createElement('div');
    messageEl.className = `chat-message ${role}`;

    const avatarEl = document.createElement('div');
    avatarEl.className = 'message-avatar';
    avatarEl.textContent = role === 'assistant' ? '🤖' : '👤';

    const bubbleEl = document.createElement('div');
    bubbleEl.className = 'message-bubble';
    
    if (typewriter && role === 'assistant') {
        // 打字机效果
        bubbleEl.textContent = '';
        messageEl.appendChild(avatarEl);
        messageEl.appendChild(bubbleEl);
        messagesEl.appendChild(messageEl);
        
        // 滚动到底部
        messagesEl.scrollTop = messagesEl.scrollHeight;
        
        // 逐字显示
        let index = 0;
        const interval = setInterval(() => {
            if (index < text.length) {
                bubbleEl.textContent += text[index];
                index++;
                // 持续滚动到底部
                messagesEl.scrollTop = messagesEl.scrollHeight;
            } else {
                clearInterval(interval);
            }
        }, 30); // 每30ms显示一个字符
    } else {
        // 直接显示
        bubbleEl.textContent = text;
        messageEl.appendChild(avatarEl);
        messageEl.appendChild(bubbleEl);
        messagesEl.appendChild(messageEl);
        
        // 滚动到底部
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }
}

// 更新进度
function updateChatProgress(percentage) {
    chatCompletionPercentage = percentage;
    document.getElementById('chatProgressBar').style.width = `${percentage}%`;
    document.getElementById('chatProgressText').textContent = `完成度: ${percentage}%`;

    // 如果完成度高，显示完成按钮
    if (percentage >= 80) {
        document.getElementById('chatFinishBtn').style.display = 'inline-block';
    } else {
        document.getElementById('chatFinishBtn').style.display = 'none';
    }
}

// 发送消息
const chatSendBtn = document.getElementById('chatSendBtn');
if (chatSendBtn) {
    chatSendBtn.addEventListener('click', async () => {
        await sendChatMessage();
    });
}

// 回车发送（Shift+Enter换行）
const chatInput = document.getElementById('chatInput');
if (chatInput) {
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });
}

async function sendChatMessage() {
    const inputEl = document.getElementById('chatInput');
    const text = inputEl.value.trim();

    if (!text) {
        showMessage('chatStatus', '请输入内容', 'error');
        return;
    }

    if (!chatSessionId) {
        showMessage('chatStatus', '会话未启动，请稍候...', 'error');
        await startChatSession();
        return;
    }

    try {
        // 显示用户消息
        addChatMessage('user', text);
        inputEl.value = '';

        // 显示加载状态
        showMessage('chatStatus', '助手正在思考...', 'info');

        const response = await fetch(`${API_BASE}/resume/interactive/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: chatSessionId,
                text: text
            })
        });

        const result = await response.json();

        if (result.success) {
            // 显示助手回复（带打字机效果）
            addChatMessage('assistant', result.assistant_reply, true);

            // 更新进度
            updateChatProgress(result.completion_percentage || 0);

            // 检查是否完成
            if (result.is_complete) {
                showMessage('chatStatus', '✅ 简历信息已收集完整！可以点击"完成生成"按钮。', 'success');
            } else {
                showMessage('chatStatus', '', 'info');
            }
        } else {
            showMessage('chatStatus', result.error || '发送失败', 'error');
        }
    } catch (error) {
        showMessage('chatStatus', '发送失败: ' + error.message, 'error');
    }
}

// 完成生成
const chatFinishBtn = document.getElementById('chatFinishBtn');
if (chatFinishBtn) {
    chatFinishBtn.addEventListener('click', async () => {
        if (!chatSessionId) {
            showMessage('chatStatus', '没有进行中的会话', 'error');
            return;
        }

        if (!confirm('确定完成简历生成吗？')) {
            return;
        }

        try {
            showMessage('chatStatus', '正在生成简历...', 'info');

            const response = await fetch(`${API_BASE}/resume/interactive/finalize`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: chatSessionId
                })
            });

            const result = await response.json();

            if (result.success) {
                showMessage('chatStatus', '✅ ' + result.message, 'success');
                addChatMessage('assistant', '简历已生成完毕！你可以在"已解析的简历"中查看。');

                // 清理会话
                chatSessionId = null;
                updateChatProgress(100);

                // 刷新简历列表
                setTimeout(() => {
                    loadResumeList();
                }, 500);
            } else {
                showMessage('chatStatus', result.error || '生成失败', 'error');
            }
        } catch (error) {
            showMessage('chatStatus', '生成失败: ' + error.message, 'error');
        }
    });
}

// 重新开始
const chatResetBtn = document.getElementById('chatResetBtn');
if (chatResetBtn) {
    chatResetBtn.addEventListener('click', async () => {
        if (!confirm('确定要重新开始吗？当前的对话内容将丢失。')) {
            return;
        }

        try {
            // 重置会话
            if (chatSessionId) {
                await fetch(`${API_BASE}/resume/interactive/reset`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: chatSessionId
                    })
                });
            }

            // 清空UI
            document.getElementById('chatMessages').innerHTML = '';
            document.getElementById('chatInput').value = '';
            updateChatProgress(0);

            // 重新启动
            chatSessionId = null;
            await startChatSession();

            showMessage('chatStatus', '已重新开始', 'success');
        } catch (error) {
            showMessage('chatStatus', '重置失败: ' + error.message, 'error');
        }
    });
}

// 确保DOM完全加载后再初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApp);
} else {
    initializeApp();
}

function initializeApp() {
    // 触发初始tab的数据加载
    loadResumeList();
}
