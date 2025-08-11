// 主应用脚本 - 组合所有组件和功能

import { DOM, HTTP, Format, Validate } from "./utils/common.js";
import Toast from "./components/toast.js";
import Modal from "./components/modal.js";
import Filter from "./components/filter.js";
import ImageViewer from "./components/image-viewer.js";
import ListLoader from "./components/list-loader.js";

class HamsterWalletApp {
  constructor() {
    this.components = {};
    this.init();
  }

  /**
   * 初始化应用
   */
  init() {
    this.setupGlobalErrorHandling();
    this.initializeComponents();
    this.bindGlobalEvents();
    this.setupAnimations();

    // 兼容旧版本的全局函数
    this.setupLegacyFunctions();

    console.log("HamsterWallet App initialized");
  }

  /**
   * 设置全局错误处理
   */
  setupGlobalErrorHandling() {
    // AJAX错误处理
    DOM.on(document, "ajaxError", (event, xhr, settings, error) => {
      if (xhr.status === 0) return; // 忽略取消的请求

      let message = "网络错误，请重试";
      if (xhr.responseJSON && xhr.responseJSON.message) {
        message = xhr.responseJSON.message;
      } else if (xhr.status === 404) {
        message = "请求的资源不存在";
      } else if (xhr.status === 500) {
        message = "服务器内部错误";
      }

      Toast.error(message);
    });

    // 全局错误捕获
    window.addEventListener("error", (event) => {
      console.error("Global error:", event.error);
      // 这里可以添加错误上报逻辑
    });

    // Promise错误捕获
    window.addEventListener("unhandledrejection", (event) => {
      console.error("Unhandled promise rejection:", event.reason);
      event.preventDefault();
    });
  }

  /**
   * 初始化组件
   */
  initializeComponents() {
    // 初始化筛选器
    const filterElements = DOM.$$(".filter-section");
    filterElements.forEach((element) => {
      const filter = new Filter(element, {
        autoSubmit: true,
        debounceDelay: 800,
      });
      this.components.filters = this.components.filters || [];
      this.components.filters.push(filter);
    });

    // 初始化列表加载器
    const listLoaders = DOM.$$("[data-list-loader]");
    listLoaders.forEach((element) => {
      const options = this.parseDataAttributes(element, "data-list-");
      const loader = new ListLoader(element, options);
      this.components.loaders = this.components.loaders || [];
      this.components.loaders.push(loader);
    });

    // 初始化模态框
    const modals = DOM.$$(".modal");
    modals.forEach((element) => {
      const modal = new Modal(element);
      this.components.modals = this.components.modals || [];
      this.components.modals.push(modal);
    });

    // 初始化图片查看器
    this.components.imageViewer = new ImageViewer();

    // 初始化Toast
    this.components.toast = Toast;
  }

  /**
   * 解析数据属性
   * @param {Element} element - 元素
   * @param {string} prefix - 属性前缀
   * @returns {Object}
   */
  parseDataAttributes(element, prefix) {
    const options = {};
    const attrs = element.attributes;

    for (let i = 0; i < attrs.length; i++) {
      const attr = attrs[i];
      if (attr.name.startsWith(prefix)) {
        const key = attr.name
          .slice(prefix.length)
          .replace(/-([a-z])/g, (match, letter) => letter.toUpperCase());
        let value = attr.value;

        // 尝试解析为数字或布尔值
        if (value === "true") value = true;
        else if (value === "false") value = false;
        else if (!isNaN(value) && value !== "") value = Number(value);

        options[key] = value;
      }
    }

    return options;
  }

  /**
   * 绑定全局事件
   */
  bindGlobalEvents() {
    // 表单验证
    this.setupFormValidation();

    // 确认对话框
    this.setupConfirmations();

    // 图片预览
    this.setupImagePreviews();

    // 数字格式化
    this.setupNumberFormatting();

    // 自动保存
    this.setupAutoSave();
  }

  /**
   * 设置表单验证
   */
  setupFormValidation() {
    DOM.delegate(document, "form[data-validate]", "submit", (e) => {
      const form = e.target;
      if (!this.validateForm(form)) {
        e.preventDefault();
        return false;
      }
    });

    // 实时验证
    DOM.delegate(
      document,
      "input[data-validate], select[data-validate]",
      "blur",
      (e) => {
        this.validateField(e.target);
      }
    );
  }

  /**
   * 验证表单
   * @param {HTMLFormElement} form - 表单元素
   * @returns {boolean}
   */
  validateForm(form) {
    const fields = DOM.$$("input[data-validate], select[data-validate]", form);
    let isValid = true;

    fields.forEach((field) => {
      if (!this.validateField(field)) {
        isValid = false;
      }
    });

    return isValid;
  }

  /**
   * 验证字段
   * @param {HTMLInputElement} field - 字段元素
   * @returns {boolean}
   */
  validateField(field) {
    const rules = field.dataset.validate.split("|");
    const value = field.value.trim();
    let isValid = true;
    let message = "";

    for (const rule of rules) {
      const [ruleName, ruleValue] = rule.split(":");

      switch (ruleName) {
        case "required":
          if (!Validate.required(value)) {
            isValid = false;
            message = "此字段为必填项";
          }
          break;
        case "email":
          if (value && !Validate.email(value)) {
            isValid = false;
            message = "请输入有效的邮箱地址";
          }
          break;
        case "min":
          if (value && !Validate.minLength(value, parseInt(ruleValue))) {
            isValid = false;
            message = `最少需要${ruleValue}个字符`;
          }
          break;
        case "max":
          if (value && !Validate.maxLength(value, parseInt(ruleValue))) {
            isValid = false;
            message = `最多允许${ruleValue}个字符`;
          }
          break;
        case "number":
          if (value && !Validate.number(value)) {
            isValid = false;
            message = "请输入有效的数字";
          }
          break;
      }

      if (!isValid) break;
    }

    // 更新UI
    DOM.removeClass(field, "is-valid");
    DOM.removeClass(field, "is-invalid");

    if (value !== "") {
      DOM.addClass(field, isValid ? "is-valid" : "is-invalid");
    }

    // 显示错误信息
    this.showFieldError(field, isValid ? "" : message);

    return isValid;
  }

  /**
   * 显示字段错误
   * @param {HTMLElement} field - 字段元素
   * @param {string} message - 错误信息
   */
  showFieldError(field, message) {
    let errorElement = field.parentNode.querySelector(".invalid-feedback");

    if (!errorElement) {
      errorElement = DOM.create("div", { className: "invalid-feedback" });
      field.parentNode.appendChild(errorElement);
    }

    errorElement.textContent = message;
  }

  /**
   * 设置确认对话框
   */
  setupConfirmations() {
    DOM.delegate(document, "[data-confirm]", "click", async (e) => {
      e.preventDefault();

      const element = e.target.closest("[data-confirm]");
      const message = element.dataset.confirm;
      const type = element.dataset.confirmType || "warning";

      const confirmed = await Modal.confirm({
        message: message,
        type: type,
      });

      if (confirmed) {
        // 执行原始操作
        if (element.href) {
          window.location.href = element.href;
        } else if (element.onclick) {
          element.onclick();
        } else if (element.type === "submit") {
          element.closest("form").submit();
        }
      }
    });
  }

  /**
   * 设置图片预览
   */
  setupImagePreviews() {
    // 自动为图片添加预览功能
    DOM.delegate(document, "img[src]:not([data-no-preview])", "click", (e) => {
      const img = e.target;
      if (img.dataset.preview !== "false") {
        this.components.imageViewer.show(img.src, img.alt || "图片预览");
      }
    });
  }

  /**
   * 设置数字格式化
   */
  setupNumberFormatting() {
    // 货币格式化
    DOM.delegate(document, ".format-currency", "blur", (e) => {
      const input = e.target;
      const value = parseFloat(input.value);
      if (!isNaN(value)) {
        input.value = Format.currency(value, "");
        DOM.addClass(input, "text-success");
      }
    });

    // 数字格式化
    DOM.delegate(document, ".format-number", "input", (e) => {
      const input = e.target;
      const value = input.value.replace(/[^\d.-]/g, "");
      if (value !== input.value) {
        input.value = value;
      }
    });
  }

  /**
   * 设置自动保存
   */
  setupAutoSave() {
    const autoSaveForms = DOM.$$("form[data-autosave]");

    autoSaveForms.forEach((form) => {
      const interval = parseInt(form.dataset.autosave) || 30000; // 默认30秒
      const debouncedSave = Throttle.debounce(() => {
        this.autoSaveForm(form);
      }, interval);

      DOM.on(form, "input", debouncedSave);
      DOM.on(form, "change", debouncedSave);
    });
  }

  /**
   * 自动保存表单
   * @param {HTMLFormElement} form - 表单元素
   */
  async autoSaveForm(form) {
    try {
      const formData = new FormData(form);
      const saveUrl = form.dataset.autosaveUrl || form.action;

      await HTTP.post(saveUrl, formData);

      // 显示保存成功提示
      const indicator = DOM.$(".autosave-indicator", form);
      if (indicator) {
        indicator.textContent = "已自动保存";
        indicator.className = "autosave-indicator text-success";
        setTimeout(() => {
          indicator.textContent = "";
        }, 2000);
      }
    } catch (error) {
      console.error("Auto save failed:", error);

      const indicator = DOM.$(".autosave-indicator", form);
      if (indicator) {
        indicator.textContent = "保存失败";
        indicator.className = "autosave-indicator text-danger";
      }
    }
  }

  /**
   * 设置动画效果
   */
  setupAnimations() {
    // 页面加载动画
    DOM.addClass(document.body, "page-enter");

    // 滚动显示动画
    this.setupScrollAnimations();

    // 点击反馈动画
    this.setupClickFeedback();
  }

  /**
   * 设置滚动动画
   */
  setupScrollAnimations() {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            DOM.addClass(entry.target, "revealed");
          }
        });
      },
      {
        threshold: 0.1,
        rootMargin: "0px 0px -50px 0px",
      }
    );

    // 观察需要动画的元素
    const animatedElements = DOM.$$(
      ".reveal-on-scroll, .card-enter, .list-item-enter"
    );
    animatedElements.forEach((el) => observer.observe(el));
  }

  /**
   * 设置点击反馈动画
   */
  setupClickFeedback() {
    DOM.delegate(document, "button, .btn, .card", "mousedown", (e) => {
      const element = e.target.closest("button, .btn, .card");
      DOM.addClass(element, "click-feedback");

      setTimeout(() => {
        DOM.removeClass(element, "click-feedback");
      }, 150);
    });
  }

  /**
   * 设置兼容旧版本的全局函数
   */
  setupLegacyFunctions() {
    // Toast函数
    window.showToast = (message, type = "info") => {
      Toast.show(message, type);
    };

    // 确认对话框
    window.iosConfirm = (message, title = "确认") => {
      return Modal.confirm({ title, message });
    };

    // 图片查看器
    window.showImageModal = (imageUrl, title) => {
      this.components.imageViewer.show(imageUrl, title);
    };

    // 筛选器相关
    window.clearFilters = () => {
      if (this.components.filters) {
        this.components.filters.forEach((filter) => filter.clear());
      }
    };
  }

  /**
   * 获取组件实例
   * @param {string} name - 组件名称
   * @returns {Object|null}
   */
  getComponent(name) {
    return this.components[name] || null;
  }

  /**
   * 销毁应用
   */
  destroy() {
    // 销毁所有组件
    Object.values(this.components).forEach((component) => {
      if (component && typeof component.destroy === "function") {
        component.destroy();
      }
    });

    this.components = {};
  }
}

// 自动初始化应用
document.addEventListener("DOMContentLoaded", () => {
  window.HamsterWalletApp = new HamsterWalletApp();
});

export default HamsterWalletApp;
