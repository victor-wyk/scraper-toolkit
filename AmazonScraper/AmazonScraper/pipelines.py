# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

from .items import AmazonDepItem, AmazonProductItem
import psycopg2, re, json
from datetime import datetime
import logging
from dotenv import load_dotenv
load_dotenv()
import os

hostname = os.getenv('HOSTNAME')
username = os.getenv('USERNAME')
password = os.getenv('PASSWORD')
database = os.getenv('AMAZON_DATABASE')

class DatabaseDepPipeline(object):
    def open_spider(self, spider):
        self.connection = psycopg2.connect(
            host=hostname,
            user=username,
            password=password,
            dbname=database)
        self.cur = self.connection.cursor()

    def close_spider(self, spider):
        self.cur.close()
        self.connection.close()

    def process_item(self, item, spider):
        # Check if item is correct
        if not isinstance(item, AmazonDepItem):
            return item
        # Check if pipeline is used by spider
        if 'DatabaseDepPipeline' not in getattr(spider, 'pipelines'):
            return item

        if item.get('path'):
            item['path'].reverse()
            item['path'] = ".".join(item['path'])

        # Item fields cannot be non-existent when inserting to database- this is why DefaultNullValues pipeline exists.
        try:
            self.cur.execute(
                "INSERT INTO amazon.public.department(name, path, parent, url, hash) "
                "VALUES(%s,%s,%s,%s,%s)"
                "ON CONFLICT (path) DO NOTHING",
                (item['name'], item['path'], item['parent'], item['url'], item['hash'])
            )

        except Exception as e:
            logger = logging.getLogger('database_product_pipeline')
            logger.error(e)
            self.connection.rollback()

        else:
            self.connection.commit()
            return item


class DatabaseCatalogPipeline(object):
    def open_spider(self, spider):
        self.connection = psycopg2.connect(
            host=hostname,
            user=username,
            password=password,
            dbname=database)
        self.cur = self.connection.cursor()

    def close_spider(self, spider):
        self.cur.close()
        self.connection.close()

    def process_item(self, item, spider):
        # Check if item is correct
        if not isinstance(item, AmazonProductItem):
            return item
        # Check if pipeline is used by spider
        if 'DatabaseCatalogPipeline' not in getattr(spider, 'pipelines'):
            return item

            # Item fields cannot be non-existent when inserting to database- this is why DefaultNullValues pipeline exists.
        try:
            self.cur.execute(
                "INSERT INTO amazon.public.catalog(url, page_no, department_id) "
                "VALUES(%s,%s,%s)"
                "ON CONFLICT (page_no, department_id) DO NOTHING",
                (item['name'], item['path'], item['parent'])
            )

        except Exception as e:
            logger = logging.getLogger('database_catalog_pipeline')
            logger.error(e)
            self.connection.rollback()

        else:
            self.connection.commit()
            return item


class DatabaseProductPipeline(object):
    def open_spider(self, spider):
        self.connection = psycopg2.connect(
            host=hostname,
            user=username,
            password=password,
            dbname=database)
        self.cur = self.connection.cursor()

    def close_spider(self, spider):
        self.cur.close()
        self.connection.close()

    def process_item(self, item, spider):
        # Check if item is correct
        if not isinstance(item, AmazonProductItem):
            return item
        # Check if pipeline is used by spider
        if 'DatabaseProductPipeline' not in getattr(spider, 'pipelines'):
            return item

        if item.get('product_dimensions'):  # converts 5.5 x 1.57 x 1.57 inches to 5.5x1.57x1.57/in
            v = item['product_dimensions']
            v = v.replace(" x ", "x")
            v = v.replace(" ", "/")
            if "inches" in v:
                v = v.replace("inches", "in")
            item['product_dimensions'] = v

        if item.get('package_dimensions'):
            v = item['package_dimensions']
            v = v.replace(" x ", "x")
            v = v.replace(" ", "/")
            if "inches" in v:
                v = v.replace("inches", "in")
            item['package_dimensions'] = v

        if item.get('date_first_available'):
            v = item['date_first_available']
            v = datetime.strptime(v, '%B %d, %Y')
            item['date_first_available'] = v

        if item.get('weight'):
            v = item['weight']
            v = v.replace(" ", "/")
            if "pounds" in v:
                v = v.replace("pounds", "lb")
            if "ounces" in v:
                v = v.replace("ounces", "oz")
            item['weight'] = v

        if item.get('rating'):
            v = item['rating']
            v = [float(s) for s in re.findall(r"\d*\.\d+|\d+", v)]
            v = round(v[0] / v[1], 2)
            item['rating'] = v

            # Primary Function:
        if item.get(
                'ranking'):  # converts #587 in Video Games ( See Top 100 in Video Games )  #5 in GameCube Accessories   #8 in Mac Gaming Mice   #9 in Wii Accessories
            v = item[
                'ranking']  # to {'Video Games': 587, 'GameCube Accessories': 5, 'Mac Gaming Mice': 8, 'Wii Accessories': 9}
            v = re.sub(r"\(.\s*?.*\)", "", v)  # Deletes brackets and its enclosed characters
            v = re.sub(r"\bin\b", ":", v)  # Replaces 'in' with colon
            v = v.split('#')  # Splits string into list elements between hashtag
            temp = {}
            for i in v:
                try:
                    key = re.search(r"[A-Z](.*)[a-z]", i).group(
                        0)  # Extract anything from first capital letter to last lowercase letter
                    value = re.search(r"[0-9]*", i).group(0)  # Extract number of any length
                    temp.update({key: int(value)})
                except:
                    continue
            v = temp
            v = json.dumps(v)
            item['ranking'] = v

        if item.get('details'):
            item['details'] = item['details'][0]  # Removes square brackets, returning pure dict

        if item.get('price'):
            v = item['price']
            v = "".join([x.strip('$') for x in v])

            # If it is a price range- switch to price range
            if "-" in v:
                v = v.split('-')
                item['price_range'] = '[' + v[0] + ',' + v[1] + ']'
                item['price'] = None
            else:
                item['price'] = float(v)

        if item.get('retail_price'):
            v = item['retail_price']
            v = "".join([x.strip('$') for x in v])
            v = "".join([x.strip(',') for x in v])
            item['retail_price'] = float(v)
            item['discount'] = (item['retail_price'] - item['price']) / item['retail_price']

        if item.get('ASIN'):
            item['url'] = 'http://www.amazon.com/dp/' + item['ASIN']  # Cleaner URL format than getting response URL.
        # Convert list to int
        if item.get('department_id'):
            item['department_id'] = item['department_id'][0]

        # Item fields cannot be non-existent when inserting to database- this is why DefaultNullValues pipeline exists.
        try:
            self.cur.execute(
                "INSERT INTO amazon.public.product(title, asin, price, price_range, retail_price, discount, currency, rating, ranking, "
                "stock_total, brand_name, date_first_available, unspsc, discontinued, "
                "package_dimensions, product_dimensions, details, description, features, weight, manufacturer, date_scraped) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())"
                "ON CONFLICT (title) DO NOTHING "
                # "UPDATE SET (asin, price, price_range, retail_price, discount, currency, rating, ranking, "
                # "stock_total, brand_name, date_first_available, unspsc, discontinued, "
                # "package_dimensions, product_dimensions, details, description, features, weight, manufacturer, date_scraped) = "
                # "(EXCLUDED.asin, EXCLUDED.price, EXCLUDED.price_range, EXCLUDED.retail_price, EXCLUDED.discount, "
                # "EXCLUDED.currency, EXCLUDED.rating, EXCLUDED.ranking, EXCLUDED.stock_total, "
                # "EXCLUDED.brand_name, EXCLUDED.date_first_available, EXCLUDED.unspsc, EXCLUDED.discontinued, "
                # "EXCLUDED.package_dimensions, EXCLUDED.product_dimensions, EXCLUDED.details, EXCLUDED.description, "
                # "EXCLUDED.features, EXCLUDED.weight, EXCLUDED.manufacturer, now())"
                "RETURNING id;",
                (
                    item['title'], item['ASIN'], item['price'], item['price_range'], item['retail_price'],
                    item['discount'],
                    item['currency'],
                    item['rating'], item['ranking'], item['stock_total'],
                    item['brand_name'], item['date_first_available'], item['UNSPSC'], item['discontinued'],
                    item['package_dimensions'], item['product_dimensions'], item['details'], item['description'],
                    item['features'], item['weight'], item['manufacturer']
                )
            )
            # Get generated product id and insert with its department id into junction table
            product_id = self.cur.fetchone()
            if product_id:
                self.cur.execute(
                    "INSERT INTO amazon.public.product_department_xref(product_id, department_id) "
                    "VALUES (%s,%s)"
                    "ON CONFLICT (product_id, department_id)"
                    "DO NOTHING;",
                    (product_id[0], item['department_id'])
                )

        except Exception as e:

            logger = logging.getLogger('database_product_pipeline')
            logger.error(e)
            self.connection.rollback()

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
