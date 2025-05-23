# Yahoo Japan News 爬虫工具

## 一、项目概述  
### 1. 功能简介  
本工具用于爬取雅虎日本新闻（Yahoo Japan News）的文章内容，支持多维度数据采集：  
- **分类爬取**：覆盖经济、娱乐、科技、科学等多个新闻分类  
- **关键词搜索**：根据自定义关键词获取相关新闻  
- **话题页爬取**：从各话题板块提取热点文章  
- **数据存储**：支持CSV和JSON格式存储，包含图片链接、分类信息等  

### 2. 技术架构  
- **编程语言**：Python 3.8+  
- **主要库**：  
  - `selenium`：模拟浏览器操作（处理动态加载内容）  
  - `BeautifulSoup`：HTML解析  
  - `requests`：HTTP请求  
  - `pandas`（隐式依赖）：CSV处理  
  - `logging`：日志系统  
- **反爬机制**：  
  - 随机User-Agent轮换  
  - 动态延迟模拟人类行为  
  - 广告内容过滤（基于关键词匹配）  

## 二、环境配置  
### 1. 依赖安装  
```bash  
pip install selenium beautifulsoup4 requests python-dateutil python-dotenv  
```  

### 2. 浏览器驱动  
需安装Chrome浏览器及对应版本的[ChromeDriver](https://sites.google.com/chromium.org/driver/)：  
1. 下载驱动程序并解压  
2. 将驱动路径添加到系统环境变量`PATH`中  
3. 或直接指定驱动路径（修改代码中`webdriver.Chrome()`参数）  

## 三、使用说明  
### 1. 核心参数配置  
#### 类初始化参数  
| 参数名       | 类型   | 默认值       | 说明                     |  
|--------------|--------|--------------|--------------------------|  
| `log_file`   | str    | `None`       | 日志文件路径（可选）     |  

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
    # 可根据需要扩展更多分类  
}  

# 话题板块（键为话题ID，值为显示名称）  
self.topics = {  
    "it": "科技",  
    "sports": "运动",  
    # 可添加更多话题如"domestic"（国内）、"world"（国际）  
}  
```  

#### （2）关键词与广告过滤  
```python  
# 搜索关键词列表（支持日文/英文）  
self.keywords = ['AI', '経済', 'スポーツ']  

# 广告过滤关键词（支持英文/日文）  
self.ad_keywords = [  
    'advertisement', '広告', 'PR', 'sponsored',  
    'adserver', 'doubleclick'  
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
    # 配置日志  
    log_file = "./logs/scraper_{}.log".format(datetime.now().strftime("%Y%m%d_%H%M%S"))  
    scraper = YahooJapanNewsScraper(log_file=log_file)  
    
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
├─ logs/                # 日志文件（自动生成）  
│  └─ scraper_*.log  
├─ saves/               # 数据文件（自动生成）  
│  ├─ yahoo_news_*.csv  # CSV格式（含图片链接、分类等）  
│  └─ yahoo_news_*.json # JSON格式（原始数据）  
└─ main.py              # 主程序文件  
```  


## 六、示例展示  
以下是爬取结果的 **JSON** 和 **CSV** 格式示例（数据已简化，仅保留核心字段）：  

### **1. JSON 格式示例**  
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
    "url": "https://news.yahoo.co.jp/articles/def456",  
    "source": "Yahoo Japan News",  
    "category": "経済"  
  }  
]  
```  

### **2. CSV 格式示例（表格展示）**  
| 序号 | 标题                              | 发布时间           | 正文（示例）                                                                 | 分类   | 图片数量 | 图片链接（示例）                                                                 | 原文链接                  | 来源         |  
|------|-----------------------------------|--------------------|-----------------------------------------------------------------------------|--------|----------|-----------------------------------------------------------------------------|---------------------------|--------------|  
| 1    | AI技術が医療分野で大きな進展…    | 2023-10-25T14:30:00+09:00 | ～最新研究成果による画期的な応用～<br>米国の研究チームがAIを用いたがん細胞検出技術を発表... | 科学   | 2        | https://news.yahoo.co.jp/images/2023/10/25/ai_medical_1.jpg,<br>https://news.yahoo.co.jp/images/2023/10/25/ai_medical_2.jpg | https://news.yahoo.co.jp/articles/abc123 | Yahoo Japan |  
| 2    | 株価急落　米国債金利上昇が影響    | 2023-10-24T16:15:00+09:00 | ニューヨーク株式市場では、主要銘柄が全面安...<br>分析によると、10年物米国債利回りが4.5%を突破… | 経済   | 0        | -                                                                           | https://news.yahoo.co.jp/articles/def456 | Yahoo Japan |  

### **3. 格式说明**  
- **JSON**：  
  采用嵌套结构存储数据，`content`（正文）和 `images`（图片链接）为数组类型，方便程序解析。分类信息通过 `category` 字段标注（如 `"category": "科学"`）。  

- **CSV**：  
  表格化格式适合直接用 Excel/Google Sheets 打开。正文段落用 `<br>` 分隔，图片链接用逗号拼接（可通过 Excel 的“数据分列”功能处理），`序号` 字段用于数据排序。  

### **4. 数据处理建议**  
- **JSON 解析**（Python 示例）：  
  ```python  
  import json  
  with open('saves/yahoo_news_20231025_1430.json', 'r', encoding='utf-8') as f:  
      articles = json.load(f)  
      for article in articles:  
          print(f"标题：{article['title']}，分类：{article['category']}")  
  ```  

- **CSV 分析**：  
  使用 Excel 的“数据透视表”功能，可按 `分类` 字段统计各领域文章数量；图片链接字段可通过公式 `=HYPERLINK(A1, "查看图片")` 生成可点击链接（假设图片链接在第 7 列）。  

## 七、注意事项  
### 1. 反爬限制  
- 控制并发请求数（默认单线程）  
- 避免频繁爬取同一分类/关键词  

### 2. 法律声明  
本工具仅用于学术研究和数据备份，严禁用于商业用途或违反雅虎日本网站的使用条款。使用前请确保符合当地法律法规。  

### 3. 日志查看  
日志文件包含详细的爬取过程记录：  
- `INFO`：正常流程信息（如链接提取、保存结果）  
- `DEBUG`：调试信息（如无效URL过滤）  
- `ERROR`：错误信息（如页面加载失败）  
