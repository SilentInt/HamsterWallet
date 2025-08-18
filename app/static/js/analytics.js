// 数据报告页面JavaScript

class AnalyticsPage {
  constructor() {
    this.trendChart = null;
    this.categoryChart = null;
    this.currentCategoryLevel = 1;
    this.currentParentCategory = null;
    this.categoryStack = [];
    this.hiddenCategories = new Set(); // 添加隐藏分类集合

    this.init();
  }

  init() {
    this.setupEventListeners();
    this.initDateFilter();
    this.loadInitialData();
  }

  setupEventListeners() {
    // 全部时间筛选
    document.getElementById("allTimeFilter").addEventListener("click", () => {
      this.setAllTimeFilter();
    });

    // 近7天筛选
    document.getElementById("last7DaysFilter").addEventListener("click", () => {
      this.setLast7DaysFilter();
    });

    // 近一月筛选
    document.getElementById("resetFilter").addEventListener("click", () => {
      this.resetDateFilter();
    });

    // 近3月筛选
    document
      .getElementById("last3MonthsFilter")
      .addEventListener("click", () => {
        this.setLast3MonthsFilter();
      });

    // 日期变化自动更新
    document.getElementById("startDate").addEventListener("change", () => {
      this.applyDateFilter();
    });

    document.getElementById("endDate").addEventListener("change", () => {
      this.applyDateFilter();
    });
  }

  initDateFilter() {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setMonth(endDate.getMonth() - 1);

    document.getElementById("startDate").value = this.formatDate(startDate);
    document.getElementById("endDate").value = this.formatDate(endDate);
  }

  formatDate(date) {
    return date.toISOString().split("T")[0];
  }

  getDateFilter() {
    const startDate = document.getElementById("startDate").value;
    const endDate = document.getElementById("endDate").value;

    const params = new URLSearchParams();
    if (startDate) params.append("start_date", startDate);
    if (endDate) params.append("end_date", endDate);

    return params.toString();
  }

  setAllTimeFilter() {
    // 清空日期输入框以获取全部数据
    document.getElementById("startDate").value = "";
    document.getElementById("endDate").value = "";
    this.loadInitialData();
  }

  applyDateFilter() {
    this.loadInitialData();
  }

  resetDateFilter() {
    this.initDateFilter();
    this.loadInitialData();
  }

  setLast7DaysFilter() {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(endDate.getDate() - 7);

    document.getElementById("startDate").value = this.formatDate(startDate);
    document.getElementById("endDate").value = this.formatDate(endDate);
    this.loadInitialData();
  }

  setLast3MonthsFilter() {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setMonth(endDate.getMonth() - 3);

    document.getElementById("startDate").value = this.formatDate(startDate);
    document.getElementById("endDate").value = this.formatDate(endDate);
    this.loadInitialData();
  }

  async loadInitialData() {
    try {
      await Promise.all([
        this.loadDashboardData(),
        this.loadTrendData(),
        this.loadCategoryData(),
      ]);
    } catch (error) {
      console.error("加载数据失败:", error);
      this.showError("加载数据失败，请刷新页面重试");
    }
  }

  async loadDashboardData() {
    try {
      const params = this.getDateFilter();
      const response = await fetch(`/api/analytics/dashboard?${params}`);
      const data = await response.json();

      if (response.ok) {
        this.updateDashboard(data);
      } else {
        throw new Error(data.message || "获取仪表盘数据失败");
      }
    } catch (error) {
      console.error("加载仪表盘数据失败:", error);
      throw error;
    }
  }

  updateDashboard(data) {
    // 总支出
    document.getElementById(
      "totalSpending"
    ).textContent = `¥${data.total_spending.jpy.toLocaleString()}`;
    document.getElementById(
      "totalSpendingCny"
    ).textContent = `￥${data.total_spending.cny.toLocaleString()}`;

    // 小票数量
    document.getElementById("receiptCount").textContent =
      data.receipt_count.toLocaleString();

    // 商品数量
    document.getElementById("itemCount").textContent =
      data.item_count.toLocaleString();

    // 时间跨度
    document.getElementById("usageDays").textContent = `${data.time_span}天`;

    // 日均开销
    document.getElementById(
      "dailyAverage"
    ).textContent = `¥${data.daily_average.jpy.toLocaleString()}`;
    document.getElementById(
      "dailyAverageCny"
    ).textContent = `￥${data.daily_average.cny.toLocaleString()}`;

    // 折扣商品占比
    document.getElementById(
      "discountRatio"
    ).textContent = `${data.discount_ratio}%`;

    // 添加更新动画
    this.addUpdateAnimation();
  }

  addUpdateAnimation() {
    const values = document.querySelectorAll(".metric-value");
    values.forEach((value) => {
      value.classList.add("updating");
      setTimeout(() => {
        value.classList.remove("updating");
      }, 300);
    });
  }

  async loadTrendData() {
    try {
      const params = this.getDateFilter();
      const response = await fetch(`/api/analytics/trend?${params}`);
      const data = await response.json();

      if (response.ok) {
        this.updateTrendChart(data.data);
      } else {
        throw new Error(data.message || "获取趋势数据失败");
      }
    } catch (error) {
      console.error("加载趋势数据失败:", error);
      throw error;
    }
  }

  updateTrendChart(trendData) {
    const ctx = document.getElementById("trendChart").getContext("2d");

    if (this.trendChart) {
      this.trendChart.destroy();
    }

    const labels = trendData.map((item) => item.date);
    const jpyData = trendData.map((item) => item.spending.jpy);
    const cnyData = trendData.map((item) => item.spending.cny);

    this.trendChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: "支出 (日元)",
            data: jpyData,
            borderColor: "#3498db",
            backgroundColor: "rgba(52, 152, 219, 0.1)",
            tension: 0.4,
            fill: true,
            yAxisID: "y",
          },
          {
            label: "支出 (人民币)",
            data: cnyData,
            borderColor: "#e74c3c",
            backgroundColor: "rgba(231, 76, 60, 0.1)",
            tension: 0.4,
            fill: true,
            yAxisID: "y1",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: "index",
          intersect: false,
        },
        plugins: {
          title: {
            display: true,
            text: "消费趋势",
          },
          legend: {
            position: "top",
            onClick: (e, legendItem, legend) => {
              // 默认的图例点击行为
              const index = legendItem.datasetIndex;
              const chart = legend.chart;
              const meta = chart.getDatasetMeta(index);

              // 切换数据集的可见性
              meta.hidden =
                meta.hidden === null
                  ? !chart.data.datasets[index].hidden
                  : null;

              // 更新坐标轴的显示状态
              if (index === 0) {
                // 日元数据集对应y轴
                chart.options.scales.y.display = !meta.hidden;
              } else if (index === 1) {
                // 人民币数据集对应y1轴
                chart.options.scales.y1.display = !meta.hidden;
              }

              // 重新渲染图表
              chart.update();
            },
          },
        },
        scales: {
          x: {
            display: true,
            title: {
              display: false, // 隐藏坐标轴名称
              text: "日期",
            },
          },
          y: {
            type: "linear",
            display: true,
            position: "left",
            title: {
              display: false, // 隐藏坐标轴名称
              text: "日元 (¥)",
              color: "#3498db",
            },
            ticks: {
              color: "#3498db",
            },
          },
          y1: {
            type: "linear",
            display: true,
            position: "right",
            title: {
              display: false, // 隐藏坐标轴名称
              text: "人民币 (￥)",
              color: "#e74c3c",
            },
            ticks: {
              color: "#e74c3c",
            },
            grid: {
              drawOnChartArea: false,
            },
          },
        },
        onClick: (event, elements) => {
          if (elements.length > 0) {
            const index = elements[0].index;
            const clickedDate = labels[index];
            this.loadDailyItems(clickedDate);
          }
        },
      },
    });
  }

  async loadDailyItems(date) {
    try {
      const response = await fetch(`/api/analytics/daily/${date}/items`);
      const data = await response.json();

      if (response.ok) {
        this.updateDailyItemsList(data.data, date);
      } else {
        throw new Error(data.message || "获取每日商品数据失败");
      }
    } catch (error) {
      console.error("加载每日商品失败:", error);
      this.showError("加载每日商品失败");
    }
  }

  updateDailyItemsList(items, date) {
    const container = document.getElementById("dailyItemsList");
    const title = document.getElementById("selectedDateTitle");

    title.innerHTML = `<i class="fas fa-calendar-day"></i> ${date} 的商品 (${items.length}件)`;

    if (items.length === 0) {
      container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-calendar-times"></i>
                    <p>该日期没有商品记录</p>
                </div>
            `;
      return;
    }

    // 添加统计信息和视图切换
    const totalJpy = items.reduce(
      (sum, item) => sum + (item.price_jpy || 0),
      0
    );
    const totalCny = items.reduce(
      (sum, item) => sum + (item.price_cny || 0),
      0
    );
    const specialCount = items.filter((item) => item.is_special_offer).length;

    const controlsHtml = `
      <div class="items-controls">
        <div class="items-stats">
          <div class="items-stats-left">
            <i class="fas fa-shopping-bag"></i> ${items.length} 件商品
          </div>
          <div class="items-stats-right">
            <span>总计: <span class="items-stats-value">¥${totalJpy.toLocaleString()}</span></span>
            ${totalCny > 0 ? `<span>￥${totalCny.toLocaleString()}</span>` : ""}
            ${
              specialCount > 0
                ? `<span>特价: <span class="items-stats-value">${specialCount}</span> 件</span>`
                : ""
            }
          </div>
        </div>
        
        <div class="items-toolbar">
          <div class="items-search">
            <i class="fas fa-search"></i>
            <input type="text" placeholder="搜索商品..." class="search-input">
          </div>
          
          <div class="items-sort">
            <select class="sort-select">
              <option value="name">按名称排序</option>
              <option value="price_desc">价格：高到低</option>
              <option value="price_asc">价格：低到高</option>
              <option value="special">特价商品优先</option>
            </select>
          </div>
        </div>
      </div>
    `;

    const contentHtml = `
      <div class="items-content">
        <div class="items-grid">
          ${items.map((item) => this.generateItemCard(item)).join("")}
        </div>
      </div>
    `;

    container.innerHTML = controlsHtml + contentHtml;

    // 添加交互事件
    this.setupItemsInteraction(container, items);
  }

  generateItemCard(item) {
    const categories = [item.category_1, item.category_2, item.category_3]
      .filter(Boolean)
      .map((cat, index) => {
        const bgClass =
          ["bg-primary", "bg-info", "bg-success"][index] || "bg-secondary";
        return `<span class="badge ${bgClass}">${cat}</span>`;
      })
      .join("");

    const hasPrice = item.price_jpy || item.price_cny;
    const priceDisplay = !hasPrice
      ? '<span class="text-muted">价格待定</span>'
      : `${
          item.price_jpy
            ? `<span class="analytics-price-jpy">¥${item.price_jpy.toLocaleString()}</span>`
            : ""
        }
       ${
         item.price_cny
           ? `<span class="analytics-price-cny">￥${item.price_cny.toLocaleString()}</span>`
           : ""
       }`;

    return `
      <div class="analytics-item-compact" 
           data-item-id="${item.id || ""}"
           data-price-jpy="${item.price_jpy || 0}"
           data-is-special="${item.is_special_offer || false}">
        
        <!-- 商品名称和价格行 -->
        <div class="analytics-item-header">
          <div class="analytics-item-name">
            ${item.name_zh || item.name_ja || "未知商品"}
            ${
              item.name_ja && item.name_zh
                ? `<span class="text-muted">${item.name_ja}</span>`
                : ""
            }
            ${
              item.is_special_offer
                ? '<span class="analytics-special-offer-badge" title="特价商品">特价</span>'
                : ""
            }
          </div>
          <div class="analytics-item-price">
            ${priceDisplay}
          </div>
        </div>

        <!-- 商品详细信息 -->
        <div class="analytics-item-details">
          <div class="analytics-item-detail-row" title="店铺名称">
            <i class="fas fa-store"></i>
            <span>${item.store_name || "未知店铺"}</span>
          </div>
          ${
            item.special_info
              ? `
            <div class="analytics-item-detail-row" title="特价信息">
              <i class="fas fa-percent"></i>
              <span>${item.special_info}</span>
            </div>
          `
              : ""
          }
          ${
            item.notes
              ? `
            <div class="analytics-item-detail-row" title="商品备注">
              <i class="fas fa-comment"></i>
              <span>${
                item.notes.length > 30
                  ? item.notes.substr(0, 30) + "..."
                  : item.notes
              }</span>
            </div>
          `
              : ""
          }
        </div>

        <!-- 分类标签和操作按钮 -->
        <div class="analytics-item-footer">
          ${
            categories
              ? `<div class="analytics-item-categories">${categories}</div>`
              : '<div class="analytics-item-categories"></div>'
          }
          <div class="analytics-item-actions">
            <button class="btn btn-sm btn-outline-primary" onclick="window.analytics.viewReceipt('${
              item.receipt_id || ""
            }')" title="查看小票">
              <i class="fas fa-receipt"></i>
            </button>
            <button class="btn btn-sm btn-outline-warning" onclick="window.analytics.editItem('${
              item.id || ""
            }')" title="编辑商品">
              <i class="fas fa-edit"></i>
            </button>
          </div>
        </div>
      </div>
    `;
  }

  generateItemRow(item) {
    return `
      <div class="item-row">
        <div class="item-info">
          <div class="item-name">
            ${item.name_zh || item.name_ja || "未知商品"}
            ${
              item.is_special_offer
                ? '<span class="special-offer-badge">特价</span>'
                : ""
            }
          </div>
          <div class="item-details">
            <span><i class="fas fa-store"></i> ${
              item.store_name || "未知店铺"
            }</span>
            <span><i class="fas fa-tag"></i> ${
              item.category_1 || "未分类"
            }</span>
            ${
              item.special_info
                ? `<span><i class="fas fa-percent"></i> ${item.special_info}</span>`
                : ""
            }
          </div>
        </div>
        <div class="item-price">
          <div>¥${(item.price_jpy || 0).toLocaleString()}</div>
          ${
            item.price_cny
              ? `<div>￥${item.price_cny.toLocaleString()}</div>`
              : ""
          }
        </div>
      </div>
    `;
  }

  async loadCategoryData() {
    try {
      const params = this.getDateFilter();
      const response = await fetch(
        `/api/analytics/category?${params}&category_level=${
          this.currentCategoryLevel
        }${
          this.currentParentCategory
            ? `&parent_category=${encodeURIComponent(
                this.currentParentCategory
              )}`
            : ""
        }`
      );
      const data = await response.json();

      if (response.ok) {
        this.updateCategoryChart(data);
      } else {
        throw new Error(data.message || "获取分类数据失败");
      }
    } catch (error) {
      console.error("加载分类数据失败:", error);
      throw error;
    }
  }

  updateCategoryChart(categoryData) {
    const ctx = document.getElementById("categoryChart").getContext("2d");

    if (this.categoryChart) {
      this.categoryChart.destroy();
    }

    const categories = categoryData.categories;
    const labels = categories.map((item) => item.category || "未分类");
    const data = categories.map((item) => item.spending.jpy);
    const colors = this.generateColors(categories.length);

    this.categoryChart = new Chart(ctx, {
      type: "pie",
      data: {
        labels: labels,
        datasets: [
          {
            data: data,
            backgroundColor: colors,
            borderWidth: 2,
            borderColor: "#fff",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          title: {
            display: true,
            text: `${this.getCategoryLevelName(
              categoryData.category_level
            )}支出分布`,
          },
          legend: {
            position: "bottom",
            labels: {
              generateLabels: (chart) => {
                const data = chart.data;
                if (data.labels.length && data.datasets.length) {
                  return data.labels.map((label, index) => {
                    const value = data.datasets[0].data[index];
                    const percentage = categories[index].percentage;
                    const isHidden = this.hiddenCategories.has(label);
                    const meta = chart.getDatasetMeta(0);
                    const actuallyHidden = meta.data[index].hidden;

                    return {
                      text: `${label} (${percentage}%)`,
                      fillStyle: actuallyHidden
                        ? "#ccc"
                        : data.datasets[0].backgroundColor[index],
                      strokeStyle: data.datasets[0].borderColor,
                      lineWidth: data.datasets[0].borderWidth,
                      index: index,
                      hidden: actuallyHidden,
                      fontColor: actuallyHidden ? "#999" : "#666",
                      textDecoration: actuallyHidden ? "line-through" : "none",
                    };
                  });
                }
                return [];
              },
              filter: (legendItem, chartData) => {
                // 保持所有图例项可见，即使分类被隐藏
                return true;
              },
            },
            onClick: (event, legendItem) => {
              const category = labels[legendItem.index];

              // 普通点击切换隐藏状态
              this.toggleCategoryVisibility(category);
            },
          },
          tooltip: {
            callbacks: {
              label: (context) => {
                const category = categories[context.dataIndex];
                const isHidden = this.hiddenCategories.has(context.label);
                const status = isHidden ? " [已隐藏]" : "";
                return [
                  `${
                    context.label
                  }: ¥${context.parsed.toLocaleString()}${status}`,
                  `占比: ${category.percentage}%`,
                  `商品数: ${category.item_count}件`,
                ];
              },
            },
          },
        },
        onClick: (event, elements) => {
          if (elements.length > 0) {
            const index = elements[0].index;
            const clickedCategory = categories[index];
            this.onCategoryClick(clickedCategory.category);
          }
        },
        onHover: (event, activeElements) => {
          event.native.target.style.cursor =
            activeElements.length > 0 ? "pointer" : "default";
        },
      },
    });

    this.updateCategoryBreadcrumb(categoryData);
  }

  // 新增：切换分类可见性
  toggleCategoryVisibility(category) {
    if (this.hiddenCategories.has(category)) {
      this.hiddenCategories.delete(category);
    } else {
      this.hiddenCategories.add(category);
    }

    // 更新图表显示，隐藏/显示对应的数据段
    if (this.categoryChart && this.categoryChart.data) {
      const categoryIndex = this.categoryChart.data.labels.indexOf(category);
      if (categoryIndex !== -1) {
        const isHidden = this.hiddenCategories.has(category);

        // 切换数据段的hidden状态
        this.categoryChart.getDatasetMeta(0).data[categoryIndex].hidden =
          isHidden;

        // 更新图表
        this.categoryChart.update();
      }
    }

    // 显示操作提示
    const action = this.hiddenCategories.has(category) ? "隐藏" : "显示";
    this.showToast(`${action}分类 "${category}"`, "info");
  }

  getCategoryLevelName(level) {
    const names = { 1: "一级分类", 2: "二级分类", 3: "三级分类" };
    return names[level] || "分类";
  }

  generateColors(count) {
    const colors = [
      "#FF6384",
      "#36A2EB",
      "#FFCE56",
      "#4BC0C0",
      "#9966FF",
      "#FF9F40",
      "#FF6384",
      "#C9CBCF",
      "#4BC0C0",
      "#FF6384",
    ];
    return Array.from({ length: count }, (_, i) => colors[i % colors.length]);
  }

  updateCategoryBreadcrumb(categoryData) {
    const breadcrumb = document.getElementById("categoryBreadcrumb");
    let breadcrumbHtml = "";

    // 一级分类
    if (this.currentCategoryLevel === 1) {
      breadcrumbHtml =
        '<span class="breadcrumb-item active" data-level="1">一级分类</span>';
    } else {
      breadcrumbHtml =
        '<span class="breadcrumb-item" data-level="1">一级分类</span>';
    }

    // 二级分类
    if (this.currentCategoryLevel >= 2 && this.categoryStack.length > 0) {
      const isActive = this.currentCategoryLevel === 2 ? "active" : "";
      breadcrumbHtml += `<span class="breadcrumb-item ${isActive}" data-level="2">${this.categoryStack[0]}</span>`;
    }

    // 三级分类
    if (this.currentCategoryLevel === 3 && this.categoryStack.length > 1) {
      breadcrumbHtml += `<span class="breadcrumb-item active" data-level="3">${this.categoryStack[1]}</span>`;
    }

    breadcrumb.innerHTML = breadcrumbHtml;

    // 添加面包屑点击事件
    breadcrumb.querySelectorAll(".breadcrumb-item").forEach((item) => {
      item.addEventListener("click", () => {
        const level = parseInt(item.dataset.level);
        this.navigateToLevel(level);
      });
    });
  }

  onCategoryClick(category) {
    if (this.currentCategoryLevel < 3) {
      this.categoryStack.push(category);
      this.currentCategoryLevel++;
      this.currentParentCategory = category;
      Promise.all([
        this.loadCategoryData(),
        this.loadCategoryItems(category, this.currentCategoryLevel - 1),
      ]).catch((error) => {
        console.error("加载分类数据失败:", error);
        this.showError("加载分类数据失败");
      });
    } else {
      // 已经是三级分类，只显示商品列表
      this.loadCategoryItems(category, this.currentCategoryLevel);
    }
  }

  navigateToLevel(level) {
    if (level === this.currentCategoryLevel) return;

    this.currentCategoryLevel = level;

    if (level === 1) {
      this.categoryStack = [];
      this.currentParentCategory = null;
    } else if (level === 2) {
      this.categoryStack = this.categoryStack.slice(0, 1);
      this.currentParentCategory = this.categoryStack[0];
    }

    this.loadCategoryData();

    // 清空商品列表
    this.clearCategoryItems();
  }

  async loadCategoryItems(category, categoryLevel) {
    try {
      const params = this.getDateFilter();
      const response = await fetch(
        `/api/analytics/category/${encodeURIComponent(
          category
        )}/items?${params}&category_level=${categoryLevel}`
      );
      const data = await response.json();

      if (response.ok) {
        this.updateCategoryItemsList(data.data, category);
      } else {
        throw new Error(data.message || "获取分类商品数据失败");
      }
    } catch (error) {
      console.error("加载分类商品失败:", error);
      this.showError("加载分类商品失败");
    }
  }

  updateCategoryItemsList(items, category) {
    const container = document.getElementById("categoryItemsList");
    const title = document.getElementById("selectedCategoryTitle");

    title.innerHTML = `<i class="fas fa-tag"></i> ${category} (${items.length}件商品)`;

    if (items.length === 0) {
      container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-box-open"></i>
                    <p>该分类下没有商品</p>
                </div>
            `;
      return;
    }

    // 添加统计信息和视图切换
    const totalJpy = items.reduce(
      (sum, item) => sum + (item.price_jpy || 0),
      0
    );
    const totalCny = items.reduce(
      (sum, item) => sum + (item.price_cny || 0),
      0
    );
    const specialCount = items.filter((item) => item.is_special_offer).length;

    const controlsHtml = `
      <div class="items-controls">
        <div class="items-stats">
          <div class="items-stats-left">
            <i class="fas fa-tag"></i> ${category} 分类
          </div>
          <div class="items-stats-right">
            <span>总计: <span class="items-stats-value">¥${totalJpy.toLocaleString()}</span></span>
            ${totalCny > 0 ? `<span>￥${totalCny.toLocaleString()}</span>` : ""}
            ${
              specialCount > 0
                ? `<span>特价: <span class="items-stats-value">${specialCount}</span> 件</span>`
                : ""
            }
          </div>
        </div>
        
        <div class="items-toolbar">
          <div class="items-search">
            <i class="fas fa-search"></i>
            <input type="text" placeholder="搜索商品..." class="search-input">
          </div>
          
          <div class="items-sort">
            <select class="sort-select">
              <option value="name">按名称排序</option>
              <option value="price_desc">价格：高到低</option>
              <option value="price_asc">价格：低到高</option>
              <option value="date_desc">最新购买</option>
              <option value="special">特价商品优先</option>
            </select>
          </div>
        </div>
      </div>
    `;

    const contentHtml = `
      <div class="items-content">
        <div class="items-grid">
          ${items.map((item) => this.generateCategoryItemCard(item)).join("")}
        </div>
      </div>
    `;

    container.innerHTML = controlsHtml + contentHtml;

    // 添加交互事件
    this.setupItemsInteraction(container, items);
  }

  generateCategoryItemCard(item) {
    const categories = [item.category_1, item.category_2, item.category_3]
      .filter(Boolean)
      .map((cat, index) => {
        const bgClass =
          ["bg-primary", "bg-info", "bg-success"][index] || "bg-secondary";
        return `<span class="badge ${bgClass}">${cat}</span>`;
      })
      .join("");

    const transactionDate = item.transaction_time
      ? new Date(item.transaction_time).toLocaleDateString("zh-CN")
      : "未知日期";

    const hasPrice = item.price_jpy || item.price_cny;
    const priceDisplay = !hasPrice
      ? '<span class="text-muted">价格待定</span>'
      : `${
          item.price_jpy
            ? `<span class="analytics-price-jpy">¥${item.price_jpy.toLocaleString()}</span>`
            : ""
        }
       ${
         item.price_cny
           ? `<span class="analytics-price-cny">￥${item.price_cny.toLocaleString()}</span>`
           : ""
       }`;

    return `
      <div class="analytics-item-compact" 
           data-item-id="${item.id || ""}"
           data-price-jpy="${item.price_jpy || 0}"
           data-is-special="${item.is_special_offer || false}">
        
        <!-- 商品名称和价格行 -->
        <div class="analytics-item-header">
          <div class="analytics-item-name">
            ${item.name_zh || item.name_ja || "未知商品"}
            ${
              item.name_ja && item.name_zh
                ? `<span class="text-muted">${item.name_ja}</span>`
                : ""
            }
            ${
              item.is_special_offer
                ? '<span class="analytics-special-offer-badge" title="特价商品">特价</span>'
                : ""
            }
          </div>
          <div class="analytics-item-price">
            ${priceDisplay}
          </div>
        </div>

        <!-- 商品详细信息 -->
        <div class="analytics-item-details">
          <div class="analytics-item-detail-row" title="店铺名称">
            <i class="fas fa-store"></i>
            <span>${item.store_name || "未知店铺"}</span>
          </div>
          <div class="analytics-item-detail-row" title="购买日期">
            <i class="fas fa-calendar"></i>
            <span>${transactionDate}</span>
          </div>
          ${
            item.special_info
              ? `
            <div class="analytics-item-detail-row" title="特价信息">
              <i class="fas fa-percent"></i>
              <span>${item.special_info}</span>
            </div>
          `
              : ""
          }
          ${
            item.notes
              ? `
            <div class="analytics-item-detail-row" title="商品备注">
              <i class="fas fa-comment"></i>
              <span>${
                item.notes.length > 30
                  ? item.notes.substr(0, 30) + "..."
                  : item.notes
              }</span>
            </div>
          `
              : ""
          }
        </div>

        <!-- 分类标签和操作按钮 -->
        <div class="analytics-item-footer">
          ${
            categories
              ? `<div class="analytics-item-categories">${categories}</div>`
              : '<div class="analytics-item-categories"></div>'
          }
          <div class="analytics-item-actions">
            <button class="btn btn-sm btn-outline-primary" onclick="window.analytics.viewReceipt('${
              item.receipt_id || ""
            }')" title="查看小票">
              <i class="fas fa-receipt"></i>
            </button>
            <button class="btn btn-sm btn-outline-warning" onclick="window.analytics.editItem('${
              item.id || ""
            }')" title="编辑商品">
              <i class="fas fa-edit"></i>
            </button>
          </div>
        </div>
      </div>
    `;
  }

  generateCategoryItemRow(item) {
    const transactionDate = item.transaction_time
      ? new Date(item.transaction_time).toLocaleDateString("zh-CN")
      : "未知日期";

    return `
      <div class="item-row">
        <div class="item-info">
          <div class="item-name">
            ${item.name_zh || item.name_ja || "未知商品"}
            ${
              item.is_special_offer
                ? '<span class="special-offer-badge">特价</span>'
                : ""
            }
          </div>
          <div class="item-details">
            <span><i class="fas fa-store"></i> ${
              item.store_name || "未知店铺"
            }</span>
            <span><i class="fas fa-calendar"></i> ${transactionDate}</span>
            ${
              item.special_info
                ? `<span><i class="fas fa-percent"></i> ${item.special_info}</span>`
                : ""
            }
          </div>
        </div>
        <div class="item-price">
          <div>¥${(item.price_jpy || 0).toLocaleString()}</div>
          ${
            item.price_cny
              ? `<div>￥${item.price_cny.toLocaleString()}</div>`
              : ""
          }
        </div>
      </div>
    `;
  }

  setupItemsInteraction(container, items) {
    const searchInput = container.querySelector(".search-input");
    const sortSelect = container.querySelector(".sort-select");

    // 搜索功能
    searchInput.addEventListener("input", (e) => {
      const query = e.target.value.toLowerCase().trim();
      this.filterAndUpdateItems(container, items, query, sortSelect.value);
    });

    // 排序功能
    sortSelect.addEventListener("change", (e) => {
      const query = searchInput.value.toLowerCase().trim();
      this.filterAndUpdateItems(container, items, query, e.target.value);
    });

    // 添加商品卡片进入动画
    setTimeout(() => {
      const itemCards = container.querySelectorAll(".analytics-item-compact");
      itemCards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
        card.classList.add("animate-in");
      });
    }, 100);
  }

  filterAndUpdateItems(container, allItems, searchQuery = "", sortBy = "name") {
    let filteredItems = [...allItems];

    // 搜索过滤
    if (searchQuery) {
      filteredItems = filteredItems.filter((item) => {
        const name = (item.name_zh || item.name_ja || "").toLowerCase();
        const store = (item.store_name || "").toLowerCase();
        const category = (item.category_1 || "").toLowerCase();
        const notes = (item.notes || "").toLowerCase();

        return (
          name.includes(searchQuery) ||
          store.includes(searchQuery) ||
          category.includes(searchQuery) ||
          notes.includes(searchQuery)
        );
      });
    }

    // 排序
    switch (sortBy) {
      case "price_desc":
        filteredItems.sort((a, b) => (b.price_jpy || 0) - (a.price_jpy || 0));
        break;
      case "price_asc":
        filteredItems.sort((a, b) => (a.price_jpy || 0) - (b.price_jpy || 0));
        break;
      case "date_desc":
        filteredItems.sort((a, b) => {
          const dateA = new Date(a.transaction_time || 0);
          const dateB = new Date(b.transaction_time || 0);
          return dateB - dateA;
        });
        break;
      case "special":
        filteredItems.sort((a, b) => {
          if (a.is_special_offer && !b.is_special_offer) return -1;
          if (!a.is_special_offer && b.is_special_offer) return 1;
          return (b.price_jpy || 0) - (a.price_jpy || 0);
        });
        break;
      default: // name
        filteredItems.sort((a, b) => {
          const nameA = (a.name_zh || a.name_ja || "").toLowerCase();
          const nameB = (b.name_zh || b.name_ja || "").toLowerCase();
          return nameA.localeCompare(nameB, "zh-CN");
        });
    }

    // 更新显示
    const gridView = container.querySelector(".items-grid");

    if (filteredItems.length === 0) {
      const emptyHtml = `
        <div class="empty-state" style="grid-column: 1 / -1;">
          <i class="fas fa-search"></i>
          <p>没有找到匹配的商品</p>
        </div>
      `;
      gridView.innerHTML = emptyHtml;
    } else {
      // 判断当前是日期商品还是分类商品
      const isDateItems = container.closest("#dailyItemsList");

      if (isDateItems) {
        gridView.innerHTML = filteredItems
          .map((item) => this.generateItemCard(item))
          .join("");
      } else {
        gridView.innerHTML = filteredItems
          .map((item) => this.generateCategoryItemCard(item))
          .join("");
      }
    }

    // 更新统计信息
    const statsLeft = container.querySelector(".items-stats-left");
    const originalText = statsLeft.textContent;
    const newText = originalText.replace(/\d+/, filteredItems.length);
    statsLeft.innerHTML = newText;

    // 重新添加动画
    setTimeout(() => {
      const itemCards = container.querySelectorAll(".analytics-item-compact");
      itemCards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.05}s`;
        card.classList.add("animate-in");
      });
    }, 50);
  }

  clearCategoryItems() {
    const container = document.getElementById("categoryItemsList");
    const title = document.getElementById("selectedCategoryTitle");

    title.innerHTML = '<i class="fas fa-list"></i> 选择分类查看商品';
    container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-mouse-pointer"></i>
                <p>点击饼图中的分类查看商品列表</p>
            </div>
        `;
  }

  showError(message) {
    // 可以使用toast或者alert显示错误
    this.showToast(message, "error");
  }

  showToast(message, type = "info") {
    // 创建toast元素
    const toast = document.createElement("div");
    toast.className = `toast-notification toast-${type}`;
    toast.innerHTML = `
      <div class="toast-content">
        <i class="fas ${
          type === "error" ? "fa-exclamation-circle" : "fa-info-circle"
        }"></i>
        <span>${message}</span>
      </div>
    `;

    // 添加到页面
    document.body.appendChild(toast);

    // 显示动画
    setTimeout(() => toast.classList.add("show"), 100);

    // 自动移除
    setTimeout(() => {
      toast.classList.remove("show");
      setTimeout(() => document.body.removeChild(toast), 300);
    }, 3000);
  }

  showItemDetail(itemId) {
    if (!itemId) {
      this.showToast("商品信息不完整", "error");
      return;
    }

    // 这里可以实现商品详情的模态框或跳转
    this.showToast("商品详情功能开发中...", "info");
    console.log("查看商品详情:", itemId);
  }

  viewReceipt(receiptId) {
    if (!receiptId) {
      this.showToast("小票信息不完整", "error");
      return;
    }

    // 跳转到小票详情页
    window.location.href = `/receipts/${receiptId}`;
  }

  async editItem(itemId) {
    if (!itemId) {
      this.showToast("商品信息不完整", "error");
      return;
    }

    try {
      // 获取商品详细信息
      const response = await fetch(`/api/items/${itemId}`);
      if (!response.ok) {
        throw new Error("获取商品信息失败");
      }

      const item = await response.json();

      // 使用公共的商品编辑组件
      const editor = new ItemEditor();
      editor.show(item, () => {
        // 保存成功回调，刷新当前数据
        this.refreshCurrentData();
      });
    } catch (error) {
      console.error("获取商品信息失败:", error);
      this.showToast("获取商品信息失败: " + error.message, "error");
    }
  }

  refreshCurrentData() {
    // 重新加载当前显示的数据（根据当前状态判断是重新加载日期数据还是分类数据）
    const dailyContainer = document.getElementById("dailyItemsList");
    const categoryContainer = document.getElementById("categoryItemsList");

    // 检查哪个容器有数据并且不是空状态
    if (dailyContainer && !dailyContainer.querySelector(".empty-state")) {
      // 有日期数据，重新加载趋势数据
      this.loadTrendData();
    }

    if (categoryContainer && !categoryContainer.querySelector(".empty-state")) {
      // 有分类数据，重新加载分类数据
      this.loadCategoryData();
    }
  }
}

// 页面加载完成后初始化
let analytics;

document.addEventListener("DOMContentLoaded", () => {
  analytics = new AnalyticsPage();

  // 让analytics对象全局可用
  window.analytics = analytics;
});
