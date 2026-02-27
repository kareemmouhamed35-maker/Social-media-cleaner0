// متغيرات عامة
let currentPlatform = '';
let currentAction = '';
let currentItems = [];
let selectedItems = [];
let sessionCookies = '';
let userInfo = {};
let isDeleting = false;
let isPaused = false;
let deleteInterval = null;
let deleteSpeed = 0;
let startTime = null;
let totalToDelete = 0;
let deletedCount = 0;
let failedCount = 0;
let currentTaskId = null;
// عناصر DOM
const screens = {
    start: document.getElementById('start-screen'),
    sessionGuide: document.getElementById('session-guide-screen'),
    actions: document.getElementById('actions-screen'),
    selection: document.getElementById('selection-screen'),
    progress: document.getElementById('progress-screen'),
    results: document.getElementById('results-screen')
};
// دوال التنقل
function showScreen(screenId) {
    Object.values(screens).forEach(screen => {
        if (screen) screen.classList.remove('active');
    });
    if (screens[screenId]) {
        screens[screenId].classList.add('active');
    }
}
function goBack() {
    if (screens.sessionGuide.classList.contains('active')) {
        showScreen('start');
    } else if (screens.actions.classList.contains('active')) {
        showScreen('sessionGuide');
    } else if (screens.selection.classList.contains('active')) {
        showScreen('actions');
    } else if (screens.progress.classList.contains('active')) {
        if (!isDeleting) {
            showScreen('actions');
        } else {
            showConfirm('هل تريد إيقاف عملية الحذف؟', () => {
                stopDeleting();
                showScreen('actions');
            });
        }
    } else if (screens.results.classList.contains('active')) {
        showScreen('start');
    }
}
function goHome() {
    if (isDeleting) {
        showConfirm('هل تريد إلغاء عملية الحذف؟', () => {
            stopDeleting();
            resetAll();
            showScreen('start');
        });
    } else {
        resetAll();
        showScreen('start');
    }
}
function resetAll() {
    currentPlatform = '';
    currentAction = '';
    currentItems = [];
    selectedItems = [];
    sessionCookies = '';
    userInfo = {};
    isDeleting = false;
    isPaused = false;
    deletedCount = 0;
    failedCount = 0;
    totalToDelete = 0;
    
    // تنظيف الحقول
    document.getElementById('session-cookies').value = '';
}
// تحميل المنصات عند بدء التشغيل
document.addEventListener('DOMContentLoaded', function() {
    loadPlatforms();
});
async function loadPlatforms() {
    try {
        const response = await fetch('/api/platforms');
        const platforms = await response.json();
        
        const grid = document.getElementById('platforms-grid');
        grid.innerHTML = '';
        
        platforms.forEach(platform => {
            const card = document.createElement('div');
            card.className = `platform-card ${platform.status === 'coming_soon' ? 'disabled' : ''}`;
            card.dataset.platform = platform.id;
            
            card.innerHTML = `
                <i class="${platform.icon}" style="color: ${platform.color}"></i>
                <span>${platform.name}</span>
                ${platform.status === 'coming_soon' ? '<span class="platform-status">قريباً</span>' : ''}
            `;
            
            if (platform.status !== 'coming_soon') {
                card.onclick = () => selectPlatform(platform.id);
            }
            
            grid.appendChild(card);
        });
    } catch (error) {
        showToast('حدث خطأ في تحميل المنصات', 'error');
    }
}
async function selectPlatform(platform) {
    currentPlatform = platform;
    
    // تحميل دليل استخراج الجلسة
    try {
        const response = await fetch(`/api/session-guide/${platform}`);
        const data = await response.json();
        
        if (data.success) {
            displaySessionGuide(data.guide);
        }
    } catch (error) {
        showToast('حدث خطأ في تحميل الدليل', 'error');
    }
    
    showScreen('sessionGuide');
}
function displaySessionGuide(guide) {
    // تحديث رأس الصفحة
    const header = document.getElementById('session-platform-header');
    header.innerHTML = `
        <i class="${guide.icon}" style="color: ${guide.color}"></i>
        <h2>${guide.name}</h2>
    `;
    
    // عرض الخطوات
    const stepsContainer = document.getElementById('steps-container');
    stepsContainer.innerHTML = guide.steps_arabic.map((step, index) => `
        <div class="step-item">
            <div class="step-number">${index + 1}</div>
            <div class="step-text">${step}</div>
        </div>
    `).join('');
    
    // عرض الروابط السريعة
    const linksContainer = document.getElementById('quick-links');
    linksContainer.innerHTML = Object.entries(guide.quick_links || {}).map(([key, url]) => `
        <a href="${url}" target="_blank" class="quick-link">
            <i class="fas fa-link"></i>
            <span>${key === 'settings' ? 'الإعدادات' : 
                     key === 'activity_log' ? 'سجل النشاطات' : 
                     key === 'profile' ? 'الملف الشخصي' : 
                     key === 'cookies_location' ? 'مكان الكوكيز' : key}</span>
        </a>
    `).join('');
    
    // تحميل الإضافات
    loadExtensions();
}
async function loadExtensions() {
    try {
        const response = await fetch('/api/extensions');
        const data = await response.json();
        
        if (data.success) {
            const grid = document.getElementById('extensions-grid');
            grid.innerHTML = data.extensions.map(ext => `
                <div class="extension-card">
                    <i class="fas fa-puzzle-piece"></i>
                    <h4>${ext.name}</h4>
                    <p>${ext.description}</p>
                    <div class="extension-links">
                        <a href="${ext.chrome}" target="_blank" title="Chrome">
                            <i class="fab fa-chrome"></i>
                        </a>
                        <a href="${ext.firefox}" target="_blank" title="Firefox">
                            <i class="fab fa-firefox"></i>
                        </a>
                    </div>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('خطأ في تحميل الإضافات:', error);
    }
}
function switchTab(tabName) {
    // إزالة active من كل التبويبات
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    // تفعيل التبويب المحدد
    document.querySelector(`.tab-btn[onclick="switchTab('${tabName}')"]`).classList.add('active');
    document.getElementById(`${tabName}-tab`).classList.add('active');
}
function openDirectLink() {
    const guide = getCurrentPlatformGuide();
    if (guide && guide.extraction_methods) {
        const directLink = guide.extraction_methods.find(m => m.type === 'direct_link');
        if (directLink) {
            window.open(directLink.url, '_blank');
        }
    }
}
async function copyQuickScript() {
    try {
        const response = await fetch(`/api/quick-copy/${currentPlatform}`);
        const data = await response.json();
        
        if (data.success) {
            // نسخ السكربت للحافظة
            await navigator.clipboard.writeText(data.script);
            showToast('✅ تم نسخ السكربت! الصقه في console المتصفح', 'success');
            
            // فتح console التعليمات
            showToast('اضغط F12 واذهب لـ Console والصق السكربت', 'info', 5000);
        }
    } catch (error) {
        showToast('حدث خطأ', 'error');
    }
}
async function verifySessionCookies() {
    const cookies = document.getElementById('session-cookies').value.trim();
    
    if (!cookies) {
        showToast('من فضلك الصق الكوكيز أولاً', 'error');
        return;
    }
    
    showToast('جاري التحقق من الكوكيز...', 'info');
    
    try {
        const response = await fetch('/api/verify-cookies', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                platform: currentPlatform,
                cookies: cookies
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            sessionCookies = cookies;
            userInfo = data;
            showToast('✅ الكوكيز صالحة!', 'success');
            
            // عرض معلومات المستخدم
            document.getElementById('user-info').innerHTML = `
                <div class="user-avatar">
                    <i class="fas fa-user"></i>
                </div>
                <div class="user-details">
                    <h4>${data.username || 'مستخدم'}</h4>
                    <p>${currentPlatform} - تم التحقق بنجاح</p>
                </div>
            `;
            
            showScreen('actions');
        } else {
            showToast(data.error || '❌ الكوكيز غير صالحة', 'error');
        }
    } catch (error) {
        showToast('حدث خطأ في الاتصال بالسيرفر', 'error');
    }
}
async function selectAction(action) {
    currentAction = action;
    
    if (action === 'comments') {
        // جلب التعليقات للاختيار
        await loadItemsForSelection();
        showScreen('selection');
    } else {
        // تأكيد الحذف المباشر
        showConfirm(`هل أنت متأكد من حذف كل ${getActionName(action)}؟`, async () => {
            await startDeleting('all', []);
        });
    }
}
async function loadItemsForSelection(loadMore = false) {
    showScreen('selection');
    
    const itemsList = document.getElementById('items-list');
    itemsList.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i> جاري تحميل التعليقات...</div>';
    
    try {
        const response = await fetch('/api/fetch-items', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                platform: currentPlatform,
                cookies: sessionCookies,
                action: currentAction,
                limit: loadMore ? 100 : 50
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (loadMore) {
                currentItems = [...currentItems, ...data.items];
            } else {
                currentItems = data.items;
            }
            
            displayItemsForSelection();
            document.getElementById('loaded-count').textContent = currentItems.length;
        } else {
            showToast(data.error || 'فشل تحميل التعليقات', 'error');
            goBack();
        }
    } catch (error) {
        showToast('حدث خطأ', 'error');
        goBack();
    }
}
function displayItemsForSelection() {
    const itemsList = document.getElementById('items-list');
    
    if (currentItems.length === 0) {
        itemsList.innerHTML = '<div class="loading-spinner">لا توجد تعليقات</div>';
        return;
    }
    
    itemsList.innerHTML = currentItems.map((item, index) => `
        <div class="item-checkbox">
            <input type="checkbox" id="item-${index}" value="${index}" onchange="updateSelectedItems()">
            <div class="item-content">
                <div class="item-text">${item.text || 'تعليق'}</div>
                <div class="item-date">${item.date || 'تاريخ غير معروف'}</div>
            </div>
        </div>
    `).join('');
    
    document.getElementById('selection-progress').style.display = 'flex';
}
function updateSelectedItems() {
    selectedItems = [];
    document.querySelectorAll('.item-checkbox input:checked').forEach(checkbox => {
        const index = parseInt(checkbox.value);
        selectedItems.push(currentItems[index]);
    });
    
    document.getElementById('selected-count').textContent = selectedItems.length;
    document.getElementById('selected-count-btn').textContent = selectedItems.length;
}
function toggleSelectAll() {
    const checkboxes = document.querySelectorAll('.item-checkbox input');
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);
    
    checkboxes.forEach(checkbox => {
        checkbox.checked = !allChecked;
    });
    
    updateSelectedItems();
}
function loadMoreItems() {
    loadItemsForSelection(true);
}
function deleteSelected() {
    if (selectedItems.length === 0) {
        showToast('اختر تعليقات أولاً', 'error');
        return;
    }
    
    showConfirm(`هل أنت متأكد من حذف ${selectedItems.length} تعليق؟`, () => {
        startDeleting('selected', selectedItems);
    });
}
async function startDeleting(deleteType, items) {
    isDeleting = true;
    startTime = Date.now();
    showScreen('progress');
    
    // إعادة تعيين شاشة التقدم
    document.getElementById('progress-fill').style.width = '0%';
    document.getElementById('progress-text').textContent = '0%';
    document.getElementById('deleted-items').textContent = '0';
    document.getElementById('failed-items').textContent = '0';
    document.getElementById('remaining-items').textContent = items.length || '?';
    document.getElementById('total-items').textContent = items.length || '?';
    document.getElementById('log-messages').innerHTML = '';
    document.getElementById('finish-btn').style.display = 'none';
    document.getElementById('pause-btn').innerHTML = '<i class="fas fa-pause"></i> إيقاف مؤقت';
    
    try {
        const response = await fetch('/api/start-deleting', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                platform: currentPlatform,
                cookies: sessionCookies,
                action: currentAction,
                delete_type: deleteType,
                selected_items: items,
                max_workers: 10
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentTaskId = data.task_id;
            totalToDelete = data.total_items;
            document.getElementById('total-items').textContent = totalToDelete;
            document.getElementById('remaining-items').textContent = totalToDelete;
            
            // بدء متابعة التقدم
            startProgressTracking();
        } else {
            showToast(data.error || 'فشل بدء الحذف', 'error');
            isDeleting = false;
            goBack();
        }
    } catch (error) {
        showToast('حدث خطأ في الاتصال بالسيرفر', 'error');
        isDeleting = false;
        goBack();
    }
}
function startProgressTracking() {
    deleteInterval = setInterval(async () => {
        if (isPaused || !currentTaskId) return;
        
        try {
            const response = await fetch(`/api/delete-status/${currentTaskId}`);
            const data = await response.json();
            
            if (data.success) {
                updateProgress(data);
                
                if (data.status === 'completed') {
                    finishDeleting(data);
                }
            }
        } catch (error) {
            console.error('خطأ في متابعة التقدم:', error);
        }
    }, 1000);
}
function updateProgress(data) {
    const progress = data.progress || 0;
    deletedCount = data.deleted || 0;
    failedCount = data.failed || 0;
    const remaining = totalToDelete - (deletedCount + failedCount);
    
    // تحديث الشريط
    document.getElementById('progress-fill').style.width = `${progress}%`;
    document.getElementById('progress-text').textContent = `${Math.round(progress)}%`;
    
    // تحديث الإحصائيات
    document.getElementById('deleted-items').textContent = deletedCount;
    document.getElementById('failed-items').textContent = failedCount;
    document.getElementById('remaining-items').textContent = remaining;
    
    // حساب السرعة
    const elapsedSeconds = (Date.now() - startTime) / 1000;
    deleteSpeed = ((deletedCount + failedCount) / elapsedSeconds).toFixed(1);
    document.getElementById('delete-speed').textContent = deleteSpeed;
    
    // إظهار تحذير rate limit
    if (data.rate_limited) {
        document.getElementById('rate-limit-warning').style.display = 'flex';
    } else {
        document.getElementById('rate-limit-warning').style.display = 'none';
    }
}
function togglePause() {
    isPaused = !isPaused;
    const pauseBtn = document.getElementById('pause-btn');
    
    if (isPaused) {
        pauseBtn.innerHTML = '<i class="fas fa-play"></i> استئناف';
        pauseBtn.style.background = '#48bb78';
        addLogMessage('⏸️ تم إيقاف الحذف مؤقتاً', 'info');
    } else {
        pauseBtn.innerHTML = '<i class="fas fa-pause"></i> إيقاف مؤقت';
        pauseBtn.style.background = '#ecc94b';
        addLogMessage('▶️ تم استئناف الحذف', 'info');
    }
}
function stopDeleting() {
    if (deleteInterval) {
        clearInterval(deleteInterval);
        deleteInterval = null;
    }
    
    isDeleting = false;
    currentTaskId = null;
    
    addLogMessage('⛔ تم إيقاف الحذف يدوياً', 'error');
    
    document.getElementById('finish-btn').style.display = 'block';
    document.getElementById('pause-btn').disabled = true;
    document.getElementById('stop-btn').disabled = true;
}
function finishDeleting(data) {
    if (deleteInterval) {
        clearInterval(deleteInterval);
        deleteInterval = null;
    }
    
    isDeleting = false;
    
    // عرض النتائج
    document.getElementById('result-total').textContent = data.total || totalToDelete;
    document.getElementById('result-success').textContent = data.deleted || deletedCount;
    document.getElementById('result-failed').textContent = data.failed || failedCount;
    
    const elapsedSeconds = ((Date.now() - startTime) / 1000).toFixed(0);
    document.getElementById('result-time').textContent = `${elapsedSeconds} ثانية`;
    
    // عرض العناصر الفاشلة إن وجدت
    if (data.failed_items && data.failed_items.length > 0) {
        document.getElementById('failed-items-list').style.display = 'block';
        const failedContainer = document.querySelector('.failed-items-container');
        failedContainer.innerHTML = data.failed_items.map(item => `
            <div class="failed-item">
                <i class="fas fa-times-circle"></i>
                <span>${item.text || 'عنصر'}</span>
            </div>
        `).join('');
    }
    
    showScreen('results');
    addLogMessage('✅ تم الانتهاء من الحذف بنجاح', 'success');
}
function addLogMessage(message, type = 'info') {
    const logMessages = document.getElementById('log-messages');
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${type}`;
    
    const time = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    logEntry.textContent = `[${time}] ${message}`;
    
    logMessages.appendChild(logEntry);
    logMessages.scrollTop = logMessages.scrollHeight;
}
function clearLog() {
    document.getElementById('log-messages').innerHTML = '';
}
function finish() {
    showScreen('results');
}
function startNew() {
    resetAll();
    showScreen('start');
}
function exportReport() {
    const report = {
        platform: currentPlatform,
        action: currentAction,
        total: document.getElementById('result-total').textContent,
        success: document.getElementById('result-success').textContent,
        failed: document.getElementById('result-failed').textContent,
        time: document.getElementById('result-time').textContent,
        date: new Date().toLocaleString('ar-EG')
    };
    
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cleaner-report-${Date.now()}.json`;
    a.click();
    
    showToast('تم تصدير التقرير بنجاح', 'success');
}
// دوال مساعدة
function getActionName(action) {
    const names = {
        'reposts': 'الريبوستات',
        'likes': 'اللايكات',
        'comments': 'التعليقات',
        'saved': 'المحفوظات'
    };
    return names[action] || action;
}
function getCurrentPlatformGuide() {
    // هون هتجيب الـ guide من الـ API
    return null;
}
async function pasteCookies() {
    try {
        const text = await navigator.clipboard.readText();
        document.getElementById('session-cookies').value = text;
        showToast('✅ تم اللصق', 'success');
    } catch (error) {
        showToast('فشل اللصق، الصق يدوياً Ctrl+V', 'error');
    }
}
function clearCookies() {
    document.getElementById('session-cookies').value = '';
    showToast('تم المسح', 'info');
}
// نظام التأكيد
let confirmCallback = null;
function showConfirm(message, callback) {
    document.getElementById('confirm-message').textContent = message;
    document.getElementById('confirm-modal').classList.add('show');
    confirmCallback = callback;
}
function confirmAction(confirmed) {
    document.getElementById('confirm-modal').classList.remove('show');
    
    if (confirmed && confirmCallback) {
        confirmCallback();
    }
    
    confirmCallback = null;
}
// نظام الإشعارات
function showToast(message, type = 'info', duration = 3000) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, duration);
}
// منع الإغلاق أثناء الحذف
window.addEventListener('beforeunload', function(e) {
    if (isDeleting) {
        e.preventDefault();
        e.returnValue = 'عملية الحذف لا تزال قيد التنفيذ، هل تريد المغادرة؟';
    }
});
