# -*- coding: utf-8 -*-

# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html
import psycopg2
from rotating_proxies.utils import extract_proxy_hostport
from scrapy import signals
from rotating_proxies.middlewares import RotatingProxyMiddleware
from rotating_proxies.expire import Proxies, ProxyState
from twisted.internet import task
import logging

from dotenv import load_dotenv
load_dotenv()
import os

hostname = os.getenv('HOSTNAME')
username = os.getenv('USERNAME')
password = os.getenv('PASSWORD')
proxy_database = os.getenv('PROXY_DATABASE')

class AmazonscraperSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, dict or Item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request, dict
        # or Item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)


class AmazonscraperDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)


# Custom proxy middleware to dynamically update proxy list every interval
class CustomRotatingProxiesMiddleware(RotatingProxyMiddleware):

    @classmethod
    def from_crawler(cls, crawler):

        # TODO: Clean up this duplicate code

        mw = super(CustomRotatingProxiesMiddleware, cls).from_crawler(crawler)
        # Substitute standard `proxies` object with a custom one

        logging.info("Updating proxy list...")
        connection = psycopg2.connect(
            host=hostname,
            user=username,
            password=password,
            dbname=proxy_database)
        cursor = connection.cursor()

        proxy_list = []
        try:
            cursor.execute("SELECT ip, port FROM proxy.public.proxy_list "
                           "WHERE alive = TRUE;")
            rows = cursor.fetchall()
            connection.commit()
            for row in rows:
                ip_port = ":".join(str(i) for i in row)
                proxy_list.append(ip_port)

        except (Exception, psycopg2.DatabaseError) as error:
            print("Psycopg2 error, ", error)

        finally:
            # closing database connection.
            if connection:
                cursor.close()
                connection.close()
                print("PostgreSQL connection closed")

        mw.proxies = CustomProxies(mw.cleanup_proxy_list(proxy_list), backoff=mw.proxies.backoff)

        # Connect `proxies` to engine signals in order to start and stop looping task
        crawler.signals.connect(mw.proxies.engine_started, signal=signals.engine_started)
        crawler.signals.connect(mw.proxies.engine_stopped, signal=signals.engine_stopped)
        return mw


class CustomProxies(Proxies):

    def engine_started(self):
        """ Create a task for updating proxies every minute """
        self.task = task.LoopingCall(self.update_proxies)
        self.task.start(300, now=True)

    def engine_stopped(self):
        if self.task.running:
            self.task.stop()

    def update_proxies(self):
        logging.info("Updating proxy list from database...")
        connection = psycopg2.connect(
            host=hostname,
            user=username,
            password=password,
            dbname=proxy_database)
        cursor = connection.cursor()
        try:
            proxy_list = []
            cursor.execute("SELECT ip, port FROM proxy.public.proxy_list "
                           "WHERE alive = TRUE;")
            rows = cursor.fetchall()
            connection.commit()
            for row in rows:
                ip_port = ":".join(str(i) for i in row)
                proxy_list.append(ip_port)

        except (Exception, psycopg2.DatabaseError) as error:
            print("Psycopg2 error, ", error)

        finally:
            # closing database connection.
            if connection:
                cursor.close()
                connection.close()
                print("PostgreSQL connection closed")
            for proxy in proxy_list:
                self.add(proxy)

    def add(self, proxy):
        """ Add a proxy to the proxy list """
        if proxy in self.proxies:
            logging.warning("Proxy %s is already in proxies list" % proxy)
            return

        hostport = extract_proxy_hostport(proxy)
        self.proxies[proxy] = ProxyState()
        self.proxies_by_hostport[hostport] = proxy
        self.unchecked.add(proxy)
