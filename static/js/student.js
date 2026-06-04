let videoStream = null;
let checkinActive = false;
let alreadySigned = false;

async function init() {
    const resp = await fetch('/api/user-info');
    const user = await resp.json();
    document.getElementById('userInfo').textContent =
        `${user.name} (${user.id})`;

    loadRecords();
    checkStatus();
    startCamera();

    setInterval(checkStatus, 5000);
}

async function checkStatus() {
    try {
        // 同时获取签到开启状态和学生自己的今日签到状态
        const [sessionResp, todayResp] = await Promise.all([
            fetch('/api/checkin-status'),
            fetch('/api/student/today-status')
        ]);
        const sessionData = await sessionResp.json();
        const todayData = await todayResp.json();

        checkinActive = sessionData.active;
        alreadySigned = todayData.signed;
        const btn = document.getElementById('checkinBtn');
        const statusEl = document.getElementById('checkinStatus');

        if (alreadySigned) {
            btn.disabled = true;
            btn.textContent = '已签到';
            statusEl.textContent = `今日已签到 (${todayData.time})`;
            statusEl.className = 'checkin-status success';
        } else if (checkinActive) {
            btn.disabled = false;
            btn.textContent = '签到';
            statusEl.textContent = '签到已开启，请对准摄像头点击签到';
            statusEl.className = 'checkin-status waiting';
        } else {
            btn.disabled = true;
            btn.textContent = '签到';
            statusEl.textContent = '等待教师开启签到...';
            statusEl.className = 'checkin-status inactive';
        }
    } catch (e) {
        console.error('状态检查失败:', e);
    }
}

async function startCamera() {
    try {
        videoStream = await navigator.mediaDevices.getUserMedia({
            video: { width: 320, height: 360, facingMode: 'user' }
        });
        document.getElementById('video').srcObject = videoStream;
    } catch (e) {
        console.error('摄像头启动失败:', e);
        document.getElementById('checkinStatus').textContent =
            '无法访问摄像头，请检查权限设置';
    }
}

async function doCheckin() {
    if (!checkinActive) return;

    const btn = document.getElementById('checkinBtn');
    const statusEl = document.getElementById('checkinStatus');
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');

    btn.disabled = true;
    btn.textContent = '识别中...';
    statusEl.textContent = '正在识别，请保持面部在摄像头前...';
    statusEl.className = 'checkin-status waiting';

    canvas.width = video.videoWidth || 320;
    canvas.height = video.videoHeight || 360;
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    const imageData = canvas.toDataURL('image/jpeg', 0.85);

    try {
        const resp = await fetch('/api/checkin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageData })
        });
        const data = await resp.json();

        if (data.success) {
            alreadySigned = true;
            statusEl.textContent = `签到成功！${data.time}`;
            statusEl.className = 'checkin-status success';
            btn.textContent = '已签到';
            btn.disabled = true;
            loadRecords();
        } else {
            statusEl.textContent = data.message;
            statusEl.className = 'checkin-status fail';
            btn.textContent = '重新签到';
            setTimeout(() => {
                btn.disabled = false;
            }, 2000);
        }
    } catch (e) {
        statusEl.textContent = '网络错误，请重试';
        statusEl.className = 'checkin-status fail';
        btn.textContent = '重新签到';
        setTimeout(() => { btn.disabled = false; }, 2000);
    }
}

async function loadRecords() {
    try {
        const resp = await fetch('/api/student/records');
        const records = await resp.json();
        const tbody = document.getElementById('recordsBody');

        if (records.length === 0) {
            tbody.innerHTML =
                '<tr><td colspan="3" style="color:#999;">暂无签到记录</td></tr>';
            return;
        }

        tbody.innerHTML = records.map(r => `
            <tr>
                <td>${r.date}</td>
                <td>${r.time || '-'}</td>
                <td>
                    <span class="badge ${r.status === '已签到' ? 'badge-signed' : 'badge-unsigned'}">
                        ${r.status}
                    </span>
                </td>
            </tr>
        `).join('');
    } catch (e) {
        console.error('加载记录失败:', e);
    }
}

document.addEventListener('DOMContentLoaded', init);
