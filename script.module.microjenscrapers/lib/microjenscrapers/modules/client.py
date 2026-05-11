# -*- coding: utf-8 -*-

"""
    MicroJen Scrapers Add-on

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from __future__ import absolute_import, division, print_function

import re, sys, gzip, time, random, base64

import simplejson as json

from microjenscrapers.modules import cache, control, dom_parser, log_utils

import six
from six.moves import range as x_range

# Py2
try:
    from urlparse import urlparse, urljoin
    from urllib import quote, urlencode, quote_plus, addinfourl
    import cookielib
    import urllib2
    from cStringIO import StringIO
    from HTMLParser import HTMLParser
    unescape = HTMLParser().unescape
    HTTPError = urllib2.HTTPError

# Py3:
except ImportError:
    from http import cookiejar as cookielib
    from html import unescape
    import urllib.request as urllib2
    from io import StringIO
    from urllib.parse import urlparse, urljoin, quote, urlencode, quote_plus
    from urllib.response import addinfourl
    from urllib.error import HTTPError

finally:
    urlopen = urllib2.urlopen
    Request = urllib2.Request

if six.PY2:
    _str = str
    str = unicode
    unicode = unicode
    basestring = basestring
    def bytes(b, encoding="ascii"):
        return _str(b)
elif six.PY3:
    bytes = bytes
    str = unicode = basestring = str



def request(url, close=True, redirect=True, error=False, verify=True, proxy=None, post=None, headers=None, mobile=False, XHR=False,
            limit=None, referer=None, cookie=None, compression=False, output='', timeout='30', username=None, password=None, as_bytes=False):

    """
    Re-adapted from Twilight0's tulip module => https://github.com/Twilight0/script.module.tulip
    """

    try:
        url = six.ensure_text(url, errors='ignore')
    except Exception:
        pass

    if isinstance(post, dict):
        post = bytes(urlencode(post), encoding='utf-8')
    elif isinstance(post, str) and six.PY3:
        post = bytes(post, encoding='utf-8')

    try:
        handlers = []

        if username is not None and password is not None and not proxy:

            passmgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
            passmgr.add_password(None, uri=url, user=username, passwd=password)
            handlers += [urllib2.HTTPBasicAuthHandler(passmgr)]
            opener = urllib2.build_opener(*handlers)
            urllib2.install_opener(opener)

        if proxy is not None:

            if username is not None and password is not None:

                if six.PY2:
                    passmgr = urllib2.ProxyBasicAuthHandler()
                else:
                    passmgr = urllib2.HTTPPasswordMgr()

                passmgr.add_password(None, uri=url, user=username, passwd=password)

                handlers += [
                    urllib2.ProxyHandler({'http': '{0}'.format(proxy)}), urllib2.HTTPHandler,
                    urllib2.ProxyBasicAuthHandler(passmgr)
                ]
            else:
                handlers += [urllib2.ProxyHandler({'http':'{0}'.format(proxy)}), urllib2.HTTPHandler]
            opener = urllib2.build_opener(*handlers)
            urllib2.install_opener(opener)

        if output == 'cookie' or output == 'extended' or close is not True:

            cookies = cookielib.LWPCookieJar()
            handlers += [urllib2.HTTPHandler(), urllib2.HTTPSHandler(), urllib2.HTTPCookieProcessor(cookies)]

            opener = urllib2.build_opener(*handlers)
            urllib2.install_opener(opener)

        try:
            import platform
            is_XBOX = platform.uname()[1] == 'XboxOne'
        except Exception:
            is_XBOX = False

        if not verify and sys.version_info >= (2, 7, 12):

            try:

                import ssl
                ssl_context = ssl._create_unverified_context()
                handlers += [urllib2.HTTPSHandler(context=ssl_context)]
                opener = urllib2.build_opener(*handlers)
                urllib2.install_opener(opener)

            except Exception:

                pass

        elif verify and ((2, 7, 8) < sys.version_info < (2, 7, 12) or is_XBOX):

            try:

                import ssl
                try:
                    import _ssl
                    CERT_NONE = _ssl.CERT_NONE
                except Exception:
                    CERT_NONE = ssl.CERT_NONE
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = CERT_NONE
                handlers += [urllib2.HTTPSHandler(context=ssl_context)]
                opener = urllib2.build_opener(*handlers)
                urllib2.install_opener(opener)

            except Exception:

                pass

        try:
            headers.update(headers)
        except Exception:
            headers = {}

        if 'User-Agent' in headers:
            pass
        elif mobile is not True:
            #headers['User-Agent'] = agent()
            headers['User-Agent'] = cache.get(randomagent, 12)
        else:
            headers['User-Agent'] = cache.get(randommobileagent, 12)

        if 'Referer' in headers:
            pass
        elif referer is None:
            headers['Referer'] = '%s://%s/' % (urlparse(url).scheme, urlparse(url).netloc)
        else:
            headers['Referer'] = referer

        if not 'Accept-Language' in headers:
            headers['Accept-Language'] = 'en-US'

        if 'X-Requested-With' in headers:
            pass
        elif XHR is True:
            headers['X-Requested-With'] = 'XMLHttpRequest'

        if 'Cookie' in headers:
            pass
        elif cookie is not None:
            headers['Cookie'] = cookie

        if 'Accept-Encoding' in headers:
            pass
        elif compression and limit is None:
            headers['Accept-Encoding'] = 'gzip'

        if redirect is False:

            class NoRedirectHandler(urllib2.HTTPRedirectHandler):

                def http_error_302(self, reqst, fp, code, msg, head):

                    infourl = addinfourl(fp, head, reqst.get_full_url())
                    infourl.status = code
                    infourl.code = code

                    return infourl

                http_error_300 = http_error_302
                http_error_301 = http_error_302
                http_error_303 = http_error_302
                http_error_307 = http_error_302

            opener = urllib2.build_opener(NoRedirectHandler())
            urllib2.install_opener(opener)

            try:
                del headers['Referer']
            except Exception:
                pass

        req = urllib2.Request(url, data=post, headers=headers)

        try:

            response = urllib2.urlopen(req, timeout=int(timeout))

        except HTTPError as response:

            if response.code == 503:

                if 'cf-browser-verification' in response.read(5242880):
                    from microjenscrapers.modules import cfscrape

                    netloc = '{0}://{1}'.format(urlparse(url).scheme, urlparse(url).netloc)

                    ua = headers['User-Agent']

                    #cf = cache.get(Cfcookie.get, 168, netloc, ua, timeout)
                    try:
                        cf = cache.get(cfscrape.get_cookie_string, 1, netloc, ua)[0]
                    except BaseException:
                        try:
                            cf = cfscrape.get_cookie_string(url, ua)[0]
                        except BaseException:
                            cf = None
                    finally:
                        headers['Cookie'] = cf

                    req = urllib2.Request(url, data=post, headers=headers)

                    response = urllib2.urlopen(req, timeout=int(timeout))

                elif error is False:
                    return

            elif error is False:
                return

        if output == 'cookie':

            try:
                result = '; '.join(['%s=%s' % (i.name, i.value) for i in cookies])
            except Exception:
                pass

            try:
                result = cf
            except Exception:
                pass

        elif output == 'response':

            if limit == '0':
                result = (str(response.code), response.read(224 * 1024))
            elif limit is not None:
                result = (str(response.code), response.read(int(limit) * 1024))
            else:
                result = (str(response.code), response.read(5242880))

        elif output == 'chunk':

            try:
                content = int(response.headers['Content-Length'])
            except Exception:
                content = (2049 * 1024)

            if content < (2048 * 1024):
                return
            result = response.read(16 * 1024)

        elif output == 'extended':

            try:
                cookie = '; '.join(['%s=%s' % (i.name, i.value) for i in cookies])
            except Exception:
                pass

            try:
                cookie = cf
            except Exception:
                pass

            content = response.headers
            result = response.read(5242880)

            if not as_bytes:

                result = six.ensure_text(result, errors='ignore')

            return result, headers, content, cookie

        elif output == 'geturl':

            result = response.geturl()

        elif output == 'headers':

            content = response.headers

            if close:
                response.close()

            return content

        elif output == 'file_size':

            try:
                content = int(response.headers['Content-Length'])
            except Exception:
                content = '0'

            response.close()

            return content

        elif output == 'json':

            content = json.loads(response.read(5242880))

            response.close()

            return content

        else:

            if limit == '0':
                result = response.read(224 * 1024)
            elif limit is not None:
                if isinstance(limit, int):
                    result = response.read(limit * 1024)
                else:
                    result = response.read(int(limit) * 1024)
            else:
                result = response.read(5242880)

        if close is True:
            response.close()

        if not as_bytes:

            result = six.ensure_text(result, errors='ignore')

        return result

    except:

        log_utils.log('Client request failed on url: ' + url + ' | Reason', 1)

        return


def _basic_request(url, headers=None, post=None, timeout='30', limit=None):
    try:
        try:
            headers.update(headers)
        except:
            headers = {}

        request = Request(url, data=post)
        _add_request_header(request, headers)
        response = urlopen(request, timeout=int(timeout))
        return _get_result(response, limit)
    except:
        return


def _add_request_header(_request, headers):
    try:
        if not headers:
            headers = {}

        try:
            scheme = _request.get_type()
        except:
            scheme = 'http'

        referer = headers.get('Referer') if 'Referer' in headers else '%s://%s/' % (scheme, _request.get_host())

        _request.add_unredirected_header('Host', _request.get_host())
        _request.add_unredirected_header('Referer', referer)
        for key in headers: _request.add_header(key, headers[key])
    except:
        return


def _get_result(response, limit=None):
    if limit == '0':
        result = response.read(224 * 1024)
    elif limit:
        result = response.read(int(limit) * 1024)
    else:
        result = response.read(5242880)

    try:
        encoding = response.info().getheader('Content-Encoding')
    except:
        encoding = None
    if encoding == 'gzip':
        result = gzip.GzipFile(fileobj=StringIO(result)).read()

    return result


def parseDOM(html, name='', attrs=None, ret=False):

    if attrs:

        attrs = dict((key, re.compile(value + ('$' if value else ''))) for key, value in six.iteritems(attrs))

    results = dom_parser.parse_dom(html, name, attrs, ret)

    if ret:
        results = [result.attrs[ret.lower()] for result in results]
    else:
        results = [result.content for result in results]

    return results


def replaceHTMLCodes(txt):
    txt = re.sub("(&#[0-9]+)([^;^0-9]+)", "\\1;\\2", txt)
    txt = unescape(txt)
    txt = txt.replace("&quot;", "\"")
    txt = txt.replace("&amp;", "&")
    txt = txt.replace("&lt;", "<")
    txt = txt.replace("&gt;", ">")
    txt = txt.replace("&#38;", "&")
    txt = txt.replace("&nbsp;", "")
    txt = txt.replace('&#8230;', '...')
    txt = txt.replace('&#8217;', '\'')
    txt = txt.replace('&#8211;', '-')
    txt = txt.strip()
    return txt


def randomagent():
    BR_VERS = [
        ['%s.0' % i for i in x_range(18, 50)],
        ['37.0.2062.103', '37.0.2062.120', '37.0.2062.124', '38.0.2125.101', '38.0.2125.104', '38.0.2125.111',
         '39.0.2171.71', '39.0.2171.95', '39.0.2171.99', '40.0.2214.93', '40.0.2214.111', '40.0.2214.115',
         '42.0.2311.90', '42.0.2311.135', '42.0.2311.152', '43.0.2357.81', '43.0.2357.124', '44.0.2403.155',
         '44.0.2403.157', '45.0.2454.101', '45.0.2454.85', '46.0.2490.71', '46.0.2490.80', '46.0.2490.86',
         '47.0.2526.73', '47.0.2526.80', '48.0.2564.116', '49.0.2623.112', '50.0.2661.86', '51.0.2704.103',
         '52.0.2743.116', '53.0.2785.143', '54.0.2840.71', '61.0.3163.100'],
        ['11.0'],
        ['8.0', '9.0', '10.0', '10.6']]
    WIN_VERS = ['Windows NT 10.0', 'Windows NT 7.0', 'Windows NT 6.3', 'Windows NT 6.2',
                'Windows NT 6.1', 'Windows NT 6.0', 'Windows NT 5.1', 'Windows NT 5.0']
    FEATURES = ['; WOW64', '; Win64; IA64', '; Win64; x64', '']
    RAND_UAS = ['Mozilla/5.0 ({win_ver}{feature}; rv:{br_ver}) Gecko/20100101 Firefox/{br_ver}',
                'Mozilla/5.0 ({win_ver}{feature}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{br_ver} Safari/537.36',
                'Mozilla/5.0 ({win_ver}{feature}; Trident/7.0; rv:{br_ver}) like Gecko',
                'Mozilla/5.0 (compatible; MSIE {br_ver}; {win_ver}{feature}; Trident/6.0)']
    index = random.randrange(len(RAND_UAS))
    return RAND_UAS[index].format(
        win_ver=random.choice(WIN_VERS),
        feature=random.choice(FEATURES),
        br_ver=random.choice(BR_VERS[index]))


def randommobileagent(mobile):
    _mobagents = [
        'Mozilla/5.0 (Linux; Android 7.1; vivo 1716 Build/N2G47H) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.98 Mobile Safari/537.36',
        'Mozilla/5.0 (Linux; U; Android 6.0.1; zh-CN; F5121 Build/34.0.A.1.247) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/40.0.2214.89 UCBrowser/11.5.1.944 Mobile Safari/537.36',
        'Mozilla/5.0 (Linux; Android 7.0; SAMSUNG SM-N920C Build/NRD90M) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/6.2 Chrome/56.0.2924.87 Mobile Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 12_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/80.0.3987.95 Mobile/15E148 Safari/605.1',
        'Mozilla/5.0 (iPad; CPU OS 10_2_1 like Mac OS X) AppleWebKit/602.4.6 (KHTML, like Gecko) Version/10.0 Mobile/14D27 Safari/602.1']

    if mobile == 'android':
        return random.choice(_mobagents[:3])
    else:
        return random.choice(_mobagents[3:5])


def agent():
    return random.choice(
            ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36",
            "Mozilla/5.0 (Linux; Android 8.0.0;) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Mobile Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 12_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/80.0.3987.95 Mobile/15E148 Safari/605.1",
            "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:54.0) Gecko/20100101 Firefox/74.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:61.0) Gecko/20100101 Firefox/74.0",
            "Mozilla/5.0 (X11; Linux i586; rv:31.0) Gecko/20100101 Firefox/74.0",
            "Mozilla/5.0 (Android 8.0.0; Mobile; rv:61.0) Gecko/61.0 Firefox/68.0",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 12_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/24.0 Mobile/16B92 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1 Safari/605.1.15",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 13_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 13_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPod Touch; CPU iPhone OS 13_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1 Mobile/15E148 Safari/604.1",
            "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0)",
            "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0; WOW64; Trident/4.0;)",
            "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; Trident/4.0)",
            "Mozilla/4.0 (compatible; MSIE 9.0; Windows NT 6.0)",
            "Mozilla/4.0 (compatible; MSIE 9.0; Windows NT 6.1)",
            "Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; WOW64; Trident/6.0)",
            "Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2)",
            "Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko",
            "Mozilla/5.0 (Windows NT 6.2; Trident/7.0; rv:11.0) like Gecko",
            "Windows 8.1	Mozilla/5.0 (Windows NT 6.3; Trident/7.0; rv:11.0) like Gecko",
            "Windows 10	Mozilla/5.0 (Windows NT 10.0; Trident/7.0; rv:11.0) like Gecko",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36 Edg/80.0.361.69",
            "Mozilla/5.0 (Windows Mobile 10; Android 8.0.0; Microsoft; Lumia 950XL) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Mobile Safari/537.36 Edge/80.0.361.69",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; Xbox; Xbox One) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36 Edge/44.18363.8131",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36 OPR/67.0.3575.115",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36 OPR/67.0.3575.115",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36 OPR/67.0.3575.115",
            "Mozilla/5.0 (Linux; Android 9; AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Mobile Safari/537.36 OPR/55.2.2719"])


class Cfcookie:
    def __init__(self):
        self.cookie = None

    def get(self, netloc, ua, timeout):
        try:
            self.netloc = netloc
            self.ua = ua
            self.timeout = timeout
            self.cookie = None
            self._get_cookie(netloc, ua, timeout)
            if self.cookie is None:
                log_utils.log('%s returned an error. Could not collect tokens.' % netloc)
            return self.cookie
        except Exception as e:
            log_utils.log('%s returned an error. Could not collect tokens - Error: %s.' % (netloc, str(e)))
            return self.cookie

    def _get_cookie(self, netloc, ua, timeout):
        class NoRedirection(urllib2.HTTPErrorProcessor):
            def http_response(self, request, response):
                return response

        def parseJSString(s):
            try:
                offset = 1 if s[0] == '+' else 0
                val = int(
                    eval(s.replace('!+[]', '1').replace('!![]', '1').replace('[]', '0').replace('(', 'str(')[offset:]))
                return val
            except:
                pass

        cookies = cookielib.LWPCookieJar()
        opener = urllib2.build_opener(NoRedirection, urllib2.HTTPCookieProcessor(cookies))
        opener.addheaders = [('User-Agent', ua)]
        try:
            response = opener.open(netloc, timeout=int(timeout))
            result = response.read()
        except HTTPError as response:
            result = response.read()
            try:
                encoding = response.info().getheader('Content-Encoding')
            except:
                encoding = None
            if encoding == 'gzip':
                result = gzip.GzipFile(fileobj=StringIO(result)).read()

        jschl = re.compile('name="jschl_vc" value="(.+?)"/>').findall(result)[0]
        init = re.compile('setTimeout\(function\(\){\s*.*?.*:(.*?)};').findall(result)[0]
        builder = re.compile(r"challenge-form\'\);\s*(.*)a.v").findall(result)[0]

        if '/' in init:
            init = init.split('/')
            decryptVal = parseJSString(init[0]) / float(parseJSString(init[1]))
        else:
            decryptVal = parseJSString(init)

        lines = builder.split(';')
        for line in lines:
            if len(line) > 0 and '=' in line:
                sections = line.split('=')
                if '/' in sections[1]:
                    subsecs = sections[1].split('/')
                    line_val = parseJSString(subsecs[0]) / float(parseJSString(subsecs[1]))
                else:
                    line_val = parseJSString(sections[1])
                decryptVal = float(eval('%.16f' % decryptVal + sections[0][-1] + '%.16f' % line_val))

        answer = float('%.10f' % decryptVal) + len(urlparse(netloc).netloc)

        query = '%scdn-cgi/l/chk_jschl?jschl_vc=%s&jschl_answer=%s' % (netloc, jschl, answer)

        if 'type="hidden" name="pass"' in result:
            passval = re.findall('name="pass" value="(.*?)"', result)[0]
            query = '%scdn-cgi/l/chk_jschl?pass=%s&jschl_vc=%s&jschl_answer=%s' % (
                netloc, quote_plus(passval), jschl, answer)
            time.sleep(6)

        opener.addheaders = [('User-Agent', ua),
                             ('Referer', netloc),
                             ('Accept', 'text/html, application/xhtml+xml, application/xml, */*'),
                             ('Accept-Encoding', 'gzip, deflate')]

        response = opener.open(query)
        response.close()

        cookie = '; '.join(['%s=%s' % (i.name, i.value) for i in cookies])
        if 'cf_clearance' in cookie: self.cookie = cookie


class bfcookie:

    def __init__(self):
        self.COOKIE_NAME = 'BLAZINGFAST-WEB-PROTECT'

    def get(self, netloc, ua, timeout):
        try:
            headers = {'User-Agent': ua, 'Referer': netloc}
            result = _basic_request(netloc, headers=headers, timeout=timeout)

            match = re.findall('xhr\.open\("GET","([^,]+),', result)
            if not match:
                return False

            url_Parts = match[0].split('"')
            url_Parts[1] = '1680'
            url = urljoin(netloc, ''.join(url_Parts))

            match = re.findall('rid=([0-9a-zA-Z]+)', url_Parts[0])
            if not match:
                return False

            headers['Cookie'] = 'rcksid=%s' % match[0]
            result = _basic_request(url, headers=headers, timeout=timeout)
            return self.getCookieString(result, headers['Cookie'])
        except:
            return

    # not very robust but lazieness...
    def getCookieString(self, content, rcksid):
        vars = re.findall('toNumbers\("([^"]+)"', content)
        value = self._decrypt(vars[2], vars[0], vars[1])
        cookie = "%s=%s;%s" % (self.COOKIE_NAME, value, rcksid)
        return cookie

    def _decrypt(self, msg, key, iv):
        from binascii import unhexlify, hexlify
        import pyaes
        msg = unhexlify(msg)
        key = unhexlify(key)
        iv = unhexlify(iv)
        if len(iv) != 16: return False
        decrypter = pyaes.Decrypter(pyaes.AESModeOfOperationCBC(key, iv))
        plain_text = decrypter.feed(msg)
        plain_text += decrypter.feed()
        f = hexlify(plain_text)
        return f


class sucuri:
    def __init__(self):
        self.cookie = None

    def get(self, result):
        try:
            s = re.compile("S\s*=\s*'([^']+)").findall(result)[0]
            s = base64.b64decode(s)
            s = s.replace(' ', '')
            s = re.sub('String\.fromCharCode\(([^)]+)\)', r'chr(\1)', s)
            s = re.sub('\.slice\((\d+),(\d+)\)', r'[\1:\2]', s)
            s = re.sub('\.charAt\(([^)]+)\)', r'[\1]', s)
            s = re.sub('\.substr\((\d+),(\d+)\)', r'[\1:\1+\2]', s)
            s = re.sub(';location.reload\(\);', '', s)
            s = re.sub(r'\n', '', s)
            s = re.sub(r'document\.cookie', 'cookie', s)

            cookie = ''
            exec(s)
            self.cookie = re.compile('([^=]+)=(.*)').findall(cookie)[0]
            self.cookie = '%s=%s' % (self.cookie[0], self.cookie[1])

            return self.cookie
        except:
            pass


def _get_keyboard(default="", heading="", hidden=False):

    keyboard = control.keyboard(default, heading, hidden)
    keyboard.doModal()
    if keyboard.isConfirmed():
        return six.ensure_text(keyboard.getText())
    return default


def removeNonAscii(s):
    return "".join(i for i in s if ord(i) < 128)
