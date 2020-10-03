"""
Created by: Victor Wan at 01/07/2020

Function to generate a tree structure of Amazon's product departments,
where each node contains department name and url.
The tree could then be used by a scraping program.

FAQ:
Q: When scraping the department list wouldn't there be any links pointing back to parent departments, creating a infinite loop?
A: When the program goes through the department list it creates a new tree node for each sub-department, which requires a unique identifier.
    The sub-department's identifier is the hash of its url. This ensures that when a new node is added to the tree if it happens to
    be the parent department or any existing departments it would be omitted due to the url existed already.
    In addition, the Xpath extractor is able to ignore the parent departments because they have a different class attribute.
"""

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


# Define department class to store metadata
class Department(object):
    def __init__(self, url, nid=None):
        self.url = url
        self.nid = nid


def get_nodeid_from_url(url):
    try:
        url = re.search(r"(?<=node=)\d+", url).group(0)
        return url
    except:
        return None


class AmazonDepTree(Spider):
    name = 'dep-tree-spider'
    pipelines = ['DatabaseDepPipeline', 'DefaultNullValuesPipeline']

    # allowed_domains = ['www.amazon.com']
    start_urls = [
        'https://www.amazon.com/b?node=17938598011',
    ]

    # Start at the departments page and create a tree structure with root 'Departments'
    def parse(self, response):

        logger = logging.getLogger('product_spider')
        logger.setLevel(logging.INFO)
        logger.info("Collecting department urls...")

        parent_tag = "International Best Sellers"
        # Instantiate treelib and define tree root
        tree = Tree()
        identifier = hashlib.md5(parent_tag.encode("utf-8")).hexdigest()
        tree.create_node(parent_tag, identifier, data={'url': response.request.url, })

        yield Request(
            url=response.request.url,
            callback=self.parse_department,
            meta={
                "tree": tree,
                "parent_id": identifier,
                "parent_tag": parent_tag,
            }
        )

    def parse_department(self, response):
        logger = logging.getLogger('tree')
        tree = response.meta['tree']

        parent_tag = response.meta['parent_tag']
        parent_id = response.meta['parent_id']

        # Instantiate the department item
        ancestors_path = list(tree.rsearch(parent_id))

        l = AmazonDepLoader(item=AmazonDepItem(), response=response)
        l.add_value('path', ancestors_path)
        l.add_value('url', response.url)
        l.add_value('name', parent_tag)
        l.add_value('hash', parent_id)
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
                department_names = department_list.xpath("./li[contains(@class,'navigation')]/span/a/span/text()").getall()

        # Create first department children layer with url metadata
        for child_tag, child_url in zip(department_names, department_urls):
            # The identifier is md5 of child tag and parent tag
            identifier = hashlib.md5((child_tag+parent_tag).encode("utf-8")).hexdigest()

            try:
                tree.create_node(
                    tag=child_tag,
                    identifier=identifier,
                    parent=parent_id,
                    data={'url': urljoin(response.url, child_url)}
                )
            except Exception as e:
                logger.error(e)

        # Display tree
        tree.show()
        # Display scraped departments
        print('SCRAPED: ', department_names)

        # Get tree node list, first element is root node, followed by children nodes
        # So children list would be node list without the first element
        children = [x for x in tree.all_nodes() if x is not tree.all_nodes()[0]]

        # For each child repeat the above function, and passing down metadata
        try:
            for child in children:
                yield Request(
                    url=child.data['url'],
                    callback=self.parse_department,
                    meta={
                        "tree": tree,
                        "parent_tag": child.tag,
                        "parent_id": child.identifier
                    }
                )
        except Exception as e:
            print("ERROR FUCKKK", tree.all_nodes())
            logger.error(e)

        dirname = os.path.dirname(__file__)
        filename = os.path.join(dirname, r'../tree/dep_tree_20200706.json')

        with open(filename, 'w') as json_file:
            json.dump(tree.to_dict(with_data=True), json_file, sort_keys=True, indent=4)
