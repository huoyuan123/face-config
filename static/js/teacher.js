let checkinActive = false;
let pieChart = null;
let lineChart = null;
let modalType = '';
let modalData = {};

async function init() {
    const resp = await fetch('/api/user-info');
    const user = await resp.json();
    document.getElementById('userInfo').textContent = `教师: ${user.name}`;

    document.getElementById('datePicker').value =
        new Date().toISOString().split('T')[0];

    await loadClasses();
    await checkSessionStatus();
    await refreshAll();

    setInterval(checkSessionStatus, 10000);
}

async function loadClasses() {
    try {
        const resp = await fetch('/api/teacher/classes');
        const classes = await resp.json();
        const sel = document.getElementById('classFilter');
        classes.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c;
            opt.textContent = c + '班';
            sel.appendChild(opt);
        });
    } catch (e) {
        console.error('加载班级失败:', e);
    }
}

async function checkSessionStatus() {
    try {
        const resp = await fetch('/api/checkin-status');
        const data = await resp.json();
        checkinActive = data.active;
        updateToggleUI();
    } catch (e) {
        console.error('状态检查失败:', e);
    }
}

function updateToggleUI() {
    const btn = document.getElementById('toggleBtn');
    const statusEl = document.getElementById('sessionStatus');
    if (checkinActive) {
        btn.textContent = '结束签到';
        btn.className = 'btn-toggle stop';
        statusEl.textContent = '当前签到: 进行中';
        statusEl.style.color = '#27ae60';
    } else {
        btn.textContent = '开启签到';
        btn.className = 'btn-toggle start';
        statusEl.textContent = '当前签到: 未开启';
        statusEl.style.color = '#999';
    }
}

async function toggleCheckin() {
    const action = checkinActive ? 'stop' : 'start';
    const btn = document.getElementById('toggleBtn');
    btn.disabled = true;
    btn.textContent = '处理中...';

    try {
        const resp = await fetch('/api/teacher/toggle-checkin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action })
        });
        const data = await resp.json();
        if (data.success) {
            checkinActive = data.active;
            updateToggleUI();
            refreshAll();
        } else {
            alert(data.message);
        }
    } catch (e) {
        alert('操作失败，请重试');
    } finally {
        btn.disabled = false;
    }
}

async function refreshAll() {
    await refreshRecords();
    await refreshChart();
}

async function refreshRecords() {
    const dateVal = document.getElementById('datePicker').value;
    const classVal = document.getElementById('classFilter').value;

    try {
        const resp = await fetch(
            `/api/teacher/records?date=${dateVal}&class=${encodeURIComponent(classVal)}`
        );
        const data = await resp.json();

        document.getElementById('statTotal').textContent = data.stats.total;
        document.getElementById('statSigned').textContent = data.stats.signed;
        document.getElementById('statUnsigned').textContent = data.stats.unsigned;
        document.getElementById('statRate').textContent = data.stats.rate + '%';

        const tbody = document.getElementById('recordsBody');
        if (data.records.length === 0) {
            tbody.innerHTML =
                '<tr><td colspan="6" style="color:#999;">暂无签到记录</td></tr>';
            return;
        }

        tbody.innerHTML = data.records.map(r => `
            <tr>
                <td>${r.id}</td>
                <td>${r.name}</td>
                <td>${r.class}班</td>
                <td>
                    <span class="badge ${r.status === '已签到' ? 'badge-signed' : 'badge-unsigned'}">
                        ${r.status}
                    </span>
                </td>
                <td>${r.time || '-'}</td>
                <td>
                    <button class="btn-small btn-edit"
                            onclick="editRecord('${r.id}','${r.name}','${r.status}','${r.time}')">
                        编辑
                    </button>
                </td>
            </tr>
        `).join('');

        updatePieChart(data.stats);
    } catch (e) {
        console.error('加载记录失败:', e);
    }
}

async function refreshChart() {
    const classVal = document.getElementById('classFilter').value;
    try {
        const resp = await fetch(
            `/api/teacher/chart?class=${encodeURIComponent(classVal)}`
        );
        const data = await resp.json();
        updateLineChart(data.dates, data.rates);
    } catch (e) {
        console.error('加载图表失败:', e);
    }
}

function updatePieChart(stats) {
    const ctx = document.getElementById('pieChart').getContext('2d');
    if (pieChart) pieChart.destroy();
    pieChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['已签到', '未签到'],
            datasets: [{
                data: [stats.signed, stats.unsigned],
                backgroundColor: ['#27ae60', '#e74c3c'],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

function updateLineChart(dates, rates) {
    const ctx = document.getElementById('lineChart').getContext('2d');
    if (lineChart) lineChart.destroy();
    lineChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                label: '签到率 %',
                data: rates,
                borderColor: '#4facfe',
                backgroundColor: 'rgba(79,172,254,0.1)',
                fill: true,
                tension: 0.3,
                pointRadius: 5,
                pointBackgroundColor: '#4facfe'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { min: 0, max: 100, ticks: { callback: v => v + '%' } }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
}

// ========== 编辑弹窗 ==========
function editRecord(sid, name, status, time) {
    modalType = 'record';
    modalData = { student_id: sid };

    document.getElementById('modalTitle').textContent =
        `编辑签到记录 - ${sid} ${name}`;
    document.getElementById('modalContent').innerHTML = `
        <div class="form-group">
            <label>签到状态</label>
            <select id="editStatus">
                <option value="已签到" ${status === '已签到' ? 'selected' : ''}>已签到</option>
                <option value="未签到" ${status === '未签到' ? 'selected' : ''}>未签到</option>
            </select>
        </div>
        <div class="form-group">
            <label>签到时间 (HH:MM:SS)</label>
            <input type="text" id="editTime" value="${time}" placeholder="例: 08:30:00">
        </div>
    `;
    document.getElementById('editModal').classList.add('active');
}

function closeModal() {
    document.getElementById('editModal').classList.remove('active');
    modalType = '';
    modalData = {};
}

async function saveModal() {
    if (modalType === 'record') {
        const status = document.getElementById('editStatus').value;
        const time = document.getElementById('editTime').value.trim();
        const dateVal = document.getElementById('datePicker').value;

        if (status === '已签到' && !time) {
            alert('已签到状态必须填写签到时间');
            return;
        }

        try {
            const resp = await fetch('/api/teacher/edit-record', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    student_id: modalData.student_id,
                    date: dateVal,
                    status: status,
                    time: status === '已签到' ? time : null
                })
            });
            const data = await resp.json();
            if (data.success) {
                closeModal();
                refreshAll();
            } else {
                alert(data.message);
            }
        } catch (e) {
            alert('保存失败，请重试');
        }
    }
}

document.addEventListener('DOMContentLoaded', init);
