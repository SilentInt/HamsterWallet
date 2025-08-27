// 商品编辑组件
class ItemEditor {
  constructor() {
    this.modalId = "editItemModal";
    this.currentItem = null;
    this.onSaveCallback = null;
    this.categoryTree = null; // 缓存分类树数据
  }

  /**
   * 显示编辑商品模态框
   * @param {Object} item - 商品数据
   * @param {Function} onSave - 保存成功回调函数
   */
  async show(item, onSave = null) {
    this.currentItem = item;
    this.onSaveCallback = onSave;

    // 如果没有分类树数据，先加载
    if (!this.categoryTree) {
      await this.loadCategoryTree();
    }

    this.createModal();
    this.showModal();
  }

  /**
   * 加载分类树数据
   */
  async loadCategoryTree() {
    try {
      const response = await fetch("/api/category/tree");
      if (!response.ok) {
        throw new Error("获取分类数据失败");
      }
      const result = await response.json();
      if (result.success) {
        this.categoryTree = result.data || [];
      } else {
        throw new Error(result.message || "获取分类数据失败");
      }
    } catch (error) {
      console.error("加载分类树数据失败:", error);
      this.showToast("加载分类数据失败，将使用输入框模式", "warning");
      this.categoryTree = [];
    }
  }

  /**
   * 创建模态框HTML
   */
  createModal() {
    const item = this.currentItem;

    // 根据分类数据是否可用选择使用下拉框还是输入框
    const categoryHtml =
      this.categoryTree && this.categoryTree.length > 0
        ? `
        <div class="row">
          <div class="col-md-4">
            <div class="mb-3 category-select-group">
              <label class="form-label">
                <i class="fas fa-tags me-1"></i>一级分类
              </label>
              <select class="form-select" name="category_1" id="editCategory1">
                <option value="">请选择一级分类</option>
                ${this.generateLevel1Options()}
              </select>
            </div>
          </div>
          <div class="col-md-4">
            <div class="mb-3 category-select-group">
              <label class="form-label">二级分类</label>
              <select class="form-select" name="category_2" id="editCategory2" disabled>
                <option value="">请选择二级分类</option>
              </select>
            </div>
          </div>
          <div class="col-md-4">
            <div class="mb-3 category-select-group">
              <label class="form-label">三级分类</label>
              <select class="form-select" name="category_3" id="editCategory3" disabled>
                <option value="">请选择三级分类</option>
              </select>
              <input type="hidden" name="category_id" id="editCategoryId" value="${item.category_id || ''}" />
            </div>
          </div>
        </div>
      `
        : this.generateCategoryInputs(item);

    const modalHtml = `
      <div class="modal fade" id="${
        this.modalId
      }" tabindex="-1" aria-labelledby="${
      this.modalId
    }Label" aria-hidden="true">
        <div class="modal-dialog modal-lg">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title" id="${this.modalId}Label">
                <i class="fas fa-edit me-2"></i>编辑商品信息
              </h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <form id="editItemForm" data-item-id="${item.id}">
              <div class="modal-body">
                <div class="row">
                  <div class="col-md-6">
                    <div class="mb-3">
                      <label class="form-label">中文名称 <span class="text-danger">*</span></label>
                      <input type="text" class="form-control" name="name_zh" value="${
                        item.name_zh || ""
                      }" required />
                      <div class="form-text">请输入商品的中文名称</div>
                    </div>
                  </div>
                  <div class="col-md-6">
                    <div class="mb-3">
                      <label class="form-label">日文名称</label>
                      <input type="text" class="form-control" name="name_ja" value="${
                        item.name_ja || ""
                      }" />
                      <div class="form-text">商品的原始日文名称（可选）</div>
                    </div>
                  </div>
                </div>
                
                <div class="row">
                  <div class="col-md-6">
                    <div class="mb-3">
                      <label class="form-label">日元价格</label>
                      <div class="input-group">
                        <span class="input-group-text">¥</span>
                        <input type="number" step="0.01" class="form-control" name="price_jpy" value="${
                          item.price_jpy || ""
                        }" />
                      </div>
                    </div>
                  </div>
                  <div class="col-md-6">
                    <div class="mb-3">
                      <label class="form-label">人民币价格</label>
                      <div class="input-group">
                        <span class="input-group-text">￥</span>
                        <input type="number" step="0.01" class="form-control" name="price_cny" value="${
                          item.price_cny || ""
                        }" />
                      </div>
                    </div>
                  </div>
                </div>

                <div class="row">
                  <div class="col-md-6">
                    <div class="mb-3">
                      <div class="form-check form-switch">
                        <input class="form-check-input" type="checkbox" name="is_special_offer" id="editIsSpecialPrice" ${
                          item.is_special_offer ? "checked" : ""
                        }>
                        <label class="form-check-label" for="editIsSpecialPrice">
                          <i class="fas fa-percent me-1"></i>特价商品
                        </label>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div class="mb-3" id="specialInfoGroup" style="display: ${
                  item.is_special_offer ? "block" : "none"
                };">
                  <label class="form-label">
                    <i class="fas fa-tag me-1"></i>特价信息
                  </label>
                  <input type="text" class="form-control" name="special_info" value="${
                    item.special_info || ""
                  }" placeholder="例如：8折优惠、买一送一、限时特价等" />
                  <div class="form-text">描述具体的特价活动内容</div>
                </div>
                
                ${categoryHtml}
                
                <div class="mb-3">
                  <label class="form-label">
                    <i class="fas fa-comment me-1"></i>备注
                  </label>
                  <textarea class="form-control" name="notes" rows="3" placeholder="添加商品备注信息（可选）">${
                    item.notes || ""
                  }</textarea>
                  <div class="form-text">可以添加购买心得、使用体验等备注信息</div>
                </div>
              </div>
              <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                  <i class="fas fa-times me-2"></i>取消
                </button>
                <button type="submit" class="btn btn-primary">
                  <i class="fas fa-save me-2"></i>保存修改
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    `;

    // 移除已存在的模态框
    const existingModal = document.getElementById(this.modalId);
    if (existingModal) {
      existingModal.remove();
    }

    // 添加到页面
    document.body.insertAdjacentHTML("beforeend", modalHtml);

    // 设置事件监听器
    this.setupEventListeners();
  }

  /**
   * 生成一级分类选项HTML
   * @returns {string} 选项HTML字符串
   */
  generateLevel1Options() {
    if (!this.categoryTree || this.categoryTree.length === 0) {
      return "";
    }

    let options = "";
    this.categoryTree.forEach((category) => {
      options += `<option value="${category.id}">${category.name}</option>`;
    });
    return options;
  }

  /**
   * 生成二级分类选项HTML
   * @param {number} level1Id - 一级分类ID
   * @returns {string} 选项HTML字符串
   */
  generateLevel2Options(level1Id) {
    if (!this.categoryTree || !level1Id) return "";

    const level1Category = this.categoryTree.find(cat => cat.id == level1Id);
    if (!level1Category || !level1Category.children) return "";

    let options = "";
    level1Category.children.forEach((category) => {
      options += `<option value="${category.id}">${category.name}</option>`;
    });
    return options;
  }

  /**
   * 生成三级分类选项HTML
   * @param {number} level1Id - 一级分类ID
   * @param {number} level2Id - 二级分类ID
   * @returns {string} 选项HTML字符串
   */
  generateLevel3Options(level1Id, level2Id) {
    if (!this.categoryTree || !level1Id || !level2Id) return "";

    const level1Category = this.categoryTree.find(cat => cat.id == level1Id);
    if (!level1Category || !level1Category.children) return "";

    const level2Category = level1Category.children.find(cat => cat.id == level2Id);
    if (!level2Category || !level2Category.children) return "";

    let options = "";
    level2Category.children.forEach((category) => {
      options += `<option value="${category.id}">${category.name}</option>`;
    });
    return options;
  }

  /**
   * 根据category_id设置分类选择器
   * @param {number} categoryId - 分类ID
   */
  async setCategoryFromId(categoryId) {
    if (!this.categoryTree || !categoryId) return;

    // 查找对应的分类及其父分类
    let targetCategory = null;
    let level1Category = null;
    let level2Category = null;

    // 遍历查找目标分类
    for (const cat1 of this.categoryTree) {
      if (cat1.id == categoryId) {
        targetCategory = cat1;
        level1Category = cat1;
        break;
      }
      if (cat1.children) {
        for (const cat2 of cat1.children) {
          if (cat2.id == categoryId) {
            targetCategory = cat2;
            level1Category = cat1;
            level2Category = cat2;
            break;
          }
          if (cat2.children) {
            for (const cat3 of cat2.children) {
              if (cat3.id == categoryId) {
                targetCategory = cat3;
                level1Category = cat1;
                level2Category = cat2;
                break;
              }
            }
            if (targetCategory) break;
          }
        }
        if (targetCategory) break;
      }
    }

    if (targetCategory) {
      const category1Select = document.getElementById("editCategory1");
      const category2Select = document.getElementById("editCategory2");
      const category3Select = document.getElementById("editCategory3");
      const categoryIdInput = document.getElementById("editCategoryId");

      // 设置一级分类
      category1Select.value = level1Category.id;

      if (level2Category) {
        // 填充并设置二级分类
        category2Select.innerHTML = '<option value="">请选择二级分类</option>' + this.generateLevel2Options(level1Category.id);
        category2Select.disabled = false;
        category2Select.value = level2Category.id;

        if (targetCategory.level === 3) {
          // 填充并设置三级分类
          category3Select.innerHTML = '<option value="">请选择三级分类</option>' + this.generateLevel3Options(level1Category.id, level2Category.id);
          category3Select.disabled = false;
          category3Select.value = targetCategory.id;
          categoryIdInput.value = targetCategory.id;
        } else {
          categoryIdInput.value = level2Category.id;
        }
      } else {
        categoryIdInput.value = level1Category.id;
      }
    }
  }

  /**
   * 生成分类输入框（回退模式）
   * @param {Object} item - 商品数据
   * @returns {string} 输入框HTML字符串
   */
  generateCategoryInputs(item) {
    return `
      <div class="alert alert-info d-flex align-items-center mb-3">
        <i class="fas fa-info-circle me-2"></i>
        <small>分类数据加载失败，已切换到输入框模式。您可以手动输入分类信息。</small>
      </div>
      <div class="row">
        <div class="col-md-12">
          <div class="mb-3">
            <label class="form-label">
              <i class="fas fa-tags me-1"></i>分类ID
            </label>
            <input type="number" class="form-control" name="category_id" value="${
      item.category_id || ""
            }" placeholder="请输入分类ID" />
            <small class="form-text text-muted">请输入有效的分类ID，或联系管理员</small>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * 设置事件监听器
   */
  setupEventListeners() {
    const form = document.getElementById("editItemForm");
    const specialOfferCheckbox = document.getElementById("editIsSpecialPrice");
    const specialInfoGroup = document.getElementById("specialInfoGroup");

    // 分类选择框和隐藏的category_id字段
    const category1Select = document.getElementById("editCategory1");
    const category2Select = document.getElementById("editCategory2");
    const category3Select = document.getElementById("editCategory3");
    const categoryIdInput = document.getElementById("editCategoryId");

    // 特价商品切换事件
    specialOfferCheckbox.addEventListener("change", (e) => {
      if (e.target.checked) {
        specialInfoGroup.style.display = "block";
        // 添加淡入动画
        specialInfoGroup.style.opacity = "0";
        setTimeout(() => {
          specialInfoGroup.style.transition = "opacity 0.3s ease";
          specialInfoGroup.style.opacity = "1";
        }, 10);
      } else {
        specialInfoGroup.style.transition = "opacity 0.3s ease";
        specialInfoGroup.style.opacity = "0";
        setTimeout(() => {
          specialInfoGroup.style.display = "none";
          // 清空特价信息
          const specialInfoInput = specialInfoGroup.querySelector(
            'input[name="special_info"]'
          );
          if (specialInfoInput) {
            specialInfoInput.value = "";
          }
        }, 300);
      }
    });

    // 分类级联事件（仅在有分类选择框时设置）
    if (category1Select && category2Select && category3Select && categoryIdInput) {
    // 一级分类变化监听器
      category1Select.addEventListener("change", (e) => {
        const level1Id = e.target.value;

        // 重置后续级别
        category2Select.innerHTML = '<option value="">请选择二级分类</option>';
        category3Select.innerHTML = '<option value="">请选择三级分类</option>';
        category2Select.disabled = true;
        category3Select.disabled = true;

        if (level1Id) {
          // 填充二级分类选项
          const level2Options = this.generateLevel2Options(level1Id);
          if (level2Options) {
            category2Select.innerHTML = '<option value="">请选择二级分类</option>' + level2Options;
            category2Select.disabled = false;
          }
          // 如果没有二级分类，则直接设置category_id为一级分类ID
          const level1Category = this.categoryTree.find(cat => cat.id == level1Id);
          if (!level1Category.children || level1Category.children.length === 0) {
            categoryIdInput.value = level1Id;
          }
        } else {
          categoryIdInput.value = "";
        }
      });

      // 二级分类变化监听器
      category2Select.addEventListener("change", (e) => {
        const level2Id = e.target.value;
        const level1Id = category1Select.value;

        // 重置三级分类
        category3Select.innerHTML = '<option value="">请选择三级分类</option>';
        category3Select.disabled = true;

        if (level2Id && level1Id) {
          // 填充三级分类选项
          const level3Options = this.generateLevel3Options(level1Id, level2Id);
          if (level3Options) {
            category3Select.innerHTML = '<option value="">请选择三级分类</option>' + level3Options;
            category3Select.disabled = false;
          }
          // 如果没有三级分类，则设置category_id为二级分类ID
          const level1Category = this.categoryTree.find(cat => cat.id == level1Id);
          const level2Category = level1Category.children.find(cat => cat.id == level2Id);
          if (!level2Category.children || level2Category.children.length === 0) {
            categoryIdInput.value = level2Id;
          }
        } else {
          categoryIdInput.value = level1Id || "";
        }
      });

      // 三级分类变化监听器
      category3Select.addEventListener("change", (e) => {
        const level3Id = e.target.value;
        const level2Id = category2Select.value;

        if (level3Id) {
          categoryIdInput.value = level3Id;
        } else {
          categoryIdInput.value = level2Id || "";
        }
      });

      // 初始化分类选择状态（基于现有的category_id）
      if (this.currentItem && this.currentItem.category_id) {
        this.setCategoryFromId(this.currentItem.category_id);
      }
    }

    // 表单提交事件
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      this.handleFormSubmit(form);
    });

    // 模态框关闭事件
    const modal = document.getElementById(this.modalId);
    modal.addEventListener("hidden.bs.modal", () => {
      // 清理资源
      modal.remove();
    });
  }

  /**
   * 显示模态框
   */
  showModal() {
    const modal = new bootstrap.Modal(document.getElementById(this.modalId));
    modal.show();
  }

  /**
   * 处理表单提交
   */
  async handleFormSubmit(form) {
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    data.is_special_offer = formData.has("is_special_offer");
    const itemId = form.dataset.itemId;

    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;

    try {
      // 验证表单
      if (!this.validateForm(data)) {
        return;
      }

      // 显示加载状态
      this.setButtonLoading(submitBtn, true);

      const response = await fetch(`/api/items/${itemId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || "保存失败");
      }

      this.showToast("商品信息已更新", "success");

      // 关闭模态框
      const modal = bootstrap.Modal.getInstance(
        document.getElementById(this.modalId)
      );
      modal.hide();

      // 调用保存成功回调
      if (this.onSaveCallback) {
        this.onSaveCallback(data);
      }
    } catch (error) {
      console.error("保存商品信息失败:", error);
      this.showToast("保存失败: " + error.message, "error");

      // 添加表单错误动画
      form.classList.add("shake");
      setTimeout(() => form.classList.remove("shake"), 500);
    } finally {
      this.setButtonLoading(submitBtn, false, originalText);
    }
  }

  /**
   * 表单验证
   */
  validateForm(data) {
    // 检查必填字段
    if (!data.name_zh || data.name_zh.trim() === "") {
      this.showToast("请输入商品的中文名称", "error");
      const nameInput = document.querySelector('input[name="name_zh"]');
      nameInput.focus();
      nameInput.classList.add("is-invalid");
      setTimeout(() => nameInput.classList.remove("is-invalid"), 3000);
      return false;
    }

    // 检查价格合法性
    if (
      data.price_jpy &&
      (isNaN(data.price_jpy) || parseFloat(data.price_jpy) < 0)
    ) {
      this.showToast("日元价格必须是有效的正数", "error");
      return false;
    }

    if (
      data.price_cny &&
      (isNaN(data.price_cny) || parseFloat(data.price_cny) < 0)
    ) {
      this.showToast("人民币价格必须是有效的正数", "error");
      return false;
    }

    return true;
  }

  /**
   * 设置按钮加载状态
   */
  setButtonLoading(button, loading, originalText = "") {
    if (loading) {
      button.disabled = true;
      button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>保存中...';
    } else {
      button.disabled = false;
      button.innerHTML =
        originalText || '<i class="fas fa-save me-2"></i>保存修改';
    }
  }

  /**
   * 重新加载分类树数据
   */
  async reloadCategoryTree() {
    this.categoryTree = null;
    await this.loadCategoryTree();
  }

  /**
   * 显示Toast通知
   */
  showToast(message, type = "info") {
    // 创建toast元素
    const toast = document.createElement("div");
    toast.className = `toast-notification toast-${type}`;
    toast.innerHTML = `
      <div class="toast-content">
        <i class="fas ${
          type === "error"
            ? "fa-exclamation-circle"
            : type === "success"
            ? "fa-check-circle"
            : type === "warning"
            ? "fa-exclamation-triangle"
            : "fa-info-circle"
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
      setTimeout(() => {
        if (document.body.contains(toast)) {
          document.body.removeChild(toast);
        }
      }, 300);
    }, 3000);
  }
}

// 创建全局实例
window.ItemEditor = ItemEditor;
