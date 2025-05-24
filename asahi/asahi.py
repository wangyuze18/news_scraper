import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import os
import json
import csv
import logging
from urllib.parse import urljoin, quote
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import random
try:
    from trafilatura import fetch_url, extract
except ImportError:
    extract = None  # Fallback to original extraction if trafilatura is not installed

class AsahiCrawler:
    def __init__(self):
        self.headers_list = [
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
            },
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            },
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0"
            },
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.2535.51"
            },
            {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            }
        ]
        self.logger = self.setup_logger()
        self.news_count = 0
        self.config = {
            "nav_selectors": ["div#GlobalNav", "ul.NavInner"],
            "content_selectors": ["div.w8Bsl", "div.Isto1", "article-content", "main-content"],
            "paid_selectors": ['img[src*="icon_key_gold.png"]', 'span.hideFromApp:contains("有料会員")'],
            "valid_image_extensions": [".jpg", ".jpeg", ".png", ".webp"],
            "request_timeout": 10,
            "max_retries": 3,
            "min_image_size": 20,  # Minimum image size in bytes (if detectable)
            "image_save_path": "./saves/pic"  # Default image save path
        }

    def setup_logger(self):
        """Configure logging"""
        log_dir = "./logs"
        os.makedirs(log_dir, exist_ok=True)
        
        logger = logging.getLogger("asahi_crawler")
        logger.setLevel(logging.INFO)
        
        file_handler = logging.FileHandler(
            f"{log_dir}/{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            encoding="utf-8"
        )
        file_handler.setLevel(logging.INFO)
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        if not logger.handlers:
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
        
        return logger
    
    def download_images(self, news_item, save_dir=None):
        """Download images from news item's image links to the specified directory"""
        if save_dir is None:
            save_dir = self.config["image_save_path"]
        
        os.makedirs(save_dir, exist_ok=True)
        downloaded_files = []
        
        # Extract URL suffix from 原文链接
        url = news_item.get("原文链接", "")
        if url:
            # Get the last part of the URL path (e.g., 'ASN123456789' from 'https://www.asahi.com/articles/ASN123456789.html')
            url_suffix = os.path.basename(url.rstrip('/')).split('?')[0]
            # Remove .html extension if present
            url_suffix = os.path.splitext(url_suffix)[0]
            # Sanitize the suffix for folder name (remove invalid characters)
            folder_name = re.sub(r'[^\w\-]', '_', url_suffix)[:50]  # Limit to 50 characters, replace invalid chars with '_'
        else:
            folder_name = "unnamed"  # Fallback if no URL is present
        
        article_dir = os.path.join(save_dir, folder_name)
        os.makedirs(article_dir, exist_ok=True)
        
        for idx, img_url in enumerate(news_item.get("图片链接", []), start=1):
            try:
                headers = random.choice(self.headers_list)
                response = requests.get(img_url, headers=headers, timeout=self.config["request_timeout"])
                if response.status_code != 200:
                    self.logger.error(f"下载图片失败: {img_url}, 状态码: {response.status_code}")
                    continue
                
                # Extract file extension
                ext = os.path.splitext(img_url)[1].lower()
                if ext not in self.config["valid_image_extensions"]:
                    self.logger.warning(f"跳过无效图片扩展名: {img_url}")
                    continue
                
                # Check image size if possible
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) < self.config["min_image_size"]:
                    self.logger.warning(f"图片过小，跳过: {img_url}, 大小: {content_length} bytes")
                    continue
                
                # Generate filename
                filename = f"{idx}{ext}"
                filepath = os.path.join(article_dir, filename)
                
                # Save image
                with open(filepath, "wb") as f:
                    f.write(response.content)
                downloaded_files.append(filepath)
                self.logger.info(f"成功下载图片: {img_url} 到 {filepath}")
            
            except Exception as e:
                self.logger.error(f"下载图片失败: {img_url}, 错误: {str(e)}")
                continue
        
        return downloaded_files
    
    def fetch_url(self, url, retries=0):
            """Fetch URL with retries and random User-Agent"""
            headers = random.choice(self.headers_list)
            self.logger.debug(f"使用 User-Agent: {headers['User-Agent']}")
            for attempt in range(retries + 1):
                try:
                    response = requests.get(url, headers=headers, timeout=self.config["request_timeout"])
                    if response.status_code != 200:
                        self.logger.error(f"请求失败: {url}, 状态码: {response.status_code}")
                        return None
                    response.encoding = response.apparent_encoding if response.encoding == 'ISO-8859-1' else response.encoding
                    return response.text
                except Exception as e:
                    if attempt < retries:
                        delay = 2 ** attempt
                        self.logger.warning(f"请求 {url} 失败，重试 {attempt + 1}/{retries}，等待 {delay}s: {str(e)}")
                        time.sleep(delay)
                    else:
                        self.logger.error(f"请求 {url} 失败: {str(e)}")
                        return None
            return None

    def fetch_rendered_page(self, url, render_timeout=15):
            """Fetch fully rendered page using Selenium with random User-Agent"""
            headers = random.choice(self.headers_list)
            self.logger.debug(f"使用 User-Agent: {headers['User-Agent']}")
            driver = None
            try:
                options = Options()
                options.headless = True
                options.add_argument(f"user-agent={headers['User-Agent']}")
                # Reduce bot detection
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option("useAutomationExtension", False)
                
                # Use webdriver_manager to ensure compatible ChromeDriver
                driver = webdriver.Chrome(options=options)
                driver.get(url)
                
                # Wait for search results or fallback selectors
                selectors = [
                    "div#Contents ul.ListBlock#SiteSearchResult li a",
                ]
                response_text = None
                for selector in selectors:
                    try:
                        self.logger.debug(f"等待元素: {selector}")
                        WebDriverWait(driver, render_timeout).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        time.sleep(random.uniform(0.5, 1.5))  # Random delay to mimic human behavior
                        response_text = driver.page_source
                        self.logger.debug(f"成功找到元素 {selector} 并渲染页面: {url}")
                        break
                    except TimeoutException:
                        self.logger.warning(f"未找到元素 {selector} 在 {render_timeout} 秒内")
                        continue
                
                # If no selectors matched, return page source for debugging
                if not response_text:
                    self.logger.warning(f"所有选择器均未找到，获取当前页面源码: {url}")
                    response_text = driver.page_source
                    self.logger.debug(f"页面内容片段: {response_text[:500]}")
                
                return response_text
            
            except WebDriverException as e:
                self.logger.error(f"Selenium 驱动错误: {url}, 错误: {str(e)}")
                return None
            except Exception as e:
                self.logger.error(f"渲染页面 {url} 失败: {str(e)}")
                return None
            finally:
                if driver:
                    try:
                        driver.quit()
                    except Exception as e:
                        self.logger.debug(f"关闭驱动时出错: {str(e)}")

    def crawl(self, url, max_news_count=float('inf'), max_nav_news=float('inf'), max_search_news=float('inf'), search_keyword=None, request_delay=0.5, render_timeout=10):
        """Crawl Asahi website, including navigation and search results"""
        self.logger.info(f"开始爬取: {url}, 最大新闻数: {max_news_count}, 导航新闻数: {max_nav_news}, 搜索新闻数: {max_search_news}, 请求延迟: {request_delay}s, 渲染超时: {render_timeout}s")
        self.news_count = 0
        visited_urls = set()
        news_list = []
        
        # 1. Crawl navigation data (using static fetch for simplicity)
        response_text = self.fetch_url(url, self.config["max_retries"])
        if not response_text:
            return {"navigation": [], "news": []}
        
        soup = BeautifulSoup(response_text, "html.parser")
        navigation = self.extract_navigation(soup, url)
        self.logger.info(f"成功提取导航数据，包含 {len(navigation)} 个分类")
        
        main_page_links = soup.find_all("a", href=True)
        self.logger.info(f"主页面共找到 {len(main_page_links)} 个链接")
        
        main_news, visited_urls = self.process_links(main_page_links, url, navigation, visited_urls, min(max_nav_news, max_news_count), request_delay)
        news_list.extend(main_news)
        
        for category in navigation:
            if self.news_count >= max_nav_news or self.news_count >= max_news_count:
                break
            category_name = category.get("name", "未知分类")
            category_url = category.get("url")
            
            if not category_url or not category_url.startswith("http"):
                self.logger.warning(f"跳过无效分类链接: {category_url}")
                continue
                
            self.logger.info(f"开始处理分类: {category_name} - {category_url}")
            category_response = self.fetch_url(category_url, self.config["max_retries"])
            if not category_response:
                continue
                
            category_soup = BeautifulSoup(category_response, "html.parser")
            category_links = category_soup.find_all("a", href=True)
            self.logger.info(f"{category_name} 页面共找到 {len(category_links)} 个链接")
            
            category_news, visited_urls = self.process_links(category_links, category_url, navigation, visited_urls, min(max_nav_news - self.news_count, max_news_count - self.news_count), request_delay)
            news_list.extend(category_news)
            self.logger.info(f"完成处理分类: {category_name}，找到 {len(category_news)} 条新闻")
            time.sleep(request_delay)
        
        # 2. Crawl search results
        if search_keyword and max_search_news > 0:
            if isinstance(search_keyword, str):
                search_keywords = [search_keyword]
            else:
                search_keywords = search_keyword
            
            for keyword in search_keywords:
                if self.news_count >= max_news_count:
                    self.logger.info(f"达到最大新闻数限制（总: {max_news_count}），停止搜索")
                    break
                try:
                    keyword_news_count = 0
                    search_news, visited_urls = self.crawl_search_results(keyword, min(max_search_news, max_news_count - self.news_count), visited_urls, max_news_count, request_delay, render_timeout)
                    news_list.extend(search_news)
                    keyword_news_count += len(search_news)
                    self.logger.info(f"关键词 {keyword} 爬取完成，共找到 {keyword_news_count} 条新闻")
                except Exception as e:
                    self.logger.error(f"搜索关键词 {keyword} 失败，跳到下一个关键词: {str(e)}")
                    continue
        
        self.logger.info(f"完成爬取，共解析 {self.news_count} 条有效新闻，跳过 {len(visited_urls) - self.news_count} 个重复链接")
        return {"navigation": navigation, "news": news_list}

    def process_links(self, links, base_url, navigation, visited_urls, max_news, request_delay):
        """Process a list of links, extract news data with URL deduplication"""
        news_items = []
        new_visited = set()
        count = 0
        for idx, link_elem in enumerate(links):
            if count >= max_news:
                break
            try:
                detail_url = link_elem["href"]
                if not detail_url.startswith("http"):
                    detail_url = urljoin(base_url, detail_url)
                detail_url = detail_url.split('?')[0] if '?' in detail_url else detail_url
                
                if not detail_url or detail_url.startswith(("#", "javascript:")) or "/video/" in detail_url.lower():
                    continue
                if detail_url in visited_urls or detail_url in new_visited:
                    self.logger.debug(f"跳过重复链接: {detail_url}")
                    continue
                new_visited.add(detail_url)
                
                if not self.is_news_link(detail_url):
                    self.logger.debug(f"跳过非新闻链接: {detail_url}")
                    continue
                
                is_paid = self.is_paid_content(detail_url)
                if is_paid:
                    self.logger.info(f"跳过付费内容: {detail_url}")
                    continue
                
                page_data = self.crawl_detail_page(detail_url)
                image_links = self.extract_images(detail_url)
                
                try:
                    title = page_data.get("title", "").encode('utf-8', 'replace').decode('utf-8')
                except UnicodeEncodeError:
                    self.logger.warning(f"标题包含无法编码的字符: {page_data.get('title', '')[:10]}...")
                    title = page_data.get("title", "")
                
                news_item = {
                    "标题": title,
                    "发布时间": page_data.get("publish_time", ""),
                    "正文": "\n".join(page_data.get("content", [])),
                    "主题": page_data.get("topic", ""),
                    "图片数量": len(image_links),
                    "图片链接": image_links,
                    "原文链接": detail_url
                }
                
                if title and page_data.get("content") and page_data.get("publish_time"):
                    news_items.append(news_item)
                    self.news_count += 1
                    count += 1
                    self.logger.info(f"成功解析新闻 {idx+1}/{len(links)}: {title[:30]}... , 链接: {detail_url}")
                else:
                    self.logger.warning(f"跳过无效新闻 {idx+1}/{len(links)}: 标题或正文为空，链接: {detail_url}")
                
                time.sleep(request_delay)
            
            except Exception as e:
                self.logger.error(f"处理链接 {idx+1}/{len(links)} 时出错: {str(e)}")
                continue
        
        return news_items, visited_urls.union(new_visited)
    
    def is_news_link(self, url):
        """Check if URL points to a news page"""
        exclude_patterns = [
            r"/profile/", r"/about/", r"/contact/", r"/privacy/", 
            r"/terms/", r"/sitemap/", r"/faq/", r"/search/",
            r"/subscribe/", r"/login/", r"/register/", r"/logout/"
        ]
        for pattern in exclude_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        news_patterns = [r"https://www.asahi.com/articles/"]
        for pattern in news_patterns:
            if pattern in url.lower():
                return True
        return False
    
    def extract_navigation(self, soup, base_url):
        """Extract website navigation data"""
        self.logger.info("开始提取导航数据")
        navigation = []
        
        nav_elem = None
        for selector in self.config["nav_selectors"]:
            nav_elem = soup.select_one(selector)
            if nav_elem:
                self.logger.info(f"使用选择器 '{selector}' 找到导航容器")
                break
        
        if not nav_elem:
            self.logger.warning("未找到导航容器")
            return navigation
        
        level1_items = nav_elem.select("li.NavItem")
        for item in level1_items:
            if "Line" in item.get("class", []):
                continue
            link = item.select_one("a")
            if link:
                href = link.get("href")
                if href and not href.startswith(("#", "javascript:")):
                    if not href.startswith("http"):
                        href = urljoin(base_url, href)
                    title = link.get_text(strip=True).encode('utf-8', errors='replace').decode('utf-8')
                    nav_item = {"title": title, "url": href, "children": []}
                    navigation.append(nav_item)
                    
                    submenu = item.select_one("ul.SubNav")
                    if submenu:
                        sub_items = submenu.select("li.NavItem a")
                        for sub_item in sub_items:
                            sub_href = sub_item.get("href")
                            if sub_href and not sub_href.startswith(("#", "javascript:")):
                                if not sub_href.startswith("http"):
                                    sub_href = urljoin(base_url, sub_href)
                                sub_title = sub_item.get_text(strip=True).encode('utf-8', errors='replace').decode('utf-8')
                                nav_item["children"].append({"title": sub_title, "url": sub_href, "children": []})
        
        self.logger.info(f"成功提取 {len(navigation)} 个导航项")
        return navigation
    
    def is_paid_content(self, url):
        """Check if URL points to paid content"""
        try:
            if not url:
                return False
            response_text = self.fetch_url(url, self.config["max_retries"])
            if not response_text:
                return False
            soup = BeautifulSoup(response_text, "html.parser")
            for selector in self.config["paid_selectors"]:
                if soup.select(selector):
                    self.logger.info(f"发现付费内容: {url}")
                    return True
            return False
        except Exception as e:
            self.logger.error(f"判断付费内容时出错: {url}, {str(e)}")
            return False
    
    def crawl_detail_page(self, url):
        """Crawl detail page content"""
        try:
            response_text = self.fetch_url(url, self.config["max_retries"])
            if not response_text:
                return {"content": [], "title": "", "publish_time": "", "topic": ""}
            
            if extract:  # Use trafilatura if available
                extracted = extract(response_text, url=url, include_images=False, include_formatting=False)
                if extracted:
                    content = [line.strip() for line in extracted.split('\n') if line.strip()]
                    soup = BeautifulSoup(response_text, 'html.parser')
                    title = soup.find('div', class_='y_Qv3') or soup.find('h1')
                    title = title.get_text(strip=True) if title else ""
                    time_element = soup.find('time')
                    publish_time = time_element.get_text(strip=True) if time_element else ""
                    topic = soup.find('meta', {'name': 'cXenseParse:ash-category'})
                    topic = topic['content'] if topic and 'content' in topic.attrs else ""
                    return {"content": content, "title": title, "publish_time": publish_time, "topic": topic}
            
            # Fallback to original extraction
            soup = BeautifulSoup(response_text, 'html.parser')
            topic = soup.find('meta', {'name': 'cXenseParse:ash-category'})
            topic = topic['content'] if topic and 'content' in topic.attrs else ""
            
            title_div = soup.find('div', class_='y_Qv3')
            title = title_div.find('h1').get_text(strip=True) if title_div else ""
            
            time_element = soup.find('time')
            publish_time = time_element.get_text(strip=True) if time_element else ""
            
            content = []
            main_content = None
            for class_name in self.config["content_selectors"]:
                main_content = soup.find(class_=class_name)
                if main_content:
                    break
            
            if not main_content:
                main_content = soup.find('div', {'id': 'content'}) or soup.find('main')
            
            if main_content:
                for p in main_content.find_all('p'):
                    text = p.get_text(strip=True)
                    if text:
                        content.append(text)
                if len(content) < 3:
                    text_blocks = main_content.find_all(string=True)
                    content = [t.strip() for t in text_blocks if t.strip()]
            
            if len(content) < 3:
                self.logger.warning(f"提取的正文内容过少: {url}")
            
            return {"content": content, "title": title, "publish_time": publish_time, "topic": topic}
        
        except Exception as e:
            self.logger.error(f"爬取详情页内容出错: {url}, {str(e)}")
            return {"content": [], "title": "", "publish_time": "", "topic": ""}
    
    def extract_images(self, url):
        """Extract all image links from a detail page"""
        try:
            response_text = self.fetch_url(url, self.config["max_retries"])
            if not response_text:
                return []
                
            soup = BeautifulSoup(response_text, "html.parser")
            image_links = set()
            
            for selector in self.config["content_selectors"]:
                content_elem = soup.select_one(selector)
                if content_elem:
                    for img in content_elem.find_all("img"):
                        src = img.get("src") or img.get("srcset")
                        if not src:
                            continue
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif not src.startswith("http"):
                            src = urljoin(url, src)
                        if self.is_valid_image(src, img):
                            src = self.replace_image_path(src)
                            image_links.add(src)
            
            return list(image_links)
        except Exception as e:
            self.logger.error(f"提取图片失败: {url}, {str(e)}")
            return []

    def replace_image_path(self, url, target="hd640"):
        """Replace the second-to-last path segment in image URL"""
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            return url
        try:
            pattern = r'(?<=/)[^/]+(?=/[^/]+$)'
            return re.sub(pattern, target, url, flags=re.IGNORECASE)
        except Exception as e:
            self.logger.error(f"URL处理失败: {url}, {str(e)}")
            return url
    
    def is_valid_image(self, url, img_element=None):
        """Validate if image is a valid news image"""
        invalid_keywords = ["icon", "logo", "sponsor", "ad-", "banner", "button", "avatar", "author"]
        if not any(ext in url.lower() for ext in self.config["valid_image_extensions"]):
            return False
        if any(keyword in url.lower() for keyword in invalid_keywords):
            return False
        return True
    
    def save_to_csv(self, data, output_dir="saves/csv"):
        """Save data to CSV file with sequence number"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            filename = f"{output_dir}/{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(filename, "w", encoding="utf-8-sig", newline="") as csvfile:
                fieldnames = ["序号", "标题", "发布时间", "正文", "主题", "图片数量", "图片链接", "原文链接", "下载的图片路径"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for idx, news in enumerate(data["news"], start=1):
                    row = {
                        "序号": idx,
                        **news,
                        "下载的图片路径": ";".join(news.get("下载的图片路径", []))  # Join paths with semicolon for CSV
                    }
                    writer.writerow(row)
            self.logger.info(f"新闻数据已保存到CSV: {filename}")
            return filename
        except Exception as e:
            self.logger.error(f"保存CSV失败: {str(e)}")
            return None

    def save_to_json(self, data, output_dir="saves/json"):
        """Save data to JSON file"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            filename = f"{output_dir}/{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, "w", encoding="utf-8") as jsonfile:
                json.dump(data, jsonfile, ensure_ascii=False, indent=2)
            self.logger.info(f"数据已保存到JSON: {filename}")
            return filename
        except Exception as e:
            self.logger.error(f"保存JSON失败: {str(e)}")
            return None

    def save_data(self, data, output_formats=["csv", "json"], output_dir="saves"):
        """Save data to specified formats and download images"""
        results = []
        
        # Update news items with downloaded image paths
        for news_item in data["news"]:
            downloaded_files = self.download_images(news_item, os.path.join(output_dir, "pic"))
            news_item["下载的图片路径"] = downloaded_files  # Add downloaded file paths to news item
        
        if "csv" in output_formats:
            results.append(self.save_to_csv(data, f"{output_dir}/csv"))
        if "json" in output_formats:
            results.append(self.save_to_json(data, f"{output_dir}/json"))
        
        return results

    def crawl_search_results(self, keyword, max_search_news, visited_urls, max_news_count, request_delay, render_timeout=15):
        """Crawl search result pages with rendering"""
        self.logger.info(f"开始爬取搜索结果，关键词: {keyword}, 最大新闻数: {max_search_news}, 渲染超时: {render_timeout}s")
        news_list = []
        new_visited = set()
        
        encoded_keyword = quote(keyword)
        base_search_url = "https://sitesearch.asahi.com/sitesearch/?Keywords={}&Searchsubmit2=検索&Searchsubmit=検索"
        
        page = 1
        while True:
            if self.news_count >= max_news_count or len(news_list) >= max_search_news:
                self.logger.info(f"达到最大新闻数限制（总: {max_news_count}, 搜索: {max_search_news}），停止搜索")
                break
            search_url = base_search_url.format(encoded_keyword) + f"&start={20 * (page - 1)}"
            self.logger.info(f"爬取搜索页面 {page}: {search_url}")
            
            # Fetch rendered page with Selenium
            response_text = self.fetch_rendered_page(search_url, render_timeout)
            if not response_text:
                self.logger.warning(f"无法渲染页面 {search_url}，停止此页")
                break
                
            soup = BeautifulSoup(response_text, "html.parser")
            
            # Try primary selector
            search_results = soup.select("ul.ListBlock#SiteSearchResult li a")
            if not search_results:
                # Fallback selector within div#Contents
                search_results = soup.select("div#Contents ul.ListBlock#SiteSearchResult li a")
                self.logger.warning(f"主选择器未找到结果，尝试备用选择器: div#Contents ul.ListBlock#SiteSearchResult li a")
            
            self.logger.info(f"搜索页面 {page} 找到 {len(search_results)} 个链接")
            if search_results:
                self.logger.debug(f"页面内容片段: {response_text[:500]}")
            else:
                self.logger.debug(f"页面无新闻，停止搜索")
                break
                
            
            page_news, visited_urls = self.process_links(search_results, search_url, [], visited_urls, min(max_search_news - len(news_list), max_news_count - self.news_count), request_delay)
            news_list.extend(page_news)
            
            page += 1
            time.sleep(random.randint(2,4))
        
        self.logger.info(f"搜索爬取完成（关键词: {keyword}），共找到 {len(news_list)} 条新闻")
        return news_list, visited_urls

if __name__ == "__main__":
    import sys
    if sys.platform.startswith('win'):
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    crawler = AsahiCrawler()
    target_url = "https://www.asahi.com/"
    search_keywords = ["花束みたいな恋をした","ラブレター","言葉の庭","君の名は。","打ち上げ花火","小森",]
    
    config = {
        "max_news_count": 100,
        "max_nav_news": 50,
        "max_search_news": 25,
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

    if result and result["news"]:
        free_news = [news for news in result["news"] if "[付费内容，无法获取全文]" not in news["正文"]]
        filtered_result = {
            "navigation": result["navigation"],
            "news": free_news,
            "stats": {
                "total_news": len(result["news"]),
                "free_news": len(free_news),
                "navigation_count": len(result["navigation"]),
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
    
    end_time = datetime.now()
    elapsed_time = end_time - start_time
    
    crawler.logger.info("\n爬取时间统计:")
    crawler.logger.info(f"- 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    crawler.logger.info(f"- 结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    crawler.logger.info(f"- 总耗时: {elapsed_time.total_seconds():.2f} 秒 ({elapsed_time})")
    