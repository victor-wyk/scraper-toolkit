# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class AmazonDepItem(scrapy.Item):
    name = scrapy.Field()
    parent = scrapy.Field()
    path = scrapy.Field()
    url = scrapy.Field()
    hash = scrapy.Field()


class AmazonCatalogItem(scrapy.Item):
    url = scrapy.Field()
    page = scrapy.Field()
    department_id = scrapy.Field()


class AmazonProductItem(scrapy.Item):
    title = scrapy.Field()  #
    ASIN = scrapy.Field()  #
    price = scrapy.Field()  #
    price_range = scrapy.Field()  #
    retail_price = scrapy.Field()  #
    details = scrapy.Field()#
    discount = scrapy.Field()  #
    currency = scrapy.Field()  #
    rating = scrapy.Field()  #
    ranking = scrapy.Field()  #
    # categories = scrapy.Field()  #
    category_main = scrapy.Field()  #
    stock_total = scrapy.Field()  #
    date_scraped = scrapy.Field()
    date_sch_scrape = scrapy.Field()
    department_id = scrapy.Field()
    catalog_id = scrapy.Field()

    brand_name = scrapy.Field()#
    discontinued = scrapy.Field()#
    date_first_available = scrapy.Field()#
    UNSPSC = scrapy.Field()#

    description = scrapy.Field()#
    features = scrapy.Field()#
    item_model_num = scrapy.Field()
    manufacturer = scrapy.Field()#
    package_dimensions = scrapy.Field()#
    product_dimensions = scrapy.Field()#
    related_products = scrapy.Field()
    url = scrapy.Field()
    volume = scrapy.Field()
    weight = scrapy.Field()#
