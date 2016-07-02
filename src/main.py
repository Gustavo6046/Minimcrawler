import BeautifulSoup
import requests
import re
import json
import os.path
import urlparse
import os
import ntpath
import urllib
import threading
import Queue
import time


class MultiThreadQueue(object):
    def __init__(self, max_simultaneous_threads):
        self.thread_queue = Queue.Queue()
        self.max_simultaneous_threads = max_simultaneous_threads
        self.executing_threads = 0
        self._threads_executed = []

    def add_thread(self, thread):
        return self.thread_queue.put(thread)

    def set_max_simultaneous_threads(self, max_simultaneous_threads):
        self.max_simultaneous_threads = max_simultaneous_threads

    def execute_last_thread(self):
        if self.executing_threads >= self.max_simultaneous_threads:
            return False

        thread = self.thread_queue.get_nowait()
        self._threads_executed.append(thread)
        self._threads_executed[-1].start()
        self.executing_threads += 1
        return True

    def execute_threads(self):
        if self.max_simultaneous_threads == 0:
            while True:
                try:
                    self.thread_queue.get().start()

                except Queue.Empty:
                    return

            return

        while True:
            try:
                if self.execute_last_thread():
                    thread = self._threads_executed[-1]
                    threading.Thread(name="Temporary internal TJT", target=self._join_thread, args=(thread,)).start()

                if self.executing_threads < 1:
                    return True

                else:
                    time.sleep(0.05)

            except Queue.Empty:
                return True

    def _join_thread(self, thread):
        thread.join()
        self.executing_threads -= 1


def regex(value, reg):
    if reg == "":
        return True

    return bool(re.search(reg, value))


def ends_with_any(string, list_of_endings):
    for ending in list_of_endings:
        if string.endswith(ending):
            return True

    return False


def fetch_from_url(link_url, regex_filter, crawl_filter, max_level=5, this_level=0):
    if max_level < 1 or max_level < this_level:
        print "|" + ("-" * this_level) + "Bug: Max level reached in this URL iteration and function called anyways!"
        return []

    images = []
    request = requests.get(link_url)

    if request.status_code != 200:
        print "|" + ("-" * this_level) + "Status code {} received! Leaving this crawl.".format(request.status_code)
        return []

    soup = BeautifulSoup.BeautifulSoup(request.text)
    print "|" + ("-" * this_level) + "Fetching images at {}!".format(link_url)

    for image in soup.findAll("img", {"src": True}):
        print "|" + ("-" * this_level) + "Trying image {}!".format(urlparse.urljoin(link_url, image["src"]))
        if not regex(urlparse.urljoin(link_url, image["src"]), regex_filter):
            print "|" + ("-" * this_level) + "Image's path does not match with the regex {}!".format(regex_filter)
            continue

        print "|" + ("-" * this_level) + "Appending image at {}!".format(urlparse.urljoin(link_url, image["src"]))
        images.append(urlparse.urljoin(link_url, image["src"]))

    if max_level > 0:
        for link in soup.findAll("a", {"href": True}):
            if ends_with_any(urlparse.urljoin(link_url, link["href"]).lower(),
                             ("png", "jpeg", "jpg", "tga", "gif", "bmp", "jpng")):
                print "|" + ("-" * this_level) + "Got image from sudden link {}!".format(
                    urlparse.urljoin(link_url, link["href"]))

                if not regex(urlparse.urljoin(link_url, link["href"]), regex_filter):
                    print "|" + ("-" * this_level) + "Image's path does not match with the regex {}!".format(
                        regex_filter)
                    continue

                images.append(urlparse.urljoin(link_url, link["href"]))

                continue

            print "|" + ("-" * this_level) + "Crawling to {}!".format(urlparse.urljoin(link_url, link["href"]))

            if regex(urlparse.urljoin(link_url, link["href"]), crawl_filter):
                images += fetch_from_url(
                    urlparse.urljoin(link_url, link["href"]),
                    regex_filter,
                    crawl_filter,
                    max_level - 1,
                    this_level + 1
                )

                continue

            print "|" + ("-" * this_level) + "Crawling path does not match with the regex {}!".format(crawl_filter)

    return images


def download(url, result_file, rewrite_file=False):
    print "Downloading from {} into {}!".format(url, result_file)

    if os.path.exists(result_file) and not rewrite_file:
        print "File already exists!"
        return False

    urllib.urlretrieve(url, result_file)
    print "Download from {} succesful! File available at {}.".format(url, result_file)
    return True


if __name__ != "__main__":
    exit()

parsed = json.load(open("texlibs.json"))

downloads = MultiThreadQueue(parsed[1])

for image_kind_or_folder, (url, regex_filter, crawl_filter, max_level) in parsed[0].items():
    if not os.path.exists(os.path.join("../result", image_kind_or_folder)):
        os.makedirs(os.path.join("../result", image_kind_or_folder))

    print "Looking for images in specified URL!"

    for image in fetch_from_url(url, regex_filter, crawl_filter, max_level):
        result_path = "../{}/{}".format(os.path.join("result", image_kind_or_folder), ntpath.basename(image))

        downloads.add_thread(
            threading.Thread(
                name="Download \'{} -> {}\' Thread".format(image, result_path),
                target=download,
                args=(image, result_path)
            )
        )

print "Downloading all appended images!"

downloads.execute_threads()
