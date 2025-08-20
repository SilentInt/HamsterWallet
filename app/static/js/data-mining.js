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
    this.editingGroupId = null; // 当前正在编辑的对比组ID

    this.init();
  }

  init() {
    this.initDateFilters();
    this.bindEvents();
    this.loadCategoryTree();
    this.loadSavedComparisonGroups();
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
    const autoSave = document.getElementById("autoSaveComparison").checked;
    
    if (!name) {
      alert("请输入对比组名称");
      return;
    }

    const comparisonGroup = {
      id: Date.now().toString(),
      name: name,
      categories: [...this.selectedCategories],
      data: null,
    };

    this.comparisonGroups.push(comparisonGroup);
    this.renderComparisonGroups();
    this.clearSelection();

    // 获取对比数据
    this.updateComparison(comparisonGroup);

    // 如果选择自动保存，立即保存对比组
    if (autoSave) {
      this.saveComparisonGroup(comparisonGroup);
    }

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
      
      // 判断是否为已保存的对比组和是否处于编辑状态
      const isSaved = group.savedId !== undefined;
      const isEditing = this.editingGroupId === group.id;
      
      // 添加状态相关的CSS类
      if (isSaved) item.classList.add("saved");
      if (isEditing) item.classList.add("editing");
      
      // 根据状态决定显示的按钮
      let actionButtons = '';
      
      if (isEditing) {
        // 编辑模式：显示保存和取消按钮
        actionButtons = `
          <button class="btn btn-success btn-sm save-edit" data-id="${group.id}" title="保存编辑">
            <i class="fas fa-check"></i> 保存
          </button>
          <button class="btn btn-secondary btn-sm cancel-edit" data-id="${group.id}" title="取消编辑">
            <i class="fas fa-times"></i> 取消
          </button>
        `;
      } else {
        // 普通模式：显示编辑、保存（如果未保存）、删除按钮
        const saveButton = isSaved ? '' : `
          <button class="btn btn-outline-success btn-sm save-group" data-id="${group.id}" title="保存对比组">
            <i class="fas fa-save"></i>
          </button>
        `;
        
        actionButtons = `
          ${saveButton}
          <button class="btn btn-outline-primary btn-sm edit-group" data-id="${group.id}" title="编辑对比组">
            <i class="fas fa-edit"></i>
          </button>
          <button class="btn btn-outline-danger btn-sm remove-group" data-id="${group.id}" title="删除对比组">
            <i class="fas fa-trash"></i>
          </button>
        `;
      }
      
      // 名称显示：编辑模式下显示输入框，普通模式下显示文本
      let nameDisplay;
      if (isEditing) {
        nameDisplay = `
          <input type="text" class="form-control form-control-sm group-name-input" 
                 value="${group.name}" data-id="${group.id}" placeholder="输入对比组名称">
        `;
      } else {
        nameDisplay = `
          <div class="group-name" data-id="${group.id}">
            ${group.name}${isSaved ? ' <i class="fas fa-bookmark text-success" title="已保存"></i>' : ''}
          </div>
        `;
      }
      
      item.innerHTML = `
        <div class="group-info">
          ${nameDisplay}
          <div class="group-categories">
            ${group.categories.map((cat) => cat.name).join(", ")}
            ${isEditing ? ' <small class="text-muted">(正在编辑分类选择)</small>' : ''}
          </div>
        </div>
        <div class="group-actions">
          ${actionButtons}
        </div>
      `;

      // 绑定事件
      this.bindGroupItemEvents(item, group, isEditing);
      container.appendChild(item);
    });
  }

  bindGroupItemEvents(item, group, isEditing) {
    if (isEditing) {
      // 编辑模式的事件绑定
      const nameInput = item.querySelector(".group-name-input");
      const saveEditBtn = item.querySelector(".save-edit");
      const cancelEditBtn = item.querySelector(".cancel-edit");

      // 输入框回车保存
      nameInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          this.saveGroupEdit(group.id);
        } else if (e.key === "Escape") {
          this.cancelGroupEdit();
        }
      });

      // 保存编辑按钮
      saveEditBtn.addEventListener("click", () => {
        this.saveGroupEdit(group.id);
      });

      // 取消编辑按钮
      cancelEditBtn.addEventListener("click", () => {
        this.cancelGroupEdit();
      });

      // 自动聚焦到输入框
      setTimeout(() => {
        nameInput.focus();
        nameInput.select();
      }, 0);

    } else {
      // 普通模式的事件绑定
      const saveBtn = item.querySelector(".save-group");
      const editBtn = item.querySelector(".edit-group");
      const removeBtn = item.querySelector(".remove-group");

      // 保存对比组按钮
      if (saveBtn) {
        saveBtn.addEventListener("click", async () => {
          const success = await this.saveComparisonGroup(group);
          if (success) {
            this.renderComparisonGroups();
          }
        });
      }

      // 编辑对比组按钮
      editBtn.addEventListener("click", () => {
        this.startEditGroup(group.id);
      });

      // 删除对比组按钮
      removeBtn.addEventListener("click", () => {
        // 使用全局确认删除模态框
        window.confirmDelete({
          title: "删除对比组",
          message: `您确定要删除对比组 "${group.name}" 吗？`,
          itemName: group.name,
          onConfirm: async () => {
            return await this.removeComparisonGroup(group.id);
          }
        });
      });
    }
  }

  startEditGroup(groupId) {
    const group = this.comparisonGroups.find(g => g.id === groupId);
    if (!group) return;

    // 设置编辑状态
    this.editingGroupId = groupId;

    // 将对比组的分类还原到选择器中
    this.selectedCategories = [...group.categories];

    // 重新渲染分类选择器和对比组列表
    this.renderCurrentLevel();
    this.renderComparisonGroups();
    this.updateSelectionCounter();
    this.updateAddComparisonButton();
  }

  async saveGroupEdit(groupId) {
    const group = this.comparisonGroups.find(g => g.id === groupId);
    if (!group) {
      this.showError('找不到要编辑的对比组');
      return;
    }

    // 获取新名称
    const nameInput = document.querySelector(`.group-name-input[data-id="${groupId}"]`);
    const newName = nameInput ? nameInput.value.trim() : "";

    if (!newName) {
      this.showError("对比组名称不能为空");
      return;
    }

    // 更新分类（从选择器中获取）
    const newCategories = [...this.selectedCategories];
    if (newCategories.length === 0) {
      this.showError("至少需要选择一个分类");
      return;
    }

    // 保存原始数据以便失败时恢复
    const originalName = group.name;
    const originalCategories = [...group.categories];

    // 显示保存中状态
    this.showLoadingState(groupId, true);

    let saveSuccess = false;

    try {
      // 更新对比组数据
      group.name = newName;
      group.categories = newCategories;

      // 如果是已保存的对比组，同步到服务器
      if (group.savedId) {
        // 更新名称
        const nameSuccess = await this.updateSavedGroupName(group, newName);
        if (!nameSuccess) {
          // 恢复原始数据
          group.name = originalName;
          group.categories = originalCategories;
          saveSuccess = false;
        } else {
          // 同时更新分类数据到服务器
          try {
            const response = await fetch(`/api/data-mining/groups/${group.savedId}`, {
              method: 'PUT',
              headers: {
                'Content-Type': 'application/json'
              },
              body: JSON.stringify({
                name: newName,
                categories: newCategories
              })
            });
            
            const result = await response.json();
            if (!result.success) {
              this.showError(result.message || '更新对比组失败');
              // 恢复原始数据
              group.name = originalName;
              group.categories = originalCategories;
              saveSuccess = false;
            } else {
              saveSuccess = true;
            }
          } catch (error) {
            console.error('更新对比组出错:', error);
            this.showError('网络错误，更新失败');
            // 恢复原始数据
            group.name = originalName;
            group.categories = originalCategories;
            saveSuccess = false;
          }
        }
      } else {
        // 未保存的对比组，直接标记为成功
        saveSuccess = true;
      }

      if (saveSuccess) {
        // 重新获取对比数据
        await this.updateComparison(group);
        this.showSuccess('对比组更新成功');
      }

    } catch (error) {
      console.error('保存编辑出错:', error);
      this.showError('保存编辑时发生错误');
      
      // 恢复原始数据
      group.name = originalName;
      group.categories = originalCategories;
      saveSuccess = false;
    } finally {
      // 无论成功还是失败，都要清除编辑状态和更新界面
      this.showLoadingState(groupId, false);
      
      // 结束编辑状态
      this.editingGroupId = null;
      this.selectedCategories = [];

      // 重新渲染界面
      this.renderCurrentLevel();
      this.renderComparisonGroups();
      this.updateSelectionCounter();
      this.updateAddComparisonButton();
      
      if (saveSuccess) {
        this.updateChart();
      }
    }
  }

  cancelGroupEdit() {
    // 结束编辑状态
    this.editingGroupId = null;
    this.selectedCategories = [];

    // 重新渲染界面
    this.renderCurrentLevel();
    this.renderComparisonGroups();
    this.updateSelectionCounter();
    this.updateAddComparisonButton();
  }

  async removeComparisonGroup(groupId) {
    try {
      const group = this.comparisonGroups.find(g => g.id === groupId);
      if (!group) {
        this.showError('找不到要删除的对比组');
        return false;
      }
      
      // 如果是已保存的对比组，先从服务器删除
      if (group.savedId) {
        const success = await this.deleteSavedGroup(group);
        if (!success) {
          return false; // 删除失败
        }
      }
      
      // 从本地列表中移除
      this.comparisonGroups = this.comparisonGroups.filter(g => g.id !== groupId);
      
      // 如果删除的是正在编辑的对比组，清除编辑状态
      if (this.editingGroupId === groupId) {
        this.editingGroupId = null;
        this.selectedCategories = [];
        this.updateSelectionCounter();
        this.updateAddComparisonButton();
      }
      
      // 重新渲染界面
      this.renderComparisonGroups();
      this.updateChart();
      
      // 显示成功消息
      this.showSuccess(`对比组 "${group.name}" 删除成功`);
      return true;
      
    } catch (error) {
      console.error('删除对比组出错:', error);
      this.showError('删除对比组时发生错误');
      return false;
    }
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
  
  async loadSavedComparisonGroups() {
    try {
      const response = await fetch('/api/data-mining/groups');
      const result = await response.json();
      
      if (result.success) {
        // 将保存的对比组转换为本地格式并添加到列表
        const savedGroups = result.data.map(savedGroup => ({
          id: `saved_${savedGroup.id}`,
          savedId: savedGroup.id,
          name: savedGroup.name,
          categories: savedGroup.categories,
          data: null,
          isSaved: true
        }));
        
        this.comparisonGroups.push(...savedGroups);
        this.renderComparisonGroups();
        
        // 为保存的对比组加载数据
        for (const group of savedGroups) {
          await this.updateComparison(group);
        }
      } else {
        this.showError(result.message || '获取保存的对比组失败');
      }
    } catch (error) {
      console.error('加载保存的对比组出错:', error);
      this.showError('网络错误，加载失败');
    }
  }
  
  async saveComparisonGroup(group) {
    try {
      const response = await fetch('/api/data-mining/groups', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: group.name,
          categories: group.categories
        })
      });
      
      const result = await response.json();
      
      if (result.success) {
        // 更新本地组的保存状态
        group.savedId = result.data.id;
        group.id = `saved_${result.data.id}`;
        group.isSaved = true;
        
        this.renderComparisonGroups();
        this.showSuccess('对比组保存成功');
        return true;
      } else {
        this.showError(result.message || '保存对比组失败');
        return false;
      }
    } catch (error) {
      console.error('保存对比组出错:', error);
      this.showError('网络错误，保存失败');
      return false;
    }
  }
  
  async updateSavedGroupName(group, newName) {
    if (!group.savedId) {
      group.name = newName;
      return true;
    }
    
    try {
      const response = await fetch(`/api/data-mining/groups/${group.savedId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name: newName })
      });
      
      const result = await response.json();
      
      if (result.success) {
        group.name = newName;
        this.showSuccess('对比组名称更新成功');
        return true;
      } else {
        this.showError(result.message || '更新对比组名称失败');
        return false;
      }
    } catch (error) {
      console.error('更新对比组名称出错:', error);
      this.showError('网络错误，更新失败');
      return false;
    }
  }
  
  async deleteSavedGroup(group) {
    if (!group.savedId) return true;
    
    try {
      const response = await fetch(`/api/data-mining/groups/${group.savedId}`, {
        method: 'DELETE'
      });
      
      const result = await response.json();
      
      if (result.success) {
        return true;
      } else {
        this.showError(result.message || '删除对比组失败');
        return false;
      }
    } catch (error) {
      console.error('删除对比组出错:', error);
      this.showError('网络错误，删除失败');
      return false;
    }
  }
  
  showSuccess(message) {
    let successDiv = document.getElementById('success-message');
    if (!successDiv) {
      successDiv = document.createElement('div');
      successDiv.id = 'success-message';
      successDiv.className = 'alert alert-success alert-dismissible fade show';
      successDiv.style.display = 'none';
      successDiv.innerHTML = `
                <span class="success-text"></span>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
      document
        .querySelector('.container')
        .insertBefore(successDiv, document.querySelector('.date-filter-section'));
    }
    
    successDiv.querySelector('.success-text').textContent = message;
    successDiv.style.display = 'block';
    
    // 3秒后自动隐藏
    setTimeout(() => {
      if (successDiv) {
        successDiv.style.display = 'none';
      }
    }, 3000);
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

  showLoadingState(groupId, isLoading) {
    const saveButton = document.querySelector(`.save-edit[data-id="${groupId}"]`);
    const cancelButton = document.querySelector(`.cancel-edit[data-id="${groupId}"]`);
    const nameInput = document.querySelector(`.group-name-input[data-id="${groupId}"]`);
    
    if (saveButton) {
      if (isLoading) {
        saveButton.disabled = true;
        saveButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 保存中...';
      } else {
        saveButton.disabled = false;
        saveButton.innerHTML = '<i class="fas fa-check"></i> 保存';
      }
    }
    
    if (cancelButton) {
      cancelButton.disabled = isLoading;
    }
    
    if (nameInput) {
      nameInput.disabled = isLoading;
    }
  }
}

// 页面加载完成后初始化
document.addEventListener("DOMContentLoaded", () => {
  new DataMiningPage();
});
