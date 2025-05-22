import re
from urllib.parse import urljoin
import time
import random
from typing import List, Dict, Optional, Set
import csv
from datetime import datetime, timedelta
import json
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import requests
import os

class YahooJapanNewsScraper:
    def __init__(self, log_file=None):
        self.base_url = "https://news.yahoo.co.jp"
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
        ]
        self.ad_keywords = [
            'advertisement', 'ad', 'promotion', 'sponsored',
            '広告', 'PR', 'スポンサー', 'プロモーション',
            'adserver', 'doubleclick', 'amazon-adsystem'
        ]
        self.visited_urls = set()  # 用于URL去重
        self.article_pattern = re.compile(
            r'^https?://news\.yahoo\.co\.jp/articles/[a-z0-9]+$',  # 匹配/articles/文章ID格式
            re.IGNORECASE
        )
        self.resource_pattern = re.compile(
            r'/images/|/videos/|/photos/|/photo/|/gallery/|/pickup/',  # 排除图片/视频/相册/过渡页路径
            re.IGNORECASE
        )
        
        # 配置日志
        self.logger = self._setup_logger(log_file)

    def _setup_logger(self, log_file=None):
        """配置日志记录器"""
        logger = logging.getLogger('YahooNewsScraper')
        logger.setLevel(logging.INFO)
        
        # 清除默认处理器
        if logger.handlers:
            logger.handlers = []
        
        # 创建文件处理器
        if log_file:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            logger.addHandler(file_handler)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(console_handler)
        
        return logger

    def get_random_headers(self):
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
            'Referer': self.base_url
        }
    
    def is_valid_news_url(self, url):
        """判断是否为有效的雅虎新闻正文链接（排除资源页）"""
        # 先清洗URL，再校验有效性
        cleaned_url = self.clean_article_url(url)
        if not cleaned_url:
            return False
            
        # 校验是否符合文章链接格式且不包含资源路径
        if not self.article_pattern.match(cleaned_url):
            return False
        if self.resource_pattern.search(cleaned_url):
            return False
            
        return True
    
    def clean_article_url(self, url: str) -> Optional[str]:
        """清洗URL，提取主文章链接（去除/images/000等后缀）"""
        # 匹配/articles/后面的路径
        match = re.search(r'(https://news\.yahoo\.co\.jp/articles/[^/]+)', url)
        if match:
            return match.group(1)  # 返回主链接部分
        return None  # 无效链接返回None
    
    # 核心方法整合
    def scrape_news(self, 
                    max_articles=None,        # 移除默认值，允许无限爬取
                    max_per_categories=None,           # 移除默认值，允许无限加载链接
                    max_per_topics=None):   # 移除默认值，允许无限分类爬取
        """整合多来源的爬取入口"""
        self.logger.info("开始爬取新闻...")
        all_articles = []
        all_links = set()
        
        # 1. 主页最新新闻
        self.logger.info("正在从主页分类获取新闻...")
        category_links = self.get_news_links_from_categories(max_links_per_category=max_per_categories)  # 取消分类内链接数限制
        all_links = set(category_links)
        self.logger.info(f"从主页获取到 {len(category_links)} 条链接")
        
        # 2. 话题爬取
        self.logger.info("正在从话题页面获取新闻...")
        topic_links = self.get_links_from_topics(max_per_topics=max_per_topics)  # 取消每个分类最大数量限制
        all_links.update(topic_links)
        self.logger.info(f"从话题页面获取到 {len(topic_links)} 条链接")
        
        # 去重后爬取详情（保留去重逻辑，但不限制数量）
        unique_links = [url for url in all_links if url not in self.visited_urls]
        self.logger.info(f"开始爬取 {len(unique_links)} 篇唯一文章...")
        
        for idx, url in enumerate(unique_links, 1):
            # 清洗并验证URL
            cleaned_url = self.clean_article_url(url)
            if not cleaned_url or not self.is_valid_news_url(cleaned_url):
                self.logger.debug(f"无效URL: {url}")
                continue
                
            self.visited_urls.add(cleaned_url)
            article = self.scrape_article(cleaned_url)
            if article:
                all_articles.append(article)
                self.logger.info(f"进度: {idx}/{len(unique_links)} - {article['title'][:30]}... \n {article['url']}")
            
            # 关联文章挖掘（取消每3篇触发的限制，改为始终执行）
            related_links = self.find_related_links(cleaned_url)
            for rel_url in related_links:
                # 清洗并验证关联链接
                cleaned_rel_url = self.clean_article_url(rel_url)
                if not cleaned_rel_url or not self.is_valid_news_url(cleaned_rel_url):
                    self.logger.debug(f"无效关联URL: {rel_url}")
                    continue
                if cleaned_rel_url not in self.visited_urls:
                    self.visited_urls.add(cleaned_rel_url)
                    rel_article = self.scrape_article(cleaned_rel_url)
                    if rel_article:
                        all_articles.append(rel_article)
                        self.logger.info(f"从关联文章获取: {rel_article['title'][:30]}... \n {rel_article['url']}")
            
            # time.sleep(random.uniform(0.5, 2.5))
        
        self.logger.info(f"爬取完成，共获取 {len(all_articles)} 篇文章")
        # 移除结果数量限制
        return all_articles if max_articles is None else all_articles[:max_articles]

    def get_news_links_from_categories(self, max_links_per_category=None, max_categories=None):
        """从/categories/下的多个分类页面爬取新闻链接（支持模拟点击加载更多）"""
        categories = {
            "": "主要",
            "domestic": "国内",
            "world": "国際",
            "business": "経済",
            "entertainment": "エンタメ",
            "sports": "スポーツ",
            "life": "生活",
            "it": "IT",
            "science": "科学",
            "local": "地域"  # 添加地域分类
        }  # 可根据实际分类扩展
        
        self.logger.info(f"开始从分类页面获取链接，共 {len(categories)} 个分类")
        all_links = set()
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("user-agent=" + random.choice(self.user_agents))
        # 添加禁用不必要功能的选项，提高稳定性
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        
        with webdriver.Chrome(options=options) as driver:
            for cat_slug, cat_name in categories.items():
                # 移除分类总数限制
                category_url = f"{self.base_url}/categories/{cat_slug}" if cat_slug != "" else self.base_url
                self.logger.info(f"\n开始爬取分类：{cat_name} ({category_url})")
                
                # 导航到分类页面
                try:
                    # 为主页添加特殊处理逻辑
                    if cat_slug == "":
                        # 主页面的文章链接选择器可能不同，尝试更通用的选择器
                        driver.get(category_url)
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/articles/"]'))
                        )
                        # 额外等待以确保JS加载完成
                        time.sleep(random.uniform(3, 5))
                    else:
                        # 其他分类页使用常规逻辑
                        driver.get(category_url)
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/articles/"]'))
                        )
                    
                    # 增加页面加载后的等待时间
                    time.sleep(random.uniform(2, 3))
                    
                    # 提取链接
                    category_links = self.extract_links_with_scroll(driver, max_links=max_links_per_category)
                    all_links.update(category_links)
                    self.logger.info(f"  该分类获取 {len(category_links)} 条链接，累计总数：{len(all_links)}")
                except Exception as e:
                    self.logger.error(f"分类 {cat_name} 页面加载失败: {e}")
        
        self.logger.info(f"从分类页面共获取 {len(all_links)} 条链接")
        # 移除返回数量限制
        return list(all_links)

    def extract_links_with_scroll(self, driver, max_links=None):
        """在分类页面中模拟滚动加载更多链接（优化滚动逻辑）"""
        self.logger.info("开始滚动页面提取链接...")
        links = set()
        scroll_count = 0
        last_link_count = 0  # 记录上次提取的链接数
        max_retries = 5  # 最大重试次数
        retry_count = 0
        
        # 增加初始等待时间，确保页面完全加载
        time.sleep(random.uniform(3, 5))  # 延长初始等待时间
        
        while True:
            # 提取当前页面链接
            current_links = self.extract_article_links(driver)
            links.update(current_links)
            
            # 检查是否达到最大链接数
            if max_links is not None and len(links) >= max_links:
                self.logger.info(f"已达到最大链接数 {max_links}，停止滚动")
                break
            
            # 判断是否还有新链接加载
            if len(links) == last_link_count:
                retry_count += 1
                if retry_count >= max_retries:
                    self.logger.info(f"连续 {max_retries} 次未获取到新链接，停止滚动")
                    break
            else:
                last_link_count = len(links)
                retry_count = 0  # 重置重试次数
            
            # 滚动到页面底部触发加载更多
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(2, 3))  # 延长滚动后的等待时间
            
            # 检查并点击"もっと見る"按钮（优化点击逻辑）
            more_button = self.find_more_button(driver)
            if more_button:
                try:
                    WebDriverWait(driver, 5).until(EC.element_to_be_clickable(more_button))
                    driver.execute_script("arguments[0].click();", more_button)
                    self.logger.info("点击'もっと見る'按钮，加载更多内容")
                    time.sleep(random.uniform(3, 4))  # 点击后增加等待时间
                except Exception as e:
                    self.logger.warning(f"按钮点击失败，继续滚动: {e}")
            else:
                self.logger.debug("未找到加载更多按钮，继续滚动")
            
            scroll_count += 1
            self.logger.info(f"滚动 {scroll_count} 次，当前累计 {len(links)} 条链接")
        
        self.logger.info(f"共提取 {len(links)} 条有效链接")
        return list(links) if max_links is None else list(links)[:max_links]

    def find_more_button(self, driver):
        """查找加载更多按钮（示例实现，可能需要根据实际页面调整）"""
        try:
            return WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//a[contains(text(), "もっと見る")]'))
            )
        except Exception as e:
            self.logger.debug(f"未找到'もっと見る'按钮: {e}")
            return None

    def extract_article_links(self, driver):
        """从当前页面提取有效新闻链接（清洗并过滤广告）"""
        links = set()
        article_elements = driver.find_elements(By.XPATH, '//a[contains(@href, "/articles/")]')
        
        for elem in article_elements:
            href = elem.get_attribute("href")
            if href:
                cleaned_url = self.clean_article_url(href)
                if cleaned_url and self.is_valid_news_url(cleaned_url):
                    links.add(cleaned_url)
        
        self.logger.debug(f"从当前页面提取 {len(links)} 条有效链接")
        return links
    
    def get_links_from_topics(self, max_per_topics=None, max_pages=None):
        """改进版分类爬取，支持多级页面提取（取消所有数量限制）"""
        categories = {
            'domestic': '国内',
            'world': '国际',
            'business': 'ビジネス',
            'science': '科学',
            'entertainment': 'エンタメ',
            'sports': 'スポーツ',
            'it': 'IT',
        }
        
        self.logger.info(f"开始从话题页面获取链接，共 {len(categories)} 个分类")
        all_links = []
        session = requests.Session()  # 使用会话保持连接
        
        for cat_id, cat_name in categories.items():
            self.logger.info(f"\n开始爬取分类: {cat_name}({cat_id})...")
            category_links = set()
            page = 1
            has_more = True
            
            base_urls = [f"{self.base_url}/topics/{cat_id}"]
            
            while has_more:
                for base_url in base_urls:
                    page_url = f"{base_url}?page={page}" if page > 1 else base_url
                    
                    try:
                        # 获取分类页内容
                        self.logger.debug(f"请求分类页: {page_url}")
                        response = session.get(page_url, headers=self.get_random_headers(), timeout=15)
                        response.raise_for_status()
                        
                        if "該当する記事が見つかりません" in response.text:
                            self.logger.info(f"分类 {cat_name} 第 {page} 页无内容，停止爬取")
                            has_more = False
                            break
                        
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # 提取/pickup/过渡链接
                        pickup_selectors = [
                            'li[data-ual-view-type="list"] a[href*="/pickup/"]',
                            'a[data-cl-params*="_cl_vmodule:st_topics"]',
                        ]
                        
                        pickup_links = set()
                        for selector in pickup_selectors:
                            for a in soup.select(selector):
                                href = a.get('href')
                                if href and '/pickup/' in href:
                                    full_url = urljoin(self.base_url, href)
                                    pickup_links.add(full_url)
                        
                        if not pickup_links:
                            self.logger.info(f"分类 {cat_name} 第 {page} 页未找到过渡链接，停止爬取")
                            has_more = False
                            break
                        
                        self.logger.info(f"分类[{cat_name}] 第{page}页 获取到{len(pickup_links)}个过渡链接")
                        
                        # 访问每个/pickup/页面，提取/articles/链接
                        for pickup_url in pickup_links:
                            try:
                                self.logger.debug(f"请求过渡页: {pickup_url}")
                                pickup_response = session.get(pickup_url, headers=self.get_random_headers(), timeout=15)
                                pickup_response.raise_for_status()
                                
                                pickup_soup = BeautifulSoup(pickup_response.text, 'html.parser')
                                
                                # 从/pickup/页面提取/articles/链接
                                article_selectors = [
                                    'a[href*="/articles/"]',
                                    'div[data-ual-component="news-feed-body"] a',
                                ]
                                
                                for selector in article_selectors:
                                    for a in pickup_soup.select(selector):
                                        href = a.get('href')
                                        if href and '/articles/' in href:
                                            full_article_url = urljoin(self.base_url, href)
                                            cleaned_url = self.clean_article_url(full_article_url)  # 清洗URL
                                            if cleaned_url and not self.is_advertisement(cleaned_url):
                                                category_links.add(cleaned_url)
                                
                                if category_links:
                                    self.logger.debug(f"  从 {pickup_url} 获取到文章链接")
                                
                            except Exception as e:
                                self.logger.warning(f"  处理过渡页面 {pickup_url} 失败: {str(e)}")
                        
                        # 检查是否达到用户指定的max_per_category（若无则继续）
                        if max_per_topics is not None and len(category_links) >= max_per_topics:
                            self.logger.info(f"分类 {cat_name} 已达到最大链接数 {max_per_topics}，停止爬取")
                            has_more = False
                            break
                        
                    except Exception as e:
                        self.logger.error(f"分类[{cat_name}] 第{page}页请求失败: {str(e)}")
                        has_more = False
                        break
                
                page += 1
                # 取消max_pages限制，无限翻页直到无内容
                if max_pages is not None and page > max_pages:
                    self.logger.info(f"分类 {cat_name} 已达到最大页数 {max_pages}，停止爬取")
                    has_more = False
            
            all_links.extend(list(category_links))
            self.logger.info(f"分类[{cat_name}] 共获取到{len(category_links)}条文章链接")
        
        self.logger.info(f"从话题页面共获取 {len(all_links)} 条链接")
        return all_links

    def find_related_links(self, article_url, max_links=None):
        """从文章正文发现相关链接（取消返回数量限制）"""
        try:
            self.logger.debug(f"查找文章 {article_url} 的相关链接")
            response = requests.get(article_url, headers=self.get_random_headers())
            soup = BeautifulSoup(response.text, 'html.parser')
            
            related = set()
            content = soup.find('div', class_=re.compile(r'article_body|content'))
            if content:
                for a in content.find_all('a', href=re.compile(r'/articles/')):
                    href = a.get('href')
                    if href and href != article_url:
                        full_url = urljoin(self.base_url, href)
                        cleaned_url = self.clean_article_url(full_url)  # 清洗URL
                        if cleaned_url:
                            related.add(cleaned_url)
            
            self.logger.info(f"从文章 {article_url} 发现 {len(related)} 条相关链接")
            # 移除数量限制，返回全部有效链接
            return list(related)
        except Exception as e:
            self.logger.error(f"关联链接发现失败: {e}")
            return []

    # 文章详情爬取（保持原有实现）
    def scrape_article(self, url: str) -> Optional[Dict]:
        """爬取单篇文章详情"""
        try:
            self.logger.debug(f"开始爬取文章: {url}")
            response = requests.get(url, headers=self.get_random_headers(), timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            article = {
                'title': self._extract_title(soup),
                'publish_time': self._extract_publish_time(soup),
                'content': self._extract_content(soup),
                'images': self._extract_images(soup, url),
                'url': url,
                'source': 'Yahoo Japan News'
            }
            
            self.logger.debug(f"成功爬取文章: {article['title']}")
            return article
        except Exception as e:
            self.logger.error(f"文章爬取失败: {url} - {e}")
            return None

    # 辅助方法（保持原有实现）
    def _extract_title(self, soup):
        """提取标题"""
        for selector in ['h1.sc-uzx6gd-1', 'h1.sc-1tt2vmb-0', 'h1.newsTitle', 'h1', 'title']:
            title_tag = soup.select_one(selector)
            if title_tag:
                title = title_tag.get_text(strip=True)
                if title and not self.is_advertisement(title):
                    return title
        return "无标题"

    def _extract_publish_time(self, soup):
        """提取发布时间"""
        for selector in ['time.sc-uzx6gd-4', 'time.sc-1tt2vmb-2', 'time.publishDate', 'time', 'span.date']:
            time_tag = soup.select_one(selector)
            if time_tag:
                time_text = re.sub(r'<!--.*?-->', '', time_tag.get_text(strip=True))
                if time_text and not self.is_advertisement(time_text):
                    return time_text
        return "未知时间"

    def _extract_content(self, soup):
        """提取正文"""
        paragraphs = []
        for selector in ['div.article_body', 'div.highLightSearchTarget', 'article.sc-1tt2vmb-1', 'div.articleDetail']:
            container = soup.select_one(selector)
            if container:
                for p in container.find_all('p'):
                    text = p.get_text(strip=True)
                    if text and len(text) > 20 and not self.is_advertisement(text):
                        paragraphs.append(text)
                if paragraphs:
                    break
        return paragraphs

    def _extract_images(self, soup, base_url):
        """提取图片"""
        images = []
        for selector in ['div.article_body', 'div.photoGallery', 'div.articleDetail']:
            container = soup.select_one(selector)
            if container:
                for img in container.find_all('img'):
                    img_url = img.get('src') or img.get('data-src')
                    if img_url and not self.is_advertisement(img_url):
                        images.append(urljoin(base_url, img_url))
        return images

    def is_advertisement(self, text: str) -> bool:
        """判断广告内容"""
        lower_text = text.lower()
        return any(keyword in lower_text for keyword in self.ad_keywords)

    # 存储方法增强
    def save_to_csv(self, articles: List[Dict], filename: str = None):
        """增强版CSV存储，包含图片链接"""
        if not articles:
            self.logger.warning("无有效文章可保存")
            return
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"./saves/yahoo_news_{timestamp}.csv"
        
        try:
            self.logger.info(f"开始保存 {len(articles)} 篇文章到 {filename}")
            with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    '序号', '标题', '发布时间', '正文', '图片数量', '图片链接', '原文链接', '来源'
                ])
                writer.writeheader()
                
                for idx, article in enumerate(articles, 1):
                    # 将图片链接列表转为逗号分隔的字符串
                    image_links = ','.join(article.get('images', []))
                    
                    writer.writerow({
                        '序号': idx,
                        '标题': article['title'],
                        '发布时间': article['publish_time'],
                        '正文': '\n'.join(article['content']),
                        '图片数量': len(article.get('images', [])),
                        '图片链接': image_links,  # 新增图片链接字段
                        '原文链接': article['url'],
                        '来源': article.get('source', 'Yahoo Japan')
                    })
            
            self.logger.info(f"成功保存 {len(articles)} 篇文章到 {filename}")
        except Exception as e:
            self.logger.error(f"CSV保存失败: {e}")

    def save_to_json(self, articles: List[Dict], filename: str = None):
        """JSON格式存储"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"./saves/yahoo_news_{timestamp}.json"
        
        try:
            self.logger.info(f"开始保存 {len(articles)} 篇文章到 {filename}")
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(articles, f, ensure_ascii=False, indent=2)
            self.logger.info(f"JSON保存成功: {filename}")
        except Exception as e:
            self.logger.error(f"JSON保存失败: {e}")

# 使用示例
if __name__ == "__main__":
    # 配置日志文件
    os.makedirs('./logs', exist_ok=True)  # 确保日志目录存在
    log_file = f"./logs/yahoo_news_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # 创建爬虫实例并指定日志文件
    scraper = YahooJapanNewsScraper(log_file=log_file)
    
    # 记录开始时间
    start_time = datetime.now()
    scraper.logger.info(f"开始爬取时间：{start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 综合爬取（最多100篇，启用分类和关联文章爬取）
    # 注意：由于已取消所有数量限制，建议设置合理的max参数避免无限爬取
    articles = scraper.scrape_news(
        max_articles=100,       # 总共爬取的文章数
        max_per_topics=1,    # 每个分类最多爬取数量
        max_per_categories=1           # 主页最多加载链接数
    )
    
    # 记录结束时间并计算耗时
    end_time = datetime.now()
    elapsed_time = end_time - start_time
    
    # 保存结果
    if articles:
        scraper.save_to_csv(articles)
        scraper.save_to_json(articles)
    else:
        scraper.logger.warning("未获取到任何文章，跳过保存")
    
    # 爬取时间统计
    scraper.logger.info("\n爬取时间统计:")
    scraper.logger.info(f"- 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    scraper.logger.info(f"- 结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    scraper.logger.info(f"- 总耗时: {elapsed_time.total_seconds():.2f} 秒 ({elapsed_time})")
    
    # 爬取结果统计
    scraper.logger.info("\n爬取结果统计:")
    if articles:
        scraper.logger.info(f"- 总文章数: {len(articles)}")
        valid_times = [a['publish_time'] for a in articles if a['publish_time'] != '未知时间']
        scraper.logger.info(f"- 最早发布时间: {'无有效时间' if not valid_times else min(valid_times)}")
        scraper.logger.info(f"- 包含图片的文章: {sum(1 for a in articles if a['images'])} 篇")
    else:
        scraper.logger.info("- 未获取到有效文章")