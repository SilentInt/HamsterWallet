# API 快速参考

## 🚀 快速开始

**基础URL**: `http://localhost:5000`

## 📋 核心字段

### 小票字段
```json
{
  "name": "小票名称",
  "store_name": "店铺名称", 
  "store_category": "店铺分类",
  "notes": "备注",
  "transaction_time": "交易时间"
}
```

### 商品字段  
```json
{
  "name_zh": "中文名称",
  "name_ja": "日文名称",
  "price_cny": 15.8,
  "price_jpy": 298,
  "category_1": "一级分类",
  "category_2": "二级分类", 
  "category_3": "三级分类",
  "special_info": "特价信息",
  "notes": "备注"
}
```

## 🔗 API端点

### 小票管理
- `GET /receipts` - 获取小票列表
- `POST /receipts` - 创建小票 (multipart/form-data)
- `GET /receipts/{id}` - 获取单个小票
- `PUT /receipts/{id}` - 更新小票
- `DELETE /receipts/{id}` - 删除小票
- `POST /receipts/{id}/recognize` - 触发AI识别

### 商品管理
- `GET /items` - 获取商品列表
- `POST /receipts/{receipt_id}/items` - 创建商品
- `GET /items/{id}` - 获取单个商品
- `PUT /items/{id}` - 更新商品
- `DELETE /items/{id}` - 删除商品

## 📊 响应格式

### 列表响应
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 10,
    "total_pages": 5,
    "total_items": 42
  }
}
```

### 错误响应
```json
{
  "message": "错误描述"
}
```

## 🔧 状态码
- `200` - 成功
- `201` - 创建成功  
- `202` - 已接受
- `204` - 删除成功
- `400` - 请求错误
- `404` - 未找到

## 💡 使用示例

### 创建小票
```bash
curl -X POST http://localhost:5000/receipts \
  -F "image=@receipt.jpg" \
  -F "name=便利店购物"
```

### 添加商品
```bash
curl -X POST http://localhost:5000/receipts/1/items \
  -H "Content-Type: application/json" \
  -d '{
    "name_zh": "苹果",
    "price_cny": 15.8,
    "category_1": "食品"
  }'
```

### 查询参数
- `page` - 页码
- `per_page` - 每页数量
- `search` - 搜索关键词
- `category_1` - 分类筛选
- `receipt_id` - 小票筛选
