# HamsterWallet API 文档

## 📋 概述

HamsterWallet API 提供小票管理和AI识别功能。所有字段名称严格遵循AI prompt中定义的标准，确保前端、后端、AI服务的数据一致性。

**基础URL**: `http://localhost:5000`

**内容类型**: `application/json` (除文件上传外)

## 🎯 AI标准字段规范

### 小票字段 (Receipt Fields)
| 字段名 | 类型 | 描述 | 示例 |
|--------|------|------|------|
| `name` | string | 小票名称 | "2024-01-15_日用品_全家" |
| `store_name` | string | 店铺名称 | "全家便利店" |
| `store_category` | string | 店铺分类 | "便利店" |
| `notes` | string | 备注信息 | "购买日用品" |
| `transaction_time` | string | 交易时间 | "2024-01-15 14:30:00" |

### 商品字段 (Item Fields)
| 字段名 | 类型 | 描述 | 示例 |
|--------|------|------|------|
| `name_ja` | string | 日文名称 | "りんご" |
| `name_zh` | string | 中文名称 | "苹果" |
| `category_1` | string | 一级分类 | "食品" |
| `category_2` | string | 二级分类 | "水果" |
| `category_3` | string | 三级分类 | "新鲜水果" |
| `price_jpy` | number | 日元价格 | 298 |
| `price_cny` | number | 人民币价格 | 15.8 |
| `special_info` | string | 特价信息 | "特价商品" 或 "否" |
| `notes` | string | 商品备注 | "用户添加的备注" |

### 自动字段
| 字段名 | 类型 | 描述 | 生成规则 |
|--------|------|------|----------|
| `is_special_offer` | boolean | 是否特价 | 当 `special_info` 不为 "否"/""/null 时为 true |

---

## 📁 小票 API

### 1. 获取小票列表

**GET** `/receipts`

**查询参数**:
- `page` (int, 可选): 页码，默认 1
- `per_page` (int, 可选): 每页数量，默认 10
- `search` (string, 可选): 搜索关键词

**响应**:
```json
{
  "data": [
    {
      "id": 1,
      "name": "2024-01-15_日用品_全家",
      "store_name": "全家便利店",
      "store_category": "便利店",
      "notes": "购买日用品",
      "transaction_time": "2024-01-15 14:30:00",
      "status": "COMPLETED",
      "image_path": "/uploads/receipt1.jpg",
      "created_at": "2024-01-15T14:35:00Z",
      "updated_at": "2024-01-15T14:40:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 10,
    "total_pages": 5,
    "total_items": 42
  }
}
```

### 2. 创建小票

**POST** `/receipts`

**内容类型**: `multipart/form-data`

**请求参数**:
- `image` (file, 可选): 小票图片文件
- `name` (string, 可选): 小票名称
- `store_name` (string, 可选): 店铺名称
- `store_category` (string, 可选): 店铺分类
- `notes` (string, 可选): 备注信息
- `text_description` (string, 可选): 文字描述

**注意**: 必须提供 `image`、`text_description` 或 `name` 中的至少一个

**示例请求**:
```bash
curl -X POST http://localhost:5000/receipts \
  -F "image=@receipt.jpg" \
  -F "name=测试小票" \
  -F "store_name=便利店" \
  -F "notes=测试用途"
```

**响应**:
```json
{
  "id": 1,
  "name": "测试小票",
  "store_name": "便利店",
  "store_category": null,
  "notes": "测试用途",
  "transaction_time": null,
  "status": "PENDING",
  "image_path": "/uploads/abc123.jpg",
  "created_at": "2024-01-15T14:35:00Z",
  "updated_at": "2024-01-15T14:35:00Z"
}
```

### 3. 获取单个小票

**GET** `/receipts/{receipt_id}`

**路径参数**:
- `receipt_id` (int): 小票ID

**响应**:
```json
{
  "id": 1,
  "name": "2024-01-15_日用品_全家",
  "store_name": "全家便利店",
  "store_category": "便利店",
  "notes": "购买日用品",
  "transaction_time": "2024-01-15 14:30:00",
  "status": "COMPLETED",
  "image_path": "/uploads/receipt1.jpg",
  "created_at": "2024-01-15T14:35:00Z",
  "updated_at": "2024-01-15T14:40:00Z"
}
```

### 4. 更新小票

**PUT** `/receipts/{receipt_id}`

**路径参数**:
- `receipt_id` (int): 小票ID

**请求体**:
```json
{
  "name": "更新后的小票名称",
  "store_name": "更新后的店铺",
  "store_category": "超市",
  "notes": "更新后的备注"
}
```

**响应**: 返回更新后的小票信息 (同获取单个小票)

### 5. 删除小票

**DELETE** `/receipts/{receipt_id}`

**路径参数**:
- `receipt_id` (int): 小票ID

**响应**: `204 No Content`

### 6. 触发小票识别

**POST** `/receipts/{receipt_id}/recognize`

**路径参数**:
- `receipt_id` (int): 小票ID

**响应**:
```json
{
  "message": "已加入重新识别队列"
}
```

---

## 🛍️ 商品 API

### 1. 获取商品列表

**GET** `/items`

**查询参数**:
- `page` (int, 可选): 页码，默认 1
- `per_page` (int, 可选): 每页数量，默认 10
- `search` (string, 可选): 搜索关键词
- `category_1` (string, 可选): 按一级分类筛选
- `receipt_id` (int, 可选): 按小票ID筛选

**响应**:
```json
{
  "data": [
    {
      "id": 1,
      "receipt_id": 1,
      "name_ja": "りんご",
      "name_zh": "苹果",
      "category_1": "食品",
      "category_2": "水果",
      "category_3": "新鲜水果",
      "price_jpy": 298,
      "price_cny": 15.8,
      "special_info": "特价商品",
      "is_special_offer": true,
      "notes": "新鲜脆甜",
      "created_at": "2024-01-15T14:40:00Z",
      "updated_at": "2024-01-15T14:40:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 10,
    "total_pages": 3,
    "total_items": 25
  }
}
```

### 2. 创建商品项目

**POST** `/receipts/{receipt_id}/items`

**路径参数**:
- `receipt_id` (int): 小票ID

**请求体**:
```json
{
  "name_zh": "苹果",
  "name_ja": "りんご",
  "price_cny": 15.80,
  "price_jpy": 298,
  "category_1": "食品",
  "category_2": "水果",
  "category_3": "新鲜水果",
  "special_info": "特价商品",
  "notes": "新鲜脆甜"
}
```

**响应**:
```json
{
  "id": 1,
  "receipt_id": 1,
  "name_ja": "りんご",
  "name_zh": "苹果",
  "category_1": "食品",
  "category_2": "水果",
  "category_3": "新鲜水果",
  "price_jpy": 298,
  "price_cny": 15.8,
  "special_info": "特价商品",
  "is_special_offer": true,
  "notes": "新鲜脆甜",
  "created_at": "2024-01-15T14:40:00Z",
  "updated_at": "2024-01-15T14:40:00Z"
}
```

### 3. 获取单个商品

**GET** `/items/{item_id}`

**路径参数**:
- `item_id` (int): 商品ID

**响应**: 返回单个商品信息 (同创建商品响应)

### 4. 更新商品

**PUT** `/items/{item_id}`

**路径参数**:
- `item_id` (int): 商品ID

**请求体**:
```json
{
  "name_zh": "更新后的苹果",
  "name_ja": "更新されたりんご",
  "price_cny": 18.50,
  "price_jpy": 350,
  "category_1": "食品饮料",
  "category_2": "新鲜水果",
  "category_3": "进口水果",
  "special_info": "否",
  "notes": "更新后的商品备注"
}
```

**响应**: 返回更新后的商品信息

### 5. 删除商品

**DELETE** `/items/{item_id}`

**路径参数**:
- `item_id` (int): 商品ID

**响应**: `204 No Content`

---

## 🔧 状态码说明

| 状态码 | 含义 | 说明 |
|--------|------|------|
| 200 | OK | 请求成功 |
| 201 | Created | 资源创建成功 |
| 202 | Accepted | 请求已接受，异步处理中 |
| 204 | No Content | 请求成功，无返回内容 |
| 400 | Bad Request | 请求参数错误 |
| 404 | Not Found | 资源不存在 |
| 500 | Internal Server Error | 服务器内部错误 |

---

## 📝 错误响应格式

```json
{
  "message": "错误描述",
  "error": "ERROR_CODE",
  "details": {
    "field": "错误字段",
    "reason": "具体原因"
  }
}
```

### 常见错误示例

**400 Bad Request - 缺少必需字段**:
```json
{
  "message": "创建小票需要提供图片、文字描述或名称"
}
```

**404 Not Found - 资源不存在**:
```json
{
  "message": "The requested URL was not found on the server."
}
```

---

## 🔄 AI识别状态

小票识别状态说明：

| 状态 | 英文 | 描述 |
|------|------|------|
| 等待识别 | PENDING | 已上传，等待AI识别 |
| 识别中 | PROCESSING | AI正在识别中 |
| 识别完成 | COMPLETED | AI识别完成 |
| 识别失败 | FAILED | AI识别失败 |

---

## 📊 使用示例

### 完整的小票处理流程

```bash
# 1. 上传小票图片
curl -X POST http://localhost:5000/receipts \
  -F "image=@receipt.jpg" \
  -F "name=便利店购物"

# 响应: {"id": 1, "status": "PENDING", ...}

# 2. 手动触发识别 (如果需要)
curl -X POST http://localhost:5000/receipts/1/recognize

# 3. 检查识别状态
curl -X GET http://localhost:5000/receipts/1

# 4. 获取识别出的商品
curl -X GET http://localhost:5000/items?receipt_id=1

# 5. 手动添加/修改商品
curl -X POST http://localhost:5000/receipts/1/items \
  -H "Content-Type: application/json" \
  -d '{
    "name_zh": "可乐",
    "name_ja": "コーラ",
    "price_cny": 3.5,
    "price_jpy": 65,
    "category_1": "饮料",
    "special_info": "否"
  }'

# 6. 更新商品信息
curl -X PUT http://localhost:5000/items/1 \
  -H "Content-Type: application/json" \
  -d '{
    "price_cny": 4.0,
    "notes": "价格有调整"
  }'
```

---

## 🎯 字段使用注意事项

### 1. 价格字段
- `price_jpy`: 日元价格，整数
- `price_cny`: 人民币价格，保留2位小数

### 2. 分类字段
- `category_1`: 必填，一级分类
- `category_2`: 可选，二级分类
- `category_3`: 可选，三级分类

### 3. 特价字段
- `special_info`: 字符串，如 "特价商品"、"-20%"、"是"、"否"
- `is_special_offer`: 布尔值，自动根据 `special_info` 生成

### 4. 名称字段
- `name_ja`: 日文原文，从小票直接提取
- `name_zh`: 中文翻译，AI生成的规范名称

---

## 🔐 身份验证

当前版本无需身份验证。生产环境建议添加：
- API Key 验证
- JWT Token 认证
- 请求频率限制

---

## 📚 开发建议

### 前端集成
1. 使用 AI 标准字段名发送请求
2. 显示时可以使用字段的中文别名
3. 处理异步识别状态更新

### 错误处理
1. 检查 HTTP 状态码
2. 解析错误响应的 `message` 字段
3. 对用户友好的错误提示

### 性能优化
1. 使用分页参数控制列表大小
2. 适当使用搜索和筛选参数
3. 缓存不经常变化的数据

---

*文档版本: v1.0*  
*最后更新: 2024年1月15日*
