// 应用状态
const state = {
    currentPage: 1,
    pageSize: 20,
    totalRecords: 0,
    currentType: '',
    searchQuery: '',
    favoriteFilter: '',
    sortField: 'id',
    sortOrder: 'desc',
    isLoading: false,
    selectedIds: []  // 选中的记录ID
};

const API_BASE = '/api';

// 格式化时间
function formatTime(isoString) {
    if (!isoString) return '-';
    const date = new Date(isoString);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// 格式化大小/长度
function formatSize(bytes, type, content) {
    // 文本类型显示字符数
    if (type === 'Text' && content) {
        return content.length + ' 字符';
    }

    // 文件类型显示字节数
    if (!bytes) return '-';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
}

// HTML转义
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 检查登录状态
async function checkAuth() {
    try {
        const res = await fetch('/api/check-auth');
        const data = await res.json();
        if (!data.authenticated) {
            window.location.href = '/login.html';
            return false;
        }
        document.getElementById('username').textContent = data.username;
        return true;
    } catch (e) {
        window.location.href = '/login.html';
        return false;
    }
}

// 登出
async function logout() {
    await fetch('/api/logout', { method: 'POST' });
    window.location.href = '/login.html';
}

// 加载历史记录
async function loadHistory() {
    // 如果正在加载，跳过
    if (state.isLoading) {
        return;
    }

    state.isLoading = true;

    const loading = document.getElementById('loading');
    const tableBody = document.getElementById('table-body');
    const emptyState = document.getElementById('empty-state');

    loading.style.display = 'block';
    tableBody.innerHTML = '';
    emptyState.style.display = 'none';

    try {
        const params = new URLSearchParams({
            page: state.currentPage,
            page_size: state.pageSize
        });

        if (state.currentType) params.append('type', state.currentType);
        if (state.searchQuery) params.append('search', state.searchQuery);
        if (state.favoriteFilter) params.append('favorited', state.favoriteFilter);

        const res = await fetch(`${API_BASE}/history?${params}`);
        const data = await res.json();

        state.totalRecords = data.total;
        document.getElementById('total-records').textContent = data.total;

        if (data.items.length === 0) {
            emptyState.style.display = 'block';
        } else {
            // 本地排序
            let items = [...data.items];
            if (state.sortField) {
                items.sort((a, b) => {
                    let va = a[state.sortField];
                    let vb = b[state.sortField];
                    if (state.sortField === 'created_at') {
                        va = new Date(va).getTime();
                        vb = new Date(vb).getTime();
                    }
                    if (va < vb) return state.sortOrder === 'asc' ? -1 : 1;
                    if (va > vb) return state.sortOrder === 'asc' ? 1 : -1;
                    return 0;
                });
            }

            items.forEach(item => {
                const tr = document.createElement('tr');

                const typeClass = item.type.toLowerCase();
                const content = item.type === 'Text' ? item.content : item.content;
                const contentPreview = content ? content.substring(0, 100) : '';
                const hasMore = content && content.length > 100;

                // 解析收藏状态
                let favorited = false;
                try {
                    const extraData = item.extra_data ? JSON.parse(item.extra_data) : {};
                    favorited = extraData.favorited || false;
                } catch (e) { }

                const isChecked = state.selectedIds.includes(item.id);

                tr.innerHTML = `
                    <td><input type="checkbox" class="row-checkbox" data-id="${item.id}" ${isChecked ? 'checked' : ''}></td>
                    <td>${item.id}</td>
                    <td><span class="type-tag ${typeClass}">${item.type}</span></td>
                    <td class="content-cell" title="${hasMore ? '点击查看完整内容' : escapeHtml(content)}">
                        ${escapeHtml(contentPreview)}${hasMore ? '<span class="ellipsis"> ···</span>' : ''}
                    </td>
                    <td>${formatSize(item.file_size, item.type, content)}</td>
                    <td>${formatTime(item.created_at)}</td>
                    <td><span class="favorite-btn ${favorited ? 'favorited' : ''}" data-id="${item.id}">★</span></td>
                    <td>
                        <button class="action-btn delete-btn" data-id="${item.id}" style="color:#ff4d4f;border-color:#ffccc7;">删除</button>
                    </td>
                `;

                // 复选框事件
                tr.querySelector('.row-checkbox').addEventListener('change', (e) => {
                    if (e.target.checked) {
                        if (!state.selectedIds.includes(item.id)) {
                            state.selectedIds.push(item.id);
                        }
                    } else {
                        state.selectedIds = state.selectedIds.filter(id => id !== item.id);
                    }
                    // Assuming updateBatchDeleteBtn and updateSelectAllCheckbox are defined elsewhere
                    updateBatchDeleteBtn();
                    updateSelectAllCheckbox();
                });

                // 点击内容单元格
                tr.querySelector('.content-cell').addEventListener('click', () => {
                    if (item.type === 'Text') {
                        showTextModal(item.content);
                    } else {
                        handleRowClick(item);
                    }
                });

                // 收藏按钮事件
                tr.querySelector('.favorite-btn').addEventListener('click', (e) => {
                    e.stopPropagation();
                    toggleFavorite(item.id, e.target);
                });

                // 删除按钮事件
                tr.querySelector('.delete-btn').addEventListener('click', (e) => {
                    e.stopPropagation();
                    deleteRecord(item.id);
                });

                tableBody.appendChild(tr);
            });
        }

        updatePagination();
    } catch (e) {
        console.error('加载失败:', e);
        tableBody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#c00">加载失败</td></tr>';
    } finally {
        loading.style.display = 'none';
        state.isLoading = false;
    }
}

// 处理行点击
function handleRowClick(item) {
    if (item.type === 'Text') {
        copyText(item.content);
    } else if (item.type === 'Image' && item.file_path) {
        showImage(item.id);
    } else if (item.file_path) {
        downloadFile(item.id);
    }
}

// 复制文本
async function copyText(text, event) {
    try {
        await navigator.clipboard.writeText(text);
        showTooltip(event?.target || document.body, '已复制');
    } catch (e) {
        console.error('复制失败:', e);
    }
}

// 显示 tooltip
function showTooltip(element, message) {
    // 移除已有的 tooltip
    const existing = document.querySelector('.copy-tooltip');
    if (existing) existing.remove();

    const tooltip = document.createElement('div');
    tooltip.className = 'copy-tooltip';
    tooltip.textContent = message;
    document.body.appendChild(tooltip);

    // 定位到元素上方
    const rect = element.getBoundingClientRect();
    tooltip.style.left = rect.left + rect.width / 2 + 'px';
    tooltip.style.top = rect.top - 30 + 'px';

    // 1.5秒后消失
    setTimeout(() => tooltip.remove(), 1500);
}

// 显示文本预览
function showTextModal(text) {
    const modal = document.getElementById('text-modal');
    const textContent = document.getElementById('text-content');
    textContent.textContent = text;
    modal.classList.add('active');
}

// 复制模态框中的文本
async function copyModalText() {
    const text = document.getElementById('text-content').textContent;
    try {
        await navigator.clipboard.writeText(text);
        const btn = document.querySelector('.text-modal-copy');
        const originalText = btn.textContent;
        btn.textContent = '已复制';
        setTimeout(() => btn.textContent = originalText, 1500);
    } catch (e) {
        console.error('复制失败:', e);
    }
}

// 显示图片
function showImage(id) {
    const modal = document.getElementById('image-modal');
    const img = document.getElementById('modal-image');
    img.src = `/api/file/${id}`;
    modal.classList.add('active');
}

// 下载文件
function downloadFile(id) {
    window.location.href = `/api/file/${id}`;
}

// 切换收藏
async function toggleFavorite(id, element) {
    try {
        const res = await fetch(`${API_BASE}/history/${id}/favorite`, { method: 'POST' });
        const data = await res.json();

        if (data.favorited) {
            element.classList.add('favorited');
        } else {
            element.classList.remove('favorited');
        }
    } catch (e) {
        console.error('切换收藏失败:', e);
    }
}

// 自定义确认框
function showConfirm(title, message) {
    return new Promise((resolve) => {
        const modal = document.getElementById('confirm-modal');
        const titleEl = document.getElementById('confirm-title');
        const msgEl = document.getElementById('confirm-message');
        const okBtn = document.getElementById('confirm-ok');
        const cancelBtn = document.getElementById('confirm-cancel');
        const closeBtn = modal.querySelector('.modal-close');

        titleEl.textContent = title;
        msgEl.textContent = message;
        modal.classList.add('active');

        const cleanup = () => {
            modal.classList.remove('active');
            okBtn.removeEventListener('click', onOk);
            cancelBtn.removeEventListener('click', onCancel);
            closeBtn.removeEventListener('click', onCancel);
            modal.querySelector('.modal-overlay').removeEventListener('click', onCancel);
        };

        const onOk = () => {
            cleanup();
            resolve(true);
        };

        const onCancel = () => {
            cleanup();
            resolve(false);
        };

        okBtn.addEventListener('click', onOk);
        cancelBtn.addEventListener('click', onCancel);
        closeBtn.addEventListener('click', onCancel);
        modal.querySelector('.modal-overlay').addEventListener('click', onCancel);

        // 聚焦确认按钮
        okBtn.focus();
    });
}

// 删除单条记录
async function deleteRecord(id) {
    const confirmed = await showConfirm('删除确认', '确定要删除这条记录吗？此操作无法撤销。');
    if (!confirmed) return;

    try {
        const res = await fetch(`${API_BASE}/history/${id}`, { method: 'DELETE' });
        if (res.ok) {
            state.selectedIds = state.selectedIds.filter(selectedId => selectedId !== id); // Remove from selectedIds
            loadHistory();
            updateBatchDeleteBtn(); // Update batch delete button state
            updateSelectAllCheckbox(); // Update select all checkbox state
        } else {
            alert('删除失败');
        }
    } catch (e) {
        console.error('删除失败:', e);
        alert('删除失败');
    }
}

// 批量删除
async function batchDelete() {
    if (state.selectedIds.length === 0) {
        return;
    }

    const confirmed = await showConfirm('批量删除确认', `确定要删除选中的 ${state.selectedIds.length} 条记录吗？此操作无法撤销。`);
    if (!confirmed) return;

    try {
        const res = await fetch(`${API_BASE}/history/batch-delete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(state.selectedIds)
        });

        if (res.ok) {
            state.selectedIds = [];
            loadHistory();
            updateBatchDeleteBtn();
            updateSelectAllCheckbox();
        } else {
            alert('批量删除失败');
        }
    } catch (e) {
        console.error('批量删除失败:', e);
        alert('批量删除失败');
    }
}

// 更新批量删除按钮显示
function updateBatchDeleteBtn() {
    const btn = document.getElementById('batch-delete-btn');
    if (state.selectedIds.length > 0) {
        btn.style.display = 'inline-block';
        btn.textContent = `删除选中 (${state.selectedIds.length})`;
    } else {
        btn.style.display = 'none';
    }
}

// 更新全选复选框状态
function updateSelectAllCheckbox() {
    const selectAll = document.getElementById('select-all');
    const checkboxes = document.querySelectorAll('.row-checkbox');
    const checkedCount = document.querySelectorAll('.row-checkbox:checked').length;

    if (checkboxes.length === 0) { // No checkboxes to select
        selectAll.checked = false;
        selectAll.indeterminate = false;
        return;
    }

    if (checkedCount === 0) {
        selectAll.checked = false;
        selectAll.indeterminate = false;
    } else if (checkedCount === checkboxes.length) {
        selectAll.checked = true;
        selectAll.indeterminate = false;
    } else {
        selectAll.checked = false;
        selectAll.indeterminate = true;
    }
}

// 更新分页
function updatePagination() {
    const totalPages = Math.ceil(state.totalRecords / state.pageSize);
    const start = state.totalRecords > 0 ? (state.currentPage - 1) * state.pageSize + 1 : 0;
    const end = Math.min(state.currentPage * state.pageSize, state.totalRecords);

    document.getElementById('page-range').textContent =
        state.totalRecords > 0 ? `${start}-${end} / ${state.totalRecords}` : '无记录';

    document.getElementById('prev-btn').disabled = state.currentPage === 1;
    document.getElementById('next-btn').disabled = state.currentPage >= totalPages;
}

// 更新排序指示器
function updateSortIndicators() {
    document.querySelectorAll('.sortable').forEach(th => {
        th.classList.remove('asc', 'desc');
        if (th.dataset.field === state.sortField) {
            th.classList.add(state.sortOrder);
        }
    });
}

// 防抖
function debounce(fn, wait) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), wait);
    };
}

// 初始化事件
function initEvents() {
    // 全选复选框
    document.getElementById('select-all').addEventListener('change', (e) => {
        const checkboxes = document.querySelectorAll('.row-checkbox');
        checkboxes.forEach(cb => {
            cb.checked = e.target.checked;
            const id = parseInt(cb.dataset.id);
            if (e.target.checked) {
                if (!state.selectedIds.includes(id)) {
                    state.selectedIds.push(id);
                }
            } else {
                state.selectedIds = state.selectedIds.filter(i => i !== id);
            }
        });
        updateBatchDeleteBtn();
    });

    // 批量删除按钮
    document.getElementById('batch-delete-btn').addEventListener('click', batchDelete);

    // 类型筛选
    document.getElementById('type-filter').addEventListener('change', (e) => {
        state.currentType = e.target.value;
        state.currentPage = 1;
        loadHistory();
    });

    // 收藏筛选
    document.getElementById('favorite-filter').addEventListener('change', (e) => {
        state.favoriteFilter = e.target.value;
        state.currentPage = 1;
        loadHistory();
    });

    // 搜索
    document.getElementById('search-input').addEventListener('input', debounce((e) => {
        state.searchQuery = e.target.value;
        state.currentPage = 1;
        loadHistory();
    }, 400));

    // 分页
    document.getElementById('prev-btn').addEventListener('click', () => {
        if (state.currentPage > 1) {
            state.currentPage--;
            loadHistory();
        }
    });

    document.getElementById('next-btn').addEventListener('click', () => {
        const totalPages = Math.ceil(state.totalRecords / state.pageSize);
        if (state.currentPage < totalPages) {
            state.currentPage++;
            loadHistory();
        }
    });

    document.getElementById('page-size-select').addEventListener('change', (e) => {
        state.pageSize = parseInt(e.target.value);
        state.currentPage = 1;
        loadHistory();
    });

    // 排序
    document.querySelectorAll('.sortable').forEach(th => {
        th.addEventListener('click', () => {
            const field = th.dataset.field;
            if (state.sortField === field) {
                state.sortOrder = state.sortOrder === 'asc' ? 'desc' : 'asc';
            } else {
                state.sortField = field;
                state.sortOrder = 'desc';
            }
            updateSortIndicators();
            loadHistory();
        });
    });

    // 图片模态框
    const modal = document.getElementById('image-modal');
    modal.querySelector('.modal-overlay').addEventListener('click', () => modal.classList.remove('active'));
    modal.querySelector('.modal-close').addEventListener('click', () => modal.classList.remove('active'));

    // 文本模态框
    const textModal = document.getElementById('text-modal');
    textModal.querySelector('.modal-overlay').addEventListener('click', () => textModal.classList.remove('active'));
    textModal.querySelector('.modal-close').addEventListener('click', () => textModal.classList.remove('active'));
    textModal.querySelector('.text-modal-copy').addEventListener('click', copyModalText);

    // 登出
    document.getElementById('logout-btn').addEventListener('click', logout);
}

// 检查是否有新记录
async function checkForUpdates() {
    // 如果用户正在搜索或筛选，不自动刷新
    if (state.searchQuery || state.currentType || state.favoriteFilter) {
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/stats`);
        const data = await res.json();
        if (data.total_records !== state.totalRecords) {
            // 有新记录，刷新列表
            loadHistory();
        }
    } catch (e) {
        // 忽略错误
    }
}

// 初始化
async function init() {
    const auth = await checkAuth();
    if (!auth) return;

    initEvents();
    updateSortIndicators();
    loadHistory();

    // 每3秒检查一次是否有新内容
    setInterval(checkForUpdates, 1000);
}

document.addEventListener('DOMContentLoaded', init);
