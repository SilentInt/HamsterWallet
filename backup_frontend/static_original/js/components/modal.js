// 模态框组件

import { DOM } from '../utils/common.js';

class Modal {
  constructor(element) {
    this.element = typeof element === 'string' ? DOM.$(element) : element;
    this.isOpen = false;
    this.backdrop = null;
    this.init();
  }

  /**
   * 初始化模态框
   */
  init() {
    if (!this.element) return;

    // 添加iOS样式类
    DOM.addClass(this.element, 'modal-ios');

    // 绑定关闭事件
    this.bindEvents();
  }

  /**
   * 绑定事件
   */
  bindEvents() {
    // 点击关闭按钮
    const closeButtons = DOM.$$('[data-bs-dismiss="modal"]', this.element);
    closeButtons.forEach(btn => {
      DOM.on(btn, 'click', () => this.hide());
    });

    // 点击背景关闭
    DOM.on(this.element, 'click', (e) => {
      if (e.target === this.element) {
        this.hide();
      }
    });

    // ESC键关闭
    DOM.on(document, 'keydown', (e) => {
      if (e.key === 'Escape' && this.isOpen) {
        this.hide();
      }
    });
  }

  /**
   * 显示模态框
   * @param {Object} options - 选项
   */
  show(options = {}) {
    if (this.isOpen) return;

    this.isOpen = true;
    
    // 创建背景
    this.createBackdrop();
    
    // 显示模态框
    this.element.style.display = 'block';
    DOM.addClass(this.element, 'show');
    
    // 添加动画
    this.element.style.animation = 'fadeInScale 0.3s ease-out';
    
    // 聚焦到模态框
    this.element.focus();
    
    // 锁定背景滚动
    document.body.style.overflow = 'hidden';
    
    // 触发事件
    this.trigger('show');
  }

  /**
   * 隐藏模态框
   */
  hide() {
    if (!this.isOpen) return;

    this.isOpen = false;
    
    // 添加退出动画
    this.element.style.animation = 'fadeOutScale 0.3s ease-out';
    
    setTimeout(() => {
      this.element.style.display = 'none';
      DOM.removeClass(this.element, 'show');
      this.removeBackdrop();
      
      // 恢复背景滚动
      document.body.style.overflow = '';
      
      // 触发事件
      this.trigger('hide');
    }, 300);
  }

  /**
   * 创建背景
   */
  createBackdrop() {
    if (this.backdrop) return;

    this.backdrop = DOM.create('div', {
      className: 'modal-backdrop',
      style: {
        position: 'fixed',
        top: '0',
        left: '0',
        width: '100%',
        height: '100%',
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        zIndex: '1040',
        animation: 'fadeIn 0.3s ease-out'
      }
    });

    document.body.appendChild(this.backdrop);

    // 点击背景关闭
    DOM.on(this.backdrop, 'click', () => this.hide());
  }

  /**
   * 移除背景
   */
  removeBackdrop() {
    if (this.backdrop) {
      this.backdrop.style.animation = 'fadeOut 0.3s ease-out';
      setTimeout(() => {
        if (this.backdrop && this.backdrop.parentNode) {
          this.backdrop.parentNode.removeChild(this.backdrop);
          this.backdrop = null;
        }
      }, 300);
    }
  }

  /**
   * 触发自定义事件
   * @param {string} eventName - 事件名称
   */
  trigger(eventName) {
    const event = new CustomEvent(`modal.${eventName}`, {
      detail: { modal: this }
    });
    this.element.dispatchEvent(event);
  }

  /**
   * 切换显示/隐藏
   */
  toggle() {
    if (this.isOpen) {
      this.hide();
    } else {
      this.show();
    }
  }

  /**
   * 设置标题
   * @param {string} title - 标题
   */
  setTitle(title) {
    const titleElement = DOM.$('.modal-title', this.element);
    if (titleElement) {
      titleElement.textContent = title;
    }
  }

  /**
   * 设置内容
   * @param {string} content - 内容
   */
  setContent(content) {
    const bodyElement = DOM.$('.modal-body', this.element);
    if (bodyElement) {
      if (typeof content === 'string') {
        bodyElement.innerHTML = content;
      } else {
        bodyElement.innerHTML = '';
        bodyElement.appendChild(content);
      }
    }
  }

  /**
   * 设置大小
   * @param {string} size - 大小 (sm, lg, xl)
   */
  setSize(size) {
    const dialog = DOM.$('.modal-dialog', this.element);
    if (dialog) {
      // 移除旧的大小类
      DOM.removeClass(dialog, 'modal-sm');
      DOM.removeClass(dialog, 'modal-lg');
      DOM.removeClass(dialog, 'modal-xl');
      
      if (size && size !== 'md') {
        DOM.addClass(dialog, `modal-${size}`);
      }
    }
  }

  /**
   * 静态方法：创建确认对话框
   * @param {Object} options - 选项
   * @returns {Promise<boolean>}
   */
  static confirm(options = {}) {
    const {
      title = '确认',
      message = '确定要执行此操作吗？',
      confirmText = '确定',
      cancelText = '取消',
      type = 'warning'
    } = options;

    const icons = {
      warning: 'fas fa-exclamation-triangle text-warning',
      danger: 'fas fa-exclamation-circle text-danger',
      info: 'fas fa-info-circle text-info',
      success: 'fas fa-check-circle text-success'
    };

    return new Promise((resolve) => {
      const modalHtml = `
        <div class="modal fade modal-ios" tabindex="-1">
          <div class="modal-dialog modal-sm">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title">${title}</h5>
              </div>
              <div class="modal-body text-center">
                <i class="${icons[type]} mb-3" style="font-size: 3rem;"></i>
                <p class="mb-0">${message}</p>
              </div>
              <div class="modal-footer">
                <button type="button" class="btn-ios btn-secondary" data-action="cancel">${cancelText}</button>
                <button type="button" class="btn-ios btn-danger" data-action="confirm">${confirmText}</button>
              </div>
            </div>
          </div>
        </div>
      `;

      const modalElement = DOM.create('div', { innerHTML: modalHtml });
      const modal = modalElement.firstElementChild;
      document.body.appendChild(modal);

      const modalInstance = new Modal(modal);

      // 绑定按钮事件
      DOM.on(modal, 'click', (e) => {
        const action = e.target.dataset.action;
        if (action) {
          modalInstance.hide();
          resolve(action === 'confirm');
        }
      });

      // 清理
      DOM.on(modal, 'modal.hide', () => {
        setTimeout(() => {
          if (modal.parentNode) {
            modal.parentNode.removeChild(modal);
          }
        }, 300);
      });

      modalInstance.show();
    });
  }

  /**
   * 静态方法：创建提示对话框
   * @param {Object} options - 选项
   */
  static alert(options = {}) {
    const {
      title = '提示',
      message = '',
      buttonText = '确定',
      type = 'info'
    } = options;

    const icons = {
      warning: 'fas fa-exclamation-triangle text-warning',
      danger: 'fas fa-exclamation-circle text-danger',
      info: 'fas fa-info-circle text-info',
      success: 'fas fa-check-circle text-success'
    };

    return new Promise((resolve) => {
      const modalHtml = `
        <div class="modal fade modal-ios" tabindex="-1">
          <div class="modal-dialog modal-sm">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title">${title}</h5>
              </div>
              <div class="modal-body text-center">
                <i class="${icons[type]} mb-3" style="font-size: 3rem;"></i>
                <p class="mb-0">${message}</p>
              </div>
              <div class="modal-footer">
                <button type="button" class="btn-ios btn-primary" data-action="ok">${buttonText}</button>
              </div>
            </div>
          </div>
        </div>
      `;

      const modalElement = DOM.create('div', { innerHTML: modalHtml });
      const modal = modalElement.firstElementChild;
      document.body.appendChild(modal);

      const modalInstance = new Modal(modal);

      // 绑定按钮事件
      DOM.on(modal, 'click', (e) => {
        if (e.target.dataset.action === 'ok') {
          modalInstance.hide();
          resolve(true);
        }
      });

      // 清理
      DOM.on(modal, 'modal.hide', () => {
        setTimeout(() => {
          if (modal.parentNode) {
            modal.parentNode.removeChild(modal);
          }
        }, 300);
      });

      modalInstance.show();
    });
  }
}

// 添加动画CSS
const style = DOM.create('style', {
  textContent: `
    @keyframes fadeInScale {
      from {
        opacity: 0;
        transform: scale(0.8);
      }
      to {
        opacity: 1;
        transform: scale(1);
      }
    }
    
    @keyframes fadeOutScale {
      from {
        opacity: 1;
        transform: scale(1);
      }
      to {
        opacity: 0;
        transform: scale(0.8);
      }
    }
    
    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }
    
    @keyframes fadeOut {
      from { opacity: 1; }
      to { opacity: 0; }
    }
  `
});
document.head.appendChild(style);

export default Modal;
