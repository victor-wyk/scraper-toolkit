# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
import urllib
import urllib.request
import urllib.error

import psycopg2
from dotenv import load_dotenv
load_dotenv()

import os


class DatabaseProxyPipeline(object):
    def open_spider(self, spider):
        hostname = os.getenv('HOSTNAME', 'localhost')
        username = os.getenv('USERNAME')
        password = os.getenv('PASSWORD')  # your password
        database = os.getenv('PROXY_DATABASE')
        self.connection = psycopg2.connect(host=hostname, user=username, password=password, dbname=database)
        self.cur = self.connection.cursor()

    def close_spider(self, spider):
        self.cur.close()
        self.connection.close()

    def process_item(self, item, spider):
        # Check if pipeline is used by spider
        if 'DatabaseProxyPipeline' not in getattr(spider, 'pipelines'):
            return item

        try:
            self.cur.execute(
                "INSERT INTO proxy.public.proxy_list(ip, alive, port, anonymity_level, uptime, response, isp, organization, country, "
                "region, city, site_scraped, protocol, date_scraped) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())"
                "ON CONFLICT (ip) DO UPDATE SET (alive, port, anonymity_level, uptime, response, isp, organization, country, "
                "region, city, site_scraped, protocol, date_scraped) = "
                "(EXCLUDED.alive, EXCLUDED.port, EXCLUDED.anonymity_level, EXCLUDED.uptime, EXCLUDED.response, EXCLUDED.isp, EXCLUDED.organization, EXCLUDED.country,"
                "EXCLUDED.region, EXCLUDED.city, EXCLUDED.site_scraped, EXCLUDED.protocol, now());",

                (item['ip'], item['alive'], item['port'], item['anonymity_level'], item['uptime'], item['response'], item['isp'], item['organization'],
                 item['country'], item['region'], item['city'], item['site_scraped'], item['protocol'])
            )


        except:
            self.connection.rollback()
            print('Failed, rollback...')
        else:
            self.connection.commit()
            return item


# Set all item fields to None before everything happens- so no database insert problems
class DefaultNullValuesPipeline(object):
    def process_item(self, item, spider):

        # Check if pipeline is used by spider
        if 'DefaultNullValuesPipeline' not in getattr(spider, 'pipelines'):
            return item

        for field in item.fields:
            item.setdefault(field, None)

        return item

'''"ON CONFLICT (ip) DO UPDATE SET (port, anonymity_level, uptime, response, isp, organization, country,"
                "region, city, site_scraped, protocol, date_scraped) = "
                "(EXCLUDED.port, EXCLUDED.anonymity_level, EXCLUDED.uptime, EXCLUDED.response, EXCLUDED.isp, "
                "EXCLUDED.organization, EXCLUDED.country, EXCLUDED.region, EXCLUDED.city, EXCLUDED.site_scraped, "
                "EXCLUDED.protocol, EXCLUDED.date_scraped, now())'''
