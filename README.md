# scraper-toolkit

### Overview
Program to scrape large volumes of product information from Amazon. Also comes with a proxy scraper so you could hide your real address to prevent getting recaptcha-ed by Amazon.

Because it is dependent on Amazon's page formatting which might change anytime, it's not guaranteed to make you a big data master overnight. You will also have to configure the database schemas yourself.

### How does it work?
#### Step 1: Department Scraper
Amazon (and every other online store) categorizes its products in a tree structure.

* All Departments
  * Automotive
    * Oils
    * Car Parts
    * ...
  * Beauty
    * Makeup
    * Fragrances
    * ...
  * ...
  
However this tree isn't given by Amazon and has to be created by going through links and collecting department names, which is done by the program. 

#### Step 2: Catalog Scraper
Each department and sub-department has a product catalog which are pages each containing a list of products. For each department in the department tree, a catalog tree is created.
* Automotive
  * Page 1
  * Page 2
  * ...
  * Page 190
  
#### Step 3: Product Scraper
Each page of the catalog contains a list of products, and the program goes through each product for data extraction. Information such as price, rating, title, weight, discount, etc. are collected using XPath, which is a path expression that tells the program how to navigate through HTML to get the information on a webpage.

A profile of the product is created and loaded into the database. Rinse and repeat for another product, for eternity.

### Extras
#### Proxy Scraper
Amazon does not like you harvesting their data. If they catch you doing that, they make it harder for you by making you do a recaptcha, which is an effective way to ward off bots. Thankfully this can be mitigated by using proxies, well, a lot of proxy addresses, which is gathered from free sites such as Spys.net. We simply gather the IP proxy addresses into our database and rotate these in our Amazon scraper. These IP proxy addresses are also periodically speed tested and only responsive ones are used.

You should keep in mind that if a product is free, that means you are the product itself. Taking advantage of free proxy services comes with a price- that your IP address will be used for malicious purposes. More important if your machine is using a static IP, or domain and DDNS. Recommended to chain a paid VPN in front first so the free services don't know your actual IP address, or just simply pay for a scraping VPN service.

#### User-Agent Rotation
When the program sends an HTTP request to Amazon (or any other website) it includes a string of text called the User-Agent. It lets the server identify what browser, operating system, version that you are currently using. If the server receives a lot of requests that have the same User-Agent header from you, then it is possible that you can be blocked by the server.

There is a Scrapy plugin that rotates the User-Agent for you so you won't have to worry about this kind of situation.
