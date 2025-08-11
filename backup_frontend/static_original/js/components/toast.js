// Toast 通知组件

import { DOM } from '../utils/common.js';

class Toast {
  constructor() {
    this.container = null;
    this.init();
  }

  /**
   * 初始化Toast容器
   */
  init() {
    this.container = DOM.$('#toastContainer');
    if (!this.container) {
      this.container = DOM.create('div', {
        attributes: { id: 'toastContainer' },
        style: {
          position: 'fixed',
          top: '20px',
          right: '20px',
          zIndex: '9999',
          maxWidth: '400px'
        }
      });
      document.body.appendChild(this.container);
    }
  }

  /**
   * 显示Toast通知
   * @param {string} message - 消息内容
   * @param {string} type - 消息类型 (success, error, warning, info)
   * @param {number} duration - 显示持续时间（毫秒）
   * @param {Object} options - 额外选项
   */
  show(message, type = 'info', duration = 3000, options = {}) {
    const toastId = 'toast-' + Date.now();
    
    const icons = {
      success: 'fas fa-check-circle',
      error: 'fas fa-exclamation-circle',
      warning: 'fas fa-exclamation-triangle',
      info: 'fas fa-info-circle'
    };

    const colors = {
      success: 'var(--ios-green)',
      error: 'var(--ios-red)',
      warning: 'var(--ios-orange)',
      info: 'var(--ios-blue)'
    };

    const toast = DOM.create('div', {
      className: 'toast-ios',
      attributes: { id: toastId },
      innerHTML: `
        <div style="display: flex; align-items: center; padding: 12px 16px;">
          <i class="${icons[type]} me-2" style="color: ${colors[type]}; font-size: 1.2rem;"></i>
          <span style="font-weight: 500; flex: 1;">${message}</span>
          ${options.closable !== false ? '<button class="toast-close" style="background: none; border: none; color: var(--ios-gray-5); font-size: 1.2rem; cursor: pointer; margin-left: 12px;">&times;</button>' : ''}
        </div>
      `,
      style: {
        marginBottom: '8px',
        animation: 'slideInRight 0.3s ease-out'
      }
    });

    // 添加关闭按钮事件
    if (options.closable !== false) {
      const closeBtn = DOM.$('.toast-close', toast);
      DOM.on(closeBtn, 'click', () => {
        this.hide(toastId);
      });
    }

    this.container.appendChild(toast);

    // 自动隐藏
    if (duration > 0) {
      setTimeout(() => {
        this.hide(toastId);
      }, duration);
    }

    return toastId;
  }

  /**
   * 隐藏Toast
   * @param {string} toastId - Toast ID
   */
  hide(toastId) {
    const toast = DOM.$('#' + toastId);
    if (toast) {
      toast.style.animation = 'slideOutRight 0.3s ease-out';
      setTimeout(() => {
        if (toast.parentNode) {
          toast.parentNode.removeChild(toast);
        }
      }, 300);
    }
  }

  /**
   * 成功消息
   * @param {string} message - 消息内容
   * @param {Object} options - 选项
   */
  success(message, options = {}) {
    return this.show(message, 'success', 3000, options);
  }

  /**
   * 错误消息
   * @param {string} message - 消息内容
   * @param {Object} options - 选项
   */
  error(message, options = {}) {
    return this.show(message, 'error', 5000, options);
  }

  /**
   * 警告消息
   * @param {string} message - 消息内容
   * @param {Object} options - 选项
   */
  warning(message, options = {}) {
    return this.show(message, 'warning', 4000, options);
  }

  /**
   * 信息消息
   * @param {string} message - 消息内容
   * @param {Object} options - 选项
   */
  info(message, options = {}) {
    return this.show(message, 'info', 3000, options);
  }

  /**
   * 清除所有Toast
   */
  clear() {
    if (this.container) {
      this.container.innerHTML = '';
    }
  }
}

// 添加滑出动画CSS
const style = DOM.create('style', {
  textContent: `
    @keyframes slideOutRight {
      from {
        opacity: 1;
        transform: translateX(0);
      }
      to {
        opacity: 0;
        transform: translateX(100%);
      }
    }
  `
});
document.head.appendChild(style);

// 导出单例实例
export default new Toast();
