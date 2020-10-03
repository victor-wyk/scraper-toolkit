import threading
import urllib
import urllib.request
import urllib.error


class ProxyChecker:

    def run_item(self, f, item):
        result_info = [threading.Event(), None]
        def runit():
            result_info[1] = f(item)
            result_info[0].set()
        threading.Thread(target=runit).start()
        return result_info

    def gather_results(self, result_infos):
        results = []
        for i in range(len(result_infos)):
            result_infos[i][0].wait()
            results.append(result_infos[i][1])
        return results

    # Function to test if proxy is alive
    def check(self, entry):
        try:
            proxy_handler = urllib.request.ProxyHandler({'http': entry['proxy']})
            opener = urllib.request.build_opener(proxy_handler)
            opener.addheaders = [('User-agent', 'Mozilla/5.0')]
            urllib.request.install_opener(opener)
            req=urllib.request.Request('http://www.google.com')  # change the URL to test here
            sock=urllib.request.urlopen(req, timeout=2)
        except urllib.error.HTTPError as e:
            print('Error code: ', e.code)
            return {'proxy': entry['proxy'], 'alive': False, 'meta': entry['meta']}
        except Exception as detail:
            print("ERROR:", detail)
            return {'proxy': entry['proxy'], 'alive': False, 'meta': entry['meta']}
        return {'proxy': entry['proxy'], 'alive': True, 'meta': entry['meta']}

    def run(self, proxy_list):
        return self.gather_results([self.run_item(self.check, entry) for entry in proxy_list])
