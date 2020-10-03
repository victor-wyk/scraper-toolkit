'''
Spider that scrapes spys.one using Selenium
Created by: Victor Wan at 14/06/2020
'''

from scrapy import Request
from scrapy.spiders import Spider
from ..items import ProxyItem
from ..loaders import ProxyLoader
import re
from selenium import webdriver
from selenium.webdriver.opera.options import Options
import time
import urllib.request
import socket
import urllib.error
import os
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

class ProxySpider(Spider):
    name = 'spys_site'
    allowed_domains = ['spys.one']
    start_urls = ['http://spys.one/free-proxy-list/US/']
    pipelines = ['DatabaseProxyPipeline', 'DefaultNullValuesPipeline']

    def is_bad_proxy(self, pip):
        try:
            proxy_handler = urllib.request.ProxyHandler({'http': pip})
            opener = urllib.request.build_opener(proxy_handler)
            opener.addheaders = [('User-agent', 'Mozilla/5.0')]
            urllib.request.install_opener(opener)
            req = urllib.request.Request('http://www.google.com')  # change the URL to test here
            sock = urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            print('Error code: ', e.code)
            return e.code
        except Exception as detail:
            print("ERROR:", detail)
            return True
        return False

    def parse(self, response):
        # Initiating the webdriver
        dirname = os.path.dirname(__file__)
        filename = os.path.join(dirname, r'../../../webdriver/geckodriver')
        options = webdriver.FirefoxOptions()
        #options.headless = True
        options.add_argument('--disable-gpu')  # Only required for Windows
        driver = webdriver.Firefox(
            executable_path=filename,
            options=options
        )

        driver.get(response.url)

        max_amount = driver.find_element_by_xpath('//*[@id="xpp"]/option[6]')
        max_amount.click()
        time.sleep(3)

        # Extract locational info
        city = None
        location = driver.find_element_by_xpath('//h1').text
        location = re.search(r'\((.*?)\)', location).group(1)
        if "/" in location:
            location = location.split("/")
            country = location[0]
            city = location[1]
        else:
            country = location

        # Split content into table rows and iterate
        trs = driver.find_elements_by_xpath('//tr[contains(@class,"spy1x")]')
        counter = 0
        for tr in trs:
            counter = counter +1
            print(counter)
            try:
                ip_port = tr.find_element_by_xpath('./td[1]/font').text
                print(ip_port)

                if re.search(r'^\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}', ip_port):

                    if self.is_bad_proxy(ip_port):
                        print("Bad Proxy %s" % ip_port)


                    # If ip-port combination exists then process row
                    ip_port = ip_port.split(":")
                    ip = ip_port[0]
                    port = ip_port[1]

                    # Extract protocol
                    protocol = tr.find_elements_by_xpath('./td[2]/a/font')
                    temp = []
                    for p in protocol:
                        temp.append(p.text)
                    protocol = "".join(temp)

                    # Extract anonymity level
                    anon_lvl = tr.find_element_by_xpath('./td[3]/font').text
                    anon_dict = {'NOA': 3, 'ANM': 2, 'HIA': 1}
                    anon_lvl = anon_dict.get(anon_lvl)

                    # Extract organization
                    try:
                        organization = tr.find_element_by_xpath('./td[4]/font[2]').text
                        if organization:
                            organization = re.search(r'(?<=\()(.*?)(?=\))', organization).group(0)

                    except:
                        organization = None

                    # Extract uptime
                    uptime = tr.find_element_by_xpath('./td[7]/font/acronym').text
                    uptime = re.match(r'\d+(?=%)', uptime)



                    print("number ", counter, ip, port, protocol, anon_lvl, organization, uptime)

                    l = ProxyLoader(item=ProxyItem(), response=response)
                    l.add_value('ip', ip)
                    l.add_value('port', port)
                    l.add_value('protocol', protocol)
                    l.add_value('anonymity_level', anon_lvl)
                    l.add_value('organization', organization)
                    l.add_value('country', country)
                    l.add_value('city', city)

                    if uptime:
                        l.add_value('uptime', uptime.group(0))
                    yield l.load_item()
            except:
                continue

        driver.close()
