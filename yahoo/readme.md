
# Yahoo Japan News Scraper

## 项目简介
这是一个用于爬取雅虎日本新闻的Python工具，支持从主页分类、话题页面及关联文章中提取新闻内容，并提供去重、广告过滤、数据存储（CSV/JSON）等功能。适用于新闻数据采集、分析及研究场景。


## 功能特性
1. **多来源爬取**  
   - 主页分类（国内、国际、经济等）  
   - 话题页面（IT、科学、娱乐等）  
   - 关联文章挖掘（从正文提取相关链接）  

2. **智能过滤**  
   - URL去重（避免重复爬取）  
   - 广告内容识别（基于关键词匹配）  
   - 无效链接过滤（排除图片/视频页）  

3. **数据存储**  
   - CSV格式（包含标题、时间、正文、图片链接等字段）  
   - JSON格式（原始数据存储）  

4. **浏览器模拟**  
   - 使用Selenium驱动Chrome浏览器（支持无头模式）  
   - 自动滚动页面加载更多内容  
   - 随机User-Agent模拟真实访问  

5. **日志系统**  
   - 记录爬取进度、错误信息及统计数据  
   - 支持文件和控制台双重输出  


## 依赖环境
### 必备库
```python
pip install selenium beautifulsoup4 requests python-dateutil python-dotenv
```

### 浏览器驱动
需下载对应版本的Chrome驱动：  
- [ChromeDriver下载地址](https://sites.google.com/chromium.org/driver/)  
- 需将驱动路径添加到系统环境变量或代码中指定路径  


## 使用说明
### 初始化配置
```python
from yahoo_news_scraper import YahooJapanNewsScraper

# 创建实例（可选日志文件路径）
scraper = YahooJapanNewsScraper(log_file="./logs/scraper.log")
```

### 核心爬取方法
```python
articles = scraper.scrape_news(
   max_articles=100,       # 总共爬取的文章数
   max_per_topics=100,    # 每个话题最多加载链接数
   max_per_categories=100           # 每个分类最多加载链接数
)
```

### 数据存储
```python
# 保存为CSV
scraper.save_to_csv(articles, filename="yahoo_news.csv")

# 保存为JSON
scraper.save_to_json(articles, filename="yahoo_news.json")
```


## 目录结构
```
project-root/
├─ logs/                # 日志文件
├─ saves/               # 数据存储文件
├─ yahoo_news_scraper.py # 主程序文件
└─ requirements.txt     # 依赖清单
```


## 配置参数说明
| 参数名               | 类型       | 默认值       | 说明                                                                 |
|----------------------|------------|--------------|----------------------------------------------------------------------|
| `log_file`           | str        | None         | 日志文件路径，若未指定则输出到控制台                               |
| `max_articles`       | int        | None         | 最大爬取文章总数（0或负数表示无限制）                             |
| `max_per_topics`     | int        | None         | 每个话题分类的最大链接数                                           |
| `max_per_categories` | int        | None         | 主页每个分类的最大链接数                                           |
| `headless`           | bool       | True         | 是否启用无头模式（节省资源）                                       |
| `user_agents`        | list       | 内置UA列表   | 自定义User-Agent池                                                  |
| `ad_keywords`        | list       | 内置关键词   | 广告内容过滤关键词（支持英文和日文）                               |


## 注意事项
1. **反爬机制**  
   - 建议设置合理的`time.sleep`间隔（默认已包含随机延迟）  
   - 避免短时间内大量请求（可能触发IP封禁）  

2. **法律合规**  
   - 请遵守雅虎日本的robots协议及当地法律法规  
   - 禁止将爬取数据用于商业用途或非法传播  

3. **页面变化**  
   - 若爬取失败可能是页面结构变更，需调整CSS选择器或XPath表达式  
   - 关注`find_more_button`和`extract_article_links`方法中的选择器逻辑  


## 示例输出
### CSV文件片段
| 序号 | 标题                          | 发布时间          | 正文                          | 图片数量 | 图片链接                                  | 原文链接                          | 来源         |
|------|-------------------------------|-------------------|-------------------------------|----------|-------------------------------------------|-----------------------------------|--------------|
| 1    | 東京五輪開幕式の最新情報      | 2025-07-23 10:00 | [正文段落1...][正文段落2...]   | 3        | https://example.com/img1.jpg,https://...   | https://news.yahoo.co.jp/...      | Yahoo Japan  |
```plain text
图片请及时下载保存，目前程序爬取图片链接的有效期一般为3小时
```

## 贡献与反馈
- 欢迎提交PR修复bug或新增功能  
- 问题反馈请创建[Issue](https://github.com/wangyuze18/newscraper/issues)  
