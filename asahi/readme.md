# Asahi 新闻爬虫工具

## 一、工具简介
本工具用于爬取日本《朝日新闻》（Asahi Shimbun）网站的公开新闻内容，支持以下功能：
1. **导航栏分类爬取**：自动解析网站导航结构，遍历各分类下的新闻链接。
2. **关键词搜索爬取**：通过 Selenium 渲染动态页面，获取搜索结果中的新闻数据。
3. **内容过滤与验证**：
   - 排除付费内容（含“有料会員”标识或黄金钥匙图标）。
   - 过滤非新闻链接（如登录页、视频页、隐私政策等）。
   - 提取正文、图片、发布时间等关键信息，并验证内容有效性。
4. **图片下载**：自动下载新闻正文中的图片，保存到以文章 URL 后缀命名的文件夹（如 `./saves/pic/ASN123456789/`）。
5. **数据存储**：支持将结果保存为 CSV 或 JSON 格式，自动生成带时间戳的文件名，包含下载的图片路径。
6. **日志与调试**：记录详细的请求日志、错误信息及图片下载状态，便于问题排查。

## 二、环境依赖
### 1. 基础依赖
```python
requests          # HTTP 请求库
beautifulsoup4    # HTML 解析库
selenium          # 浏览器自动化工具
trafilatura       # 可选：用于更精准的内容提取（若未安装则使用原生解析）
python-dateutil   # 日期处理（隐式依赖）
urllib3           # HTTP 连接池（requests 依赖）
```

### 2. 浏览器驱动（Selenium 使用）
- **ChromeDriver**：需与本地 Chrome 浏览器版本匹配，建议通过 `webdriver-manager` 自动管理驱动版本（程序已内置相关配置）。
- **无头模式**：默认启用，无需图形界面。

## 三、关键配置参数
### 类初始化参数（`AsahiCrawler`）
| 参数名               | 类型       | 默认值                     | 说明                                                                 |
|----------------------|------------|----------------------------|----------------------------------------------------------------------|
| `headers_list`       | list       | 包含 5 个 User-Agent 的列表 | 随机切换请求头，降低反爬检测概率。                                   |
| `config`             | dict       | 见下方详细配置             | 核心配置项，包括选择器、超时时间、文件路径等。                       |

### `config` 字典详细配置
| 键名                  | 类型       | 默认值                          | 说明                                                                 |
|-----------------------|------------|---------------------------------|----------------------------------------------------------------------|
| `nav_selectors`       | list       | `["div#GlobalNav", "ul.NavInner"]` | 导航栏容器的 CSS 选择器（按优先级尝试）。                            |
| `content_selectors`   | list       | `["div.w8Bsl", "div.Isto1", "article-content", "main-content"]` | 正文内容容器的 CSS 选择器（按优先级尝试）。                          |
| `paid_selectors`      | list       | `['img[src*="icon_key_gold.png"]', 'span.hideFromApp:contains("有料会員")']` | 付费内容检测选择器（匹配任意一个即判定为付费）。                     |
| `valid_image_extensions` | list   | `[".jpg", ".jpeg", ".png", ".webp"]` | 有效图片文件扩展名。                                                 |
| `request_timeout`     | int        | `10`                            | HTTP 请求超时时间（秒）。                                             |
| `max_retries`         | int        | `3`                             | 单个请求最大重试次数。                                               |
| `min_image_size`      | int        | `10000`                         | 图片最小字节大小（若可检测，通过 Content-Length 判断）。             |
| `image_save_path`     | str        | `"./saves/pic"`                 | 图片默认保存路径，子文件夹以文章 URL 后缀命名（如 `ASN123456789`）。|

## 四、使用方法
### 1. 初始化爬虫
```python
from asahi_crawler import AsahiCrawler

crawler = AsahiCrawler()
```

### 2. 启动爬取
```python
result = crawler.crawl(
    target_url="https://www.asahi.com/",         # 起始 URL（建议使用首页）
    max_news_count=100,                         # 全局最大新闻数限制
    max_nav_news=90,                            # 导航栏分类爬取的最大新闻数
    max_search_news=10,                         # 搜索爬取的最大新闻数
    search_keyword="東京",                       # 搜索关键词（支持字符串或列表）
    request_delay=0.5,                          # 请求间隔时间（秒），模拟人类行为
    render_timeout=15                           # Selenium 渲染超时时间（秒）
)
```

### 3. 保存结果
```python
saved_files = crawler.save_data(
    result,
    output_formats=["csv", "json"],  # 可选格式："csv"、"json"
    output_dir="saves"               # 输出目录（默认：saves/）
)
```

### 4. 图片下载
- 图片自动下载并保存到 `./saves/pic/<url_suffix>/`（如 `./saves/pic/ASN123456789/`），其中 `url_suffix` 为文章 URL 的最后部分（去除 `.html` 和查询参数）。
- 图片文件名格式为 `序号.扩展名`（如 `1.jpg`, `2.png`）。
- 下载的图片路径记录在新闻数据的 `下载的图片路径` 字段中。

## 五、输出数据结构
### 1. 新闻数据字段（`result["news"]`）
| 字段名         | 类型       | 说明                                                                 |
|----------------|------------|----------------------------------------------------------------------|
| 标题           | str        | 新闻标题（UTF-8 编码，处理非法字符）。                               |
| 发布时间       | str        | 原文中的时间信息（未标准化，保留原始格式）。                         |
| 正文           | str        | 段落分隔的正文内容（通过 `\n` 连接）。                               |
| 主题           | str        | 新闻所属分类（通过 meta 标签提取）。                                 |
| 图片数量       | int        | 正文中有效图片的数量。                                               |
| 图片链接       | list       | 图片 URL 列表（已处理相对路径，替换为高清版本路径）。                 |
| 原文链接       | str        | 新闻详情页 URL（如 `https://www.asahi.com/articles/ASN123456789.html`）。|
| 下载的图片路径 | list       | 下载的图片文件路径列表（如 `["./saves/pic/ASN123456789/1.jpg", ...]`）。|

### 2. 导航数据结构（`result["navigation"]`）
```python
[
    {
        "title": "分类名称",
        "url": "分类首页 URL",
        "children": [            # 二级子分类（若有）
            {
                "title": "子分类名称",
                "url": "子分类 URL",
                "children": []  # 三级子分类（目前未深度解析）
            }
        ]
    }
]
```

### 3. 输出文件
- **CSV**：保存到 `saves/csv/YYYYMMDD_HHMMSS.csv`，包含所有新闻数据字段，`下载的图片路径` 以分号分隔（如 `./saves/pic/ASN123456789/1.jpg;./saves/pic/ASN123456789/2.png`）。
- **JSON**：保存到 `saves/json/YYYYMMDD_HHMMSS.json`，包含完整结果（`navigation` 和 `news`），`下载的图片路径` 为数组。
- **图片**：保存到 `saves/pic/<url_suffix>/`，每个文章的图片存储在以 URL 后缀命名的子文件夹中。

## 六、日志与调试
- **日志存储**：自动创建 `./logs` 目录，按时间戳生成日志文件，记录请求细节、错误信息及图片下载状态。
- **调试技巧**：
  - 若解析失败，可查看日志中的 `页面内容片段` 字段，手动分析 HTML 结构。
  - 若图片下载失败，检查日志中的下载错误信息（如状态码或超时）。
  - 修改 `config` 中的选择器（如 `nav_selectors`、`content_selectors`）或 `image_save_path` 以适配需求。
  - 关闭无头模式（`options.headless = False`）观察浏览器行为，定位渲染问题。

## 七、注意事项
1. **反爬机制**：
   - 建议设置 `request_delay >= 0.5` 秒，避免高频请求触发封禁。
   - 随机 User-Agent 和 Selenium 防检测参数（如 `--disable-blink-features=AutomationControlled`）已内置，但仍需注意网站策略变化。
2. **付费内容**：程序通过 `paid_selectors` 过滤付费内容，但可能存在漏检，需人工验证。
3. **图片下载**：
   - 仅下载符合 `valid_image_extensions` 和 `min_image_size` 的图片。
   - 图片存储路径基于文章 URL 后缀（如 `ASN123456789`），确保唯一性。
   - 若下载失败，日志会记录具体错误（如网络问题或无效 URL）。
4. **法律合规**：本工具仅用于学术研究或数据备份，禁止用于商业用途或侵犯版权的行为。
5. **依赖更新**：定期检查 `trafilatura`、`selenium` 等库的版本，确保与网站结构兼容。

## 八、示例代码（`__main__` 入口）
```python
if __name__ == "__main__":
    import sys
    if sys.platform.startswith('win'):
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    crawler = AsahiCrawler()
    target_url = "https://www.asahi.com/"
    search_keywords = ["東京"]
    
    config = {
        "max_news_count": 100,
        "max_nav_news": 90,
        "max_search_news": 10,
        "request_delay": 0.5,
        "render_timeout": 15,
        "output_formats": ["csv", "json"]
    }
    
    start_time = datetime.now()
    result = crawler.crawl(
        target_url,
        max_news_count=config["max_news_count"],
        max_nav_news=config["max_nav_news"],
        max_search_news=config["max_search_news"],
        search_keyword=search_keywords,
        request_delay=config["request_delay"],
        render_timeout=config["render_timeout"]
    )
    
    end_time = datetime.now()
    elapsed_time = end_time - start_time
    
    crawler.logger.info("\n爬取时间统计:")
    crawler.logger.info(f"- 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    crawler.logger.info(f"- 结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    crawler.logger.info(f"- 总耗时: {elapsed_time.total_seconds():.2f} 秒 ({elapsed_time})")
    
    if result and result["news"]:
        free_news = [news for news in result["news"] if "[付费内容，无法获取全文]" not in news["正文"]]
        filtered_result = {
            "navigation": result["navigation"],
            "news": free_news,
            "stats": {
                "total_news": len(result["news"]),
                "free_news": len(free_news),
                "navigation_count": len(result["navigation"]),
                "crawl_duration": str(elapsed_time)
            }
        }
        
        if free_news:
            saved_files = crawler.save_data(filtered_result, output_formats=config["output_formats"])
            print(f"\n共爬取到 {len(result['news'])} 条新闻，其中 {len(free_news)} 条为免费内容")
            print(f"发现 {len(result['navigation'])} 个导航分类")
            print(f"数据已保存到: {', '.join([f for f in saved_files if f])}")
            print(f"图片已保存到: {crawler.config['image_save_path']}")
        else:
            print("未爬取到任何免费新闻数据")
    else:
        print("未爬取到任何新闻数据")
        print("提示：网站结构可能已更新，需要进一步调试选择器")
```

---
