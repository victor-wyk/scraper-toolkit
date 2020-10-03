
from ..items import AmazonDepItem
from ..loaders import AmazonDepLoader

from scrapy.spiders import Request, Spider
from urllib.parse import urljoin
import re
import logging
from treelib import Node, Tree
import hashlib
import os
import json


class AmazonDepTree(Spider):
    name = 'dep-spider'
    pipelines = ['DatabaseDepPipeline', 'DefaultNullValuesPipeline']
    # allowed_domains = ['www.amazon.com']
    # Start at International Best Sellers page
    start_urls = [
        'https://www.amazon.com/b?node=17938598011',
    ]

    # Start at the departments page and create a tree structure with root 'Departments'
    def parse(self, response):
        logger = logging.getLogger('product_spider')
        logger.setLevel(logging.INFO)
        logger.info("Collecting department urls...")
        current_tag = "International Best Sellers"

        l = AmazonDepLoader(item=AmazonDepItem(), response=response)
        l.add_value('name', current_tag)
        l.add_value('url', response.request.url)
        to_hash = current_tag
        l.add_value('hash', hashlib.md5(to_hash.encode("utf-8")).hexdigest())
        yield l.load_item()

        # Parse children departments
        yield Request(
            url=response.request.url,
            callback=self.parse_department,
            meta={
                "parent_tag": None,
                "current_tag": current_tag,
            }
        )

    # Still in the departments page, create a tree structure of the departments.
    # This function will loop until a large tree is formed
    def parse_department(self, response):
        current_tag = response.meta['current_tag']
        parent_tag = response.meta['parent_tag']

        current_url = response.request.url


        # Instantiate the department item for current department
        l = AmazonDepLoader(item=AmazonDepItem(), response=response)
        l.add_value('name', current_tag)
        l.add_value('parent', parent_tag)
        l.add_value('url', current_url)

        if parent_tag is None:
            to_hash = current_tag
        else:
            to_hash = current_tag + parent_tag
        l.add_value('hash', hashlib.md5(to_hash.encode("utf-8")).hexdigest())
        yield l.load_item()

        # Go through the department list navigation box
        # Many types of navigation box format- if not one...
        department_list = response.xpath("//div[contains(@class,'browseBox')]")
        department_urls = department_list.xpath(".//a/@href").getall()
        department_names = department_list.xpath(".//a/text()").getall()
        # ...then the other, or if not...
        if not department_list:
            department_list = response.xpath("//div[@id='leftNav']/ul/ul/div")
            # Div does not contain any parent departments
            department_urls = department_list.xpath("./li/span/a/@href").getall()
            department_names = department_list.xpath("./li/span/a/span/text()").getall()
            # ...then the other
            if not department_list:
                department_list = response.xpath("//div[@id='departments']/ul")
                # Xpath is able to differentiate sub-departments from parent departments
                department_urls = department_list.xpath("./li[contains(@class,'navigation')]/span/a/@href").getall()
                department_names = department_list.xpath(
                    "./li[contains(@class,'navigation')]/span/a/span/text()").getall()

        for child_tag, child_url in zip(department_names, department_urls):
            yield Request(
                url=urljoin(current_url, child_url),
                callback=self.parse_department,
                meta={
                    "current_tag": child_tag,
                    "parent_tag": current_tag,
                }
            )
