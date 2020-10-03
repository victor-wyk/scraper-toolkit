# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class ProxyItem(scrapy.Item):
    # define the fields for your item here like:
    alive = scrapy.Field()
    ip = scrapy.Field()
    port = scrapy.Field()
    anonymity_level = scrapy.Field()
    uptime = scrapy.Field()
    response = scrapy.Field()
    country = scrapy.Field()
    region = scrapy.Field()
    city = scrapy.Field()
    latitude = scrapy.Field()
    longitude = scrapy.Field()
    site_scraped = scrapy.Field()
    protocol = scrapy.Field()
    organization = scrapy.Field()
    isp = scrapy.Field()

