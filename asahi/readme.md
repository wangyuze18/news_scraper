
以下是根据程序内容修改后的 README 文档，包含功能说明、使用方法、依赖环境、配置参数、输出说明等关键信息：


# Asahi 新闻爬虫工具

## 一、工具简介
本工具用于爬取日本《朝日新闻》（Asahi Shimbun）网站的公开新闻内容，支持以下功能：
1. **导航栏分类爬取**：自动解析网站导航结构，遍历各分类下的新闻链接。
2. **关键词搜索爬取**：通过 Selenium 渲染动态页面，获取搜索结果中的新闻数据。
3. **内容过滤与验证**：
   - 排除付费内容（含“有料会員”标识或黄金钥匙图标）。
   - 过滤非新闻链接（如登录页、视频页、隐私政策等）。
   - 提取正文、图片、发布时间等关键信息，并验证内容有效性。
4. **数据存储**：支持将结果保存为 CSV 或 JSON 格式，自动生成带时间戳的文件名。
5. **日志与调试**：记录详细的请求日志、错误信息，便于问题排查。


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
| `min_image_size`      | int        | `10000`                         | 图片最小字节大小（若可检测，目前仅通过扩展名过滤）。                 |


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


## 五、输出数据结构
### 1. 新闻数据字段（`result["news"]`）
| 字段名       | 类型       | 说明                                                                 |
|--------------|------------|----------------------------------------------------------------------|
| 标题         | str        | 新闻标题（UTF-8 编码，处理非法字符）。                               |
| 发布时间     | str        | 原文中的时间信息（未标准化，保留原始格式）。                         |
| 正文         | str        | 段落分隔的正文内容（通过 `\n` 连接）。                               |
| 主题         | str        | 新闻所属分类（通过 meta 标签提取）。                                 |
| 图片数量     | int        | 正文中有效图片的数量。                                               |
| 图片链接     | list       | 图片 URL 列表（已处理相对路径，替换为高清版本路径）。                 |
| 原文链接     | str        | 新闻详情页 URL。                                                     |

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


## 六、日志与调试
- **日志存储**：自动创建 `./logs` 目录，按时间戳生成日志文件，包含请求细节、错误信息等。
- **调试技巧**：
  - 若解析失败，可查看日志中的 `页面内容片段` 字段，手动分析 HTML 结构。
  - 修改 `config` 中的选择器（如 `nav_selectors`、`content_selectors`）以适配网站更新。
  - 关闭无头模式（`options.headless = False`）观察浏览器行为，定位渲染问题。


## 七、注意事项
1. **反爬机制**：
   - 建议设置 `request_delay >= 0.5` 秒，避免高频请求触发封禁。
   - 随机 User-Agent 和 Selenium 防检测参数（如 `--disable-blink-features=AutomationControlled`）已内置，但仍需注意网站策略变化。
2. **付费内容**：程序通过 `paid_selectors` 过滤付费内容，但可能存在漏检，需人工验证。
3. **法律合规**：本工具仅用于学术研究或数据备份，禁止用于商业用途或侵犯版权的行为。
4. **依赖更新**：定期检查 `trafilatura`、`selenium` 等库的版本，确保与网站结构兼容。


## 八、示例代码（`__main__` 入口）
```python
if __name__ == "__main__":
    crawler = AsahiCrawler()
    target_url = "https://www.asahi.com/"
    search_keywords = ["東京"]
    
    config = {
        "max_news_count": 100,
        "max_nav_news": 90,
        "max_search_news": 10,
        "request_delay": 0.5,
        "output_formats": ["csv", "json"]
    }
    
    result = crawler.crawl(
        target_url,
        search_keyword=search_keywords,
        **config
    )
    
    # 保存结果并打印统计信息
    crawler.save_data(result, **config)
    print(f"总新闻数：{len(result['news'])}, 免费新闻数：{len([n for n in result['news'] if not n['正文'].startswith('[付费内容]')])}")
```
