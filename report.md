## 时间  
### 新闻爬取时间  
新闻爬取耗时分为两部分：  
1. **新闻链接的获取**：需模拟页面滑动、点击「もっと見る」按钮、翻页、进入子导航页等操作获取新闻链接。  
2. **新闻图文的提取**：进入新闻详情页后，筛选提取所需文字内容，并保存图片到本地。  

#### 雅虎日本：  
- 爬取100篇新闻耗时：669.50s  
  - 新闻链接的获取：317.08s  
  - 新闻图文的提取：350.42s  
  - 其他时间：2.00 s

#### 朝日新闻(免费内容):  
- 爬取100篇新闻耗时：1425.00s
  - 新闻链接的获取：864.78s  
  - 新闻图文的提取：526.20s
  - 其他时间: 34.02s

## 数据可爬性
```plaintext
⚠️ 重要提示：  
访问及爬取朝日新闻数据可能需要 VPN（因地域限制或反爬机制），使用时需遵守当地法律法规及网站服务条款，避免违规风险。  
```  
- [x] 雅虎日本 (https://news.yahoo.co.jp)
- [x] 朝日新闻(免费内容) (https://www.asahi.com)

## 测试详情
### 雅虎日本爬取页面
共爬取以下页面获取新闻链接，最终去重后得到 127 个唯一 URL，爬取 100 篇文章：

#### 分类页面（6 个分类）：
总计：30 条链接
+ 科学 (https://news.yahoo.co.jp/categories/science)：获取 5 条链接
+ 经济 (https://news.yahoo.co.jp/categories/business)：获取 5 条链接
+ 娱乐 (https://news.yahoo.co.jp/categories/entertainment)：获取 5 条链接
+ 运动 (https://news.yahoo.co.jp/categories/sports)：获取 5 条链接
+ 生活 (https://news.yahoo.co.jp/categories/life)：获取 5 条链接
+ 科技 (https://news.yahoo.co.jp/categories/it)：获取 5 条链接



#### 话题页面（5 个话题）：
总计：25 条链接
+ 经济 (https://news.yahoo.co.jp/topics/business)：获取 5 条链接
+ 娱乐 (https://news.yahoo.co.jp/topics/entertainment)：获取 5 条链接
+ 运动 (https://news.yahoo.co.jp/topics/sports)：获取 5 条链接
+ 科技 (https://news.yahoo.co.jp/topics/it)：获取 5 条链接
+ 科学 (https://news.yahoo.co.jp/topics/science)：获取 5 条链接



#### 关键词搜索页面（4 个关键词）：
总计：81 条链接
+ 花束みたいな恋をした (https://news.yahoo.co.jp/search?p=花束みたいな恋をした&ei=utf-8)：获取 21 条链接
+ ラブレター (https://news.yahoo.co.jp/search?p=ラブレター&ei=utf-8)：获取 21 条链接
+ リアル鬼ごっこ (https://news.yahoo.co.jp/search?p=リアル鬼ごっこ&ei=utf-8)：获取 18 条链接
+ 君の名は。 (https://news.yahoo.co.jp/search?p=君の名は。&ei=utf-8)：获取 21 条链接

### 朝日新闻爬取页面

#### 主页及子导航页面
总计: 50 条免费新闻链接
+ https://www.asahi.com : 获取37条免费新闻链接(37/102)
+ https://www.asahi.com/national/?iref=pc_gnavi : 获取12条免费新闻链接(12/42)
+ https://www.asahi.com/investigative-reporting/?iref=pc_gnavi : 获取1条免费新闻链接(1/10)
  
#### 关键词搜索页面
总计: 50 条免费新闻链接
+ 花束みたいな恋をした ：获取 3 条免费新闻链接(3/62)
  + https://sitesearch.asahi.com/sitesearch/?Keywords=%E8%8A%B1%E6%9D%9F%E3%81%BF%E3%81%9F%E3%81%84%E3%81%AA%E6%81%8B%E3%82%92%E3%81%97%E3%81%9F&Searchsubmit2=検索&Searchsubmit=検索&start=0
  + https://sitesearch.asahi.com/sitesearch/?Keywords=%E8%8A%B1%E6%9D%9F%E3%81%BF%E3%81%9F%E3%81%84%E3%81%AA%E6%81%8B%E3%82%92%E3%81%97%E3%81%9F&Searchsubmit2=検索&Searchsubmit=検索&start=20
  + https://sitesearch.asahi.com/sitesearch/?Keywords=%E8%8A%B1%E6%9D%9F%E3%81%BF%E3%81%9F%E3%81%84%E3%81%AA%E6%81%8B%E3%82%92%E3%81%97%E3%81%9F&Searchsubmit2=検索&Searchsubmit=検索&start=40
  + https://sitesearch.asahi.com/sitesearch/?Keywords=%E8%8A%B1%E6%9D%9F%E3%81%BF%E3%81%9F%E3%81%84%E3%81%AA%E6%81%8B%E3%82%92%E3%81%97%E3%81%9F&Searchsubmit2=検索&Searchsubmit=検索&start=60
  
+ ラブレター ：获取 25 条免费新闻链接(25/160)
  + https://sitesearch.asahi.com/sitesearch/?Keywords=%E3%83%A9%E3%83%96%E3%83%AC%E3%82%BF%E3%83%BC&Searchsubmit2=検索&Searchsubmit=検索&start=0
  + https://sitesearch.asahi.com/sitesearch/?Keywords=%E3%83%A9%E3%83%96%E3%83%AC%E3%82%BF%E3%83%BC&Searchsubmit2=検索&Searchsubmit=検索&start=20
  + https://sitesearch.asahi.com/sitesearch/?Keywords=%E3%83%A9%E3%83%96%E3%83%AC%E3%82%BF%E3%83%BC&Searchsubmit2=検索&Searchsubmit=検索&start=40
  + https://sitesearch.asahi.com/sitesearch/?Keywords=%E3%83%A9%E3%83%96%E3%83%AC%E3%82%BF%E3%83%BC&Searchsubmit2=検索&Searchsubmit=検索&start=60
  + https://sitesearch.asahi.com/sitesearch/?Keywords=%E3%83%A9%E3%83%96%E3%83%AC%E3%82%BF%E3%83%BC&Searchsubmit2=検索&Searchsubmit=検索&start=80
  + https://sitesearch.asahi.com/sitesearch/?Keywords=%E3%83%A9%E3%83%96%E3%83%AC%E3%82%BF%E3%83%BC&Searchsubmit2=検索&Searchsubmit=検索&start=100
  + https://sitesearch.asahi.com/sitesearch/?Keywords=%E3%83%A9%E3%83%96%E3%83%AC%E3%82%BF%E3%83%BC&Searchsubmit2=検索&Searchsubmit=検索&start=120
  + https://sitesearch.asahi.com/sitesearch/?Keywords=%E3%83%A9%E3%83%96%E3%83%AC%E3%82%BF%E3%83%BC&Searchsubmit2=検索&Searchsubmit=検索&start=140
  
+ 君の名は。 ：获取 20 条免费新闻链接(20/112)
  + https://sitesearch.asahi.com/sitesearch/?Keywords=%E5%90%9B%E3%81%AE%E5%90%8D%E3%81%AF%E3%80%82&Searchsubmit2=検索&Searchsubmit=検索&start=0
  + https://sitesearch.asahi.com/sitesearch/?Keywords=%E5%90%9B%E3%81%AE%E5%90%8D%E3%81%AF%E3%80%82&Searchsubmit2=検索&Searchsubmit=検索&start=20
  + https://sitesearch.asahi.com/sitesearch/?Keywords=%E5%90%9B%E3%81%AE%E5%90%8D%E3%81%AF%E3%80%82&Searchsubmit2=検索&Searchsubmit=検索&start=40
  + https://sitesearch.asahi.com/sitesearch/?Keywords=%E5%90%9B%E3%81%AE%E5%90%8D%E3%81%AF%E3%80%82&Searchsubmit2=検索&Searchsubmit=検索&start=60
  + https://sitesearch.asahi.com/sitesearch/?Keywords=%E5%90%9B%E3%81%AE%E5%90%8D%E3%81%AF%E3%80%82&Searchsubmit2=検索&Searchsubmit=検索&start=80
  + https://sitesearch.asahi.com/sitesearch/?Keywords=%E5%90%9B%E3%81%AE%E5%90%8D%E3%81%AF%E3%80%82&Searchsubmit2=検索&Searchsubmit=検索&start=100
  
+ 打ち上げ花火：获取 2 条免费新闻链接(2/3)
  + https://sitesearch.asahi.com/sitesearch/?Keywords=%E6%89%93%E3%81%A1%E4%B8%8A%E3%81%92%E8%8A%B1%E7%81%AB&Searchsubmit2=検索&Searchsubmit=検索&start=0 