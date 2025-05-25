以下是更新后的中文 README 文件，基于您提供的代码修改，增加了关于图片下载功能的说明，并确保与代码保持一致。更新内容主要包括：

1. **图片下载功能**：在功能简介、核心参数配置、输出说明等部分添加了图片下载相关的描述。
2. **文件结构**：更新了文件结构说明，包含图片保存目录。
3. **示例展示**：在 JSON 和 CSV 示例中添加了本地图片路径字段。
4. **依赖安装**：确保所有必要的库都包含在安装说明中。

以下是完整的更新版 README：

---

# Yahoo Japan News 爬虫工具

## 一、项目概述  
### 1. 功能简介  
本工具用于爬取雅虎日本新闻（Yahoo Japan News）的文章内容，支持多维度数据采集：  
- **分类爬取**：覆盖经济、娱乐、科技、科学等多个新闻分类  
- **关键词搜索**：根据自定义关键词获取相关新闻  
- **话题页爬取**：从各话题板块提取热点文章  
- **图片下载**：支持将文章中的图片下载到本地指定目录（默认 `./saves/pic`）  
- **数据存储**：支持CSV和JSON格式存储，包含图片链接、本地图片路径、分类信息等  

### 2. 技术架构  
- **编程语言**：Python 3.8+  
- **主要库**：  
  - `selenium`：模拟浏览器操作（处理动态加载内容）  
  - `beautifulsoup4`：HTML解析  
  - `requests`：HTTP请求  
  - `python-dateutil`：时间处理  
  - `logging`：日志系统  
- **反爬机制**：  
  - 随机User-Agent轮换  
  - 动态延迟模拟人类行为  
  - 广告内容过滤（基于关键词匹配）  

## 二、环境配置  
### 1. 依赖安装  
```bash  
pip install selenium beautifulsoup4 requests python-dateutil
```  

### 2. 浏览器驱动  
需安装Chrome浏览器及对应版本的[ChromeDriver](https://sites.google.com/chromium.org/driver/)：  
1. 下载驱动程序并解压  
2. 将驱动路径添加到系统环境变量`PATH`中  
3. 或直接指定驱动路径（修改代码中`webdriver.Chrome()`参数）  

## 三、使用说明  
### 1. 核心参数配置  
#### 类初始化参数  
| 参数名            | 类型   | 默认值            | 说明                          |  
|-------------------|--------|-------------------|-------------------------------|  
| `log_file`        | str    | `None`            | 日志文件路径（可选）          |  
| `download_images` | bool   | `False`           | 是否下载图片到本地            |  
| `image_save_dir`  | str    | `"./saves/pic"`   | 图片保存目录（仅当下载启用）  |  

#### 爬取控制参数（`scrape_news`方法）  
| 参数名               | 类型   | 默认值       | 说明                                                                 |  
|----------------------|--------|--------------|----------------------------------------------------------------------|  
| `max_articles`       | int    | `None`       | 最大爬取文章总数（全局限制）                                         |  
| `max_per_categories` | int    | `None`       | 每个分类最多爬取链接数                                               |  
| `max_per_topics`     | int    | `None`       | 每个话题最多爬取链接数                                               |  
| `max_links_per_keyword` | int  | `None`       | 每个关键词最多爬取链接数                                             |  

### 2. 自定义配置项  
#### （1）分类与话题配置  
```python  
# 新闻分类（键为分类URL后缀，值为显示名称）  
self.categories = {  
    "science": "科学",  
    "business": "经济",  
    "entertainment": "娱乐",  
    "sports": "运动",  
    "life": "生活",  
    "it": "科技",  
}  

# 话题板块（键为话题ID，值为显示名称）  
self.topics = {  
    "business": "经济",  
    "entertainment": "娱乐",  
    "sports": "运动",  
    "it": "科技",  
    "science": "科学",  
}  
```  

#### （2）关键词与广告过滤  
```python  
# 搜索关键词列表（支持日文/英文）  
self.keywords = ['AI', '経済', 'スポーツ']  

# 广告过滤关键词（支持英文/日文）  
self.ad_keywords = [  
    'advertisement', 'ad', 'promotion', 'sponsored',  
    '広告', 'PR', 'スポンサー', 'プロモーション',  
    'adserver', 'doubleclick', 'amazon-adsystem'  
]  
```  

#### （3）请求头与延迟  
```python  
# 随机User-Agent列表（可添加更多浏览器指纹）  
self.user_agents = [  
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...',  
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36...'  
]  

# 随机延迟范围（单位：秒）  
time.sleep(random.uniform(0.5, 2.5))  # 建议保留默认值  
```  

## 四、运行示例  
```python  
if __name__ == "__main__":  
    from datetime import datetime  
    import os  

    # 配置日志  
    os.makedirs('./logs', exist_ok=True)  
    log_file = f"./logs/yahoo_news_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"  

    # 创建爬虫实例（启用图片下载）  
    scraper = YahooJapanNewsScraper(  
        log_file=log_file,  
        download_images=True,  # 启用图片下载  
        image_save_dir="./saves/images"  # 自定义图片保存目录  
    )  

    # 执行爬取（示例：爬取最多50篇文章，每个分类最多20条链接）  
    articles = scraper.scrape_news(  
        max_articles=50,  
        max_per_categories=20,  
        max_per_topics=15,  
        max_links_per_keyword=10  
    )  

    # 保存结果  
    if articles:  
        scraper.save_to_csv(articles)  
        scraper.save_to_json(articles)  
```  

## 五、输出说明  
### 1. 文件结构  
```  
项目根目录  
├─ logs/                    # 日志文件（自动生成）  
│  └─ yahoo_news_scraper_*.log  
├─ saves/                   # 数据文件（自动生成）  
│  ├─ pic/                  # 图片保存目录（默认，启用下载时生成）  
│  ├─ images/               # 自定义图片保存目录（示例）  
│  ├─ yahoo_news_*.csv      # CSV格式（含图片链接、本地路径等）  
│  └─ yahoo_news_*.json     # JSON格式（原始数据）  
└─ main.py                  # 主程序文件  
```  

### 2. 示例展示  
以下是爬取结果的 **JSON** 和 **CSV** 格式示例（数据已简化，仅保留核心字段）：  

#### **JSON 格式示例**  
```json  
[  
  {  
    "title": "AI技術が医療分野で大きな進展　がん診断精度向上",  
    "publish_time": "2023-10-25T14:30:00+09:00",  
    "content": [  
      "～最新研究成果による画期的な応用～",  
      "米国の研究チームがAIを用いたがん細胞検出技術を発表...",  
      "この技術により、早期発見率は従来の30%から55%に向上したという。"  
    ],  
    "images": [  
      "https://news.yahoo.co.jp/images/2023/10/25/ai_medical_1.jpg",  
      "https://news.yahoo.co.jp/images/2023/10/25/ai_medical_2.jpg"  
    ],  
    "local_images": [  
      "./saves/images/abc123_0.jpg",  
      "./saves/images/abc123_1.jpg"  
    ],  
    "url": "https://news.yahoo.co.jp/articles/abc123",  
    "source": "Yahoo Japan News",  
    "category": "科学"  
  },  
  {  
    "title": "株価急落　米国債金利上昇が影響",  
    "publish_time": "2023-10-24T16:15:00+09:00",  
    "content": [  
      "ニューヨーク株式市場では、主要銘柄が全面安...",  
      "分析によると、10年物米国債利回りが4.5%を突破したことが主因とみられる。"  
    ],  
    "images": [],  
    "local_images": [],  
    "url": "https://news.yahoo.co.jp/articles/def456",  
    "source": "Yahoo Japan News",  
    "category": "経済"  
  }  
]  
```  

#### **CSV 格式示例（表格展示）**  
| 序号 | 标题                              | 发布时间           | 正文（示例）                                                                 | 分类   | 图片数量 | 图片链接（示例）                                                                 | 本地图片路径（示例）                                           | 原文链接                  | 来源         |  
|------|-----------------------------------|--------------------|-----------------------------------------------------------------------------|--------|----------|-----------------------------------------------------------------------------|-------------------------------------------------------------|---------------------------|--------------|  
| 1    | AI技術が医療分野で大きな進展…    | 2023-10-25T14:30:00+09:00 | ～最新研究成果による画期的な応用～<br>米国の研究チームがAIを用いたがん細胞検出技術を発表... | 科学   | 2        | https://news.yahoo.co.jp/images/2023/10/25/ai_medical_1.jpg,<br>https://news.yahoo.co.jp/images/2023/10/25/ai_medical_2.jpg | ./saves/images/abc123_0.jpg,./saves/images/abc123_1.jpg     | https://news.yahoo.co.jp/articles/abc123 | Yahoo Japan |  
| 2    | 株価急落　米国債金利上昇が影響    | 2023-10-24T16:15:00+09:00 | ニューヨーク株式市場では、主要銘柄が全面安...<br>分析によると、10年物米国債利回りが4.5%を突破… | 経済   | 0        | -                                                                           | -                                                           | https://news.yahoo.co.jp/articles/def456 | Yahoo Japan |  

#### **格式说明**  
- **JSON**：  
  采用嵌套结构存储数据，`content`（正文）、`images`（图片链接）和 `local_images`（本地图片路径）为数组类型，方便程序解析。分类信息通过 `category` 字段标注（如 `"category": "科学"`）。  

- **CSV**：  
  表格化格式适合直接用 Excel/Google Sheets 打开。正文段落用 `<br>` 分隔，图片链接和本地图片路径用逗号拼接（可通过 Excel 的“数据分列”功能处理），`序号` 字段用于数据排序。  

#### **数据处理建议**  
- **JSON 解析**（Python 示例）：  
  ```python  
  import json  
  with open('saves/yahoo_news_20231025_1430.json', 'r', encoding='utf-8') as f:  
      articles = json.load(f)  
      for article in articles:  
          print(f"标题：{article['title']}，分类：{article['category']}，本地图片：{article['local_images']}")  
  ```  

- **CSV 分析**：  
  使用 Excel 的“数据透视表”功能，可按 `分类` 字段统计各领域文章数量；`图片链接` 和 `本地图片路径` 字段可通过公式 `=HYPERLINK(A1, "查看图片")` 生成可点击链接（假设字段在第 7 或第 8 列）。  

## 六、注意事项  
### 1. 反爬限制  
- 控制并发请求数（默认单线程）  
- 避免频繁爬取同一分类/关键词  
- 图片下载可能增加网络请求，建议根据带宽调整 `max_articles`  

### 2. 图片下载  
- 图片保存路径可通过 `image_save_dir` 参数自定义，默认 `./saves/pic`  
- 图片文件名格式为 `<文章ID>_<序号>.jpg`（或原始扩展名）  
- 下载失败的图片将记录在日志中，`local_images` 字段可能为空  

### 3. 法律声明  
本工具仅用于学术研究和数据备份，严禁用于商业用途或违反雅虎日本网站的使用条款。使用前请确保符合当地法律法规。  

### 4. 日志查看  
日志文件包含详细的爬取过程记录：  
- `INFO`：正常流程信息（如链接提取、保存结果、图片下载）  
- `DEBUG`：调试信息（如无效URL过滤）  
- `ERROR`：错误信息（如页面加载失败、图片下载失败）  

---
