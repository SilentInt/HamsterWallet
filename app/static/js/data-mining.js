// 数据挖掘页面JavaScript

class DataMiningPage {
  constructor() {
    this.categoryTree = [];
    this.currentPath = [];
    this.currentLevel = 0;
    this.selectedCategories = [];
    this.comparisonGroups = [];
    this.chart = null;
    this.currentDateFilter = this.getDefaultDateFilter();

    this.init();
  }

  init() {
    this.initDateFilters();
    this.bindEvents();
    this.loadCategoryTree();
  }

  getDefaultDateFilter() {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setMonth(startDate.getMonth() - 1);

    return {
      start_date: startDate.toISOString().split("T")[0],
      end_date: endDate.toISOString().split("T")[0],
    };
  }

  initDateFilters() {
    const startDateInput = document.getElementById("startDate");
    const endDateInput = document.getElementById("endDate");

    // 设置默认日期
    startDateInput.value = this.currentDateFilter.start_date;
    endDateInput.value = this.currentDateFilter.end_date;

    // 绑定日期变化事件
    startDateInput.addEventListener("change", () => {
      this.currentDateFilter.start_date = startDateInput.value;
      this.loadCategoryTree();
      this.updateAllComparisons();
    });

    endDateInput.addEventListener("change", () => {
      this.currentDateFilter.end_date = endDateInput.value;
      this.loadCategoryTree();
      this.updateAllComparisons();
    });
  }

  bindEvents() {
    // 日期筛选按钮
    document.getElementById("allTimeFilter").addEventListener("click", () => {
      this.setDateFilter(null, null);
    });

    document.getElementById("last7DaysFilter").addEventListener("click", () => {
      const endDate = new Date();
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - 7);
      this.setDateFilter(startDate, endDate);
    });

    document.getElementById("resetFilter").addEventListener("click", () => {
      const endDate = new Date();
      const startDate = new Date();
      startDate.setMonth(startDate.getMonth() - 1);
      this.setDateFilter(startDate, endDate);
    });

    document
      .getElementById("last3MonthsFilter")
      .addEventListener("click", () => {
        const endDate = new Date();
        const startDate = new Date();
        startDate.setMonth(startDate.getMonth() - 3);
        this.setDateFilter(startDate, endDate);
      });

    // 分类操作按钮
    document.getElementById("backBtn").addEventListener("click", () => {
      this.navigateBack();
    });

    document
      .getElementById("clearSelectionBtn")
      .addEventListener("click", () => {
        this.clearSelection();
      });

    document
      .getElementById("addComparisonBtn")
      .addEventListener("click", () => {
        this.showNameComparisonModal();
      });

    // 模态框确认按钮
    document
      .getElementById("confirmAddComparison")
      .addEventListener("click", () => {
        this.confirmAddComparison();
      });

    // 关闭详情按钮
    document.getElementById("closeDetailsBtn").addEventListener("click", () => {
      this.hideDataPointDetails();
    });
  }

  setDateFilter(startDate, endDate) {
    const startDateInput = document.getElementById("startDate");
    const endDateInput = document.getElementById("endDate");

    if (startDate) {
      this.currentDateFilter.start_date = startDate.toISOString().split("T")[0];
      startDateInput.value = this.currentDateFilter.start_date;
    } else {
      this.currentDateFilter.start_date = "";
      startDateInput.value = "";
    }

    if (endDate) {
      this.currentDateFilter.end_date = endDate.toISOString().split("T")[0];
      endDateInput.value = this.currentDateFilter.end_date;
    } else {
      this.currentDateFilter.end_date = "";
      endDateInput.value = "";
    }

    this.loadCategoryTree();
    this.updateAllComparisons();
  }

  async loadCategoryTree() {
    try {
      const params = new URLSearchParams();
      if (this.currentDateFilter.start_date) {
        params.append("start_date", this.currentDateFilter.start_date);
      }
      if (this.currentDateFilter.end_date) {
        params.append("end_date", this.currentDateFilter.end_date);
      }

      const response = await fetch(`/api/data-mining/category-tree?${params}`);
      const result = await response.json();

      if (response.ok) {
        this.categoryTree = result.data || [];
        this.renderCurrentLevel();
      } else {
        console.error("加载分类树失败:", result.message);
        // 显示错误消息给用户
        this.showError("加载分类数据失败: " + (result.message || "未知错误"));
      }
    } catch (error) {
      console.error("加载分类树出错:", error);
      this.showError("网络错误，请检查连接");
    }
  }

  getCurrentCategories() {
    let categories = this.categoryTree;

    // 根据当前路径获取当前层级的分类
    for (const pathItem of this.currentPath) {
      const category = categories.find((cat) => cat.name === pathItem);
      if (category) {
        categories = category.children;
      } else {
        categories = [];
        break;
      }
    }

    return categories;
  }

  renderCurrentLevel() {
    const categories = this.getCurrentCategories();
    const grid = document.getElementById("categoryGrid");
    const levelTitle = document.getElementById("currentLevelTitle");
    const backBtn = document.getElementById("backBtn");

    // 更新层级标题
    const levelNames = ["一级分类", "二级分类", "三级分类"];
    levelTitle.textContent = levelNames[this.currentLevel] || "分类";

    // 更新返回按钮状态
    backBtn.disabled = this.currentLevel === 0;

    // 更新面包屑
    this.updateBreadcrumb();

    // 渲染分类卡片
    grid.innerHTML = "";
    categories.forEach((category) => {
      const card = this.createCategoryCard(category);
      grid.appendChild(card);
    });

    this.updateSelectionCounter();
  }

  createCategoryCard(category) {
    const card = document.createElement("div");
    card.className = "category-card";
    card.dataset.categoryId = category.id;

    // 检查是否有子分类
    const hasChildren = category.children && category.children.length > 0;
    if (hasChildren) {
      card.classList.add("has-children");
    }

    // 检查是否已选中
    const isSelected = this.selectedCategories.some(
      (selected) => selected.id === category.id
    );
    if (isSelected) {
      card.classList.add("selected");
    }

    card.innerHTML = `
            <div class="category-name">${category.name}</div>
            <div class="category-stats">
                <span>¥${category.total_cny}</span>
                <span>${category.item_count}项</span>
            </div>
            <input type="checkbox" class="select-checkbox" ${
              isSelected ? "checked" : ""
            }>
            ${
              hasChildren
                ? '<div class="children-indicator"><i class="fas fa-chevron-right"></i></div>'
                : ""
            }
        `;

    // 绑定事件
    const checkbox = card.querySelector(".select-checkbox");
    checkbox.addEventListener("change", (e) => {
      e.stopPropagation();
      this.toggleCategorySelection(category, e.target.checked);
    });

    card.addEventListener("click", (e) => {
      if (e.target === checkbox) return;

      if (hasChildren) {
        this.navigateToCategory(category.name);
      } else {
        // 如果没有子分类，切换选择状态
        checkbox.checked = !checkbox.checked;
        this.toggleCategorySelection(category, checkbox.checked);
      }
    });

    return card;
  }

  toggleCategorySelection(category, isSelected) {
    if (isSelected) {
      // 添加到选择列表
      if (
        !this.selectedCategories.some((selected) => selected.id === category.id)
      ) {
        this.selectedCategories.push({
          id: category.id,
          name: category.name,
          path: [...this.currentPath, category.name],
          total_cny: category.total_cny,
          item_count: category.item_count,
        });
      }
    } else {
      // 从选择列表中移除
      this.selectedCategories = this.selectedCategories.filter(
        (selected) => selected.id !== category.id
      );
    }

    this.updateSelectionCounter();
    this.updateAddComparisonButton();
    this.renderCurrentLevel(); // 重新渲染以更新选中状态
  }

  navigateToCategory(categoryName) {
    this.currentPath.push(categoryName);
    this.currentLevel++;
    this.renderCurrentLevel();
  }

  navigateBack() {
    if (this.currentLevel > 0) {
      this.currentPath.pop();
      this.currentLevel--;
      this.renderCurrentLevel();
    }
  }

  navigateToBreadcrumb(level) {
    this.currentPath = this.currentPath.slice(0, level);
    this.currentLevel = level;
    this.renderCurrentLevel();
  }

  updateBreadcrumb() {
    const breadcrumb = document.getElementById("categoryBreadcrumb");
    breadcrumb.innerHTML = "";

    // 添加根目录
    const rootItem = document.createElement("li");
    rootItem.className = "breadcrumb-item";
    if (this.currentLevel === 0) {
      rootItem.classList.add("active");
      rootItem.textContent = "全部分类";
    } else {
      rootItem.innerHTML = '<a href="#" data-level="0">全部分类</a>';
    }
    breadcrumb.appendChild(rootItem);

    // 添加路径中的每一级
    this.currentPath.forEach((pathItem, index) => {
      const item = document.createElement("li");
      item.className = "breadcrumb-item";

      if (index === this.currentPath.length - 1) {
        item.classList.add("active");
        item.textContent = pathItem;
      } else {
        item.innerHTML = `<a href="#" data-level="${
          index + 1
        }">${pathItem}</a>`;
      }

      breadcrumb.appendChild(item);
    });

    // 绑定点击事件
    breadcrumb.addEventListener("click", (e) => {
      if (e.target.tagName === "A") {
        e.preventDefault();
        const level = parseInt(e.target.dataset.level);
        this.navigateToBreadcrumb(level);
      }
    });
  }

  updateSelectionCounter() {
    const counter = document.getElementById("selectedCount");
    counter.textContent = this.selectedCategories.length;
  }

  updateAddComparisonButton() {
    const btn = document.getElementById("addComparisonBtn");
    btn.disabled = this.selectedCategories.length === 0;
  }

  clearSelection() {
    this.selectedCategories = [];
    this.updateSelectionCounter();
    this.updateAddComparisonButton();
    this.renderCurrentLevel();
  }

  showNameComparisonModal() {
    if (this.selectedCategories.length === 0) return;

    // 生成默认名称
    const categoryNames = this.selectedCategories.map((cat) => cat.name);
    const defaultName = categoryNames.join(" + ");

    document.getElementById("comparisonName").value = defaultName;

    // 显示选中的分类预览
    const preview = document.getElementById("selectedCategoriesPreview");
    preview.innerHTML = this.selectedCategories
      .map((cat) => `<span class="category-tag">${cat.name}</span>`)
      .join("");

    // 显示模态框
    const modalElement = document.getElementById("nameComparisonModal");
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
  }

  confirmAddComparison() {
    const name = document.getElementById("comparisonName").value.trim();
    if (!name) {
      alert("请输入对比组名称");
      return;
    }

    const comparisonGroup = {
      id: Date.now().toString(),
      name: name,
      categories: [...this.selectedCategories],
      data: null, // 将通过API获取
    };

    this.comparisonGroups.push(comparisonGroup);
    this.renderComparisonGroups();
    this.clearSelection();

    // 获取对比数据
    this.updateComparison(comparisonGroup);

    // 关闭模态框
    const modalElement = document.getElementById("nameComparisonModal");
    const modal = bootstrap.Modal.getInstance(modalElement);
    if (modal) {
      modal.hide();
    }
  }

  renderComparisonGroups() {
    const container = document.getElementById("comparisonGroups");
    container.innerHTML = "";

    this.comparisonGroups.forEach((group) => {
      const item = document.createElement("div");
      item.className = "comparison-group-item";
      item.innerHTML = `
                <div class="group-info">
                    <div class="group-name">${group.name}</div>
                    <div class="group-categories">
                        ${group.categories.map((cat) => cat.name).join(", ")}
                    </div>
                </div>
                <div class="group-actions">
                    <button class="btn btn-outline-danger btn-sm remove-group" data-id="${
                      group.id
                    }">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;

      // 绑定删除事件
      const removeBtn = item.querySelector(".remove-group");
      removeBtn.addEventListener("click", () => {
        this.removeComparisonGroup(group.id);
      });

      container.appendChild(item);
    });
  }

  removeComparisonGroup(groupId) {
    this.comparisonGroups = this.comparisonGroups.filter(
      (group) => group.id !== groupId
    );
    this.renderComparisonGroups();
    this.updateChart();
  }

  async updateComparison(group) {
    try {
      const requestData = {
        selections: [
          {
            name: group.name,
            categories: group.categories,
          },
        ],
        start_date: this.currentDateFilter.start_date || null,
        end_date: this.currentDateFilter.end_date || null,
      };

      const response = await fetch("/api/data-mining/comparison", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestData),
      });

      const result = await response.json();

      if (response.ok && result.data.length > 0) {
        group.data = result.data[0]; // 只有一个选择组
        this.updateChart();
      } else {
        console.error("获取对比数据失败:", result.message);
      }
    } catch (error) {
      console.error("获取对比数据出错:", error);
    }
  }

  async updateAllComparisons() {
    for (const group of this.comparisonGroups) {
      await this.updateComparison(group);
    }
  }

  updateChart() {
    const ctx = document.getElementById("comparisonChart").getContext("2d");

    if (this.chart) {
      this.chart.destroy();
    }

    if (this.comparisonGroups.length === 0) {
      // 显示空状态
      ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
      ctx.font = "16px Arial";
      ctx.fillStyle = "#666";
      ctx.textAlign = "center";
      ctx.fillText(
        "请添加对比组来查看数据",
        ctx.canvas.width / 2,
        ctx.canvas.height / 2
      );
      return;
    }

    // 收集所有日期并排序
    const allDates = new Set();
    this.comparisonGroups.forEach((group) => {
      if (group.data && group.data.time_series) {
        group.data.time_series.forEach((point) => {
          allDates.add(point.date);
        });
      }
    });
    const sortedDates = Array.from(allDates).sort();

    // 准备图表数据
    const datasets = [];
    const colors = [
      "#3498db",
      "#e74c3c",
      "#2ecc71",
      "#f39c12",
      "#9b59b6",
      "#1abc9c",
      "#34495e",
      "#e67e22",
      "#c0392b",
      "#8e44ad",
    ];

    this.comparisonGroups.forEach((group, index) => {
      if (!group.data || !group.data.time_series) return;

      const color = colors[index % colors.length];

      // 为每个日期创建数据点，如果某天没有数据则为0
      const dataPoints = sortedDates.map((date) => {
        const dayData = group.data.time_series.find(
          (point) => point.date === date
        );
        return dayData ? dayData.total_cny : 0;
      });

      const dataset = {
        label: group.name,
        data: dataPoints,
        borderColor: color,
        backgroundColor: color + "20",
        fill: false,
        tension: 0.1,
        pointRadius: 6,
        pointHoverRadius: 8,
        groupData: group.data, // 保存原始数据用于点击事件
        dateMapping: sortedDates, // 保存日期映射
      };

      datasets.push(dataset);
    });

    this.chart = new Chart(ctx, {
      type: "line",
      data: {
        labels: sortedDates.map((date) => {
          // 格式化日期显示
          const d = new Date(date);
          return `${d.getMonth() + 1}-${d.getDate()}`;
        }),
        datasets: datasets,
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          intersect: false,
          mode: "point",
        },
        plugins: {
          title: {
            display: true,
            text: "分类对比趋势图",
          },
          legend: {
            display: true,
            position: "top",
          },
        },
        scales: {
          x: {
            title: {
              display: true,
              text: "日期",
            },
          },
          y: {
            title: {
              display: true,
              text: "金额 (¥)",
            },
            beginAtZero: true,
          },
        },
        onClick: (event, elements) => {
          if (elements.length > 0) {
            const element = elements[0];
            const dataset = this.chart.data.datasets[element.datasetIndex];
            const pointIndex = element.index;
            const date = dataset.dateMapping[pointIndex];
            const groupData = dataset.groupData;

            // 找到对应日期的商品数据
            const dayData = groupData.time_series.find(
              (point) => point.date === date
            );
            if (dayData) {
              this.showDataPointDetails(dataset.label, date, dayData.items);
            }
          }
        },
      },
    });
  }

  showDataPointDetails(groupName, date, items) {
    const detailsContainer = document.getElementById("dataPointDetails");
    const detailsTitle = document.getElementById("detailsTitle");
    const itemsList = document.getElementById("itemsList");

    detailsTitle.textContent = `${groupName} - ${date}`;

    itemsList.innerHTML = "";
    items.forEach((item) => {
      const row = document.createElement("div");
      row.className = "item-row";
      row.innerHTML = `
                <div class="item-info">
                    <div class="item-name">${
                      item.name_zh || item.name_ja || "未知商品"
                    }</div>
                    <div class="item-details">
                        ${item.receipt_name} - ${item.store_name || ""}
                        ${
                          item.is_special_offer
                            ? '<span class="badge bg-warning">特价</span>'
                            : ""
                        }
                    </div>
                </div>
                <div class="item-price">¥${item.price_cny || 0}</div>
            `;
      itemsList.appendChild(row);
    });

    detailsContainer.style.display = "block";
  }

  hideDataPointDetails() {
    document.getElementById("dataPointDetails").style.display = "none";
  }

  showError(message) {
    // 创建或更新错误提示
    let errorDiv = document.getElementById("errorMessage");
    if (!errorDiv) {
      errorDiv = document.createElement("div");
      errorDiv.id = "errorMessage";
      errorDiv.className = "alert alert-danger alert-dismissible fade show";
      errorDiv.innerHTML = `
                <span class="error-text"></span>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
      document
        .querySelector(".container")
        .insertBefore(errorDiv, document.querySelector(".date-filter-section"));
    }

    errorDiv.querySelector(".error-text").textContent = message;
    errorDiv.style.display = "block";

    // 5秒后自动隐藏
    setTimeout(() => {
      if (errorDiv) {
        errorDiv.style.display = "none";
      }
    }, 5000);
  }
}

// 页面加载完成后初始化
document.addEventListener("DOMContentLoaded", () => {
  new DataMiningPage();
});
