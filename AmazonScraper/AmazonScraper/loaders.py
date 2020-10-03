'''
Created by: Victor Wan at 12/06/2020
'''

from scrapy.loader import ItemLoader
from scrapy.loader.processors import Join, MapCompose, TakeFirst, Identity, Compose
from .processors import TakeLast, Sum
from w3lib.html import remove_tags, replace_escape_chars, strip_html5_whitespace, replace_entities


class AmazonDepLoader(ItemLoader):
    def __init__(self, **context):
        super().__init__(**context)
        # self.default_input_processor = MapCompose(replace_escape_chars, replace_entities, strip_html5_whitespace)
        self.default_output_processor = TakeFirst()

    path_out = Identity()
    path_in = Identity()


class AmazonCatalogLoader(ItemLoader):
    def __init__(self, **context):
        super().__init__(**context)
        self.default_output_processor = TakeFirst()


class AmazonProductLoader(ItemLoader):
    def __init__(self, **context):
        super().__init__(**context)
        self.default_input_processor = MapCompose(replace_escape_chars, replace_entities, strip_html5_whitespace)
        self.default_output_processor = Join()

    # Item fields that do not use default processors
    # Format: item_field_in for input processor, item_field_out for output processor
    # categories_out = Identity()
    currency_out = TakeFirst()
    ASIN_out = TakeFirst()
    details_in = Identity()
    details_out = Identity()
    department_id_in = Identity()
    department_id_out = Identity()
    price_out = TakeFirst()
    retail_price_out = TakeFirst()
    stock_total_out = Sum()
    date_scraped_in = Identity()
    date_scraped_out = Identity()
    catalog_in = Identity()

