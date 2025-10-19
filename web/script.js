// API基础URL
const API_BASE = 'http://localhost:8021/plugins/GeQian.order_qqmusic';

// DOM元素
const qqLoginBtn = document.getElementById('qqLoginBtn');
const wxLoginBtn = document.getElementById('wxLoginBtn');
const qrcodeContainer = document.getElementById('qrcodeContainer');
const qrcodeImage = document.getElementById('qrcodeImage');
const qrcodeStatus = document.getElementById('qrcodeStatus');
const checkStatusBtn = document.getElementById('checkStatusBtn');
const statusResult = document.getElementById('statusResult');
const refreshBtn = document.getElementById('refreshBtn');
const refreshResult = document.getElementById('refreshResult');
const infoBtn = document.getElementById('infoBtn');
const infoResult = document.getElementById('infoResult');

// 事件监听器
qqLoginBtn.addEventListener('click', () => generateQRCode('qq'));
wxLoginBtn.addEventListener('click', () => generateQRCode('wx'));
checkStatusBtn.addEventListener('click', checkCredentialStatus);
refreshBtn.addEventListener('click', refreshCredential);
infoBtn.addEventListener('click', getCredentialInfo);

// 生成二维码
async function generateQRCode(type) {
    try {
        showLoading(qrcodeStatus);
        qrcodeContainer.style.display = 'block';
        
        const response = await fetch(`${API_BASE}/get_qrcode/${type}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        // 1. 拿到裸 base64 字符串
        let qrBase64 = await response.text();

        // 2. 去掉首尾可能出现的引号、换行、空格
        qrBase64 = qrBase64.trim().replace(/^["']|["']$/g, '');

        // 3. 拼成 data-url（后端返回的是 PNG）
        qrcodeImage.src = `data:image/png;base64,${qrBase64}`;
        qrcodeStatus.textContent = '请使用手机扫描二维码登录';
        
        // 每3秒检查一次登录状态
        const checkInterval = setInterval(async () => {
            try {
                const statusResponse = await fetch(`${API_BASE}/credential/status`);
                if (statusResponse.ok) {
                    const data = await statusResponse.json();
                    if (data.valid) {
                        clearInterval(checkInterval);
                        qrcodeStatus.textContent = '登录成功！凭证已保存。';
                        qrcodeStatus.className = 'success';
                    }
                }
            } catch (error) {
                console.error('检查登录状态失败:', error);
            }
        }, 3000);
        
    } catch (error) {
        console.error('生成二维码失败:', error);
        qrcodeStatus.textContent = `生成二维码失败: ${error.message}`;
        qrcodeStatus.className = 'error';
    }
}

// 检查凭证状态
async function checkCredentialStatus() {
    try {
        showLoading(statusResult);
        
        const response = await fetch(`${API_BASE}/credential/status`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        if (data.valid) {
            showResult(statusResult, '凭证有效', 'success');
        } else {
            showResult(statusResult, '凭证无效或已过期', 'error');
        }
    } catch (error) {
        console.error('检查凭证状态失败:', error);
        showResult(statusResult, `检查凭证状态失败: ${error.message}`, 'error');
    }
}

// 刷新凭证
async function refreshCredential() {
    try {
        showLoading(refreshResult);
        refreshBtn.disabled = true;
        
        const response = await fetch(`${API_BASE}/credential/refresh`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        if (data.success) {
            showResult(refreshResult, data.message, 'success');
        } else {
            showResult(refreshResult, data.message || '刷新失败', 'error');
        }
    } catch (error) {
        console.error('刷新凭证失败:', error);
        showResult(refreshResult, `刷新凭证失败: ${error.message}`, 'error');
    } finally {
        refreshBtn.disabled = false;
    }
}

// 获取凭证信息
async function getCredentialInfo() {
    try {
        showLoading(infoResult);
        
        const response = await fetch(`${API_BASE}/credential/info`);
        if (!response.ok) {
            if (response.status === 404) {
                throw new Error('未找到凭证文件，请先登录生成凭证');
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        let infoText = '<strong>凭证信息：</strong><br>';
        for (const [key, value] of Object.entries(data)) {
            infoText += `<strong>${key}:</strong> ${value}<br>`;
        }
        showResult(infoResult, infoText, 'info');
    } catch (error) {
        console.error('获取凭证信息失败:', error);
        showResult(infoResult, `获取凭证信息失败: ${error.message}`, 'error');
    }
}

// 显示加载状态
function showLoading(element) {
    element.innerHTML = '加载中...';
    element.className = 'result';
}

// 显示结果
function showResult(element, message, type) {
    element.innerHTML = message;
    element.className = `result ${type}`;
}