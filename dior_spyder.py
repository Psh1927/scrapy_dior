import scrapy
from scrapy.crawler import CrawlerProcess
import datetime
import re
import json
import csv


class DiorSpider(scrapy.Spider):
    name = 'dior'
    domen = 'https://www.dior.com'
    regions = ['en_us', 'fr_fr']
    fieldnames = ['url', 'name', 'price', 'currency', 'category', 'sku', 'stock', 'date', 'color', 'size', 'country',
                  'description']
    writer = csv.DictWriter(open('dior.csv', 'w', encoding='utf-8', newline=''), fieldnames=fieldnames)

    def start_requests(self):
        self.writer.writeheader()
        urls = []
        for region in self.regions:
            urls.append(self.domen + '/' + region)
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        for url in response.css(".navigation-item-link::attr(href)").extract():
            if self.domen not in url:
                yield response.follow(self.domen + url, self.parse_page)

    def parse_page(self, response):
        for url in response.css(".product-link::attr(href)").extract():
            if 'products' in url:
                yield response.follow(self.domen + url, self.parse_item)

    def parse_item(self, response):
        productinfo = {fieldname: "" for fieldname in self.fieldnames}
        productinfo['date'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        productinfo['url'] = response.url
        data_script_1 = json.loads(
            re.findall('<script type="application/ld\+json">(.+?)</script>', response.body.decode("utf-8"))[1])
        productinfo['name'] = data_script_1['name'].replace('\n', '').replace('\r', '')
        productinfo['description'] = data_script_1['description'].replace('\n', '').replace('\r', '')
        data_script_2 = json.loads(re.findall("var dataLayer = (.+?);\n", response.body.decode("utf-8"))[0])[0]
        productinfo['country'] = data_script_2['country']
        productinfo['category'] = data_script_2['ecommerce']['detail']['products']['category']
        if data_script_2['ecommerce']['detail']['products']['variant'].isalpha():
            productinfo['color'] = data_script_2['ecommerce']['detail']['products']['variant']
        productinfo['stock'] = "yes" if data_script_2['ecommerce']['detail']['products']['dimension25'] == "inStock" else "no"
        data_script_3 = json.loads(re.findall("window.initialState = (.+?)\n", response.body.decode("utf-8"))[0])
        product_variations = []
        product_unique = []
        for element in data_script_3['CONTENT']['cmsContent']['elements']:
            if type(element) is dict and element['type'] == 'PRODUCTVARIATIONS':
                product_variations = element['variations']
            if type(element) is dict and element['type'] == 'PRODUCTUNIQUE':
                product_unique = element
        if product_unique:
            productinfo['price'] = product_unique['price']['value']
            productinfo['currency'] = product_unique['price']['currency']
            productinfo['sku'] = product_unique['sku']
            self.writer.writerow(productinfo)
        if product_variations:
            for product in product_variations:
                productinfo['stock'] = "yes" if 'status' in product.keys() and product['status'] == "AVAILABLE" else "no"
                if 'detail' in product.keys():
                    productinfo['size'] = re.findall(": (.+)", product['detail'])[0]
                productinfo['price'] = product['price']['value']
                productinfo['currency'] = product['price']['currency']
                productinfo['sku'] = product['sku']
                self.writer.writerow(productinfo)


process = CrawlerProcess({
    'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'
})
process.crawl(DiorSpider)
process.start()
