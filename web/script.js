// 1. 从地址栏取 IP，没带参数就默认 localhost
const urlParams = new URLSearchParams(window.location.search);
const hostFromUrl = urlParams.get('ip') || window.location.hostname || 'localhost';
const BASE_URL = `http://${hostFromUrl}:8021/plugins/GeQian.order_qqmusic`;

console.log('自动生成的 BASE_URL:', BASE_URL);


// 3. DOM 元素缓存
const qqLoginBtn      = document.getElementById('qqLoginBtn');
const wxLoginBtn      = document.getElementById('wxLoginBtn');
const qrcodeContainer = document.getElementById('qrcodeContainer');
const qrcodeImage     = document.getElementById('qrcodeImage');
const qrcodeStatus    = document.getElementById('qrcodeStatus');
const checkStatusBtn  = document.getElementById('checkStatusBtn');
const statusResult    = document.getElementById('statusResult');
const refreshBtn      = document.getElementById('refreshBtn');
const refreshResult   = document.getElementById('refreshResult');
const infoBtn         = document.getElementById('infoBtn');
const infoResult      = document.getElementById('infoResult');

// 4. 事件绑定
qqLoginBtn.addEventListener('click', () => generateQRCode('qq'));
wxLoginBtn.addEventListener('click', () => generateQRCode('wx'));
checkStatusBtn.addEventListener('click', checkCredentialStatus);
refreshBtn.addEventListener('click', refreshCredential);
infoBtn.addEventListener('click', getCredentialInfo);

// 5. 生成二维码
async function generateQRCode(type) {
    try {
        showLoading(qrcodeStatus);
        qrcodeContainer.style.display = 'block';

        const response = await fetch(`${BASE_URL}/get_qrcode/${type}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        let qrBase64 = await response.text();
        qrBase64     = qrBase64.trim().replace(/^["']|["']$/g, ''); // 去引号/空格
        qrcodeImage.src = `data:image/png;base64,${qrBase64}`;
        qrcodeStatus.textContent = '请使用手机扫描二维码登录';

        const checkInterval = setInterval(async () => {
            try {
                const statusResponse = await fetch(`${BASE_URL}/credential/status`);
                if (statusResponse.ok) {
                    const data = await statusResponse.json();
                    if (data.valid) {
                        clearInterval(checkInterval);
                        qrcodeStatus.textContent = '登录成功！凭证已保存。';
                        qrcodeStatus.className   = 'success';
                    }
                }
            } catch (e) {
                console.error('轮询登录状态失败:', e);
            }
        }, 3000);
    } catch (error) {
        console.error('生成二维码失败:', error);
        qrcodeStatus.textContent = `生成二维码失败: ${error.message}`;
        qrcodeStatus.className   = 'error';
    }
}

// 6. 检查凭证状态
async function checkCredentialStatus() {
    try {
        showLoading(statusResult);
        const response = await fetch(`${BASE_URL}/credential/status`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const data = await response.json();
        showResult(statusResult, data.valid ? '凭证有效' : '凭证无效或已过期',
                   data.valid ? 'success' : 'error');
    } catch (error) {
        console.error(error);
        showResult(statusResult, `检查凭证状态失败: ${error.message}`, 'error');
    }
}

// 7. 刷新凭证
async function refreshCredential() {
    try {
        showLoading(refreshResult);
        refreshBtn.disabled = true;

        const response = await fetch(`${BASE_URL}/credential/refresh`, { method: 'POST' });
        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        showResult(refreshResult, data.message || '刷新成功', 'success');
    } catch (error) {
        showResult(refreshResult, `刷新凭证失败: ${error.message}`, 'error');
    } finally {
        refreshBtn.disabled = false;
    }
}

// 8. 获取凭证信息
async function getCredentialInfo() {
    try {
        showLoading(infoResult);
        const response = await fetch(`${BASE_URL}/credential/info`);
        if (!response.ok) {
            if (response.status === 404)
                throw new Error('未找到凭证文件，请先登录生成凭证');
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        let infoText = '<strong>凭证信息：</strong><br>';
        for (const [k, v] of Object.entries(data)) infoText += `<strong>${k}:</strong> ${v}<br>`;
        showResult(infoResult, infoText, 'info');
    } catch (error) {
        showResult(infoResult, `获取凭证信息失败: ${error.message}`, 'error');
    }
}

// 9. 工具函数
function showLoading(el) { el.innerHTML = '加载中...'; el.className = 'result'; }
function showResult(el, msg, type) { el.innerHTML = msg; el.className = `result ${type}`; }