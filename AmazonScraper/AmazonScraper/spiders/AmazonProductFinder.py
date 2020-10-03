from scrapy.loader import ItemLoader

from ..items import AmazonProductItem, AmazonCatalogItem
from ..loaders import AmazonProductLoader, AmazonCatalogLoader

from scrapy.spiders import Request, Spider
from datetime import datetime
import re
import logging
import psycopg2
import random
from scrapy.utils.log import configure_logging

from dotenv import load_dotenv
load_dotenv()
import os

hostname = os.getenv('HOSTNAME')
username = os.getenv('USERNAME')
password = os.getenv('PASSWORD')
database = os.getenv('AMAZON_DATABASE')
proxy_database = os.getenv('AMAZON_DATABASE')
driver = os.getenv('DB_DRIVER')
port = os.getenv('PORT')


class AmazonProductFinder(Spider):
    name = 'product-spider'
    configure_logging(install_root_handler=False)

    logging.basicConfig(format='%(asctime)s [%(filename)s:%(lineno)d] %(levelname)s %(message)s',
                        level=logging.INFO)

    pipelines = ['DatabaseProductPipeline', 'DefaultNullValuesPipeline']

    # allowed_domains = ['www.amazon.com']
    start_urls = []

    def __init__(self, mode=None, **kwargs):
        super().__init__(mode=None, **kwargs)
        self.mode = mode

    # Start at the departments page and create a tree structure with root 'Departments'
    def start_requests(self):
        logger = logging.getLogger('product_spider')
        logger.setLevel(logging.INFO)
        logger.info("Collecting department urls...")

        # Get department urls and ids from database
        connection = psycopg2.connect(
            host=hostname,
            user=username,
            password=password,
            dbname=database)
        cursor = connection.cursor()


        if self.mode == 'from-root':
            # Scrapes from each department root url, passing down department id as metadata
            cursor.execute("SELECT url, id FROM amazon.public.department")
            departments = cursor.fetchall()
            random.shuffle(departments)
            connection.close()
            cursor.close()
            for department in departments:
                department_url = department[0]
                department_id = department[1]
                yield Request(
                    url=department_url,
                    callback=self.parse_catalog,
                    meta={'department_id': department_id}
                )

        if self.mode == 'continue':
            # Continue scraping starting from last department catalog page
            cursor.execute("SELECT DISTINCT ON (department_id) t.url, t.department_id, t.page_no "
                           "FROM amazon.public.catalog t "
                           "ORDER BY department_id, page_no DESC;")
            results = cursor.fetchall()
            random.shuffle(results)
            connection.close()
            cursor.close()
            for result in results:
                catalog_page_url = result[0]
                department_id = result[1]
                yield Request(
                    url=catalog_page_url,
                    callback=self.parse_catalog,
                    meta={'department_id': department_id}
                )

    # Using the department tree structure, in each department page extract all product urls
    def parse_catalog(self, response):
        logger = logging.getLogger('product_spider')
        logger.setLevel(logging.INFO)
        logger.info('Collecting product urls visible in page...')
        department_id = response.meta['department_id']

        # Want to do this but cannot get database id from pipeline back to spider...
        # Create new catalog item
        # url = response.request.url
        # l = AmazonCatalogLoader(item=AmazonCatalogItem(), response=response)
        # # Strip qid component from url since it is a unique identifier
        # l.add_value('url', url.split("&qid=", 1)[0])
        #
        # l.add_xpath('page','//li[@class="a-selected"]/a/text()')
        # page_no = re.search(r'(?<=(page=))\d+', url)
        # if page_no is not None:
        #     l.add_value('page', page_no.group(0))
        # l.add_value('department_id', department_id)
        # yield l.load_item()

        # Get catalog page info and save to database
        url = response.request.url
        url = url.split("&qid=", 1)[0]

        page_no = re.search(r'(?<=(page=))\d+', url)
        page_no = page_no.group(0) if page_no is not None \
            else response.xpath('//li[@class="a-selected"]/a/text()').get()
        page_no = 1 if page_no is None else page_no

        connection = psycopg2.connect(
            host=hostname,
            user=username,
            password=password,
            dbname=database)

        cursor = connection.cursor()
        cursor.execute("INSERT INTO amazon.public.catalog(url, page_no, department_id)"
                       "VALUES (%s,%s,%s) "
                       "ON CONFLICT (url, department_id) "
                       "DO NOTHING;",
                       (url, page_no, department_id))   # todo: since not returning to spider we can make it an item
        connection.commit()
        connection.close()
        cursor.close()

        # Extract all product urls visible on page
        product_urls = response.xpath("//a[@class='a-link-normal a-text-normal']").xpath("@href").getall()
        logger.info("Amount of products on page: " + str(len(product_urls)))

        # Iterate through product urls and parse product
        for product_url in product_urls:
            if "books" in product_url:
                continue
            url = response.urljoin(product_url)
            yield Request(url=url, callback=self.parse_product,
                          meta={'department_id': department_id})#,'catalog_id': catalog_id})

        # After going through all products, head to the next page
        next_page_url = response.xpath(
            "//span/a[@class='pagnNext'] | //ul[@class='a-pagination']/li[@class='a-last']/a").xpath(
            "@href").extract_first()
        url = response.urljoin(next_page_url)
        yield Request(url=url, callback=self.parse_catalog,
                      meta={'department_id': department_id})#,'catalog_id': catalog_id})

    # Using extracted product urls go to each url and extract data
    def parse_product(self, response):
        logging.info('Parsing product...')
        department_id = response.meta['department_id']
        # catalog_id = response.meta['catalog_id']
        title = response.xpath('//span[@id="productTitle"]')
        price = response.xpath('//span[contains(@id,"priceblock")]')

        if title and price:  # if url points to a legit product
            # Find Xpaths of product attributes and append to item object- change in website format will lead to xpaths unusable
            l = AmazonProductLoader(item=AmazonProductItem(), response=response)  # instantiates ItemLoader object

            l.add_xpath('ASIN', '//tr/*[contains(text(),"ASIN")]/following-sibling::td/text()')
            asin_url_regex = re.search(r'(?<=\/)[A-Z0-9]{10}(?=\/)', response.request.url)
            if asin_url_regex:
                l.add_value('ASIN', asin_url_regex.group(0))
            l.add_value('department_id', department_id)
            # l.add_value('catalog_id', str(catalog_id))
            l.add_xpath('UNSPSC', '//tr/*[contains(text(),"UNSPSC")]/following-sibling::td/text()')
            l.add_xpath('brand_name', '//tr/*[contains(text(),"Brand Name")]/following-sibling::td/text()')
            # l.add_xpath('categories',
            #             '//div[@id="wayfinding-breadcrumbs_feature_div"]//li/span[@class="a-list-item"]/a/text()')
            l.add_xpath('currency', '//*/@data-asin-currency-code')
            l.add_xpath('date_first_available',
                        '//tr/*[contains(text(),"Date First Available")]/following-sibling::td/text()')
            l.add_xpath('description', '//div[@id="productDescription"]//text() | '
                                       '//div[contains(@class,"aplus-module")]'
                                       '//*[starts-with(name(), "h") or self::p]/text()')  # todo: two types of description
            l.add_xpath('features',
                        '//div[@id="feature-bullets"]//li[not(@id="replacementPartsFitmentBullet")]//text()')
            l.add_xpath('item_model_num', '//tr/*[contains(text(),"Item model number")]/following-sibling::td/text()')
            l.add_xpath('manufacturer', '//tr/th[re:test(text(),"^\s*Manufacturer\s*$")]/following-sibling::td/text()')
            l.add_xpath('package_dimensions',
                        '//tr/*[contains(text(),"Package Dimensions")]/following-sibling::td/text()')
            l.add_xpath('price', '//span[contains(@id,"priceblock")]/text()')
            l.add_xpath('product_dimensions',
                        '//tr/*[contains(text(),"Product Dimensions")]/following-sibling::td/text()')
            l.add_xpath('ranking', '//tr/*[contains(text(),"Best Sellers Rank")]/following-sibling::td//span//text()')
            l.add_xpath('rating', '//tr/*[contains(text(),"Customer Reviews")]/following-sibling::td/text()')
            l.add_xpath('discontinued',
                        '//tr/*[contains(text(),"Is Discontinued By Manufacturer")]/following-sibling::td/text()')
            l.add_xpath('retail_price', '//span[contains(@class,"priceBlockStrikePrice")]/text()')
            l.add_xpath('title', '//span[@id="productTitle"]/text()')
            l.add_xpath('weight', '//tr/*[contains(text(),"Item Weight")]/following-sibling::td/text()')

            details_key = response.xpath('//div[@id="prodDetails"]//*[contains(text(),"Technical Details")]'
                                         '/parent::*/following-sibling::*//tr/td[1]/text()').extract()
            details_value = response.xpath('//div[@id="prodDetails"]//*[contains(text(),"Technical Details")]'
                                           '/parent::*/following-sibling::*//tr/td[2]/text()').extract()
            if details_key and details_value:
                filter_values = [')', '', '\xa0']
                details_key = [x for x in details_key if x not in filter_values]
                details_value = [x for x in details_value if x not in filter_values]
                l.add_value('details', dict(zip(details_key, details_value)))

            l.add_value('date_scraped', datetime.utcnow())
            # from scrapy.shell import inspect_response
            # inspect_response(response, self)
            yield l.load_item()
        else:
            logging.warning('Cannot parse product- no title found')


'''except:
    add_to_cart = driver.find_element_by_xpath('//input[@id="add-to-cart-button"]')
    add_to_cart.click()
    goto_cart = driver.find_element_by_xpath('//a[@id="hlb-view-cart-announce"]')
    goto_cart.click()
    qty = driver.find_element_by_xpath('//span[@class="a-dropdown-prompt"]')
    qty.click()
    dropdown_last = driver.find_element_by_xpath('//*[@id="dropdown1_10"]')
    dropdown_last.click()
    qty_box = driver.find_element_by_xpath('//input[@name="quantityBox"]')
    qty_box.send_keys("999")
    update = driver.find_element_by_xpath('//span[contains(@class,"inner")]/a[@data-action="update"]')
    update.click()
    alert = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//div[@class="a-alert-content"]/span')))
    l.add_value('stock_total', re.search(r'\d+', alert.text).group(0))

finally:
    driver.quit()
    yield l.load_item()'''

'''
related_products = response.xpath('//li[contains(@id,"style_name") or '
                                              'contains(@id,"color_name") or '
                                              'contains(@id,"size_name") and '
                                              'contains(@data-dp-url,"/")]/@data-dp-url').extract()

            if related_products:
                related_products = [i for i in related_products if i != ""]  # Gets rid of empty elements
                for i in range(len(related_products)):
                    rp = related_products[i]

                    try:
                        asin = str(re.search(r'[A-Z0-9]{10}', rp).group(0))
                    except AttributeError:
                        asin = str(re.search(r'[A-Z0-9]{10}', rp))

                    url = "https://www.amazon.com/dp/" + asin
                    yield Request(url, callback=self.parse_product)
                    print("related_product " + str(i) + ": " + url)
                    related_products[i] = asin


                print("test", related_products)

            product['related_products'] = related_products'''

'''product['title'] = response.xpath('normalize-space(//span[@id="productTitle"]/text())').extract_first()
            product['ASIN'] = response.xpath('normalize-space(//tr/th[contains(text(),"ASIN")]/following-sibling::td/text())').extract_first()
            product['UNSPSC'] = response.xpath('normalize-space(//tr/th[contains(text(),"UNSPSC")]/following-sibling::td/text())').extract_first()
            product['price'] = response.xpath('//span[contains(@id,"priceblock")]/text()'.strip()).extract_first()
            product['retail_price'] = response.xpath('//span[contains(@class,"priceBlockStrikePrice")]/text()'.strip()).extract_first()
            product['rating'] = response.xpath('normalize-space(//tr/th[contains(text(),"Customer Reviews")]/following-sibling::td/text()[last()])').extract_first()

            product['date_first_available'] = response.xpath('normalize-space(//tr/th[contains(text(),"Date First Available")]/following-sibling::td/text())').extract_first()
            product['manufacturer'] = response.xpath('normalize-space(//tr/th[re:test(text(),"^\s*Manufacturer\s*$")]/following-sibling::td/text())').extract_first()

            product['brand_name'] = response.xpath('normalize-space(//tr/th[contains(text(),"Brand Name")]/following-sibling::td/text())').extract_first()
            product['weight'] = response.xpath('normalize-space(//tr/th[contains(text(),"Item Weight")]/following-sibling::td/text())').extract_first()
            product['product_dimensions'] = response.xpath('normalize-space(//tr/th[contains(text(),"Product Dimensions")]/following-sibling::td/text())').extract_first()
            product['package_dimensions'] = response.xpath('normalize-space(//tr/th[contains(text(),"Package Dimensions")]/following-sibling::td/text())').extract_first()
            product['color'] = response.xpath('normalize-space(//tr/th[contains(text(),"Color")]/following-sibling::td/text())').extract_first()
            product['weight'] = response.xpath('normalize-space(//tr/th[contains(text(),"Item Weight")]/following-sibling::td/text())').extract_first()
            product['item_model_num'] = response.xpath('normalize-space(//tr/th[contains(text(),"Item model number")]/following-sibling::td/text())').extract_first()
            product['url'] = response.request.url

            description = response.xpath('//div[@id="productDescription"]/p//text() | '
                                         '//div[@id="dpx-aplus-3p-product-description_feature_div"]//div//*[contains(@class,"a-")]/text()').extract()
            description = [item.strip() for item in description if description]
            product['description'] = description

            ranking = response.xpath('//tr/th[contains(text(),"Best Sellers Rank")]/following-sibling::td//span//text()').re("^[A-Za-z0-9,.# ]+")
            ranking = [item.strip() for item in ranking if ranking]
            product['ranking'] = ranking

            category = response.xpath('//div[@id="wayfinding-breadcrumbs_feature_div"]//li/span[@class="a-list-item"]/a/text()').extract()
            category = [item.strip() for item in category if category]
            product['category'] = category

            features = response.xpath('//div[@id="feature-bullets"]//li//text()').extract()
            features = [item.strip() for item in features if features]
            features = [i for i in features if i != ""]
            product['features'] = features
            yield product'''

'''protected $LUMINATI_USER = "lum-customer-hl_bfad3af8-zone-scrapezone";
    protected $LUMINATI_PASS = '1bbltfy6sv09';

    protected $LUMINATI_USER_ANNOYING = "lum-customer-hl_bfad3af8-zone-nomnomnom";
    protected $LUMINATI_PASS_ANNOYING = 'a8cqk40q0bfj';
    
    'proxy' => 'http://'.$user.':'.$pass.'@zproxy.lum-superproxy.io:22225' '''

'''if style: # if product has different styles
                self.driver.get(response.request.url)
                self.extract_info(response, product)
                yield {
                    'test': "round1",
                    'ASIN': response.xpath(
                        'normalize-space(//tr/th[contains(text(),"ASIN")]/following-sibling::td/text())').extract_first()
                }


                button = self.driver.find_element_by_xpath('//li[contains(@id,"style_name_")]//span[@aria-checked="false"]//button')
                button.click()
                time.sleep(5)
                self.driver.get(response.request.url)

                yield{
                    'test': "round2",
                    'ASIN': response.xpath('normalize-space(//tr/th[contains(text(),"ASIN")]/following-sibling::td/text())').extract_first()
                }


            else: # if product has no styles'''
