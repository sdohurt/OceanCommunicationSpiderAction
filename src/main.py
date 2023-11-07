import requests
from bs4 import BeautifulSoup
import configparser
import time
from datetime import datetime, timedelta
from chardet import detect
import sys

from mailbox import send_email

# init
try:
    print(f'使用控制命令行获取')
    EMAIL_PASSWORD = sys.argv[1]
    EMAIL_SENDER = sys.argv[2]
    EMAIL_RECIVER = sys.argv[3]
    print(EMAIL_PASSWORD, EMAIL_SENDER, EMAIL_RECIVER)

except Exception as e:
    print(e, f'\n使用ini文件读取')
    config_secret = configparser.ConfigParser()
    config_secret.read('sc.ini', encoding='utf-8')
    section = config_secret['secret']

    EMAIL_SENDER = section['EMAIL_SENDER']
    EMAIL_PASSWORD = section['EMAIL_PASSWORD']
    EMAIL_RECIVER = section['EMAIL_RECIVER']


def is_within_3_days(date_str):

    # 解决报错ValueError: time data '2023.11.03' does not match format '%Y-%m-%d'
    if '.' in date_str:
        date_str = date_str.replace('.', '-')

    # 指定天数内
    num = 1

    # 解析日期字符串为日期对象
    date = datetime.strptime(date_str, '%Y-%m-%d')

    # 获取当前日期
    today = datetime.today()

    # 计算3天内的日期
    three_days = today - timedelta(days=num)

    # 比较日期对象与当前日期和3天后的日期
    if today >= date >= three_days:
        print(f'>> 当前时间为{today},报道时间为{date}，在{num}天时间内')
        return True
    else:
        return False


class ContentParser:
    def __init__(self, original_url, object, title_css, href_css, date_css, referer) -> None:
        self.original_url = original_url
        self.object = object
        self.title_css = title_css
        self.href_css = href_css
        self.date_css = date_css
        self.referer = referer

    def detect_encoding(self, html):
        encoding = detect(html)['encoding']
        return encoding

    def parse(self):
        print(f'Starting parse for object: {self.object}')  # 开始解析对象时打印的信息
        time.sleep(1.0)
        # 使用request+bs4
        r = requests.get(
            self.original_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.69"}
        )

        encoding = self.detect_encoding(r.content)
        print(f'{self.object}-encoding: {encoding}')
        r.encoding = encoding

        soup = BeautifulSoup(r.text, 'html.parser')
        print(f'Finished parsing for object: {self.object}')  # 解析结束时打印的信息

        try:
            title_elements = soup.select(self.title_css)
            href_elements = soup.select(self.href_css)
            date_elements = soup.select(self.date_css)

            return zip(title_elements, href_elements, date_elements)

        except Exception as e:
            return zip('', e, '')

    def check_href(self, href):
        if not href.startswith('http://') and not href.startswith('https://'):
            # print(f'raw_href: {href}, charge_href:{self.referer + href}')
            return self.referer + href
        else:
            return href

    def get_content(self):

        # content = pd.DataFrame(columns=['object', 'title', 'href', 'date'])
        content = ''
        i = 1

        for title_element, href_element, date_element in self.parse():
            # title_element,  date_element = i
            if title_element != '':
                title = title_element.text.strip()
                href = href_element.get('href')
                href = self.check_href(href)
                date = date_element.text.strip()

                if is_within_3_days(date):
                    print(f'--收录报道{title},{date}')
                    a = f'<a href="{href}">{title}</a>'
                    content += f"<p>{i}. {a} {date}</p>\n"
                    i += 1

            else:
                error = href_element
                print(f'{self.object}采集失败，报错为{error}')
                content += f"[error]-[部门]{self.object}采集失败\n"

            # content = pd.concat([content, row], ignore_index=True)

        return content

    def get_item(self):
        print(f'----------------{self.object}----------------')
        # return self.get_content()

        content = self.get_content()
        if content == '':
            return content
        else:
            return f"""
            <h3>{self.object}</h3>
            <link>{self.original_url}</link>
            <div>
                {content}
            </div>
            """


def main():
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')

    content_parser_list = []

    for section in config.sections():
        content_parser_list.append(ContentParser(
            config.get(section, 'original_url'),
            config.get(section, 'object'),
            config.get(section, 'title_css'),
            config.get(section, 'href_css'),
            config.get(section, 'date_css'),
            config.get(section, 'referer')
        ))

    # pd
    # result = pd.concat([c_p.get_item() for c_p in content_parser_list], ignore_index=True)
    # result_html = result.to_html

    # html
    result = ''.join([c_p.get_item() for c_p in content_parser_list])

    # 测试-检查最新添加内容；需注释上一行内容
    # result = ''.join(content_parser_list[-1].get_item())

    output = f"""
    <html>
    <body>
        {result}
    </body>
    </html>
    """

    print(f'-------------------------以下为爬取结果：-------------------------\n', output)
    return output


if __name__ == '__main__':
    title = f'{datetime.today().strftime("%Y-%m-%d")}-海洋行业通讯'

    communication = main()

    send_email(title, communication, EMAIL_PASSWORD, EMAIL_SENDER, EMAIL_RECIVER)
