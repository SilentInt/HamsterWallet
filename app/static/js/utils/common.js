// 通用工具函数库

/**
 * DOM 操作工具
 */
export const DOM = {
  /**
   * 查询单个元素
   * @param {string} selector - CSS选择器
   * @param {Element} parent - 父元素，默认为document
   * @returns {Element|null}
   */
  $(selector, parent = document) {
    return parent.querySelector(selector);
  },

  /**
   * 查询多个元素
   * @param {string} selector - CSS选择器
   * @param {Element} parent - 父元素，默认为document
   * @returns {NodeList}
   */
  $$(selector, parent = document) {
    return parent.querySelectorAll(selector);
  },

  /**
   * 创建元素
   * @param {string} tag - 标签名
   * @param {Object} options - 选项
   * @returns {Element}
   */
  create(tag, options = {}) {
    const element = document.createElement(tag);

    if (options.className) {
      element.className = options.className;
    }

    if (options.textContent) {
      element.textContent = options.textContent;
    }

    if (options.innerHTML) {
      element.innerHTML = options.innerHTML;
    }

    if (options.attributes) {
      Object.entries(options.attributes).forEach(([key, value]) => {
        element.setAttribute(key, value);
      });
    }

    if (options.style) {
      Object.assign(element.style, options.style);
    }

    return element;
  },

  /**
   * 添加事件监听器
   * @param {Element|string} element - 元素或选择器
   * @param {string} event - 事件类型
   * @param {Function} handler - 事件处理函数
   * @param {Object} options - 选项
   */
  on(element, event, handler, options = {}) {
    if (typeof element === "string") {
      element = this.$(element);
    }
    if (element) {
      element.addEventListener(event, handler, options);
    }
  },

  /**
   * 移除事件监听器
   * @param {Element|string} element - 元素或选择器
   * @param {string} event - 事件类型
   * @param {Function} handler - 事件处理函数
   */
  off(element, event, handler) {
    if (typeof element === "string") {
      element = this.$(element);
    }
    if (element) {
      element.removeEventListener(event, handler);
    }
  },

  /**
   * 委托事件监听
   * @param {Element|string} parent - 父元素或选择器
   * @param {string} selector - 子元素选择器
   * @param {string} event - 事件类型
   * @param {Function} handler - 事件处理函数
   */
  delegate(parent, selector, event, handler) {
    if (typeof parent === "string") {
      parent = this.$(parent);
    }
    if (parent) {
      parent.addEventListener(event, (e) => {
        if (e.target.matches(selector)) {
          handler.call(e.target, e);
        }
      });
    }
  },

  /**
   * 添加CSS类
   * @param {Element|string} element - 元素或选择器
   * @param {string} className - 类名
   */
  addClass(element, className) {
    if (typeof element === "string") {
      element = this.$(element);
    }
    if (element) {
      element.classList.add(className);
    }
  },

  /**
   * 移除CSS类
   * @param {Element|string} element - 元素或选择器
   * @param {string} className - 类名
   */
  removeClass(element, className) {
    if (typeof element === "string") {
      element = this.$(element);
    }
    if (element) {
      element.classList.remove(className);
    }
  },

  /**
   * 切换CSS类
   * @param {Element|string} element - 元素或选择器
   * @param {string} className - 类名
   */
  toggleClass(element, className) {
    if (typeof element === "string") {
      element = this.$(element);
    }
    if (element) {
      element.classList.toggle(className);
    }
  },

  /**
   * 检查是否包含CSS类
   * @param {Element|string} element - 元素或选择器
   * @param {string} className - 类名
   * @returns {boolean}
   */
  hasClass(element, className) {
    if (typeof element === "string") {
      element = this.$(element);
    }
    return element ? element.classList.contains(className) : false;
  },
};

/**
 * 网络请求工具
 */
export const HTTP = {
  /**
   * 通用请求方法
   * @param {string} url - 请求URL
   * @param {Object} options - 请求选项
   * @returns {Promise}
   */
  async request(url, options = {}) {
    const defaultOptions = {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
    };

    const config = { ...defaultOptions, ...options };

    if (config.body && typeof config.body === "object") {
      config.body = JSON.stringify(config.body);
    }

    try {
      const response = await fetch(url, config);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        return await response.json();
      } else {
        return await response.text();
      }
    } catch (error) {
      console.error("Request failed:", error);
      throw error;
    }
  },

  /**
   * GET请求
   * @param {string} url - 请求URL
   * @param {Object} params - 查询参数
   * @returns {Promise}
   */
  get(url, params = {}) {
    if (Object.keys(params).length > 0) {
      const searchParams = new URLSearchParams(params);
      url += (url.includes("?") ? "&" : "?") + searchParams.toString();
    }
    return this.request(url);
  },

  /**
   * POST请求
   * @param {string} url - 请求URL
   * @param {Object} data - 请求数据
   * @returns {Promise}
   */
  post(url, data) {
    return this.request(url, {
      method: "POST",
      body: data,
    });
  },

  /**
   * PUT请求
   * @param {string} url - 请求URL
   * @param {Object} data - 请求数据
   * @returns {Promise}
   */
  put(url, data) {
    return this.request(url, {
      method: "PUT",
      body: data,
    });
  },

  /**
   * DELETE请求
   * @param {string} url - 请求URL
   * @returns {Promise}
   */
  delete(url) {
    return this.request(url, {
      method: "DELETE",
    });
  },
};

/**
 * 防抖和节流工具
 */
export const Throttle = {
  /**
   * 防抖函数
   * @param {Function} func - 要防抖的函数
   * @param {number} delay - 延迟时间（毫秒）
   * @returns {Function}
   */
  debounce(func, delay) {
    let timeoutId;
    return function (...args) {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
  },

  /**
   * 节流函数
   * @param {Function} func - 要节流的函数
   * @param {number} delay - 延迟时间（毫秒）
   * @returns {Function}
   */
  throttle(func, delay) {
    let inThrottle;
    return function (...args) {
      if (!inThrottle) {
        func.apply(this, args);
        inThrottle = true;
        setTimeout(() => (inThrottle = false), delay);
      }
    };
  },
};

/**
 * 本地存储工具
 */
export const Storage = {
  /**
   * 设置本地存储
   * @param {string} key - 键
   * @param {any} value - 值
   */
  set(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.error("LocalStorage set error:", error);
    }
  },

  /**
   * 获取本地存储
   * @param {string} key - 键
   * @param {any} defaultValue - 默认值
   * @returns {any}
   */
  get(key, defaultValue = null) {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue;
    } catch (error) {
      console.error("LocalStorage get error:", error);
      return defaultValue;
    }
  },

  /**
   * 移除本地存储
   * @param {string} key - 键
   */
  remove(key) {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.error("LocalStorage remove error:", error);
    }
  },

  /**
   * 清空本地存储
   */
  clear() {
    try {
      localStorage.clear();
    } catch (error) {
      console.error("LocalStorage clear error:", error);
    }
  },
};

/**
 * 格式化工具
 */
export const Format = {
  /**
   * 格式化货币
   * @param {number} amount - 金额
   * @param {string} currency - 货币符号
   * @returns {string}
   */
  currency(amount, currency = "¥") {
    if (isNaN(amount)) return currency + "0.00";
    return currency + parseFloat(amount).toFixed(2);
  },

  /**
   * 格式化日期
   * @param {Date|string} date - 日期
   * @param {string} format - 格式
   * @returns {string}
   */
  date(date, format = "YYYY-MM-DD") {
    const d = new Date(date);
    if (isNaN(d.getTime())) return "";

    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    const hours = String(d.getHours()).padStart(2, "0");
    const minutes = String(d.getMinutes()).padStart(2, "0");
    const seconds = String(d.getSeconds()).padStart(2, "0");

    return format
      .replace("YYYY", year)
      .replace("MM", month)
      .replace("DD", day)
      .replace("HH", hours)
      .replace("mm", minutes)
      .replace("ss", seconds);
  },

  /**
   * 格式化文件大小
   * @param {number} bytes - 字节数
   * @returns {string}
   */
  fileSize(bytes) {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  },

  /**
   * 截断文本
   * @param {string} text - 文本
   * @param {number} length - 最大长度
   * @param {string} suffix - 后缀
   * @returns {string}
   */
  truncate(text, length = 50, suffix = "...") {
    if (!text || text.length <= length) return text;
    return text.substring(0, length - suffix.length) + suffix;
  },
};

/**
 * 验证工具
 */
export const Validate = {
  /**
   * 验证邮箱
   * @param {string} email - 邮箱地址
   * @returns {boolean}
   */
  email(email) {
    const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return pattern.test(email);
  },

  /**
   * 验证手机号
   * @param {string} phone - 手机号
   * @returns {boolean}
   */
  phone(phone) {
    const pattern = /^1[3-9]\d{9}$/;
    return pattern.test(phone);
  },

  /**
   * 验证数字
   * @param {any} value - 值
   * @returns {boolean}
   */
  number(value) {
    return !isNaN(value) && isFinite(value);
  },

  /**
   * 验证非空
   * @param {any} value - 值
   * @returns {boolean}
   */
  required(value) {
    if (value === null || value === undefined) return false;
    if (typeof value === "string") return value.trim().length > 0;
    return true;
  },

  /**
   * 验证最小长度
   * @param {string} value - 值
   * @param {number} min - 最小长度
   * @returns {boolean}
   */
  minLength(value, min) {
    return value && value.length >= min;
  },

  /**
   * 验证最大长度
   * @param {string} value - 值
   * @param {number} max - 最大长度
   * @returns {boolean}
   */
  maxLength(value, max) {
    return !value || value.length <= max;
  },
};

/**
 * URL 工具
 */
export const URL = {
  /**
   * 获取查询参数
   * @param {string} name - 参数名
   * @returns {string|null}
   */
  getParam(name) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(name);
  },

  /**
   * 设置查询参数
   * @param {string} name - 参数名
   * @param {string} value - 参数值
   */
  setParam(name, value) {
    const url = new URL(window.location.href);
    url.searchParams.set(name, value);
    window.history.replaceState({}, "", url.toString());
  },

  /**
   * 移除查询参数
   * @param {string} name - 参数名
   */
  removeParam(name) {
    const url = new URL(window.location.href);
    url.searchParams.delete(name);
    window.history.replaceState({}, "", url.toString());
  },

  /**
   * 构建URL
   * @param {string} base - 基础URL
   * @param {Object} params - 参数对象
   * @returns {string}
   */
  build(base, params = {}) {
    const url = new URL(base, window.location.origin);
    Object.entries(params).forEach(([key, value]) => {
      if (value !== null && value !== undefined && value !== "") {
        url.searchParams.set(key, value);
      }
    });
    return url.toString();
  },
};
