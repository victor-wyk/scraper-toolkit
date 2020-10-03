# -*- coding: utf-8 -*-
import logging

from scrapy.spiders import Spider
from ..items import ProxyItem
from ..loaders import ProxyLoader
import re
import pycountry
from ..proxychecker import ProxyChecker


class ProxySpider(Spider):
    name = 'spys_txt'
    allowed_domains = ['spys.me']
    start_urls = ['http://spys.me/proxy.txt']
    pipelines = ['DatabaseProxyPipeline', 'DefaultNullValuesPipeline']
    def parse(self, response):

        content = response.xpath('//body//text()').extract_first()  # Extract text content
        rows = re.split("\n+", content)  # List of lines
        proxy_list = []
        for row in rows:
            try:
                proxy = re.search(r'^[0-9]+(?:\.[0-9]+){3}:[0-9]+', row)   # If ip exists in line then progress
                if proxy:
                    country_code = re.search(r'[A-Z]{2}', row)  # Look for two capital letters
                    anonymity_code = re.search(r'(?<=-)(N|A|H)', row)  # Lookbehind for minus symbol and capture anonymity level
                    meta = {}
                    if country_code:
                        country = pycountry.countries.get(alpha_2=country_code.group(0))
                        meta.update({'country': country.name})
                    if anonymity_code:
                        anon_dict = {'N': 3, 'A': 2, 'H': 1}
                        anonymity_level = anon_dict.get(anonymity_code.group(0))
                        meta.update({'anonymity_level': anonymity_level})

                    proxy_list.append({'proxy': proxy.group(0), 'meta': meta})
            except Exception as e:
                logging.error(e)
                continue

        proxychecker = ProxyChecker()
        result_proxy_list = proxychecker.run(proxy_list)
        for i in result_proxy_list:
            l = ProxyLoader(item=ProxyItem(), response=response)
            ip = re.search(r'^[0-9]+(?:\.[0-9]+){3}', i['proxy'])
            port = re.search(r'(?<=:)([0-9]{1,5})', i['proxy'])
            if ip:
                l.add_value('ip', ip.group(0))
            if port:
                l.add_value('port', port.group(0))
            if 'country' in i['meta']:
                l.add_value('country', i['meta']['country'])
            if 'anonymity_level' in i['meta']:
                l.add_value('anonymity_level', i['meta']['anonymity_level'])
            l.add_value('alive', i['alive'])
            yield l.load_item()
