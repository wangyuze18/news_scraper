
# 朝日新闻爬虫工具（AsahiCrawler）

## 项目简介
本工具用于爬取朝日新闻 (https://www.asahi.com) 的公开新闻内容，支持提取新闻标题、发布时间、正文、图片链接等信息，并将结果保存为CSV或JSON格式。工具具备导航栏解析、付费内容识别、URL去重、异常处理等功能，可应对网站的基本反爬机制。


## 目录结构
```
.
├── asahi_crawler.py       # 核心爬虫代码
├── saves                 # 数据保存目录
│   ├── csv              # CSV文件
│   └── json             # JSON文件
├── logs                  # 日志文件目录
├── README.md             # 项目说明
└── .gitignore            # Git忽略规则
```


## 功能特性
1. **导航栏解析**  
   自动提取网站导航分类，支持一级和二级菜单解析，生成结构化导航数据。

2. **新闻内容爬取**  
   - 识别新闻链接（排除登录、订阅等非新闻页面）。  
   - 跳过付费内容（通过特定图标和文本检测）。  
   - 提取正文、图片链接（自动替换为高清版本路径）、发布时间等信息。  

3. **数据去重与持久化**  
   - 记录已访问URL，避免重复爬取。  
   - 结果可保存为CSV或JSON格式，文件按时间戳命名。  

4. **健壮性设计**  
   - 日志系统记录爬取过程（`logs/`目录）。  
   - 重试机制应对网络波动。  
   - 编码处理避免中文乱码（Windows系统需特别配置控制台编码）。  


## 环境依赖
- **Python版本**：3.8+  
- **依赖库**：  
  ```python
  requests         # HTTP请求
  beautifulsoup4   # HTML解析
  python-dateutil  # 时间处理（隐式依赖，需确保安装）
  ```  
  安装命令：  
  ```bash
  pip install requests beautifulsoup4 python-dateutil
  ```


## 使用说明
### 1. 配置与运行
```python
# 主程序入口（asahi_crawler.py）
if __name__ == "__main__":
    MAX_NEWS_COUNT = 10  # 最大爬取新闻数量
    crawler = AsahiCrawler()
    target_url = "https://www.asahi.com/"  # 可修改为其他朝日新闻子页面
    result = crawler.crawl(target_url)
    
    # 结果处理与保存（自动过滤付费内容）
    if result and result["news"]:
        free_news = [news for news in result["news"] if not news["正文"].startswith("[付费内容")]
        crawler.save_to_csv({"navigation": result["navigation"], "news": free_news})
        crawler.save_to_json(free_news)
```

### 2. 关键参数说明
- `headers`：请求头模拟浏览器行为（可根据需要修改User-Agent）。  
- `visited_urls`：自动维护的已访问URL集合，避免重复爬取。  
- `is_paid_content`：通过页面元素检测付费内容，可根据网站更新调整检测规则。  

### 3. 输出结果
- **CSV文件**：包含新闻详细字段（标题、时间、正文等），路径为`saves/csv/`。  
- **JSON文件**：结构化新闻数据，路径为`saves/json/`。  
- **日志文件**：记录爬取过程、错误信息，路径为`logs/`。  


## 调试与维护
- **网站结构变化**：若爬取失败，可能是页面选择器失效（如导航栏、正文容器的HTML结构变更），需修改`extract_navigation`、`crawl_detail_page`等方法中的选择器。  
- **反爬应对**：可调整`time.sleep()`延时（当前注释掉，建议根据网站限制添加），或增加代理IP池。  
- **付费内容检测**：更新`is_paid_content`方法中的选择器或关键词，以适应网站付费标识的变化。  


## 贡献与反馈
- 欢迎提交PR修复bug或新增功能  
- 问题反馈请创建[Issue](https://github.com/wangyuze18/newscraper/issues)  

