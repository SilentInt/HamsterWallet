// 商品编辑组件
class ItemEditor {
  constructor() {
    this.modalId = "editItemModal";
    this.currentItem = null;
    this.onSaveCallback = null;
  }

  /**
   * 显示编辑商品模态框
   * @param {Object} item - 商品数据
   * @param {Function} onSave - 保存成功回调函数
   */
  show(item, onSave = null) {
    this.currentItem = item;
    this.onSaveCallback = onSave;
    this.createModal();
    this.showModal();
  }

  /**
   * 创建模态框HTML
   */
  createModal() {
    const item = this.currentItem;
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
                
                <div class="row">
                  <div class="col-md-4">
                    <div class="mb-3">
                      <label class="form-label">
                        <i class="fas fa-tags me-1"></i>一级分类
                      </label>
                      <input type="text" class="form-control" name="category_1" value="${
                        item.category_1 || ""
                      }" placeholder="例如：食品" />
                    </div>
                  </div>
                  <div class="col-md-4">
                    <div class="mb-3">
                      <label class="form-label">二级分类</label>
                      <input type="text" class="form-control" name="category_2" value="${
                        item.category_2 || ""
                      }" placeholder="例如：零食" />
                    </div>
                  </div>
                  <div class="col-md-4">
                    <div class="mb-3">
                      <label class="form-label">三级分类</label>
                      <input type="text" class="form-control" name="category_3" value="${
                        item.category_3 || ""
                      }" placeholder="例如：饼干" />
                    </div>
                  </div>
                </div>
                
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
   * 设置事件监听器
   */
  setupEventListeners() {
    const form = document.getElementById("editItemForm");
    const specialOfferCheckbox = document.getElementById("editIsSpecialPrice");
    const specialInfoGroup = document.getElementById("specialInfoGroup");

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
