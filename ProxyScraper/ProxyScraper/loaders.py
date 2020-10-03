'''
Created by: Victor Wan at 13/06/2020
'''

from scrapy.loader import ItemLoader
from scrapy.loader.processors import Join, MapCompose, TakeFirst, Identity, Compose
from w3lib.html import remove_tags, replace_escape_chars, strip_html5_whitespace, replace_entities

class ProxyLoader(ItemLoader):
    def __init__(self, **context):
        super().__init__(**context)
        self.default_output_processor = TakeFirst()