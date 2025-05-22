import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import os
import json
import csv
import logging
from urllib.parse import urljoin
import time

MAX_NEWS_COUNT = 10  # 最大爬取新闻数量

class AsahiCrawler:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        }
        self.logger = self.setup_logger()
        self.news_count = 0

    def setup_logger(self):
        """配置日志记录"""
        log_dir = "./logs"
        os.makedirs(log_dir, exist_ok=True)
        
        logger = logging.getLogger("asahi_crawler")
        logger.setLevel(logging.INFO)
        
        # 指定文件处理器的编码为utf-8
        file_handler = logging.FileHandler(
            f"{log_dir}/{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            encoding="utf-8"
        )
        file_handler.setLevel(logging.INFO)
        
        # 为控制台处理器添加编码设置
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        if not logger.handlers:
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
        
        return logger
    
    def crawl(self, url):
        """爬取朝日新闻网站"""
        self.logger.info(f"开始爬取: {url}")
        
        # 用于记录已访问的URL，避免重复爬取
        visited_urls = set()
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                self.logger.error(f"请求失败：状态码 {response.status_code}")
                return []
        except Exception as e:
            self.logger.error(f"请求异常: {str(e)}")
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        news_list = []
        
        # 提取导航数据
        navigation = self.extract_navigation(soup, url)
        self.logger.info(f"成功提取导航数据，包含 {len(navigation)} 个分类")
        
        # 主页面的链接
        main_page_links = soup.find_all("a", href=True)
        self.logger.info(f"主页面共找到 {len(main_page_links)} 个链接")
        
        # 处理主页面上的链接
        main_news, visited_urls = self.process_links(main_page_links, url, navigation, visited_urls)
        news_list.extend(main_news)
        
        # 处理导航栏中的每个分类链接
        for category in navigation:
            if self.news_count >= MAX_NEWS_COUNT:
                break

            category_name = category.get("name", "未知分类")
            category_url = category.get("url")
            
            if not category_url or not category_url.startswith("http"):
                self.logger.warning(f"跳过无效分类链接: {category_url}")
                continue
                
            self.logger.info(f"开始处理分类: {category_name} - {category_url}")
            
            try:
                # 请求分类页面
                category_response = requests.get(category_url, headers=self.headers, timeout=10)
                if category_response.status_code != 200:
                    self.logger.error(f"请求分类页面失败：{category_url}，状态码 {category_response.status_code}")
                    continue
                    
                category_soup = BeautifulSoup(category_response.text, "html.parser")
                
                # 提取分类页面上的所有链接
                category_links = category_soup.find_all("a", href=True)
                self.logger.info(f"{category_name} 页面共找到 {len(category_links)} 个链接")
                
                # 处理分类页面上的链接，传递已访问URL集合
                category_news, visited_urls = self.process_links(category_links, category_url, navigation, visited_urls)
                news_list.extend(category_news)

                self.logger.info(f"完成处理分类: {category_name}，找到 {len(category_news)} 条新闻")
                
                
            except Exception as e:
                self.logger.error(f"处理分类 {category_name} 时出错: {str(e)}")
                continue
        
        self.logger.info(f"完成爬取，共解析 {len(news_list)} 条有效新闻，跳过 {len(visited_urls) - len(news_list)} 个重复链接")


        # 返回包含导航数据和新闻数据的结果
        return {
            "navigation": navigation,
            "news": news_list
        }

    def process_links(self, links, base_url, navigation, visited_urls):
        """处理一组链接，提取新闻数据，同时进行URL去重"""
        news_items = []
        new_visited = set()
        
        for idx, link_elem in enumerate(links):
            try:
                # 提取详情页URL
                detail_url = link_elem["href"]
                
                # 处理相对路径和特殊URL
                if not detail_url.startswith("http"):
                    detail_url = urljoin(base_url, detail_url)
                
                # 处理可能的参数化URL
                detail_url = detail_url.split('?')[0] if '?' in detail_url else detail_url
                
                # 跳过无效链接
                if not detail_url or detail_url.startswith(("#", "javascript:")):
                    continue
                
                # 跳过视频链接
                if "/video/" in detail_url.lower():
                    self.logger.info(f"跳过视频链接: {detail_url}")
                    continue
                
                # 跳过已访问的链接
                if detail_url in visited_urls or detail_url in new_visited:
                    self.logger.debug(f"跳过重复链接: {detail_url}")
                    continue
                new_visited.add(detail_url)
                
                # 判断是否为新闻链接
                if not self.is_news_link(detail_url):
                    self.logger.debug(f"跳过非新闻链接: {detail_url}")
                    continue
                
                content = []
                image_links = []
                title = ""
                publish_time = ""
                
                # 判断是否为付费内容
                is_paid = self.is_paid_content(detail_url)
                
                # 爬取详情页，添加延时避免被反爬
                if detail_url and not detail_url.startswith("/login"):
                    if is_paid:
                        content = ["[付费内容，无法获取全文]"]
                        image_links = []
                        title = link_elem.get_text(strip=True)  # 使用链接文本作为标题
                        publish_time = ""
                        self.logger.info(f"跳过付费内容: {detail_url}")
                        continue
                    else:
                        # time.sleep(1)  # 延时1秒
                        # 从详情页获取完整信息
                        page_data = self.crawl_detail_page(detail_url)
                        content = page_data.get("content", [])
                        title = page_data.get("title", "")
                        publish_time = page_data.get("publish_time", "")
                        image_links = self.extract_images(detail_url)
                
                # 对标题进行编码处理
                try:
                    title.encode('utf-8')
                except UnicodeEncodeError:
                    self.logger.warning(f"标题包含无法编码的字符: {title[:10]}...")
                    title = title.encode('utf-8', 'replace').decode('utf-8')
                
                
                # 构建新闻条目
                news_item = {
                    "标题": title,
                    "发布时间": publish_time,
                    "正文": "\n".join(content),
                    "图片数量": len(image_links),
                    "图片链接": image_links,
                    "原文链接": detail_url,
                }
                
                # 验证并添加新闻条目
                if title and content and publish_time and content!='[付费内容，无法获取全文]':
                    news_items.append(news_item)
                    self.news_count += 1
                    if self.news_count >= MAX_NEWS_COUNT:
                        self.logger.info(f"达到最大爬取数量 {MAX_NEWS_COUNT}，停止爬取")
                        break
                    # 对日志中的标题进行编码处理
                    safe_title = title.encode('utf-8', 'replace').decode('utf-8')
                    self.logger.info(f"成功解析新闻 {idx+1}/{len(links)}: {safe_title[:30]}... , 链接: {detail_url}")
                else:
                    self.logger.warning(f"跳过无效新闻 {idx+1}/{len(links)}: 标题或正文为空，链接: {detail_url}")
            
            except Exception as e:
                self.logger.error(f"处理链接 {idx+1}/{len(links)} 时出错: {str(e)}")
                continue
        
        # 返回新闻列表和更新后的已访问URL集合
        return news_items, visited_urls.union(new_visited)
    
    def is_news_link(self, url):
        """判断URL是否指向新闻页面"""
        # 排除非新闻页面的URL模式
        exclude_patterns = [
            r"/profile/", r"/about/", r"/contact/", r"/privacy/", 
            r"/terms/", r"/sitemap/", r"/faq/", r"/search/",
            r"/subscribe/", r"/login/", r"/register/", r"/logout/"
        ]
        
        # 检查URL是否匹配排除模式
        for pattern in exclude_patterns:
            if re.search(pattern, url):
                return False
        
        # 检查URL是否包含新闻标识
        news_patterns = [
            r"https://www.asahi.com/articles/"
        ]
        
        for pattern in news_patterns:
            if pattern in url.lower():
                return True
        
        return False 
    
    def extract_navigation(self, soup, base_url):
        """提取网站导航数据"""
        self.logger.info("开始提取导航数据")
        navigation = []
        
        # 尝试多种可能的导航容器选择器
        nav_selectors = [
            "div#GlobalNav",       # 添加：通过id匹配导航容器
            "ul.NavInner",         # 添加：通过class匹配导航容器    
        ]
        
        nav_elem = None
        for selector in nav_selectors:
            nav_elem = soup.select_one(selector)
            if nav_elem:
                self.logger.info(f"使用选择器 '{selector}' 找到导航容器")
                break
        
        if not nav_elem:
            self.logger.warning("未找到导航容器")
            return navigation
        
        level1_items = nav_elem.select("li.NavItem")
        for item in level1_items:
            # 跳过分隔线或非导航项（如Line类）
            if "Line" in item.get("class", []):
                continue
                
            link = item.select_one("a")
            if link:
                href = link.get("href")
                if href and not href.startswith(("#", "javascript:")):
                    if not href.startswith("http"):
                        href = urljoin(base_url, href)
                        
                    # ---------------------- 关键修改：标题编码处理 ----------------------
                    # 提取标题并转换为UTF-8编码的Unicode字符串
                    title = link.get_text(strip=True)
                    # 处理可能的编码错误（如替换无法解析的字符）
                    title = title.encode('utf-8', errors='replace').decode('utf-8')
                    # ------------------------------------------------------------------
                    
                    nav_item = {
                        "title": title,
                        "url": href,
                        "children": []
                    }
                    navigation.append(nav_item)
                    
                    # 查找子菜单
                    submenu = item.select_one("ul.SubNav")
                    if submenu:
                        sub_items = submenu.select("li.NavItem a")
                        for sub_item in sub_items:
                            sub_href = sub_item.get("href")
                            if sub_href and not sub_href.startswith(("#", "javascript:")):
                                if not sub_href.startswith("http"):
                                    sub_href = urljoin(base_url, sub_href)
                                    
                                # ---------------------- 子标题编码处理 ----------------------
                                sub_title = sub_item.get_text(strip=True)
                                sub_title = sub_title.encode('utf-8', errors='replace').decode('utf-8')
                                # ----------------------------------------------------------------
                                
                                child = {
                                    "title": sub_title,
                                    "url": sub_href,
                                    "children": []
                                }
                                nav_item["children"].append(child)
        # print(f"导航数据：{navigation}")
        self.logger.info(f"成功提取 {len(navigation)} 个导航项")
        return navigation
    
    
    
    
    def is_paid_content(self, url):
        """判断URL是否指向付费内容"""
        try:
            if not url:
                return False
                
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return False
                
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 0. 专门检测特定网站的付费图标元素
            if soup.select('img[src="//www.asahicom.jp/images/icon_key_gold.png"]'):
                self.logger.info(f"发现特定付费图标元素: {url}")
                return True
            
            # 1. 检测特定的付费提示文本
            if soup.select('span.hideFromApp:contains("有料会員になると続きをお読みいただけます。")'):
                self.logger.info(f"发现特定付费提示: {url}")
                return True
                           
            return False
            
        except Exception as e:
            self.logger.error(f"判断付费内容时出错: {str(e)}")
            return False
        
    def crawl_detail_page(self, url):
        """爬取详情页内容，返回包含标题、时间和正文的字典"""
        try:
            # 添加重试机制
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = requests.get(url, headers=self.headers, timeout=10)
                    response.raise_for_status()
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        self.logger.error(f"请求详情页失败: {url}, 错误: {str(e)}")
                        return {"content": [], "title": "", "publish_time": ""}
                    time.sleep(2 * (attempt + 1))  # 指数退避
                    
            # 设置编码，优先使用网页指定的编码
            if response.encoding == 'ISO-8859-1':
                response.encoding = response.apparent_encoding
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取标题 - 尝试多种可能的标题元素
            title_div = soup.find('div', class_='y_Qv3')
            title = title_div.find('h1').get_text(strip=True) if title_div else ""
            
            # 提取发布时间 - 尝试多种可能的时间元素
            time_element = soup.find('time')
            datetime_str = time_element['datetime'] if time_element and 'datetime' in time_element.attrs else ""
            publish_time = time_element.get_text(strip=True) if time_element else ""
            
            # 提取正文内容 - 方法1: 寻找具有特定class的正文容器
            content = []
            main_content = None
            
            # 尝试常见的正文容器类名
            container_classes = [
                'article-content', 'main-content', 'post-content', 
                'entry-content', 'news-content', 'story-body',
                'article-body', 'article-main'
            ]
            
            for class_name in container_classes:
                main_content = soup.find(class_=class_name)
                if main_content:
                    break
            
            # 如果没找到，尝试通过标签结构猜测
            if not main_content:
                main_content = soup.find('div', {'id': 'content'}) or soup.find('main')
            
            # 如果还没找到，尝试提取多个段落
            if not main_content:
                paragraphs = soup.find_all('p')
                if len(paragraphs) > 3:  # 如果有足够多的段落，认为这是正文
                    content = [p.get_text(strip=True) for p in paragraphs]
                    return {"content": content, "title": title, "publish_time": publish_time}
                else:
                    self.logger.warning(f"未找到正文容器: {url}")
                    return {"content": [], "title": title, "publish_time": publish_time}
            
            # 提取正文内容
            if main_content:
                # 提取所有段落文本
                for p in main_content.find_all('p'):
                    text = p.get_text(strip=True)
                    if text:
                        content.append(text)
                
                # 如果提取的内容太少，尝试其他方法
                if len(content) < 3:
                    # 方法2: 提取所有有意义的文本块
                    text_blocks = main_content.find_all(string=True)
                    text_content = [t.strip() for t in text_blocks if t.strip()]
                    content = text_content
                
                # 如果还是很少内容，可能是JavaScript渲染的页面
                if len(content) < 3:
                    self.logger.warning(f"提取的正文内容过少: {url}")
            
            return {"content": content, "title": title, "publish_time": publish_time}
            
        except Exception as e:
            self.logger.error(f"爬取详情页内容出错: {url}, 错误: {str(e)}")
            return {"content": [], "title": "", "publish_time": ""}
    
    def extract_images(self, url):
        """提取详情页中的所有图片链接（包括大图和缩略图）"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return []
                
            soup = BeautifulSoup(response.text, "html.parser")
            content_selectors = ["div.w8Bsl", "div.Isto1"]
                
            image_links = set()  # 使用集合去重
            
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    
                    # 统一处理所有img标签
                    for img in content_elem.find_all("img"):
                        src = img.get("src") or img.get("srcset")
                        if not src:
                            continue
                            
                        # 标准化URL格式
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif not src.startswith("http"):
                            src = urljoin(url, src)
                            
                        # 验证图片有效性（可根据实际需求调整过滤条件）
                        if self.is_valid_image(src, img):
                            src = self.replace_image_path(src)
                            image_links.add(src)  # 自动去重
                        
            return list(image_links)
            
        except Exception as e:
            self.logger.error(f"提取图片失败: {str(e)}")
            return []

    import re

    def replace_image_path(self, url, target="hd640"):
        """
        替换图片URL中倒数第二个路径段为目标字符串
        例如: https://example.com/img/axsada/hw120/filename.jpg → https://example.com/img/axsada/hd640/filename.jpg
        """
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            return url
        
        try:
            # 新正则模式：匹配倒数第二个路径段（文件名前的路径段）
            pattern = r'(?<=/)[^/]+(?=/[^/]+$)'
            
            # 执行替换
            modified_url = re.sub(
                pattern,
                target,
                url,
                flags=re.IGNORECASE
            )
            
            return modified_url
        except Exception as e:
            self.logger.error(f"URL处理失败: {str(e)}")
            return url
    def is_valid_image(self, url, img_element=None):
        """判断是否为有效新闻配图"""
        invalid_keywords = ["icon", "logo", "sponsor", "ad-", "banner", "button", "avatar", "author"]
        valid_extensions = [".jpg"]
        
        lower_url = url.lower()
        
        # 检查文件扩展名
        if not any(ext in lower_url for ext in valid_extensions):
            return False
        
        # 排除包含无效关键词的URL
        if any(keyword in lower_url for keyword in invalid_keywords):
            return False
        
        return True
    
    def save_to_csv(self, data, output_dir="saves/csv"):
        """保存数据到CSV文件"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            filename = f"{output_dir}/{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            with open(filename, "w", encoding="utf-8-sig", newline="") as csvfile:
                # 保存新闻数据
                fieldnames = ["标题", "发布时间", "正文", "图片数量", "图片链接", "原文链接"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for news in data["news"]:
                    writer.writerow(news)
            
            self.logger.info(f"新闻数据已保存到CSV: {filename}")
            return filename
        except Exception as e:
            self.logger.error(f"保存CSV失败: {str(e)}")
            return None

    def save_to_json(self, data, output_dir="saves/json"):
        """保存数据到JSON文件"""
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

# 主程序入口
if __name__ == "__main__":
    # 设置控制台编码为utf-8
    import sys
    if sys.platform.startswith('win'):
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    

    MAX_NEWS_COUNT = 100  # 最大爬取新闻数量

    crawler = AsahiCrawler()
    target_url = "https://www.asahi.com/"
    
    start_time = datetime.now()
    # 爬取新闻
    result = crawler.crawl(target_url)

    end_time = datetime.now()
    elapsed_time = end_time - start_time

    crawler.logger.info("\n爬取时间统计:")
    crawler.logger.info(f"- 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    crawler.logger.info(f"- 结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    crawler.logger.info(f"- 总耗时: {elapsed_time.total_seconds():.2f} 秒 ({elapsed_time})")
    if result and result["news"]:
        # 过滤掉付费新闻
        free_news = result["news"]
        filtered_result = {
            "navigation": result["navigation"],
            "news": free_news
        }
        
        # 保存数据
        if free_news:
            csv_file = crawler.save_to_csv(filtered_result)
            json_file = crawler.save_to_json(filtered_result["news"])
            
            # 打印示例结果
            print(f"\n共爬取到 {len(result['news'])} 条新闻，其中{len(free_news)}条为免费内容")
            print(f"发现 {len(result['navigation'])} 个导航分类")
            
        else:
            print("未爬取到任何免费新闻数据")
    else:
        print("未爬取到任何新闻数据")
        print("提示：网站结构可能已更新，需要进一步调试选择器")