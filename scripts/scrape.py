import csv
import os.path as osp
import random
import time
import re

from bs4 import BeautifulSoup
import pandas as pd
import requests
from tqdm import tqdm


def scrape_mal_ids(start=0, stop=24200, out_fn='mal_links.txt'):
    """Gets URLs for the main page of every anime on MAL by going to Anime ->
    Anime Search -> Just Added, which gives a full list sorted by descending ids.
    ``stop`` should be (current last page x 50) or slightly bigger (extras are ignored).
    ``out_fn`` should be a full path to a .txt file where the results will be saved.
    """
    base = 'https://myanimelist.net/anime.php?o=9&cv=2&w=1&show='
    links = [base + str(k) for k in range(start, stop, 50)]
    data = _scrape(links, _parse_mal_ids)
    with open(out_fn, 'a') as f:
        for d in data[::-1]:
            f.write(d + '\n')

def _parse_mal_ids(soup, url, data):
    for t in soup.find_all('div', class_='title'):
         data.append(t.find('a')['href'])
    return data
    
    
def scrape_mal_ids_special(out_fn='mal_ids_excl.txt'):
    stop_hentai = 2000
    stop_agarde = 1000
    base = 'https://myanimelist.net/anime.php?o=9&cv=2&w=1&%s&show='
    base_hentai = base % 'r=6'
    base_agarde = base % 'genre%5B%5D=5'
    links_h = [base_hentai + str(k) for k in range(0, stop_hentai, 50)]
    links_a = [base_agarde + str(k) for k in range(0, stop_agarde, 50)]
    data1 = _scrape(links_h, _parse_mal_ids_special)
    data2 = _scrape(links_a, _parse_mal_ids_special)
    with open(out_fn, 'a') as f:
        f.write('Hentai: ' + ' '.join(data1[::-1]) + '\n')
        f.write('Avant-garde: ' + ' '.join(data2[::-1]) + '\n')

def _parse_mal_ids_special(soup, url, data):
    for t in soup.find_all('div', class_='title'):
         data.append(t.find('a')['href'].split('/')[-2])
    return data


def scrape_mal_pics(start=0, stop=None, in_fn='mal_links.txt', out_fn='mal_pics.txt'):
    """Gets URLs of pics for every anime from links obtained earlier with scrape_mal_ids.
    The format for an image link on MAL is always without fail:
    https://cdn.myanimelist.net/images/anime/<number_1>/<number_2>l.jpg
    so it keeps only those two numbers, and save results as '<mal_id>: <n1/n2> <n1/n2> ...'
    """
    with open(in_fn) as f:
        links = f.read().splitlines()[start:stop]
    links = [link + '/pics' for link in links]
    data = _scrape(links, _parse_mal_pics)
    with open(out_fn, 'a') as f:
        for d in data:
            f.write(d['id'] + ': ' + ' '.join(d['pics']) + '\n')

def _parse_mal_pics(soup, url, data):
    pattern_malid = '(?:https\:\/\/myanimelist\.net\/anime\/)([0-9]+)(?:.+\/pics)'
    pattern_image = '(?:https\:\/\/cdn\.myanimelist\.net\/images\/anime\/)([0-9]+\/[0-9]+)(?:l\.jpg)'
    al = soup.find_all('a', rel='gallery-anime')
    pics = [re.search(pattern_image, a['href']).groups()[0] for a in al]
    malid = re.search(pattern_malid, url).groups()[0]
    data.append({'id': malid, 'pics': pics})
    return data


def scrape_wa_anime_main(start=1, stop=11660, out_fn='wa_anime_main.csv'):
    base = 'http://www.world-art.ru/animation/animation.php?id='
    links = [base + str(k) for k in range(start, stop)]
    data = _scrape(links, _parse_wa_anime_main)
    pd.DataFrame(data).to_csv(out_fn, index=False, quoting=csv.QUOTE_NONNUMERIC)

def _parse_wa_anime_main(soup, url, data):
    res = {}
    res['wa_id'] = int(url.split('=')[-1])
    t1 = soup.find('a', string='mal')
    t2 = soup.find('td', string='Тип')
    t3 = soup.find('td', string='Жанр')
    t4 = soup.find('td', string=['Премьера', 'Выпуск'])
    t5 = soup.find('td', string='Средний балл')
    t6 = soup.find('a', href='rating_top.php')
    res['mal_id']    = '' if (t1 is None) else int([p for p in t1['href'].split('/') if p][-1])
    res['title']     = soup.find('meta', attrs={'name':'Title'})['content']
    res['work_type'] = '' if (t2 is None) else t2.parent.findChildren()[-1].text
    res['genre']     = '' if (t3 is None) else t3.parent.text[4:]
    res['release']   = '' if (t4 is None) else t4.parent.findChildren(recursive=False)[-1].text.strip()
    res['score']     = '' if (t5 is None) else float(t5.parent.text[12:].split(u'\xa0')[0])
    res['top_place'] = '' if (t6 is None) else int(t6.parent.parent.parent.findChildren(recursive=False)[-1].text.split(' ')[0])
    data.append(res)
    return data


def scrape_wa_anime_posters(start=0, stop=None, in_fn='wa_anime_main.csv', out_fn='wa_anime_posters.txt'):
    with open(in_fn, encoding='utf8') as f:
        ids = [ln.split(',')[0] for ln in f.read().splitlines()[1:][start:stop]]
    base = 'http://www.world-art.ru/animation/animation_poster.php?id='
    links = [base + k for k in ids]
    data = _scrape(links, _parse_wa_anime_posters)
    with open(out_fn, 'a') as f:
        for d in data:
            f.write(str(d['id']) + ': ' + ' '.join([str(x) for x in d['pics']]) + '\n')

def _parse_wa_anime_posters(soup, url, data):
    anid = int(url.split('=')[-1])
    al = soup.find_all('a', href=lambda x: x.startswith('animation_poster.php'))
    img_nums = [int(a['href'].split('=')[-1]) for a in al]
    data.append({'id': anid, 'pics': img_nums})
    return data


def _scrape(links, parse_func):
    """Base function for downloading a bunch of similar HTML pages and scraping them with the
    provided parse_func. A random 1-4 sec delay is added between requests, and every fail (by
    HTTP response or by an exception during parsing) is caught to not interrupt the process.
    """
    data, fails = [], []
    for url in tqdm(links):
        try:
            page = requests.get(url)
            assert page.status_code == 200, 'RET %s' % page.status_code
            soup = BeautifulSoup(page.content, 'html.parser')
            data = parse_func(soup, url, data)
        except Exception as e:
            fails.append((url, str(e)))
        time.sleep(random.uniform(1, 4))
    if fails:
        print(fails)
    return data


def download_images(folder, site, inptxt, start=0, stop=None):
    assert site in ['WA', 'MAL']
    with open(inptxt) as f:
        lines = f.read().splitlines()
    ids = []
    for line in lines:
        anime_id, image_ids = line.split(':')
        for image_id in image_ids.split(' '):
            if image_id:
                ids.append((anime_id, image_id))
    fails = []
    for anid, imid in tqdm(ids[start:stop]):
        if site == 'MAL':
            url = 'https://cdn.myanimelist.net/images/anime/' + imid + 'l.jpg'
            fn = 'MAL%05d_%04d_%06d.jpg' % (int(anid), *[int(x) for x in imid.split('/')])
        else:
            bucket = ((int(anid) // 1000) + 1) * 1000
            url = 'http://www.world-art.ru/animation/img/%s/%s/%s.jpg' % (str(bucket), anid, imid)
            fn = 'WA%05d_%03d.jpg' % (int(anid), int(imid))
        ret = requests.get(url)
        if ret.status_code != 200:
            fails.append((anid, imid, url, ret.status_code))
        else:
            with open(osp.join(folder, fn), 'wb') as f:
                f.write(ret.content)
        time.sleep(random.uniform(1, 4))
    if fails:
        print(fails)