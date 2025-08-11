// 列表加载器组件 - 处理分页和无限滚动

import { DOM, HTTP, Throttle } from '../utils/common.js';
import Toast from './toast.js';

class ListLoader {
  constructor(element, options = {}) {
    this.element = typeof element === 'string' ? DOM.$(element) : element;
    this.options = {
      // 加载模式：'pagination' | 'infinite' | 'loadmore'
      mode: 'loadmore',
      // API端点
      endpoint: window.location.pathname,
      // 每页数量
      pageSize: 20,
      // 当前页
      currentPage: 1,
      // 总页数
      totalPages: 1,
      // 加载按钮选择器
      loadMoreSelector: '#loadMoreBtn',
      // 列表容器选择器
      listSelector: '.list-container',
      // 加载指示器选择器
      loadingSelector: '.loading-indicator',
      // 无限滚动阈值（距离底部多少像素开始加载）
      threshold: 200,
      // 节流延迟
      throttleDelay: 300,
      // 筛选参数
      filterParams: {},
      // 是否启用移动端无限滚动
      enableMobileInfinite: true,
      ...options
    };

    this.isLoading = false;
    this.hasMore = true;
    this.loadMoreBtn = null;
    this.listContainer = null;
    this.loadingIndicator = null;

    this.init();
  }

  /**
   * 初始化列表加载器
   */
  init() {
    this.loadMoreBtn = DOM.$(this.options.loadMoreSelector);
    this.listContainer = DOM.$(this.options.listSelector);
    this.loadingIndicator = DOM.$(this.options.loadingSelector);

    // 从按钮获取初始参数
    if (this.loadMoreBtn) {
      this.updateParamsFromButton();
    }

    this.bindEvents();
    this.setupMode();
  }

  /**
   * 从加载按钮获取参数
   */
  updateParamsFromButton() {
    if (!this.loadMoreBtn) return;

    const dataset = this.loadMoreBtn.dataset;
    this.options.currentPage = parseInt(dataset.nextPage) - 1 || 1;
    this.options.totalPages = parseInt(dataset.totalPages) || 1;
    
    // 更新筛选参数
    this.options.filterParams = {
      search: dataset.search || '',
      is_special_price: dataset.isSpecialPrice || '',
      category_filter: dataset.categoryFilter || '',
      sort_by: dataset.sortBy || 'created_at',
      order: dataset.order || 'desc',
      status: dataset.status || '',
      ...this.options.filterParams
    };

    this.hasMore = this.options.currentPage < this.options.totalPages;
  }

  /**
   * 设置加载模式
   */
  setupMode() {
    if (this.options.mode === 'infinite') {
      this.setupInfiniteScroll();
    } else if (this.options.mode === 'loadmore') {
      this.setupLoadMore();
    }
    
    // 移动端自动切换到无限滚动
    if (this.options.enableMobileInfinite && this.isMobile()) {
      this.setupInfiniteScroll();
    }
  }

  /**
   * 绑定事件
   */
  bindEvents() {
    // 加载更多按钮
    if (this.loadMoreBtn) {
      DOM.on(this.loadMoreBtn, 'click', () => {
        this.loadNext();
      });
    }

    // 监听筛选器更新
    DOM.on(document, 'filter.submit', (e) => {
      this.reset();
      this.options.filterParams = e.detail.params || {};
    });
  }

  /**
   * 设置无限滚动
   */
  setupInfiniteScroll() {
    const throttledScroll = Throttle.throttle(() => {
      if (this.shouldLoadMore()) {
        this.loadNext();
      }
    }, this.options.throttleDelay);

    DOM.on(window, 'scroll', throttledScroll);
    
    // 隐藏加载更多按钮
    if (this.loadMoreBtn) {
      this.loadMoreBtn.style.display = 'none';
    }
  }

  /**
   * 设置点击加载更多
   */
  setupLoadMore() {
    // 显示加载更多按钮
    if (this.loadMoreBtn && this.hasMore) {
      this.loadMoreBtn.style.display = 'block';
    }
  }

  /**
   * 检查是否应该加载更多
   * @returns {boolean}
   */
  shouldLoadMore() {
    if (this.isLoading || !this.hasMore) return false;

    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const windowHeight = window.innerHeight;
    const documentHeight = document.documentElement.scrollHeight;

    return scrollTop + windowHeight >= documentHeight - this.options.threshold;
  }

  /**
   * 加载下一页
   */
  async loadNext() {
    if (this.isLoading || !this.hasMore) return;

    this.isLoading = true;
    this.showLoading();

    try {
      const nextPage = this.options.currentPage + 1;
      const params = {
        page: nextPage,
        ...this.options.filterParams
      };

      const response = await HTTP.get(this.options.endpoint, params);
      
      if (typeof response === 'string') {
        // HTML响应
        this.handleHtmlResponse(response);
      } else {
        // JSON响应
        this.handleJsonResponse(response);
      }

      this.options.currentPage = nextPage;
      this.hasMore = nextPage < this.options.totalPages;
      
      // 更新按钮状态
      this.updateLoadMoreButton();
      
      // 触发事件
      this.trigger('load', { page: nextPage, hasMore: this.hasMore });

    } catch (error) {
      console.error('Load more error:', error);
      Toast.error('加载失败，请重试');
      this.trigger('error', { error });
    } finally {
      this.isLoading = false;
      this.hideLoading();
    }
  }

  /**
   * 处理HTML响应
   * @param {string} html - HTML内容
   */
  handleHtmlResponse(html) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    
    // 提取新的列表项
    const newItems = this.extractListItems(doc);
    
    if (newItems.length > 0) {
      this.appendItems(newItems);
    }
  }

  /**
   * 处理JSON响应
   * @param {Object} data - JSON数据
   */
  handleJsonResponse(data) {
    if (data.items && Array.isArray(data.items)) {
      const htmlItems = data.items.map(item => this.renderItem(item));
      this.appendItems(htmlItems);
    }
    
    if (data.pagination) {
      this.options.totalPages = data.pagination.pages;
      this.hasMore = data.pagination.page < data.pagination.pages;
    }
  }

  /**
   * 从文档中提取列表项
   * @param {Document} doc - 解析的文档
   * @returns {Array<Element>}
   */
  extractListItems(doc) {
    // 尝试多种选择器
    const selectors = [
      '.item-card',
      '.receipt-card',
      '.list-item',
      'tbody tr',
      '.card'
    ];

    for (const selector of selectors) {
      const items = doc.querySelectorAll(selector);
      if (items.length > 0) {
        return Array.from(items);
      }
    }

    return [];
  }

  /**
   * 添加项目到列表
   * @param {Array<Element|string>} items - 项目数组
   */
  appendItems(items) {
    if (!this.listContainer) return;

    items.forEach((item, index) => {
      let element;
      
      if (typeof item === 'string') {
        element = DOM.create('div', { innerHTML: item }).firstElementChild;
      } else {
        element = item.cloneNode(true);
      }

      // 添加进入动画
      element.style.opacity = '0';
      element.style.transform = 'translateY(20px)';
      
      this.listContainer.appendChild(element);

      // 延迟显示动画
      setTimeout(() => {
        element.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
        element.style.opacity = '1';
        element.style.transform = 'translateY(0)';
      }, index * 50);
    });
  }

  /**
   * 渲染单个项目（用于JSON数据）
   * @param {Object} item - 项目数据
   * @returns {string}
   */
  renderItem(item) {
    // 这里需要根据具体的数据结构来实现
    // 可以使用模板字符串或模板引擎
    return `<div class="item-card">${JSON.stringify(item)}</div>`;
  }

  /**
   * 显示加载状态
   */
  showLoading() {
    if (this.loadingIndicator) {
      this.loadingIndicator.style.display = 'block';
      this.loadingIndicator.innerHTML = `
        <div class="d-flex align-items-center justify-content-center p-3">
          <div class="loading-spinner me-2"></div>
          <span class="text-muted">正在加载...</span>
        </div>
      `;
    }

    if (this.loadMoreBtn) {
      DOM.addClass(this.loadMoreBtn, 'loading');
    }
  }

  /**
   * 隐藏加载状态
   */
  hideLoading() {
    if (this.loadingIndicator) {
      this.loadingIndicator.style.display = 'none';
    }

    if (this.loadMoreBtn) {
      DOM.removeClass(this.loadMoreBtn, 'loading');
    }
  }

  /**
   * 更新加载更多按钮
   */
  updateLoadMoreButton() {
    if (!this.loadMoreBtn) return;

    if (this.hasMore) {
      this.loadMoreBtn.style.display = 'block';
      this.loadMoreBtn.disabled = false;
      
      // 更新按钮数据
      this.loadMoreBtn.dataset.nextPage = this.options.currentPage + 1;
    } else {
      this.loadMoreBtn.style.display = 'none';
      
      // 显示加载完成提示
      if (this.loadingIndicator) {
        this.loadingIndicator.style.display = 'block';
        this.loadingIndicator.innerHTML = `
          <div class="text-center p-3">
            <span class="text-muted">已加载全部内容</span>
          </div>
        `;
      }
    }
  }

  /**
   * 重置加载器
   */
  reset() {
    this.options.currentPage = 1;
    this.hasMore = true;
    this.isLoading = false;
    
    // 清空列表
    if (this.listContainer) {
      this.listContainer.innerHTML = '';
    }
    
    // 重置按钮
    this.updateLoadMoreButton();
    this.hideLoading();
  }

  /**
   * 更新筛选参数
   * @param {Object} params - 参数对象
   */
  updateParams(params) {
    this.options.filterParams = { ...this.options.filterParams, ...params };
  }

  /**
   * 检查是否为移动设备
   * @returns {boolean}
   */
  isMobile() {
    return window.innerWidth <= 768;
  }

  /**
   * 触发自定义事件
   * @param {string} eventName - 事件名称
   * @param {Object} detail - 事件详情
   */
  trigger(eventName, detail = {}) {
    const event = new CustomEvent(`listloader.${eventName}`, {
      detail: { loader: this, ...detail }
    });
    this.element.dispatchEvent(event);
  }

  /**
   * 销毁加载器
   */
  destroy() {
    // 移除事件监听器
    DOM.off(window, 'scroll');
    
    if (this.loadMoreBtn) {
      DOM.off(this.loadMoreBtn, 'click');
    }
    
    this.trigger('destroy');
  }
}

export default ListLoader;
