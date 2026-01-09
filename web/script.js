// 1. 从地址栏取 IP
const urlParams = new URLSearchParams(window.location.search);
const hostFromUrl = urlParams.get('ip') || window.location.host || 'localhost';
const BASE_URL = `http://${hostFromUrl}/plugins/GeQian.order_qqmusic`;

console.log('BASE_URL:', BASE_URL);

// 2. DOM 元素
const toast = document.getElementById('toast');
const loginModal = document.getElementById('loginModal');
const qrcodeModal = document.getElementById('qrcodeModal');
const qrcodeImage = document.getElementById('qrcodeImage');
const qrcodePlaceholder = document.getElementById('qrcodePlaceholder');
const qrcodeStatus = document.getElementById('qrcodeStatus');
const qrcodeTitle = document.getElementById('qrcodeTitle');

// 3. 弹窗控制
function openModal(modalId) {
    document.getElementById(modalId).classList.add('show');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('show');
}

// 点击弹窗外部关闭
window.onclick = function (event) {
    if (event.target.classList.contains('modal')) {
        event.target.classList.remove('show');
    }
}

// 4. Toast 通知
function showToast(message, type = 'info') {
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    setTimeout(() => toast.classList.remove('show'), 3000);
}

// 5. 生成二维码
async function generateQRCode(type) {
    const typeNames = { qq: 'QQ', wx: '微信', mobile: 'QQ音乐客户端' };

    // 关闭登录选择弹窗，打开二维码弹窗
    closeModal('loginModal');
    openModal('qrcodeModal');

    // 重置状态
    qrcodeTitle.textContent = `${typeNames[type]}扫码登录`;
    qrcodeImage.style.display = 'none';
    qrcodePlaceholder.innerHTML = '<div class="loading-spinner"></div><p>生成中...</p>';
    qrcodePlaceholder.style.display = 'flex';
    qrcodeStatus.textContent = '正在生成二维码...';
    qrcodeStatus.className = 'qrcode-status';

    try {
        const response = await fetch(`${BASE_URL}/get_qrcode/${type}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        let qrBase64 = await response.text();
        qrBase64 = qrBase64.trim().replace(/^["']|["']$/g, '');

        qrcodeImage.onload = () => {
            qrcodePlaceholder.style.display = 'none';
            qrcodeImage.style.display = 'block';
        };

        qrcodeImage.onerror = () => {
            qrcodePlaceholder.innerHTML = '<i class="fas fa-exclamation-triangle" style="font-size:40px;color:#dc3545"></i><p>加载失败</p>';
            qrcodeStatus.textContent = '二维码加载失败';
            qrcodeStatus.className = 'qrcode-status error';
        };

        qrcodeImage.src = `data:image/png;base64,${qrBase64}`;
        qrcodeStatus.textContent = `请使用${typeNames[type]}扫描`;

        // 记录开始时间（秒）
        const startTime = Math.floor(Date.now() / 1000);

        // 轮询登录状态
        const checkInterval = setInterval(async () => {
            try {
                // 传入 since_time 参数，只检查新生成的凭证
                const statusResponse = await fetch(`${BASE_URL}/credential/status?since_time=${startTime}`);
                if (statusResponse.ok) {
                    const data = await statusResponse.json();
                    if (data.valid) {
                        clearInterval(checkInterval);
                        qrcodeStatus.textContent = '登录成功！';
                        qrcodeStatus.className = 'qrcode-status success';
                        showToast('登录成功！凭证已保存', 'success');
                        setTimeout(() => closeModal('qrcodeModal'), 1500);
                    }
                }
            } catch (e) {
                console.error('轮询失败:', e);
            }
        }, 3000);

        setTimeout(() => clearInterval(checkInterval), 120000);

    } catch (error) {
        console.error('生成二维码失败:', error);
        qrcodePlaceholder.innerHTML = '<i class="fas fa-exclamation-triangle" style="font-size:40px;color:#dc3545"></i><p>生成失败</p>';
        qrcodeStatus.textContent = error.message;
        qrcodeStatus.className = 'qrcode-status error';
    }
}

// 6. 检查凭证状态
async function checkCredentialStatus() {
    try {
        showToast('正在检查...', 'info');
        const response = await fetch(`${BASE_URL}/credential/status`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        const msg = data.detail || (data.valid ? '✓ 凭证有效' : '✗ 凭证无效或已过期');
        showToast(msg, data.valid ? 'success' : 'error');
    } catch (error) {
        showToast(`检查失败: ${error.message}`, 'error');
    }
}

// 7. 刷新凭证
async function refreshCredential() {
    try {
        showToast('正在刷新...', 'info');
        const response = await fetch(`${BASE_URL}/credential/refresh`, { method: 'POST' });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${response.status}`);
        }

        const data = await response.json();
        showToast(data.message || '刷新成功', 'success');
    } catch (error) {
        showToast(`刷新失败: ${error.message}`, 'error');
    }
}

// 8. 查看凭证信息
// 9. 复制到剪贴板
function copyToClipboard(text) {
    if (!text) {
        showToast('内容为空', 'error');
        return;
    }

    // 创建一个临时的textarea元素来复制内容
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();

    try {
        const successful = document.execCommand('copy');
        if (successful) {
            showToast('已复制到剪贴板', 'success');
        } else {
            showToast('复制失败', 'error');
        }
    } catch (err) {
        showToast('复制失败', 'error');
        console.error('复制失败:', err);
    }

    document.body.removeChild(textarea);
}

// 10. 复制所有凭证
async function copyAllCredentials() {
    try {
        const response = await fetch(`${BASE_URL}/credential/info`);

        if (!response.ok) {
            showToast('获取凭证失败，无法复制', 'error');
            return;
        }

        const data = await response.json();
        const text = JSON.stringify(data, null, 4);
        copyToClipboard(text);
    } catch (error) {
        showToast(`复制失败: ${error.message}`, 'error');
    }
}

// 8. 查看凭证信息
async function showCredentialInfo() {
    const infoContent = document.getElementById('infoContent');

    // 显示加载状态
    infoContent.innerHTML = `
        <div class="info-loading">
            <div class="loading-spinner"></div>
            <p>加载中...</p>
        </div>
    `;

    openModal('infoModal');

    try {
        const response = await fetch(`${BASE_URL}/credential/info`);

        if (!response.ok) {
            if (response.status === 404) {
                throw new Error('未找到凭证文件，请先登录');
            }
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        let html = '';
        for (const [key, value] of Object.entries(data)) {
            // 处理对象类型的值
            let displayValue = value;
            if (typeof value === 'object' && value !== null) {
                displayValue = JSON.stringify(value, null, 2);
            }

            // 对 value 进行转义，防止破坏 HTML
            const safeValue = String(displayValue)
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");

            html += `
                <div class="credential-item">
                    <div class="credential-label">${key}</div>
                    <div class="credential-value">${displayValue}</div>
                </div>
            `;
        }

        infoContent.innerHTML = html;

    } catch (error) {
        infoContent.innerHTML = `
            <div class="info-error">
                <i class="fas fa-exclamation-circle" style="font-size:40px;margin-bottom:15px"></i>
                <p>${error.message}</p>
            </div>
        `;
    }
}