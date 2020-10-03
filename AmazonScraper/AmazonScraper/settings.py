# -*- coding: utf-8 -*-

# Scrapy settings for AmazonScraper project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html
import psycopg2
from dotenv import load_dotenv
load_dotenv()
import os

hostname = os.getenv('HOSTNAME')
username = os.getenv('USERNAME')
password = os.getenv('PASSWORD')
database = os.getenv('AMAZON_DATABASE')
proxy_database = os.getenv('PROXY_DATABASE')
driver = os.getenv('DB_DRIVER')
port = os.getenv('PORT')

BOT_NAME = 'AmazonScraper'

SPIDER_MODULES = ['AmazonScraper.spiders']
NEWSPIDER_MODULE = 'AmazonScraper.spiders'

# Fuck the rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
# The more the better ;)
CONCURRENT_REQUESTS = 10000

DATABASE = {
    'drivername': driver,
    'host': hostname,
    'port': port,
    'username': username,
    'password': password,
    'database': database
}

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
    'scrapy_user_agents.middlewares.RandomUserAgentMiddleware': 400,
    'AmazonScraper.middlewares.AmazonscraperDownloaderMiddleware': 543,
    # 'AmazonScraper.middlewares.CustomRotatingProxiesMiddleware': 610,
    'rotating_proxies.middlewares.RotatingProxyMiddleware': 610,
    'rotating_proxies.middlewares.BanDetectionMiddleware': 620,
}

def get_proxy_list():
    proxy_list = []
    connection = psycopg2.connect(
        host=hostname,
        user=username,
        password=password,
        dbname=proxy_database)
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT ip, port FROM proxy.public.proxy_list "
                       "WHERE alive = TRUE;")
        rows = cursor.fetchall()
        for row in rows:
            ip_port = ":".join(str(i) for i in row)
            proxy_list.append(ip_port)
        connection.commit()

    except (Exception, psycopg2.DatabaseError) as error:
        print("Psycopg2 error, ", error)

    finally:
        # closing database connection.
        if connection:
            cursor.close()
            connection.close()
            print("PostgreSQL connection closed")
        print("Proxy List: ", proxy_list)
        return proxy_list

ROTATING_PROXY_LIST = get_proxy_list() #['134.122.26.80:69']


# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    'AmazonScraper.pipelines.DefaultNullValuesPipeline': 300,
    'AmazonScraper.pipelines.DatabaseProductPipeline': 400,
    'AmazonScraper.pipelines.DatabaseDepPipeline': 410,
    # 'AmazonScraper.pipelines.DatabaseCatalogPipeline': 420,
}

# Crawl responsibly by identifying yourself (and your website) on the user-agent
# USER_AGENT = 'AmazonScraper (+http://www.yourdomain.com)'



# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
# DOWNLOAD_DELAY = 2
# The download delay setting will honor only one of:
# CONCURRENT_REQUESTS_PER_DOMAIN = 16
# CONCURRENT_REQUESTS_PER_IP = 10000

# Disable cookies (enabled by default)
# COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
# TELNETCONSOLE_ENABLED = False

# Override the default request headers:
# DEFAULT_REQUEST_HEADERS = {
#   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#   'Accept-Language': 'en',
# }

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
# SPIDER_MIDDLEWARES = {
#    'AmazonScraper.middlewares.AmazonscraperSpiderMiddleware': 543,
# }


# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
# EXTENSIONS = {
#    'scrapy.extensions.telnet.TelnetConsole': None,
# }


# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
# AUTOTHROTTLE_ENABLED = True
# # The initial download delay
# AUTOTHROTTLE_START_DELAY = 1
# # The maximum download delay to be set in case of high latencies
# AUTOTHROTTLE_MAX_DELAY = 5
# # The average number of requests Scrapy should be sending in parallel to
# # each remote server
# AUTOTHROTTLE_TARGET_CONCURRENCY = 10000
# # Enable showing throttling stats for every response received:
# AUTOTHROTTLE_DEBUG = True

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
# HTTPCACHE_ENABLED = True
# HTTPCACHE_EXPIRATION_SECS = 0
# HTTPCACHE_DIR = 'httpcache'
# HTTPCACHE_IGNORE_HTTP_CODES = []
# HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'
