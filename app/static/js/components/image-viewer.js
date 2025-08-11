// 图片查看器组件

import { DOM } from "../utils/common.js";

class ImageViewer {
  constructor() {
    this.modal = null;
    this.currentImage = null;
    this.init();
  }

  /**
   * 初始化图片查看器
   */
  init() {
    this.createModal();
    this.bindEvents();
  }

  /**
   * 创建模态框
   */
  createModal() {
    const modalHtml = `
      <div class="modal fade" id="imageModal" tabindex="-1">
        <div class="modal-dialog modal-xl modal-dialog-centered">
          <div class="modal-content bg-transparent border-0">
            <div class="modal-header bg-dark text-white">
              <h5 class="modal-title" id="imageModalTitle">查看图片</h5>
              <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body p-0 bg-dark d-flex align-items-center justify-content-center">
              <img id="imageModalImg" class="img-fluid" style="max-height: 80vh; object-fit: contain;" />
            </div>
            <div class="modal-footer bg-dark text-white justify-content-between">
              <div class="image-info">
                <span id="imageInfo"></span>
              </div>
              <div class="image-controls">
                <button type="button" class="btn btn-outline-light btn-sm" id="zoomOut">
                  <i class="fas fa-search-minus"></i>
                </button>
                <button type="button" class="btn btn-outline-light btn-sm" id="zoomIn">
                  <i class="fas fa-search-plus"></i>
                </button>
                <button type="button" class="btn btn-outline-light btn-sm" id="resetZoom">
                  <i class="fas fa-expand-arrows-alt"></i>
                </button>
                <button type="button" class="btn btn-outline-light btn-sm" id="downloadImage">
                  <i class="fas fa-download"></i>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    const modalElement = DOM.create("div", { innerHTML: modalHtml });
    this.modal = modalElement.firstElementChild;
    document.body.appendChild(this.modal);

    // 获取元素引用
    this.modalTitle = DOM.$("#imageModalTitle", this.modal);
    this.modalImg = DOM.$("#imageModalImg", this.modal);
    this.imageInfo = DOM.$("#imageInfo", this.modal);
    this.zoomOutBtn = DOM.$("#zoomOut", this.modal);
    this.zoomInBtn = DOM.$("#zoomIn", this.modal);
    this.resetZoomBtn = DOM.$("#resetZoom", this.modal);
    this.downloadBtn = DOM.$("#downloadImage", this.modal);

    this.scale = 1;
    this.minScale = 0.1;
    this.maxScale = 5;
    this.scaleStep = 0.1;
  }

  /**
   * 绑定事件
   */
  bindEvents() {
    // 关闭按钮
    const closeBtn = DOM.$(".btn-close", this.modal);
    DOM.on(closeBtn, "click", () => this.hide());

    // 点击背景关闭
    DOM.on(this.modal, "click", (e) => {
      if (
        e.target === this.modal ||
        e.target.classList.contains("modal-body")
      ) {
        this.hide();
      }
    });

    // 缩放控制
    DOM.on(this.zoomInBtn, "click", () => this.zoomIn());
    DOM.on(this.zoomOutBtn, "click", () => this.zoomOut());
    DOM.on(this.resetZoomBtn, "click", () => this.resetZoom());

    // 下载按钮
    DOM.on(this.downloadBtn, "click", () => this.downloadImage());

    // 键盘控制
    DOM.on(document, "keydown", (e) => {
      if (this.isVisible()) {
        switch (e.key) {
          case "Escape":
            this.hide();
            break;
          case "+":
          case "=":
            e.preventDefault();
            this.zoomIn();
            break;
          case "-":
            e.preventDefault();
            this.zoomOut();
            break;
          case "0":
            e.preventDefault();
            this.resetZoom();
            break;
        }
      }
    });

    // 鼠标滚轮缩放
    DOM.on(this.modalImg, "wheel", (e) => {
      e.preventDefault();
      if (e.deltaY < 0) {
        this.zoomIn();
      } else {
        this.zoomOut();
      }
    });

    // 拖拽功能
    this.setupDrag();

    // 自动绑定图片点击事件
    this.bindImageClicks();
  }

  /**
   * 设置拖拽功能
   */
  setupDrag() {
    let isDragging = false;
    let startX, startY, startLeft, startTop;

    DOM.on(this.modalImg, "mousedown", (e) => {
      if (this.scale > 1) {
        isDragging = true;
        startX = e.clientX;
        startY = e.clientY;
        startLeft = this.modalImg.offsetLeft;
        startTop = this.modalImg.offsetTop;
        this.modalImg.style.cursor = "grabbing";
        e.preventDefault();
      }
    });

    DOM.on(document, "mousemove", (e) => {
      if (isDragging) {
        const deltaX = e.clientX - startX;
        const deltaY = e.clientY - startY;
        this.modalImg.style.left = startLeft + deltaX + "px";
        this.modalImg.style.top = startTop + deltaY + "px";
      }
    });

    DOM.on(document, "mouseup", () => {
      if (isDragging) {
        isDragging = false;
        this.modalImg.style.cursor = this.scale > 1 ? "grab" : "default";
      }
    });
  }

  /**
   * 自动绑定图片点击事件
   */
  bindImageClicks() {
    // 使用事件委托自动绑定所有图片
    DOM.delegate(document, 'img[data-bs-toggle="modal"]', "click", (e) => {
      const img = e.target;
      const src = img.src || img.dataset.src;
      const title = img.alt || img.dataset.title || "图片查看";
      this.show(src, title);
    });

    // 兼容旧版本的点击事件
    DOM.delegate(document, ".image-preview", "click", (e) => {
      const img = e.target.closest(".image-preview");
      const src = img.dataset.src || img.src;
      const title = img.dataset.title || img.alt || "图片查看";
      this.show(src, title);
    });
  }

  /**
   * 显示图片
   * @param {string} imageUrl - 图片URL
   * @param {string} title - 标题
   */
  show(imageUrl, title = "查看图片") {
    if (!imageUrl) return;

    this.currentImage = imageUrl;

    // 设置标题
    this.modalTitle.textContent = title;

    // 显示加载状态
    this.modalImg.style.opacity = "0.5";
    this.imageInfo.textContent = "加载中...";

    // 重置缩放
    this.resetZoom();

    // 加载图片
    const img = new Image();
    img.onload = () => {
      this.modalImg.src = imageUrl;
      this.modalImg.style.opacity = "1";
      this.updateImageInfo(img.naturalWidth, img.naturalHeight);
    };
    img.onerror = () => {
      this.imageInfo.textContent = "图片加载失败";
      this.modalImg.style.opacity = "1";
    };
    img.src = imageUrl;

    // 显示模态框
    this.modal.style.display = "block";
    DOM.addClass(this.modal, "show");
    document.body.style.overflow = "hidden";
  }

  /**
   * 隐藏图片查看器
   */
  hide() {
    this.modal.style.display = "none";
    DOM.removeClass(this.modal, "show");
    document.body.style.overflow = "";
    this.currentImage = null;
  }

  /**
   * 检查是否可见
   * @returns {boolean}
   */
  isVisible() {
    return DOM.hasClass(this.modal, "show");
  }

  /**
   * 放大图片
   */
  zoomIn() {
    if (this.scale < this.maxScale) {
      this.scale = Math.min(this.scale + this.scaleStep, this.maxScale);
      this.applyZoom();
    }
  }

  /**
   * 缩小图片
   */
  zoomOut() {
    if (this.scale > this.minScale) {
      this.scale = Math.max(this.scale - this.scaleStep, this.minScale);
      this.applyZoom();
    }
  }

  /**
   * 重置缩放
   */
  resetZoom() {
    this.scale = 1;
    this.applyZoom();
    // 重置位置
    this.modalImg.style.left = "";
    this.modalImg.style.top = "";
  }

  /**
   * 应用缩放
   */
  applyZoom() {
    this.modalImg.style.transform = `scale(${this.scale})`;
    this.modalImg.style.cursor = this.scale > 1 ? "grab" : "default";

    // 更新按钮状态
    this.zoomInBtn.disabled = this.scale >= this.maxScale;
    this.zoomOutBtn.disabled = this.scale <= this.minScale;
  }

  /**
   * 更新图片信息
   * @param {number} width - 宽度
   * @param {number} height - 高度
   */
  updateImageInfo(width, height) {
    const sizeText = `${width} × ${height}`;
    const scaleText = `${Math.round(this.scale * 100)}%`;
    this.imageInfo.textContent = `${sizeText} | ${scaleText}`;
  }

  /**
   * 下载图片
   */
  downloadImage() {
    if (!this.currentImage) return;

    const link = DOM.create("a", {
      attributes: {
        href: this.currentImage,
        download: this.getImageName(this.currentImage),
        target: "_blank",
      },
    });

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  /**
   * 获取图片文件名
   * @param {string} url - 图片URL
   * @returns {string}
   */
  getImageName(url) {
    const urlParts = url.split("/");
    const filename = urlParts[urlParts.length - 1];
    return filename || "image.jpg";
  }
}

// 全局函数，兼容旧版本
window.showImageModal = function (imageUrl, title) {
  if (window.imageViewer) {
    window.imageViewer.show(imageUrl, title);
  }
};

// 自动初始化
document.addEventListener("DOMContentLoaded", () => {
  window.imageViewer = new ImageViewer();
});

export default ImageViewer;
