# HamsterWallet 后端 API 详细文档

## 概述

HamsterWallet 是一个智能小票管理系统，提供小票识别、商品管理和数据导出功能。本文档详细描述了所有可用的API端点、请求格式和响应格式。

**基础URL**: `http://localhost:5000`

## 数据模型

### 小票 (Receipt) 数据模型

```json
{
  "id": 1,
  "name": "超市购物小票",
  "image_filename": "abc123.jpg",
  "text_description": "可选的文字描述",
  "notes": "用户备注",
  "exchange_rate": 0.047,
  "store_name": "AEON",
  "store_category": "超市",
  "created_at": "2024-08-17T10:30:00.000000",
  "transaction_time": "2024-08-17T15:20:00.000000",
  "updated_at": "2024-08-17T10:35:00.000000",
  "status": "识别成功",
  "items": [...]
}
```

### 商品 (Item) 数据模型

```json
{
  "id": 1,
  "receipt_id": 1,
  "name_ja": "りんご",
  "name_zh": "苹果",
  "price_jpy": 298.0,
  "price_cny": 14.0,
  "special_info": "-20%",
  "is_special_offer": true,
  "category_1": "食品",
  "category_2": "水果",
  "category_3": "苹果类",
  "notes": "商品备注"
}
```

### 识别状态枚举

- `待处理` (PENDING)
- `正在识别` (PROCESSING)
- `识别失败` (FAILED)
- `识别成功` (SUCCESS)

---

## API 端点详情

### 1. 小票管理

#### 1.1 获取小票列表

**端点**: `GET /api/receipts`

**描述**: 获取小票列表，支持分页、搜索和排序

**查询参数**:
- `page` (可选): 页码，默认 1
- `per_page` (可选): 每页条数，默认 20
- `search` (可选): 搜索关键词，会在小票名称、备注、文字描述、店铺名称中搜索
- `q` (可选): 搜索关键词的别名，与 search 功能相同
- `status` (可选): 按状态筛选，值为 `待处理`、`正在识别`、`识别失败`、`识别成功`
- `sort_by` (可选): 排序字段，支持 `created_at`、`updated_at`、`transaction_time`、`name`，默认 `created_at`
- `order` (可选): 排序方向，`asc` 或 `desc`，默认 `desc`

**请求示例**:
```
GET /api/receipts?page=1&per_page=10&search=超市&status=识别成功&sort_by=transaction_time&order=desc
```

**响应格式**:
```json
{
  "data": [
    {
      "id": 1,
      "name": "超市购物小票",
      "image_filename": "abc123.jpg",
      "text_description": null,
      "notes": "今天的购物",
      "exchange_rate": null,
      "store_name": "AEON",
      "store_category": "超市",
      "created_at": "2024-08-17T10:30:00.000000",
      "transaction_time": "2024-08-17T15:20:00.000000",
      "updated_at": "2024-08-17T10:35:00.000000",
      "status": "识别成功"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 10,
    "total_pages": 5,
    "total_items": 45
  }
}
```

#### 1.2 创建新小票

**端点**: `POST /api/receipts`

**描述**: 创建新小票，可以上传图片或提供文字描述，会自动触发AI识别

**请求格式**: `multipart/form-data`

**请求参数**:
- `image` (可选): 上传的图片文件，支持 JPG、PNG 格式，最大 16MB
- `name` (可选): 小票名称，默认为 "未命名小票"
- `text_description` (可选): 文字描述
- `notes` (可选): 用户备注
- `transaction_time` (可选): 交易时间，ISO 格式字符串
- `store_name` (可选): 店铺名称
- `store_category` (可选): 店铺分类

**请求示例**:
```bash
curl -X POST http://localhost:5000/api/receipts \
  -F "image=@receipt.jpg" \
  -F "name=超市购物" \
  -F "notes=今天的购物" \
  -F "transaction_time=2024-08-17 15:20:00"
```

**响应格式**:
```json
{
  "id": 1,
  "name": "超市购物",
  "image_filename": "abc123.jpg",
  "text_description": null,
  "notes": "今天的购物",
  "exchange_rate": null,
  "store_name": null,
  "store_category": null,
  "created_at": "2024-08-17T10:30:00.000000",
  "transaction_time": "2024-08-17T15:20:00.000000",
  "updated_at": "2024-08-17T10:30:00.000000",
  "status": "待处理",
  "items": []
}
```

**状态码**:
- `201`: 创建成功
- `400`: 请求错误（必须提供图片或文字描述）

#### 1.3 获取小票详情

**端点**: `GET /api/receipts/{receipt_id}`

**描述**: 获取指定小票的详细信息，包含所有关联的商品

**路径参数**:
- `receipt_id`: 小票ID

**请求示例**:
```
GET /api/receipts/1
```

**响应格式**:
```json
{
  "id": 1,
  "name": "超市购物小票",
  "image_filename": "abc123.jpg",
  "text_description": null,
  "notes": "今天的购物",
  "exchange_rate": null,
  "store_name": "AEON",
  "store_category": "超市",
  "created_at": "2024-08-17T10:30:00.000000",
  "transaction_time": "2024-08-17T15:20:00.000000",
  "updated_at": "2024-08-17T10:35:00.000000",
  "status": "识别成功",
  "items": [
    {
      "id": 1,
      "receipt_id": 1,
      "name_ja": "りんご",
      "name_zh": "苹果",
      "price_jpy": 298.0,
      "price_cny": 14.0,
      "special_info": "-20%",
      "is_special_offer": true,
      "category_1": "食品",
      "category_2": "水果",
      "category_3": "苹果类",
      "notes": null
    }
  ]
}
```

**状态码**:
- `200`: 获取成功
- `404`: 小票不存在

#### 1.4 更新小票信息

**端点**: `PUT /api/receipts/{receipt_id}`

**描述**: 更新小票的基本信息

**路径参数**:
- `receipt_id`: 小票ID

**请求格式**: `application/json`

**请求参数**:
- `name` (可选): 小票名称
- `notes` (可选): 用户备注
- `text_description` (可选): 文字描述
- `store_name` (可选): 店铺名称
- `store_category` (可选): 店铺分类
- `transaction_time` (可选): 交易时间

**请求示例**:
```json
{
  "name": "更新后的小票名称",
  "notes": "更新后的备注",
  "store_name": "新店铺名称",
  "transaction_time": "2024-08-17T16:00:00"
}
```

**响应格式**: 返回更新后的完整小票信息（格式同获取小票详情）

**状态码**:
- `200`: 更新成功
- `404`: 小票不存在

#### 1.5 删除小票

**端点**: `DELETE /api/receipts/{receipt_id}`

**描述**: 删除指定小票及其所有关联商品

**路径参数**:
- `receipt_id`: 小票ID

**请求示例**:
```
DELETE /api/receipts/1
```

**响应格式**: 无内容

**状态码**:
- `204`: 删除成功
- `404`: 小票不存在

#### 1.6 重新识别小票

**端点**: `POST /api/receipts/{receipt_id}/reprocess`

**描述**: 重新触发AI识别小票内容，会清空原有商品并重新识别

**路径参数**:
- `receipt_id`: 小票ID

**请求示例**:
```
POST /api/receipts/1/reprocess
```

**响应格式**:
```json
{
  "message": "已加入重新识别队列"
}
```

**状态码**:
- `202`: 已接受请求，开始处理
- `404`: 小票不存在

### 2. 商品管理

#### 2.1 获取商品列表

**端点**: `GET /api/items`

**描述**: 获取所有商品列表，支持分页、搜索和筛选

**查询参数**:
- `page` (可选): 页码，默认 1
- `per_page` (可选): 每页条数，默认 12
- `search` (可选): 搜索关键词，会在商品日文名、中文名、备注中搜索
- `is_special_price` (可选): 筛选特价商品，`true` 或 `false`
- `category_filter` (可选): 按分类筛选，会在三级分类中搜索
- `sort_by` (可选): 排序字段，支持 `created_at`、`transaction_time`、`updated_at`、`price_jpy`、`price_cny`、`name_zh`，默认 `created_at`
- `order` (可选): 排序方向，`asc` 或 `desc`，默认 `desc`

**请求示例**:
```
GET /api/items?page=1&per_page=20&search=苹果&is_special_price=true&category_filter=食品&sort_by=price_jpy&order=asc
```

**响应格式**:
```json
{
  "data": [
    {
      "id": 1,
      "receipt_id": 1,
      "name_ja": "りんご",
      "name_zh": "苹果",
      "price_jpy": 298.0,
      "price_cny": 14.0,
      "special_info": "-20%",
      "is_special_offer": true,
      "category_1": "食品",
      "category_2": "水果",
      "category_3": "苹果类",
      "notes": null
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_pages": 3,
    "total_items": 55
  }
}
```

#### 2.2 创建新商品

**端点**: `POST /api/items`

**描述**: 创建新的商品项目

**请求格式**: `application/json`

**请求参数**:
- `receipt_id` (必需): 关联的小票ID
- `name_ja` (可选): 日文商品名
- `name_zh` (可选): 中文商品名
- `price_jpy` (可选): 日元价格
- `price_cny` (可选): 人民币价格
- `category_1` (可选): 一级分类
- `category_2` (可选): 二级分类
- `category_3` (可选): 三级分类
- `special_info` (可选): 特价信息，如 "-20%"
- `is_special_offer` (可选): 是否特价商品，布尔值
- `notes` (可选): 商品备注

**请求示例**:
```json
{
  "receipt_id": 1,
  "name_ja": "バナナ",
  "name_zh": "香蕉",
  "price_jpy": 198.0,
  "price_cny": 9.3,
  "category_1": "食品",
  "category_2": "水果",
  "category_3": "香蕉类",
  "special_info": "-10%",
  "notes": "有机香蕉"
}
```

**响应格式**: 返回创建的商品信息

**状态码**:
- `201`: 创建成功
- `404`: 关联的小票不存在

#### 2.3 为指定小票添加商品

**端点**: `POST /api/receipts/{receipt_id}/items`

**描述**: 为指定小票添加新商品

**路径参数**:
- `receipt_id`: 小票ID

**请求格式**: `application/json`

**请求参数**: 同创建新商品，但不需要提供 `receipt_id`

**请求示例**:
```json
{
  "name_ja": "バナナ",
  "name_zh": "香蕉",
  "price_jpy": 198.0,
  "price_cny": 9.3,
  "category_1": "食品",
  "category_2": "水果",
  "category_3": "香蕉类"
}
```

**响应格式**: 返回创建的商品信息

**状态码**:
- `201`: 创建成功
- `404`: 小票不存在

#### 2.4 获取商品详情

**端点**: `GET /api/items/{item_id}`

**描述**: 获取指定商品的详细信息

**路径参数**:
- `item_id`: 商品ID

**请求示例**:
```
GET /api/items/1
```

**响应格式**:
```json
{
  "id": 1,
  "receipt_id": 1,
  "name_ja": "りんご",
  "name_zh": "苹果",
  "price_jpy": 298.0,
  "price_cny": 14.0,
  "special_info": "-20%",
  "is_special_offer": true,
  "category_1": "食品",
  "category_2": "水果",
  "category_3": "苹果类",
  "notes": null
}
```

**状态码**:
- `200`: 获取成功
- `404`: 商品不存在

#### 2.5 更新商品信息

**端点**: `PUT /api/items/{item_id}`

**描述**: 更新指定商品的信息

**路径参数**:
- `item_id`: 商品ID

**请求格式**: `application/json`

**请求参数**: 同创建商品（除了 receipt_id）

**请求示例**:
```json
{
  "name_zh": "红苹果",
  "price_cny": 15.0,
  "notes": "更新后的备注"
}
```

**响应格式**: 返回更新后的商品信息

**状态码**:
- `200`: 更新成功
- `404`: 商品不存在

#### 2.6 删除商品

**端点**: `DELETE /api/items/{item_id}`

**描述**: 删除指定商品

**路径参数**:
- `item_id`: 商品ID

**请求示例**:
```
DELETE /api/items/1
```

**响应格式**: 无内容

**状态码**:
- `204`: 删除成功
- `404`: 商品不存在

### 3. 数据导出

#### 3.1 导出数据

**端点**: `GET /api/export`

**描述**: 导出小票和商品的组合数据，提供扁平化的数据结构便于分析

**查询参数**:
- `page` (可选): 页码，默认 1
- `per_page` (可选): 每页记录数，不指定则导出所有记录
- `start_date` (可选): 开始日期，ISO 格式
- `end_date` (可选): 结束日期，ISO 格式
- `store_name` (可选): 店铺名称筛选
- `store_category` (可选): 店铺分类筛选
- `category` (可选): 商品分类筛选
- `is_special_offer` (可选): 是否特价商品，`true` 或 `false`
- `status` (可选): 小票状态筛选
- `search` (可选): 搜索关键词
- `sort_by` (可选): 排序字段，支持 `transaction_time`、`created_at`、`receipt_name`、`store_name`、`price_jpy`，默认 `transaction_time`
- `order` (可选): 排序方向，`asc` 或 `desc`，默认 `desc`

**请求示例**:
```
GET /api/export?start_date=2024-08-01&end_date=2024-08-31&store_category=超市&is_special_offer=true&sort_by=price_jpy&order=desc
```

**响应格式**:
```json
{
  "data": [
    {
      "receipt_id": 1,
      "receipt_name": "超市购物小票",
      "store_name": "AEON",
      "store_category": "超市",
      "transaction_time": "2024-08-17T15:20:00.000000",
      "receipt_created_at": "2024-08-17T10:30:00.000000",
      "receipt_status": "识别成功",
      "receipt_notes": "今天的购物",
      "item_id": 1,
      "item_name_ja": "りんご",
      "item_name_zh": "苹果",
      "price_jpy": 298.0,
      "price_cny": 14.0,
      "category_1": "食品",
      "category_2": "水果",
      "category_3": "苹果类",
      "special_info": "-20%",
      "is_special_offer": true,
      "item_notes": null
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 999999,
    "total_pages": 1,
    "total_items": 150
  },
  "export_info": {
    "export_time": "2024-08-17T11:00:00.000000",
    "total_records": 150,
    "has_more": false
  }
}
```

**状态码**:
- `200`: 导出成功
- `500`: 导出失败

### 4. 数据分析

#### 4.1 获取仪表盘数据

**端点**: `GET /api/analytics/dashboard`

**描述**: 获取消费总览仪表盘数据，包含总支出、小票数量、商品数量、使用天数、日均开销、折扣商品占比

**查询参数**:
- `start_date` (可选): 开始日期，ISO 格式
- `end_date` (可选): 结束日期，ISO 格式

**请求示例**:
```
GET /api/analytics/dashboard?start_date=2024-08-01&end_date=2024-08-31
```

**响应格式**:
```json
{
  "total_spending": {
    "jpy": 15000.0,
    "cny": 705.0
  },
  "receipt_count": 25,
  "item_count": 85,
  "usage_days": 30,
  "daily_average": {
    "jpy": 500.0,
    "cny": 23.5
  },
  "discount_ratio": 15.3
}
```

#### 4.2 获取消费趋势数据

**端点**: `GET /api/analytics/trend`

**描述**: 获取按日期统计的消费趋势数据

**查询参数**:
- `start_date` (可选): 开始日期，ISO 格式
- `end_date` (可选): 结束日期，ISO 格式

**请求示例**:
```
GET /api/analytics/trend?start_date=2024-08-01&end_date=2024-08-31
```

**响应格式**:
```json
{
  "data": [
    {
      "date": "2024-08-01",
      "spending": {
        "jpy": 1200.0,
        "cny": 56.4
      },
      "item_count": 8
    },
    {
      "date": "2024-08-02",
      "spending": {
        "jpy": 800.0,
        "cny": 37.6
      },
      "item_count": 5
    }
  ]
}
```

#### 4.3 获取每日商品列表

**端点**: `GET /api/analytics/daily/{date}/items`

**描述**: 获取指定日期的商品列表

**路径参数**:
- `date`: 日期，格式为 YYYY-MM-DD

**请求示例**:
```
GET /api/analytics/daily/2024-08-17/items
```

**响应格式**:
```json
{
  "data": [
    {
      "id": 1,
      "receipt_id": 1,
      "name_ja": "りんご",
      "name_zh": "苹果",
      "price_jpy": 298.0,
      "price_cny": 14.0,
      "category_1": "食品",
      "category_2": "水果",
      "category_3": "苹果类",
      "special_info": "-20%",
      "is_special_offer": true,
      "notes": null,
      "receipt_name": "超市购物",
      "store_name": "AEON",
      "transaction_time": "2024-08-17T15:20:00.000000"
    }
  ]
}
```

#### 4.4 获取分类支出分析

**端点**: `GET /api/analytics/category`

**描述**: 获取按分类统计的支出分析数据，支持多级分类钻取

**查询参数**:
- `start_date` (可选): 开始日期，ISO 格式
- `end_date` (可选): 结束日期，ISO 格式
- `category_level` (可选): 分类层级，1、2 或 3，默认为 1
- `parent_category` (可选): 父级分类名称，用于获取下级分类

**请求示例**:
```
GET /api/analytics/category?start_date=2024-08-01&end_date=2024-08-31&category_level=1
GET /api/analytics/category?category_level=2&parent_category=食品
```

**响应格式**:
```json
{
  "categories": [
    {
      "category": "食品",
      "spending": {
        "jpy": 8500.0,
        "cny": 399.0
      },
      "item_count": 45,
      "percentage": 56.7
    },
    {
      "category": "日用品",
      "spending": {
        "jpy": 4200.0,
        "cny": 197.4
      },
      "item_count": 28,
      "percentage": 28.0
    }
  ],
  "total_spending": {
    "jpy": 15000.0,
    "cny": 705.0
  },
  "category_level": "1",
  "parent_category": null
}
```

#### 4.5 获取分类商品列表

**端点**: `GET /api/analytics/category/{category}/items`

**描述**: 获取指定分类下的商品列表

**路径参数**:
- `category`: 分类名称

**查询参数**:
- `category_level` (可选): 分类层级，1、2 或 3，默认为 1
- `start_date` (可选): 开始日期，ISO 格式
- `end_date` (可选): 结束日期，ISO 格式

**请求示例**:
```
GET /api/analytics/category/食品/items?category_level=1
GET /api/analytics/category/水果/items?category_level=2
```

**响应格式**:
```json
{
  "data": [
    {
      "id": 1,
      "receipt_id": 1,
      "name_ja": "りんご",
      "name_zh": "苹果",
      "price_jpy": 298.0,
      "price_cny": 14.0,
      "category_1": "食品",
      "category_2": "水果",
      "category_3": "苹果类",
      "special_info": "-20%",
      "is_special_offer": true,
      "notes": null,
      "receipt_name": "超市购物",
      "store_name": "AEON",
      "transaction_time": "2024-08-17T15:20:00.000000"
    }
  ]
}
```

---

## 错误处理

### 通用错误格式

```json
{
  "message": "错误描述"
}
```

### 常见状态码

- `200`: 请求成功
- `201`: 创建成功
- `202`: 请求已接受，正在处理
- `204`: 删除成功
- `400`: 请求错误
- `404`: 资源不存在
- `500`: 服务器内部错误

---

## 注意事项

### 1. 时间处理
- 所有时间字段均使用UTC时间存储
- 用户输入的时间会被自动转换为UTC（假设用户时区为东九区 GMT+9）
- 响应中的时间为UTC时间，客户端需要根据需要转换为本地时间

### 2. 图片处理
- 支持的图片格式：JPG、PNG
- 最大文件大小：16MB
- 上传的图片会自动压缩（质量80%，最大尺寸1920x1080）
- 图片使用MD5哈希命名，避免重复存储

### 3. AI识别
- 创建小票时会自动触发AI识别（异步处理）
- 识别状态通过 `status` 字段查看
- 可通过重新识别接口手动触发重新处理

### 4. 分页
- 默认分页大小：小票列表20条，商品列表12条
- 最大分页大小无限制（导出接口可获取所有数据）

### 5. 搜索和筛选
- 搜索不区分大小写
- 支持模糊匹配
- 可组合多个筛选条件

### 6. 特价商品处理
- `is_special_offer` 字段基于 `special_info` 自动计算
- 当 `special_info` 不为空且不等于"否"时，`is_special_offer` 为 true

---

## 使用示例

### 创建完整的购物记录

1. **上传小票图片**
```bash
curl -X POST http://localhost:5000/api/receipts \
  -F "image=@receipt.jpg" \
  -F "name=今日购物" \
  -F "notes=在AEON购买的日用品"
```

2. **查看识别结果**
```bash
curl http://localhost:5000/api/receipts/1
```

3. **手动调整商品信息**
```bash
curl -X PUT http://localhost:5000/api/items/1 \
  -H "Content-Type: application/json" \
  -d '{"name_zh": "红富士苹果", "notes": "很甜"}'
```

4. **导出数据分析**
```bash
curl "http://localhost:5000/api/export?start_date=2024-08-01&end_date=2024-08-31&store_category=超市"
```

这份API文档涵盖了HamsterWallet后端的所有功能，包括详细的请求格式、响应格式和使用示例。
