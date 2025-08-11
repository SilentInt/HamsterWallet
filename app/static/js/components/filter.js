// 筛选器组件

import { DOM, HTTP, Throttle, URL } from "../utils/common.js";
import Toast from "./toast.js";

class Filter {
  constructor(element, options = {}) {
    this.element = typeof element === "string" ? DOM.$(element) : element;
    this.options = {
      autoSubmit: true,
      debounceDelay: 800,
      showAnimation: true,
      resetUrl: window.location.pathname,
      ...options,
    };

    this.form = null;
    this.toggleBtn = null;
    this.isExpanded = false;
    this.submitTimeout = null;

    this.init();
  }

  /**
   * 初始化筛选器
   */
  init() {
    if (!this.element) return;

    this.form = DOM.$("form", this.element);
    this.toggleBtn = DOM.$(".filter-toggle-btn", this.element);

    this.bindEvents();
    this.setupValidation();

    if (this.options.showAnimation) {
      this.setupAnimations();
    }
  }

  /**
   * 绑定事件
   */
  bindEvents() {
    // 切换展开/收起
    if (this.toggleBtn) {
      DOM.on(this.toggleBtn, "click", () => this.toggle());
    }

    // 自动提交
    if (this.options.autoSubmit && this.form) {
      const debouncedSubmit = Throttle.debounce(() => {
        this.submit();
      }, this.options.debounceDelay);

      // 绑定输入框事件
      const inputs = DOM.$$('input[type="text"], select', this.form);
      inputs.forEach((input) => {
        DOM.on(input, "input", debouncedSubmit);
        DOM.on(input, "change", debouncedSubmit);
      });
    }

    // 表单提交
    if (this.form) {
      DOM.on(this.form, "submit", (e) => {
        e.preventDefault();
        this.submit();
      });
    }

    // 清除筛选
    const clearBtn = DOM.$(
      ".filter-btn-secondary, .clear-filter-btn",
      this.element
    );
    if (clearBtn) {
      DOM.on(clearBtn, "click", (e) => {
        e.preventDefault();
        this.clear();
      });
    }

    // 快速筛选按钮
    const quickFilterBtns = DOM.$$(".quick-filter-btn", this.element);
    quickFilterBtns.forEach((btn) => {
      DOM.on(btn, "click", () => {
        this.applyQuickFilter(btn);
      });
    });
  }

  /**
   * 设置表单验证
   */
  setupValidation() {
    if (!this.form) return;

    const inputs = DOM.$$("input, select", this.form);
    inputs.forEach((input) => {
      DOM.on(input, "blur", () => {
        this.validateField(input);
      });
    });
  }

  /**
   * 设置动画效果
   */
  setupAnimations() {
    // 筛选按钮动画
    const filterBtns = DOM.$$(
      ".filter-btn-primary, .filter-btn-secondary",
      this.element
    );
    filterBtns.forEach((btn) => {
      DOM.on(btn, "click", () => {
        DOM.addClass(btn, "filter-btn-loading");
        setTimeout(() => {
          DOM.removeClass(btn, "filter-btn-loading");
        }, 500);
      });
    });

    // 清除按钮特效
    const clearBtn = DOM.$(".filter-btn-secondary", this.element);
    if (clearBtn) {
      DOM.on(clearBtn, "mouseenter", () => {
        DOM.addClass(clearBtn, "hover-effect");
      });
      DOM.on(clearBtn, "mouseleave", () => {
        DOM.removeClass(clearBtn, "hover-effect");
      });
    }
  }

  /**
   * 切换展开/收起
   */
  toggle() {
    const collapse = DOM.$(".collapse", this.element);
    if (!collapse) return;

    this.isExpanded = !this.isExpanded;

    if (this.isExpanded) {
      this.expand();
    } else {
      this.collapse();
    }

    // 更新按钮状态
    if (this.toggleBtn) {
      this.toggleBtn.setAttribute("aria-expanded", this.isExpanded);
    }
  }

  /**
   * 展开筛选器
   */
  expand() {
    const collapse = DOM.$(".collapse", this.element);
    DOM.addClass(collapse, "show");

    // 触发事件
    this.trigger("expand");
  }

  /**
   * 收起筛选器
   */
  collapse() {
    const collapse = DOM.$(".collapse", this.element);
    DOM.removeClass(collapse, "show");

    // 触发事件
    this.trigger("collapse");
  }

  /**
   * 提交筛选
   */
  async submit() {
    if (!this.form) return;

    try {
      // 显示加载状态
      const submitBtn = DOM.$(".filter-btn-primary", this.element);
      if (submitBtn) {
        DOM.addClass(submitBtn, "loading");
      }

      // 获取表单数据
      const formData = new FormData(this.form);
      const params = {};

      for (const [key, value] of formData.entries()) {
        if (value.trim() !== "") {
          params[key] = value;
        }
      }

      // 更新URL
      const newUrl = URL.build(this.options.resetUrl, params);

      if (this.options.ajaxSubmit) {
        // AJAX提交
        const response = await HTTP.get(newUrl);
        this.handleAjaxResponse(response);
      } else {
        // 页面跳转
        window.location.href = newUrl;
      }

      // 触发事件
      this.trigger("submit", { params });
    } catch (error) {
      console.error("Filter submit error:", error);
      Toast.error("筛选失败，请重试");
    } finally {
      // 移除加载状态
      const submitBtn = DOM.$(".filter-btn-primary", this.element);
      if (submitBtn) {
        DOM.removeClass(submitBtn, "loading");
      }
    }
  }

  /**
   * 清除筛选
   */
  clear() {
    if (!this.form) return;

    // 重置表单
    this.form.reset();

    // 清除验证状态
    const inputs = DOM.$$("input, select", this.form);
    inputs.forEach((input) => {
      DOM.removeClass(input, "is-valid");
      DOM.removeClass(input, "is-invalid");
    });

    // 跳转到重置URL
    window.location.href = this.options.resetUrl;

    // 触发事件
    this.trigger("clear");
  }

  /**
   * 应用快速筛选
   * @param {Element} btn - 快速筛选按钮
   */
  applyQuickFilter(btn) {
    const filterType = btn.dataset.filter;
    const filterValue = btn.dataset.value;

    if (!filterType || !this.form) return;

    // 设置对应的筛选值
    const input = DOM.$(`[name="${filterType}"]`, this.form);
    if (input) {
      input.value = filterValue;

      // 更新按钮状态
      const quickBtns = DOM.$$(".quick-filter-btn", this.element);
      quickBtns.forEach((b) => DOM.removeClass(b, "active"));
      DOM.addClass(btn, "active");

      // 自动提交
      if (this.options.autoSubmit) {
        this.submit();
      }
    }
  }

  /**
   * 验证字段
   * @param {Element} field - 字段元素
   */
  validateField(field) {
    const value = field.value.trim();
    const isValid = this.isFieldValid(field, value);

    DOM.removeClass(field, "is-valid");
    DOM.removeClass(field, "is-invalid");

    if (value !== "") {
      DOM.addClass(field, isValid ? "is-valid" : "is-invalid");
    }
  }

  /**
   * 检查字段是否有效
   * @param {Element} field - 字段元素
   * @param {string} value - 字段值
   * @returns {boolean}
   */
  isFieldValid(field, value) {
    // 简单验证逻辑
    if (field.type === "email") {
      const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      return emailPattern.test(value);
    }

    if (field.type === "number") {
      return !isNaN(value) && value !== "";
    }

    return true;
  }

  /**
   * 处理AJAX响应
   * @param {string} response - 响应内容
   */
  handleAjaxResponse(response) {
    // 解析HTML响应
    const parser = new DOMParser();
    const doc = parser.parseFromString(response, "text/html");

    // 更新内容区域
    const newContent = doc.querySelector(this.options.updateTarget);
    const currentContent = DOM.$(this.options.updateTarget);

    if (newContent && currentContent) {
      currentContent.innerHTML = newContent.innerHTML;

      // 添加动画
      const items = DOM.$$(".list-item-enter, .card-enter", currentContent);
      items.forEach((item, index) => {
        item.style.animationDelay = `${index * 0.1}s`;
      });
    }
  }

  /**
   * 获取当前筛选参数
   * @returns {Object}
   */
  getParams() {
    if (!this.form) return {};

    const formData = new FormData(this.form);
    const params = {};

    for (const [key, value] of formData.entries()) {
      if (value.trim() !== "") {
        params[key] = value;
      }
    }

    return params;
  }

  /**
   * 设置筛选参数
   * @param {Object} params - 参数对象
   */
  setParams(params) {
    if (!this.form) return;

    Object.entries(params).forEach(([key, value]) => {
      const field = DOM.$(`[name="${key}"]`, this.form);
      if (field) {
        field.value = value;
      }
    });
  }

  /**
   * 重置筛选器
   */
  reset() {
    if (this.form) {
      this.form.reset();
    }

    // 清除验证状态
    const inputs = DOM.$$("input, select", this.form);
    inputs.forEach((input) => {
      DOM.removeClass(input, "is-valid");
      DOM.removeClass(input, "is-invalid");
    });

    // 清除快速筛选按钮状态
    const quickBtns = DOM.$$(".quick-filter-btn", this.element);
    quickBtns.forEach((btn) => DOM.removeClass(btn, "active"));
  }

  /**
   * 触发自定义事件
   * @param {string} eventName - 事件名称
   * @param {Object} detail - 事件详情
   */
  trigger(eventName, detail = {}) {
    const event = new CustomEvent(`filter.${eventName}`, {
      detail: { filter: this, ...detail },
    });
    this.element.dispatchEvent(event);
  }

  /**
   * 销毁筛选器
   */
  destroy() {
    // 清除定时器
    if (this.submitTimeout) {
      clearTimeout(this.submitTimeout);
    }

    // 移除事件监听器
    // 这里可以添加更详细的清理逻辑

    // 触发事件
    this.trigger("destroy");
  }
}

export default Filter;
