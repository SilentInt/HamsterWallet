// 全局JavaScript函数

// 显示图片模态框
function showImageModal(imageUrl, title) {
  $("#imageModalTitle").text(title || "查看图片");
  $("#imageModalImg").attr("src", imageUrl);
  $("#imageModal").modal("show");
}

// iOS风格的确认对话框 - 增强版
function iosConfirm(message, title = "确认", options = {}) {
  return new Promise((resolve) => {
    const {
      confirmText = "确认",
      cancelText = "取消",
      type = "warning",
      showIcon = true,
    } = options;

    // 创建自定义确认对话框
    const modalId = `confirm-modal-${Date.now()}`;
    const modal = $(`
      <div class="modal fade" id="${modalId}" tabindex="-1" data-bs-backdrop="static">
        <div class="modal-dialog modal-dialog-centered">
          <div class="modal-content" style="border-radius: 16px; border: none; overflow: hidden;">
            <div class="modal-body text-center" style="padding: 2rem;">
              ${
                showIcon
                  ? `<div class="mb-3">
                <i class="fas fa-exclamation-triangle fa-3x" style="color: var(--ios-orange);"></i>
              </div>`
                  : ""
              }
              <h5 class="fw-bold mb-3">${title}</h5>
              <p class="text-muted mb-4">${message}</p>
              <div class="d-flex gap-3 justify-content-center">
                <button type="button" class="btn btn-outline-secondary px-4" data-action="cancel">
                  ${cancelText}
                </button>
                <button type="button" class="btn btn-primary px-4" data-action="confirm">
                  ${confirmText}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    `);

    $("body").append(modal);

    // 绑定事件
    modal.find('[data-action="confirm"]').on("click", function () {
      modal.modal("hide");
      resolve(true);
    });

    modal.find('[data-action="cancel"]').on("click", function () {
      modal.modal("hide");
      resolve(false);
    });

    // 模态框隐藏后清理
    modal.on("hidden.bs.modal", function () {
      modal.remove();
    });

    modal.modal("show");
  });
}

// 全局删除确认功能
window.confirmDelete = function(options = {}) {
  const {
    title = "确认删除",
    message = "您确定要删除这个项目吗？",
    itemName = null,
    onConfirm = null,
    onCancel = null,
    dangerText = "此操作无法撤销，请谨慎操作。"
  } = options;

  return new Promise((resolve) => {
    let isResolved = false; // 防止多次 resolve
    
    const resolveOnce = (value) => {
      if (!isResolved) {
        isResolved = true;
        resolve(value);
      }
    };

    // 更新模态框内容
    const modal = document.getElementById('confirmDeleteModal');
    const messageElement = document.getElementById('confirmDeleteMessage');
    const confirmBtn = document.getElementById('confirmDeleteBtn');
    
    // 设置消息文本
    let fullMessage = message;
    if (itemName) {
      fullMessage = `您确定要删除 "${itemName}" 吗？`;
    }
    messageElement.textContent = fullMessage;

    // 清除之前的事件监听器
    const newConfirmBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);

    // 绑定新的事件监听器
    newConfirmBtn.addEventListener('click', async () => {
      // 显示加载状态
      const originalText = newConfirmBtn.innerHTML;
      newConfirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 删除中...';
      newConfirmBtn.disabled = true;

      try {
        let result = true;
        if (onConfirm && typeof onConfirm === 'function') {
          result = await onConfirm();
        }
        
        // 恢复按钮状态
        newConfirmBtn.innerHTML = originalText;
        newConfirmBtn.disabled = false;
        
        // 隐藏模态框
        const bootstrapModal = bootstrap.Modal.getInstance(modal);
        if (bootstrapModal) {
          bootstrapModal.hide();
        }
        
        resolveOnce(result !== false); // 如果 onConfirm 返回 false，则认为删除失败
      } catch (error) {
        console.error('删除操作出错:', error);
        // 恢复按钮状态
        newConfirmBtn.innerHTML = originalText;
        newConfirmBtn.disabled = false;
        
        // 隐藏模态框
        const bootstrapModal = bootstrap.Modal.getInstance(modal);
        if (bootstrapModal) {
          bootstrapModal.hide();
        }
        
        resolveOnce(false);
      }
    });

    // 绑定取消事件 - 只在用户主动取消时触发
    modal.addEventListener('hidden.bs.modal', () => {
      if (onCancel && typeof onCancel === 'function') {
        onCancel();
      }
      // 只有在没有被其他操作 resolve 的情况下才 resolve false
      resolveOnce(false);
    }, { once: true });

    // 显示模态框
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
  });
};

// 加载状态管理器
class LoadingManager {
  constructor() {
    this.loadingStates = new Set();
  }

  show(element, text = "加载中...") {
    const $el = $(element);
    const originalContent = $el.html();
    $el.data("original-content", originalContent);
    $el.prop("disabled", true);
    $el.html(`<i class="fas fa-spinner fa-spin me-2"></i>${text}`);
    this.loadingStates.add(element);
  }

  hide(element) {
    const $el = $(element);
    const originalContent = $el.data("original-content");
    if (originalContent) {
      $el.html(originalContent);
      $el.prop("disabled", false);
      $el.removeData("original-content");
    }
    this.loadingStates.delete(element);
  }

  isLoading(element) {
    return this.loadingStates.has(element);
  }

  hideAll() {
    this.loadingStates.forEach((element) => {
      this.hide(element);
    });
  }
}

// 全局加载管理器实例
const loadingManager = new LoadingManager();

// 表单验证工具
class FormValidator {
  constructor(form) {
    this.form = $(form);
    this.rules = {};
    this.messages = {};
  }

  addRule(field, rule, message) {
    if (!this.rules[field]) {
      this.rules[field] = [];
      this.messages[field] = [];
    }
    this.rules[field].push(rule);
    this.messages[field].push(message);
    return this;
  }

  validate() {
    let isValid = true;
    this.clearErrors();

    for (const [fieldName, rules] of Object.entries(this.rules)) {
      const field = this.form.find(`[name="${fieldName}"]`);
      const value = field.val();

      for (let i = 0; i < rules.length; i++) {
        const rule = rules[i];
        const message = this.messages[fieldName][i];

        if (!rule(value, field)) {
          this.showError(field, message);
          isValid = false;
          break;
        }
      }
    }

    return isValid;
  }

  showError(field, message) {
    field.addClass("is-invalid");
    let errorDiv = field.next(".invalid-feedback");
    if (errorDiv.length === 0) {
      errorDiv = $(`<div class="invalid-feedback">${message}</div>`);
      field.after(errorDiv);
    } else {
      errorDiv.text(message);
    }
  }

  clearErrors() {
    this.form.find(".is-invalid").removeClass("is-invalid");
    this.form.find(".invalid-feedback").remove();
  }

  // 常用验证规则
  static rules = {
    required: (value) => value && value.trim() !== "",
    minLength: (min) => (value) => value && value.length >= min,
    maxLength: (max) => (value) => !value || value.length <= max,
    email: (value) => !value || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value),
    number: (value) => !value || /^\d+(\.\d+)?$/.test(value),
    positiveNumber: (value) => !value || parseFloat(value) > 0,
  };
}

// 工具函数集合
const Utils = {
  // 防抖函数
  debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  },

  // 节流函数
  throttle(func, limit) {
    let inThrottle;
    return function (...args) {
      if (!inThrottle) {
        func.apply(this, args);
        inThrottle = true;
        setTimeout(() => (inThrottle = false), limit);
      }
    };
  },

  // 格式化文件大小
  formatFileSize(bytes) {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  },

  // 格式化数字
  formatNumber(num, decimals = 2) {
    return parseFloat(num).toFixed(decimals);
  },

  // 复制到剪贴板
  async copyToClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      showToast("已复制到剪贴板", "success");
      return true;
    } catch (err) {
      // 降级方案
      const textArea = document.createElement("textarea");
      textArea.value = text;
      document.body.appendChild(textArea);
      textArea.select();
      try {
        document.execCommand("copy");
        showToast("已复制到剪贴板", "success");
        return true;
      } catch (err) {
        showToast("复制失败", "error");
        return false;
      } finally {
        document.body.removeChild(textArea);
      }
    }
  },

  // 生成随机ID
  generateId(prefix = "id") {
    return `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  },

  // 检查是否为移动设备
  isMobile() {
    return window.innerWidth <= 768;
  },

  // 平滑滚动到元素
  scrollToElement(element, offset = 0) {
    const $el = $(element);
    if ($el.length) {
      $("html, body").animate(
        {
          scrollTop: $el.offset().top - offset,
        },
        500
      );
    }
  },
};

// iOS风格的Toast通知 - 增强版
function showToast(message, type = "info", duration = 3000, clickable = false) {
  const toastContainer = $("#toastContainer");
  if (toastContainer.length === 0) {
    $("body").append(
      '<div id="toastContainer" style="position: fixed; top: 80px; right: 20px; z-index: 9999; max-width: 380px;"></div>'
    );
  }

  const colors = {
    success: "var(--ios-green)",
    error: "var(--ios-red)",
    warning: "var(--ios-orange)",
    info: "var(--ios-blue)",
  };

  const icons = {
    success: "fas fa-check-circle",
    error: "fas fa-exclamation-circle",
    warning: "fas fa-exclamation-triangle",
    info: "fas fa-info-circle",
  };

  const toastId = `toast-${Date.now()}`;
  const toast = $(`
    <div id="${toastId}" class="toast-message" style="
      background: white;
      border-left: 4px solid ${colors[type]};
      border-radius: 12px;
      padding: 16px 20px;
      margin-bottom: 10px;
      box-shadow: var(--ios-shadow-hover);
      max-width: 100%;
      animation: slideInRight 0.3s ease-out;
      cursor: ${clickable ? "pointer" : "default"};
      position: relative;
      overflow: hidden;
    ">
      <div style="display: flex; align-items: center; justify-content: space-between;">
        <div style="display: flex; align-items: center; flex: 1;">
          <i class="${icons[type]}" style="color: ${
    colors[type]
  }; font-size: 20px; margin-right: 12px; flex-shrink: 0;"></i>
          <span style="font-weight: 500; word-break: break-word;">${message}</span>
        </div>
        <button class="toast-close" style="
          background: none;
          border: none;
          color: var(--ios-gray-5);
          font-size: 18px;
          margin-left: 10px;
          cursor: pointer;
          padding: 0;
          width: 20px;
          height: 20px;
          display: flex;
          align-items: center;
          justify-content: center;
        ">×</button>
      </div>
      ${
        duration > 0
          ? `<div class="toast-progress" style="
        position: absolute;
        bottom: 0;
        left: 0;
        height: 2px;
        background: ${colors[type]};
        width: 100%;
        animation: shrinkWidth ${duration}ms linear;
      "></div>`
          : ""
      }
    </div>
  `);

  // 点击关闭功能
  toast.find(".toast-close").on("click", function (e) {
    e.stopPropagation();
    closeToast(toast);
  });

  // 可点击功能
  if (clickable) {
    toast.on("click", function () {
      closeToast(toast);
    });
  }

  $("#toastContainer").append(toast);

  // 自动关闭
  if (duration > 0) {
    setTimeout(() => {
      closeToast(toast);
    }, duration);
  }

  return toastId;
}

// 关闭Toast
function closeToast(toast) {
  if (toast && toast.length) {
    toast.addClass("toast-closing");
    toast.css({
      animation: "slideOutRight 0.3s ease-in",
      transform: "translateX(100%)",
      opacity: "0",
    });
    setTimeout(() => {
      toast.remove();
    }, 300);
  }
}

// 关闭所有Toast
function clearAllToasts() {
  $(".toast-message").each(function () {
    closeToast($(this));
  });
}

// 显示加载Toast
function showLoadingToast(message = "加载中...") {
  return showToast(
    `<i class="fas fa-spinner fa-spin me-2"></i>${message}`,
    "info",
    0
  );
}

// 隐藏特定Toast
function hideToast(toastId) {
  const toast = $(`#${toastId}`);
  closeToast(toast);
}

// 通用AJAX错误处理
$(document).ajaxError(function (event, xhr, settings, error) {
  if (xhr.status === 0) return; // 忽略取消的请求

  let message = "网络错误，请重试";
  if (xhr.responseJSON && xhr.responseJSON.message) {
    message = xhr.responseJSON.message;
  } else if (xhr.status === 404) {
    message = "请求的资源不存在";
  } else if (xhr.status === 500) {
    message = "服务器内部错误";
  }

  showToast(message, "error");
});

// 增强筛选交互功能
$(document).ready(function () {
  // 智能表单提交防抖
  let submitTimeout;
  $('.filter-form select, .filter-form input[type="text"]').on(
    "input change",
    function () {
      clearTimeout(submitTimeout);
      const isSelect = $(this).is("select");

      // 选择框立即提交，文本输入延迟提交
      const delay = isSelect ? 0 : 1000;

      submitTimeout = setTimeout(() => {
        $(this).closest("form").submit();
      }, delay);
    }
  );

  // 筛选折叠动画增强
  $(".filter-toggle-btn").on("click", function () {
    const icon = $(this).find("i:last-child");
    const isExpanded = $(this).attr("aria-expanded") === "true";

    // 手动切换图标，因为Bootstrap事件可能延迟
    if (isExpanded) {
      icon.removeClass("fa-chevron-up").addClass("fa-chevron-down");
    } else {
      icon.removeClass("fa-chevron-down").addClass("fa-chevron-up");
    }

    // 添加点击反馈
    $(this).addClass("btn-loading");
    setTimeout(() => {
      $(this).removeClass("btn-loading");
    }, 300);
  });

  // 清除筛选增强效果
  $(document).on("click", ".clear-filter-btn", function () {
    // 添加加载动画
    $(this).addClass("btn-loading");

    // 延迟执行以显示动画
    setTimeout(() => {
      if (typeof clearFilters === "function") {
        clearFilters();
      } else {
        // 如果没有定义 clearFilters，则提供一个通用后备方案
        const form = $(this).closest("form");
        if (form.length > 0) {
          form[0].reset();
          // 移除URL参数并重新加载
          window.location.href = window.location.pathname;
        }
      }
    }, 500);
  });

  // 表单验证增强
  $(".filter-form input, .filter-form select").on("blur", function () {
    const value = $(this).val();
    const $group = $(this).closest(".filter-form-group");

    // 移除之前的状态
    $(this).removeClass("is-valid is-invalid");

    // 简单验证逻辑
    if ($(this).attr("required") && !value) {
      $(this).addClass("is-invalid");
    } else if (value) {
      $(this).addClass("is-valid");
    }
  });

  // 触摸设备优化
  if ("ontouchstart" in window) {
    $(
      ".filter-toggle-btn, .filter-btn-primary, .filter-btn-secondary, .clear-filter-btn"
    ).on("touchstart", function () {
      $(this).css("transform", "scale(0.97)");
    });
    $(
      ".filter-toggle-btn, .filter-btn-primary, .filter-btn-secondary, .clear-filter-btn"
    ).on("touchend", function () {
      $(this).css("transform", "scale(1)");
    });
  }

  // 自动保存筛选状态到本地存储
  $(".filter-form").on("submit", function () {
    const formData = $(this).serialize();
    localStorage.setItem("filterState_" + window.location.pathname, formData);
  });

  // 恢复筛选状态
  const savedState = localStorage.getItem(
    "filterState_" + window.location.pathname
  );
  if (savedState && !window.location.search) {
    // 如果没有URL参数但有保存的状态，询问是否恢复
    const shouldRestore = confirm("检测到之前的筛选条件，是否恢复？");
    if (shouldRestore) {
      // 解析保存的数据并填充表单
      const params = new URLSearchParams(savedState);
      params.forEach((value, key) => {
        $(`[name="${key}"]`).val(value);
      });
      // 触发表单提交以应用筛选
      $(".filter-form").submit();
    }
  }

  // 无限滚动功能初始化
  initializeInfiniteScroll();
});

// 无限滚动功能
function initializeInfiniteScroll() {
  const loadMoreBtn = document.getElementById("loadMoreBtn");
  const loadingIndicator = document.getElementById("loadingIndicator");
  const itemsGrid =
    document.getElementById("itemsGrid") ||
    document.getElementById("receiptGrid");

  if (!loadMoreBtn || !itemsGrid) return;

  let isLoading = false;
  let isInitialized = false; // 防止重复初始化

  // 检查是否已经初始化过
  if (window.infiniteScrollInitialized) {
    return;
  }
  window.infiniteScrollInitialized = true;

  // 检测是否为移动端
  function isMobile() {
    return window.innerWidth <= 768;
  }

  // 显示/隐藏加载指示器
  function toggleLoadingIndicator() {
    if (
      loadMoreBtn.dataset.nextPage &&
      parseInt(loadMoreBtn.dataset.nextPage) <=
        parseInt(loadMoreBtn.dataset.totalPages)
    ) {
      // 有更多数据可加载，但不显示按钮，只保留加载指示器容器
      if (document.getElementById("loadMoreContainer")) {
        document.getElementById("loadMoreContainer").style.display = "block";
      }
    } else {
      // 没有更多数据，隐藏容器
      if (document.getElementById("loadMoreContainer")) {
        document.getElementById("loadMoreContainer").style.display = "none";
      }
    }
  }

  // 加载更多数据
  function loadMoreData() {
    // 严格检查加载状态，防止重复请求
    if (
      isLoading ||
      !loadMoreBtn.dataset.nextPage ||
      loadMoreBtn.dataset.nextPage === ""
    ) {
      return;
    }

    isLoading = true;
    const nextPage = loadMoreBtn.dataset.nextPage;

    // 立即更新按钮状态，防止重复点击
    if (loadMoreBtn) {
      loadMoreBtn.disabled = true;
    }

    // 显示加载动画
    if (loadingIndicator) {
      loadingIndicator.style.display = "block";
      // 桌面端添加显示动画
      if (!isMobile()) {
        loadingIndicator.classList.add("show");
      }
    }

    // 构建请求URL
    const currentUrl = new URL(window.location);
    currentUrl.searchParams.set("page", nextPage);

    fetch(currentUrl.toString())
      .then((response) => response.text())
      .then((html) => {
        // 创建临时容器解析HTML
        const tempDiv = document.createElement("div");
        tempDiv.innerHTML = html;

        // 更精确地提取网格中的列容器项
        // 首先尝试从网格容器中直接获取列
        let newItems = [];
        const gridContainer = tempDiv.querySelector("#itemsGrid, #receiptGrid");

        if (gridContainer) {
          // 从网格容器中获取直接子元素（列）
          newItems = Array.from(gridContainer.children).filter((child) => {
            return (
              child.className.includes("col-") &&
              child.querySelector(".item-compact, .receipt-compact")
            );
          });
        } else {
          // 备用方法：只选择明确在网格行中的列元素
          const gridRows = tempDiv.querySelectorAll(".row");
          gridRows.forEach((row) => {
            if (row.id === "itemsGrid" || row.id === "receiptGrid") {
              const cols = Array.from(row.children).filter((child) => {
                return (
                  child.className.includes("col-") &&
                  child.querySelector(".item-compact, .receipt-compact")
                );
              });
              newItems.push(...cols);
            }
          });
        }

        if (newItems.length > 0) {
          // 去重处理：检查是否已经存在相同的元素
          const existingIds = new Set();
          itemsGrid
            .querySelectorAll(".item-compact, .receipt-compact")
            .forEach((card) => {
              const id = card.dataset.id || card.getAttribute("data-id");
              if (id) existingIds.add(id);
            });

          // 添加进入动画类
          newItems.forEach((item, index) => {
            const cardElement = item.querySelector(
              ".item-compact, .receipt-compact"
            );
            if (cardElement) {
              // 检查是否已存在
              const itemId =
                cardElement.dataset.id || cardElement.getAttribute("data-id");
              if (itemId && existingIds.has(itemId)) {
                return; // 跳过重复项
              }

              cardElement.classList.add("fade-in-up");
              cardElement.style.transitionDelay = `${index * 0.02}s`;
            }

            // 只添加不重复的元素
            itemsGrid.appendChild(item);

            // 触发动画 - 减少延迟时间
            setTimeout(() => {
              if (cardElement) {
                cardElement.classList.add("visible");
              }
            }, 10);
          });

          // 为新加载的内容转换时区
          convertNewTimestamps(itemsGrid);

          // 更新分页信息
          const nextPageNum = parseInt(nextPage) + 1;
          const totalPages = parseInt(loadMoreBtn.dataset.totalPages);

          if (nextPageNum <= totalPages) {
            loadMoreBtn.dataset.nextPage = nextPageNum;
          } else {
            loadMoreBtn.dataset.nextPage = "";
            // 到达底部，清除滑动惯性
            clearScrollMomentum();
          }

          toggleLoadingIndicator();
        } else {
          // 没有更多数据
          loadMoreBtn.dataset.nextPage = "";
          toggleLoadingIndicator();
          // 到达底部，清除滑动惯性
          clearScrollMomentum();
        }
      })
      .catch((error) => {
        console.error("加载失败:", error);
        showToast("加载失败，请重试", "error");
      })
      .finally(() => {
        isLoading = false;
        // 恢复按钮状态
        if (loadMoreBtn) {
          loadMoreBtn.disabled = false;
        }
        if (loadingIndicator) {
          loadingIndicator.style.display = "none";
          // 桌面端移除显示动画类
          if (!isMobile()) {
            loadingIndicator.classList.remove("show");
          }
        }
      });
  }

  // 清除滑动惯性的函数
  function clearScrollMomentum() {
    // 阻止当前滚动惯性
    document.body.style.overflow = "hidden";
    setTimeout(() => {
      document.body.style.overflow = "";
    }, 10);

    // 对于移动端Safari，额外处理
    if (isMobile() && /iPhone|iPad|iPod|Safari/.test(navigator.userAgent)) {
      const scrollTop = window.pageYOffset;
      window.scrollTo(0, scrollTop);

      // 创建一个轻微的反向滚动来停止惯性
      setTimeout(() => {
        window.scrollTo(0, scrollTop - 1);
        setTimeout(() => {
          window.scrollTo(0, scrollTop);
        }, 1);
      }, 1);
    }
  }

  // 检查是否滚动到底部
  function isNearBottom() {
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const windowHeight = window.innerHeight;
    const documentHeight = document.documentElement.scrollHeight;
    return scrollTop + windowHeight >= documentHeight - 100;
  }

  // 滚动事件处理（移动端和桌面端通用）
  let scrollTimeout;
  let lastScrollTime = 0;

  function handleScroll() {
    if (isLoading) return;

    const now = Date.now();
    // 限制滚动事件频率，避免过于频繁的检查
    if (now - lastScrollTime < 150) return;
    lastScrollTime = now;

    clearTimeout(scrollTimeout);
    scrollTimeout = setTimeout(() => {
      if (isNearBottom()) {
        if (loadMoreBtn.dataset.nextPage && !isLoading) {
          loadMoreData();
        } else if (
          !loadMoreBtn.dataset.nextPage ||
          loadMoreBtn.dataset.nextPage === ""
        ) {
          // 到达底部且没有更多数据，清除滑动惯性
          clearScrollMomentum();
        }
      }
    }, 200); // 增加防抖延迟
  }

  // 清理已有的事件监听器（如果存在）
  if (window.infiniteScrollHandler) {
    window.removeEventListener("scroll", window.infiniteScrollHandler);
  }
  if (window.infiniteResizeHandler) {
    window.removeEventListener("resize", window.infiniteResizeHandler);
  }

  // 保存事件处理器引用以便后续清理
  window.infiniteScrollHandler = handleScroll;
  window.infiniteResizeHandler = () => {
    toggleLoadingIndicator();
  };

  // 滚动事件监听（桌面端和移动端通用）
  window.addEventListener("scroll", window.infiniteScrollHandler, {
    passive: true,
  });

  // 窗口大小改变时重新检查
  window.addEventListener("resize", window.infiniteResizeHandler);

  // 初始化显示状态
  toggleLoadingIndicator();
}

// 初始化列表项动画
function initializeListAnimation() {
  const observerOptions = {
    threshold: 0.1,
    rootMargin: "0px 0px -50px 0px",
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("visible");
        observer.unobserve(entry.target);
      }
    });
  }, observerOptions);

  // 为现有列表项添加动画
  document
    .querySelectorAll(".item-compact, .receipt-compact")
    .forEach((item, index) => {
      if (!item.classList.contains("fade-in-up")) {
        item.classList.add("fade-in-up");
        item.style.transitionDelay = `${index * 0.05}s`;
        observer.observe(item);
      }
    });
}

// 页面加载完成后初始化动画
document.addEventListener("DOMContentLoaded", function () {
  // 延迟一点时间以确保DOM完全渲染
  setTimeout(initializeListAnimation, 100);

  // 初始化时区转换
  convertTimestampsToLocal();
});

// 时区转换功能
function convertTimestampsToLocal() {
  // 查找所有带有 data-timestamp 属性的元素
  const timestampElements = document.querySelectorAll("[data-timestamp]");

  timestampElements.forEach((element) => {
    const isoTimestamp = element.getAttribute("data-timestamp");
    if (isoTimestamp) {
      try {
        // 解析ISO时间戳
        let date;

        // 检查是否包含时区信息
        if (isoTimestamp.includes("+") || isoTimestamp.includes("Z")) {
          // 有时区信息，直接解析
          date = new Date(isoTimestamp);
        } else {
          // 没有时区信息，假设是UTC时间
          date = new Date(isoTimestamp + "Z");
        }

        // 检查日期是否有效
        if (!isNaN(date.getTime())) {
          // 检测原始文本格式来确定输出格式
          const originalText = element.textContent.trim();
          const isFullFormat = originalText.match(/^\d{4}-\d{2}-\d{2}/); // 以年份开头的完整格式

          // 转换为用户本地时区的格式
          const format = isFullFormat ? "full" : "short";
          const localTime = formatDateToLocal(date, format);
          element.textContent = localTime;
        }
      } catch (error) {
        console.warn("时间戳转换失败:", isoTimestamp, error);
        // 保持原有显示不变
      }
    }
  });
}

// 格式化日期为本地时区
function formatDateToLocal(date, format = "short") {
  // 从localStorage获取用户设置的时区，或使用浏览器默认时区
  const userTimezone = localStorage.getItem('userTimezone') || Intl.DateTimeFormat().resolvedOptions().timeZone;
  
  try {
    const options = {
      timeZone: userTimezone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    };
    
    const formatter = new Intl.DateTimeFormat('zh-CN', options);
    const parts = formatter.formatToParts(date);
    
    const year = parts.find(part => part.type === 'year').value;
    const month = parts.find(part => part.type === 'month').value;
    const day = parts.find(part => part.type === 'day').value;
    const hours = parts.find(part => part.type === 'hour').value;
    const minutes = parts.find(part => part.type === 'minute').value;
    
    // 根据原始格式决定输出格式
    if (format === "full") {
      return `${year}-${month}-${day} ${hours}:${minutes}`;
    } else {
      return `${month}-${day} ${hours}:${minutes}`;
    }
  } catch (error) {
    console.warn('时区转换失败，使用本地时间:', error);
    // 降级到原来的逻辑
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    const hours = String(date.getHours()).padStart(2, "0");
    const minutes = String(date.getMinutes()).padStart(2, "0");

    if (format === "full") {
      return `${year}-${month}-${day} ${hours}:${minutes}`;
    } else {
      return `${month}-${day} ${hours}:${minutes}`;
    }
  }
}

// 为动态加载的内容提供时区转换
function convertNewTimestamps(container) {
  if (container) {
    const newTimestampElements = container.querySelectorAll("[data-timestamp]");
    newTimestampElements.forEach((element) => {
      const isoTimestamp = element.getAttribute("data-timestamp");
      if (isoTimestamp) {
        try {
          let date;

          // 检查是否包含时区信息
          if (isoTimestamp.includes("+") || isoTimestamp.includes("Z")) {
            // 有时区信息，直接解析
            date = new Date(isoTimestamp);
          } else {
            // 没有时区信息，假设是UTC时间
            date = new Date(isoTimestamp + "Z");
          }

          if (!isNaN(date.getTime())) {
            // 检测原始文本格式
            const originalText = element.textContent.trim();
            const isFullFormat = originalText.match(/^\d{4}-\d{2}-\d{2}/);

            const format = isFullFormat ? "full" : "short";
            const localTime = formatDateToLocal(date, format);
            element.textContent = localTime;
          }
        } catch (error) {
          console.warn("新加载时间戳转换失败:", isoTimestamp, error);
        }
      }
    });
  }
}
