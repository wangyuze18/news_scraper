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
from urllib.parse import urlparse, parse_qs

class YahooJapanNewsScraper:
    def __init__(self, log_file=None):
        self.base_url = "https://news.yahoo.co.jp"
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
        ]
        self.headers_list = [
            # 添加多个不同的User-Agent
            {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'},
            {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'},
            {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0'},
            {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 11.5; rv:90.0) Gecko/20100101 Firefox/90.0'}
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
        pattern = r'^(https://news\.yahoo\.co\.jp/(?:articles|expert/articles)/[^/?#]+)'
        match = re.match(pattern, url)
        if match:
            return match.group(1)  # 返回主链接部分
        return None  # 无效链接返回None
    
    def scrape_news(self, 
                    max_articles=None,        
                    max_per_categories=None,           
                    max_per_topics=None):   
        """整合多来源的爬取入口（含分类信息）"""
        self.logger.info("开始爬取新闻...")
        all_articles = []
        all_links_with_category = []  # 存储带分类信息的链接字典

        # 1. 主页分类爬取（带分类信息）
        self.logger.info("正在从主页分类获取新闻...")
        category_links = self.get_news_links_from_categories(max_links_per_category=max_per_categories)
        all_links_with_category.extend(category_links)
        self.logger.info(f"从主页分类获取到 {len(category_links)} 条带分类链接")

        # 2. 话题页面爬取（带二级分类信息）
        self.logger.info("正在从话题页面获取新闻...")
        topic_links = self.get_links_from_topics(max_per_topics=max_per_topics)
        all_links_with_category.extend(topic_links)
        self.logger.info(f"从话题页面获取到 {len(topic_links)} 条带分类链接")

        # 提取所有唯一URL，并保留分类信息
        unique_urls = []
        url_category_map = {}  # 存储URL对应的分类信息

        for link_info in all_links_with_category:
            url = link_info["url"]
            category_info = {k: v for k, v in link_info.items() if k != "url"}  # 提取分类字段
            
            if url not in url_category_map:
                url_category_map[url] = category_info
                unique_urls.append(url)

        self.logger.info(f"去重后得到 {len(unique_urls)} 个唯一URL，准备爬取详情...")

        for idx, url in enumerate(unique_urls, 1):
            cleaned_url = self.clean_article_url(url)
            if not cleaned_url or not self.is_valid_news_url(cleaned_url):
                self.logger.debug(f"无效URL: {url}")
                continue

            if cleaned_url in self.visited_urls:
                self.logger.debug(f"已访问过的URL: {cleaned_url}")
                continue
            self.visited_urls.add(cleaned_url)

            # 爬取文章详情并注入分类信息
            article = self.scrape_article_with_category(cleaned_url, url_category_map.get(url, {}))
            if article and self.is_valid_news(article):
                all_articles.append(article)
                self.logger.info(f"进度: {idx}/{len(unique_urls)} - {article['title'][:30]}... \n {article['url']}")
                
                if max_articles and len(all_articles) >= max_articles:
                    self.logger.info(f"达到最大爬取数量 {max_articles}，停止爬取")
                    break
            
            # -------------------- 关联文章挖掘（修改部分） --------------------
            # related_links = self.find_related_links(cleaned_url)
            # for rel_url in related_links:
            #     cleaned_rel_url = self.clean_article_url(rel_url)
            #     if not cleaned_rel_url or not self.is_valid_news_url(cleaned_rel_url):
            #         self.logger.debug(f"无效关联URL: {rel_url}")
            #         continue
                
            #     if cleaned_rel_url in self.visited_urls:
            #         continue
            #     self.visited_urls.add(cleaned_rel_url)
                
            #     # 爬取关联文章时不注入分类信息（直接使用原scrape_article）
            #     rel_article = self.scrape_article(cleaned_rel_url)
            #     if rel_article and self.is_valid_news(rel_article):
            #         # 不更新rel_article的分类字段，保持原始爬取结果
            #         all_articles.append(rel_article)
            #         self.logger.info(f"从关联文章获取: {rel_article['title'][:30]}... \n {rel_article['url']}")
                    
            #         if max_articles and len(all_articles)>=max_articles:
            #             break  # 达到数量限制时停止关联挖掘
            # time.sleep(random.uniform(0.5, 2.5))  # 保留请求间隔

        self.logger.info(f"爬取完成，共获取 {len(all_articles)} 篇带分类的文章")
        return all_articles

    def scrape_article_with_category(self, url, category_info):
        """爬取文章详情并注入分类信息"""
        try:
            article = self.scrape_article(url)
            if article:
                # 合并分类信息到文章属性中
                article.update(category_info)
                return article
        except Exception as e:
            self.logger.error(f"爬取文章 {url} 失败: {e}")
        return None
        
    def is_valid_news(self, article):
        return article['title'] and article['publish_time'] and article['title'] != 'Yahoo!ニュース' and article['publish_time'] != '未知时间'

    def get_news_links_from_categories(self, max_links_per_category=None, max_categories=None):
        """从/categories/下的多个分类页面爬取新闻链接（附带分类信息，支持模拟点击加载更多）"""
        categories = {
            # "": "主要",
            # "domestic": "国内",
            # "world": "国際",
            "science": "科学",
            "business": "经济",
            "entertainment": "娱乐",
            "sports": "运动",
            "life": "生活",
            "it": "科技",
        }  # 可根据实际分类扩展
        
        self.logger.info(f"开始从分类页面获取链接，共 {len(categories)} 个分类")
        all_links_with_category = []  # 存储带分类信息的链接
        options = Options()
        # ...（保留原有options配置）
        
        with webdriver.Chrome(options=options) as driver:
            for cat_slug, cat_name in categories.items():
                if max_categories is not None and len(all_links_with_category) >= max_categories:
                    break  # 达到分类总数限制时停止
                
                category_url = f"{self.base_url}/categories/{cat_slug}" if cat_slug else self.base_url
                self.logger.info(f"\n开始爬取分类：{cat_name} ({category_url})")
                
                try:
                    driver.get(category_url)
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/articles/"]'))
                    )
                    time.sleep(random.uniform(2, 3))
                    
                    # 提取链接并附加分类信息
                    category_links = self.extract_links_with_scroll(driver, max_links=max_links_per_category)
                    for link in category_links:
                        all_links_with_category.append({
                            "url": link,
                            "category": cat_name  # 附加分类导航信息
                        })
                    
                    self.logger.info(f"  该分类获取 {len(category_links)} 条链接，累计总数：{len(all_links_with_category)}")
                except Exception as e:
                    self.logger.error(f"分类 {cat_name} 页面加载失败: {e}")
        
        self.logger.info(f"共获取 {len(all_links_with_category)} 条带分类的链接")
        return all_links_with_category

    def get_links_from_topics(self, max_per_topics=None):
        """从话题页面爬取新闻链接（仅保留一级分类信息）"""
        categories = {
            # 'domestic': '国内',
            # 'world': '国际',
            "business": "经济",
            "entertainment": "娱乐",
            "sports": "运动",
            "it": "科技",
            "science": "科学",
        }
        
        self.logger.info(f"开始从话题页面获取链接，共 {len(categories)} 个分类")
        all_links = []  # 存储带一级分类的链接
        
        for cat_id, main_category in categories.items():
            self.logger.info(f"\n开始爬取分类: {main_category} ({cat_id})... {self.base_url}/topics/{cat_id}")
            page = 1
            has_more = True
            
            while has_more:
                page_url = f"{self.base_url}/topics/{cat_id}?page={page}" if page > 1 else f"{self.base_url}/topics/{cat_id}"
                
                try:
                    # 每次请求使用新的session，降低被封禁风险
                    with requests.Session() as session:
                        # 添加随机延迟，模拟人类浏览行为
                        time.sleep(random.uniform(1, 3))

                        response = session.get(
                            page_url, 
                            headers=random.choice(self.headers_list),
                            timeout=15,
                        )
                        response.raise_for_status()
                        
                        # 检查响应内容是否正常
                        if 'Yahoo! JAPAN' not in response.text:
                            raise ValueError("页面内容异常，可能被反爬拦截")
                        
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # 提取pickup链接
                        pickup_links = self.extract_pickup_links(soup)
                        if not pickup_links:
                            self.logger.info(f"  第 {page} 页无pickup链接，停止爬取")
                            break
                        
                        count = 0 

                        # 遍历pickup链接，提取文章
                        for pickup_url in pickup_links:
                            article_links = self.extract_articles_from_pickup(pickup_url, main_category)
                            all_links.extend(article_links)
                            count += len(article_links)

                            # 达到单分类数量限制时停止
                            if max_per_topics is not None and count >= max_per_topics:
                                has_more = False
                                break
                        
                        # 判断是否有下一页
                        next_page = soup.select_one('a[data-ual-event-name="next_page"]')
                        has_more = next_page is not None
                        page += 1
                    
                except Exception as e:
                    self.logger.error(f"  话题页 {page_url} 爬取失败: {str(e)}")
                    has_more = False
        
        self.logger.info(f"共获取 {len(all_links)} 条带分类的链接")
        return all_links


    def extract_pickup_links(self, soup, retries=3):
        """从话题页提取pickup链接（带重试机制）"""
        for attempt in range(retries):
            try:

                pickup_selectors = [
                    'div[class=\"newsFeed\"] > ul > li > a'
                ]
                pickup_links = set()
                
                for selector in pickup_selectors:
                    elements = soup.select(selector)
                    if not elements and attempt == 0:  # 首次尝试时检查选择器是否匹配到元素
                        self.logger.warning(f"选择器 '{selector}' 在话题页未匹配到任何元素")
                    
                    for a in elements:
                        href = a.get('href')
                        if href and '/pickup/' in href:
                            pickup_links.add(href)
                
                # 验证提取结果（至少有一个链接）
                if not pickup_links:
                    raise ValueError("未提取到任何pickup链接")
                
                self.logger.info(f"成功从话题页提取 {len(pickup_links)} 个pickup链接（尝试 {attempt+1}/{retries}）")
                return list(pickup_links)
            
            except Exception as e:
                wait_time = 1 * (attempt + 1)  # 等待时间递增（1s, 2s, 3s...）
                self.logger.warning(f"尝试 {attempt+1}/{retries} 失败: {str(e)}，{wait_time}秒后重试")
                time.sleep(wait_time)  # 等待后重试
        
        # 所有重试均失败
        self.logger.error("达到最大重试次数，pickup链接提取失败")
        return []  # 返回空列表，避免程序崩溃


    def extract_articles_from_pickup(self, pickup_url, main_category, retries=3):
        """从pickup页面提取文章链接（处理自动跳转至文章页的情况）"""
        for attempt in range(retries):
            try:
                # 发送请求（允许重定向，获取最终URL）
                response = requests.get(
                    pickup_url, 
                    headers=self.get_random_headers(), 
                    timeout=15,
                    allow_redirects=True  # 关键：允许自动跳转
                )
                response.raise_for_status()
                
                # 获取最终URL（处理跳转后的地址）
                final_url = response.url
                parsed_final_url = urlparse(final_url)
                
                # 判断最终URL是否为文章页
                if "/expert/articles/" in parsed_final_url.path:
                    self.logger.info(f"请求后跳转至文章页: {final_url}，直接返回")
                    return [{
                        "url": final_url,
                        "category": main_category
                    }]
                
                # 常规Pickup页面处理逻辑
                pickup_soup = BeautifulSoup(response.text, 'html.parser')
                
                # 验证页面是否存在目标元素
                target_elem = pickup_soup.select_one('div[data-ual-view-type="digest"] > a')
                if not target_elem:
                    raise ValueError("未找到文章链接元素")
                
                href = target_elem.get('href')
                if href and '/articles/' in href:
                    cleaned_url = self.clean_article_url(href)
                    article_links = [{
                        "url": cleaned_url,
                        "category": main_category
                    }]
                    self.logger.info(f"从 {pickup_url} 提取到 {len(article_links)} 篇文章")
                    return article_links
                
                # 若未找到符合条件的链接
                raise ValueError("提取的链接不符合文章页格式")
            
            except Exception as e:
                wait_time = (attempt + 1) * 1  # 等待时间递增：1s, 2s, 3s
                self.logger.warning(f"尝试 {attempt+1}/{retries} 失败: {str(e)}，等待{wait_time}秒")
                time.sleep(wait_time)
        
        self.logger.error(f"从 {pickup_url} 提取文章链接失败，达到最大重试次数")
        return []
    
    def extract_links_with_scroll(self, driver, max_links=None):
        """滚动到底部加载所有内容后，一次性提取链接（优化逻辑）"""
        self.logger.info("开始滚动页面加载所有内容...")
        links = set()
        scroll_count = 0
        max_retries = 3  # 最大重试次数
        retry_count = 0
        last_height = driver.execute_script("return document.body.scrollHeight")  # 记录上次页面高度
        
        # 增加初始等待时间，确保页面基本加载
        time.sleep(random.uniform(3, 5))
        
        while True:
            links = self.extract_article_links(driver)
            if max_links and len(links) >= max_links:
                self.logger.info(f"达到最大链接数 {max_links}，停止加载")
                break
            # 滚动到页面底部
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(2, 3))  # 等待内容加载
            
            # 检查是否出现"もっと見る"按钮
            more_button = self.find_more_button(driver)
            if more_button:
                try:
                    WebDriverWait(driver, 5).until(EC.element_to_be_clickable(more_button))
                    driver.execute_script("arguments[0].click();", more_button)
                    self.logger.info("点击'もっと見る'按钮，加载更多内容")
                    time.sleep(random.uniform(3, 4))  # 点击后等待新内容加载
                    retry_count = 0  # 重置重试次数
                except Exception as e:
                    self.logger.warning(f"按钮点击失败，继续滚动: {e}")
            else:
                # 无更多按钮时，检查页面高度是否不再变化（判断是否加载完毕）
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    retry_count += 1
                    if retry_count >= max_retries:
                        self.logger.info(f"连续 {max_retries} 次页面高度无变化，视为加载完成")
                        break
                else:
                    last_height = new_height
                    retry_count = 0  # 重置重试次数
            
            scroll_count += 1
            self.logger.info(f"滚动 {scroll_count} 次，当前页面高度: {last_height}")
        
        self.logger.info(f"共提取 {len(links)} 条有效链接")
        
        # 应用最大链接数限制
        return list(links) if max_links is None else list(links)[:max_links]

    def find_more_button(self, driver):
        """查找加载更多按钮（示例实现，可能需要根据实际页面调整）"""
        try:
            return WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((
                    By.XPATH, 
                    '//*[contains(text(), "もっと見る") and contains(@class, "sc-10wa6pi-1")]'  # 结合类名定位
                ))
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
    
    
    def find_related_links(self, article_url, max_links=None):
        """整合策略1（标题定位）的相关链接提取"""
        try:
            self.logger.debug(f"查找文章 {article_url} 的相关链接")
            response = requests.get(article_url, headers=self.get_random_headers())
            soup = BeautifulSoup(response.text, 'html.parser')
            
            related = set()
            
            # ---------------------- 策略1：通过标题文本定位相关文章区域 ----------------------
            # 调整标题匹配逻辑，适配日文「関連記事」及可能的英文标题
            related_section = soup.find(
                lambda tag: tag.name in ['h2', 'h3', 'h4'] and 
                ('関連記事' in tag.get_text(strip=True) or 'Related Articles' in tag.get_text(strip=True))
            )
            
            if related_section:
                self.logger.debug("通过标题定位到相关文章区域")
                # 调整容器查找逻辑：查找标题后的首个直接父级容器或同级列表容器
                container = related_section.find_next(['ul', 'ol'])  # 增加div容器支持
                if container:
                    self._extract_links_from_container(container, related, article_url)
                else:
                    self.logger.debug("标题下方无有效容器")
                    # 直接从标题后续的兄弟元素中提取链接
                    # for sibling in related_section.find_next_siblings():
                    #     if sibling.name == 'a':
                    #         self._process_link(sibling, related, article_url)
                    #     elif sibling.name in ['div', 'p']:
                    #         # 从段落或div中递归查找链接
                    #         for a in sibling.find_all('a', href=True, limit=50):
                    #             self._process_link(a, related, article_url)
            
            self.logger.info(f"从文章 {article_url} 发现 {len(related)} 条相关链接")
            return list(related)[:max_links] if max_links else list(related)
            
        except Exception as e:
            self.logger.error(f"关联链接发现失败: {e}")
            return []
        
    def _extract_links_from_container(self, container, related_set, base_url):
        """从容器中提取链接（仅限直接子元素）"""
        for a in container.find_all('a', href=True, limit=50):  # 限制单次提取数量
            self._process_link(a, related_set, base_url)

    def _process_link(self, a_tag, related_set, base_url):
        """统一链接处理（清洗、验证、去重）"""
        href = a_tag.get('href')
        if href:
            # 处理相对路径（兼容不同域名的相关链接）
            full_url = urljoin(base_url, href) if not href.startswith(('http://', 'https://')) else href
            
            # 清洗URL（保留参数，仅去除无效后缀）
            cleaned_url = self.clean_article_url(full_url)
            if not cleaned_url:
                return
            
            # 验证有效性（非广告、非资源页）
            if self.is_valid_news_url(cleaned_url) and cleaned_url not in self.visited_urls:
                related_set.add(cleaned_url)
                self.logger.debug(f"添加有效链接: {cleaned_url}")
                    

    def scrape_article(self, url: str) -> Optional[Dict]:
        """爬取单篇文章详情"""
        try:
            self.logger.debug(f"开始爬取文章: {url}")
            
            # 使用整合后的方法提取文章信息
            article_data = self.extract_article(url)
            
            # 添加额外信息
            article = {
                'title': article_data['title'],
                'publish_time': article_data['publish_time'],
                'content': article_data['content'],
                'images': article_data['images'],
                'url': url,
                'source': 'Yahoo Japan News'
            }
            
            self.logger.debug(f"成功爬取文章: {article['title']}")
            return article
        except Exception as e:
            self.logger.error(f"文章爬取失败: {url} - {e}")
            return None
    
    def extract_article(self, url):
        """提取文章的完整信息（标题、发布时间、内容、图片）"""
        base_url = url.split('?')[0]
        first_page_url = base_url if 'page' not in url else url
        
        try:
            # 获取第一页内容（用于提取标题、时间）
            response = requests.get(first_page_url, headers=self.get_random_headers(), timeout=10)
            response.raise_for_status()
            first_page_soup = BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            print(f"Error fetching first page: {e}")
            return {
                'title': "无标题",
                'publish_time': "未知时间",
                'content': [],
                'images': []
            }
        
        # 提取标题和发布时间（仅第一页）
        title = self._extract_title(first_page_soup)
        publish_time = self._extract_publish_time(first_page_soup)
        
        # 提取内容和图片（支持分页）
        content = []
        images = []
        page_num = 1
        
        while True:
            current_url = f"{base_url}?page={page_num}" if page_num > 1 else first_page_url
            
            try:
                response = requests.get(current_url, headers=self.get_random_headers(), timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
            except Exception as e:
                print(f"no page {page_num}: {e}")
                break
            
            # 提取内容
            page_content = self._extract_page_content(soup)
            if not page_content:
                break  # 内容为空时停止
            content.extend(page_content)
            
            # 提取图片
            page_images = self._extract_page_images(soup)
            images.extend(page_images)
            
            page_num += 1
        
        return {
            'title': title,
            'publish_time': publish_time,
            'content': content,
            'images': images
        }

    def _extract_page_content(self, soup):
        """提取单页的正文内容"""
        for selector in ['div.article_body', 'div.highLightSearchTarget', 'article.sc-1tt2vmb-1', 'div.articleDetail']:
            container = soup.select_one(selector)
            if container:
                return [
                    p.get_text(strip=True)
                    for p in container.find_all('p')
                    if p.get_text(strip=True) and len(p.get_text(strip=True)) > 20 and not self.is_advertisement(p.get_text(strip=True))
                ]
        return []

    def _extract_page_images(self, soup):
        """提取单页的图片URL"""
        images = []
        for selector in ['div.article_body', 'div.photoGallery', 'div.articleDetail', 'div.sc-1tt2vmb-1']:
            container = soup.select_one(selector)
            if container:
                for img in container.find_all('img'):
                    img_url = img.get('src') or img.get('srcset')
                    if img_url and not self.is_advertisement(img_url):
                        # 解析URL参数，保留exp字段，去除w和h参数
                        parsed = urlparse(img_url)
                        query = parse_qs(parsed.query)
                        if 'exp' in query:
                            new_query = {k: v for k, v in query.items() if k not in ['w', 'h']}
                            new_query_str = '&'.join([f"{k}={v[0]}" for k, v in new_query.items()])
                            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{new_query_str}" if new_query_str else f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                        else:
                            clean_url = re.split(r'\?|#', img_url)[0]
                        images.append(clean_url)
        return images

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
        # 优先从meta标签获取
        pubdate_meta = soup.find('meta', attrs={'name': 'pubdate'})
        if pubdate_meta and pubdate_meta.get('content'):
            return pubdate_meta['content']
        
        # 尝试其他常见的meta标签
        for meta_name in ['article:published_time', 'og:pubdate', 'date', 'dc.date.issued']:
            meta_tag = soup.find('meta', attrs={'property': meta_name}) or soup.find('meta', attrs={'name': meta_name})
            if meta_tag and meta_tag.get('content'):
                return meta_tag['content']
        
        # 回退到HTML中的time标签
        for selector in ['time.sc-uzx6gd-4', 'time.sc-1tt2vmb-2', 'time.publishDate', 'time', 'span.date']:
            time_tag = soup.select_one(selector)
            if time_tag:
                time_text = re.sub(r'<!--.*?-->', '', time_tag.get_text(strip=True))
                if time_text and not self.is_advertisement(time_text):
                    return time_text
        
        return "未知时间"


    def is_advertisement(self, text: str) -> bool:
        """判断广告内容"""
        lower_text = text.lower()
        return any(keyword in lower_text for keyword in self.ad_keywords)

    # 存储方法增强
    def save_to_csv(self, articles: List[Dict], filename: str = None):
        """增强版CSV存储，包含图片链接"""
        os.makedirs('./saves', exist_ok=True)  # 确保保存目录存在
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
                    '序号', '标题', '发布时间', '正文', '分类', '图片数量', '图片链接', '原文链接', '来源'
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
                        '分类': article.get('category', '未知分类'),
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
        os.makedirs('./saves', exist_ok=True)  # 确保保存目录存在

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
        max_per_topics=10,    # 每个话题最多加载链接数
        max_per_categories=10      # 每个分类最多加载链接数
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