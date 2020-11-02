from anime_downloader.sites import helpers
import json
import os
from tabulate import tabulate
from pySmartDL import SmartDL
import subprocess
import click
import copy
import requests


def isNum(string_):
    try:
        int(string_)
        return True
    except ValueError:
        return False


def search(query):
    results = {}
    link = 'http://hentaigasm.com/'
    html = helpers.get(link, params = {'s': query}).text
    soup = helpers.soupify(html)
    all_results = soup.find_all('div', attrs={'class': lambda e: e.startswith('post-') if e else False})
    for hentai in all_results:
        title = hentai.select_one('h2 > a').text
        clean_title = ' '.join(title.replace(' Subbed', '').replace(' Raw', '').split(' ')[:-1])
        ep_num = title.replace(' Subbed', '').replace(' Raw', '').split(' ')[-1]
        if isNum(ep_num):
            state = '(Sub)' if 'Raw' not in title else '(Raw)'
            sluggy_name = clean_title + '_' + state
            if sluggy_name not in results:
                results[sluggy_name] = {}
                results[sluggy_name]['eps'] = {}
                results[sluggy_name]['title'] = clean_title + ' ' + state
                results[sluggy_name]['state'] = state

            link = hentai.select_one('h2 > a')['href']
            thumbnail = hentai.find('img', src=True)['src']
            results[sluggy_name]['eps'][ep_num] = {
                'url': link,
                'thumb': thumbnail,
                'ep_num': int(ep_num)
                }
    copy_ = {}
    for hentai, val in results.items():
        for ____, ep in results[hentai]['eps'].items():
            if hentai not in copy_:
                copy_[hentai] = copy.deepcopy(results[hentai])
                copy_[hentai]['eps'] = []
            copy_[hentai]['eps'].append(ep)
        copy_[hentai]['eps'] = sorted(copy_[hentai]['eps'], key=lambda a_entry: int(a_entry['ep_num']))
    results = copy.copy(copy_)

    return results


def scrape_database(max_=50):
    results = {}
    base_url = 'http://hentaigasm.com/page/{}/'
    for i in range(1, max_):
        try:
            soup = helpers.soupify(helpers.get(base_url.format(i)).text)
        except Exception:
            continue
        all_hentai = soup.find_all('div', attrs={'class': lambda e: e.startswith('post-') if e else False})

        for hentai in all_hentai:
            title = hentai.select_one('h2 > a').text
            state = '(Sub)' if 'Raw' not in title else '(Raw)'
            clean_title = ' '.join(title.replace(' Subbed', '').replace(' Raw', '').split(' ')[:-1])
            sluggy_name = clean_title + '_' + state

            ep_num = title.replace(' Subbed', '').replace(' Raw', '').split(' ')[-1]
            if isNum(ep_num):
                if sluggy_name not in results:
                    results[sluggy_name] = {}
                    results[sluggy_name]['eps'] = {}
                    results[sluggy_name]['title'] = clean_title + ' ' + state
                    results[sluggy_name]['state'] = state

                link = hentai.select_one('h2 > a')['href']
                thumbnail = hentai.find('img', src=True)['src']
                results[sluggy_name]['eps'][ep_num] = {
                    'url': link,
                    'thumb': thumbnail,
                    'ep_num': ep_num
                    }
    copy_ = {}
    for hentai, val in results.items():
        for ____, ep in results[hentai]['eps'].items():
            if hentai not in copy_:
                copy_[hentai] = copy.deepcopy(results[hentai])
                copy_[hentai]['eps'] = []

            copy_[hentai]['eps'].append(ep)
        copy_[hentai]['eps'] = sorted(copy_[hentai]['eps'], key=lambda a_entry: int(a_entry['ep_num']))
    results = copy.copy(copy_)
    return results


def get_video_link(ep_link):
    soup = helpers.soupify(helpers.get(ep_link).text)
    streaming_link = soup.find('a', download=True, href=True)['href']
    return streaming_link.replace(' ', '%20')


def prepare_download(data, type_, external_downloader, thumb_dl_flag, skip_download, download_dir, stream):

    if type_ == 1:
        eps = data['links']
        for episode in eps:
            filename = '{} - {}.{}'.format(data['title'], episode['ep_num'], 'mp4')
            thumbnail = 'thumbs/{} - {}.{}'.format(data['title'], episode['ep_num'], 'jpg')
            ep_data = {
                'download_url': get_video_link(episode['url']),
                'directory': os.path.join(download_dir, data['title']),
                'filename': filename,
                'downloader': external_downloader,
                'thumb_url': episode['thumb'],
                'thumb_path': os.path.join(download_dir, data['title'], thumbnail)
            }
            downloader(ep_data, thumb_dl_flag, skip_download, stream)
    else:
        for x, y in data.items():
            eps = y['eps']
            for episode in eps:
                filename = '{} - {}.{}'.format(y['title'], episode['ep_num'], 'mp4')
                thumbnail = 'thumbs/{} - {}.{}'.format(y['title'], episode['ep_num'], 'jpg')
                ep_data = {
                    'download_url': get_video_link(episode['url']),
                    'directory': os.path.join(download_dir, y['title']),
                    'filename': filename,
                    'downloader': external_downloader,
                    'thumb_url': episode['thumb'],
                    'thumb_path': os.path.join(download_dir, y['title'], thumbnail)
                }
                downloader(ep_data, thumb_dl_flag, skip_download, stream)

import shutil
def stream(data):
    link = data['link']
    title = data['title']

    executable = 'mpv'
    cmd = [
        executable, '{}'.format(link), '--title={}'.format(title)
    ]
    f = subprocess.call(cmd, shell=True)




def downloader(data, thumb_dl_flag, skip_download, stream_):
    cmd = {
        'aria2': [
            'aria2c', '"' + data['download_url'] + '"', '-x 12 -s 12 -j 12 -k 10M',
            '-o "{}"'.format(data['filename']), '--continue=true',
            '--dir="{}"'.format(data['directory']),
            '--stream-piece-selector=inorder --min-split-size=5M',
            '--check-certificate=false', '--console-log-level=error'
            ]
    }
    if stream_:
        ff = {'link': data['download_url'], 'title': data['filename']}
        stream(ff)
        return
    if not skip_download:
        if data['downloader'] == 'pySmartDL':
            dest = os.path.join(data['directory'], data['filename'])
            obj = SmartDL(data['download_url'], dest, progress_bar=True, verify=False)
            obj.start()
        elif data['downloader'] == 'aria2':
            cmd = ' '.join(cmd[data['downloader']])
            f = subprocess.run(cmd, shell=True)

    if thumb_dl_flag:
        if not os.path.isfile(data['thumb_path']):
            if not os.path.isdir(os.path.join(data['directory'], 'thumbs')):
                os.makedirs(os.path.join(data['directory'], 'thumbs'))
            with open(data['thumb_path'], 'wb') as f:
                ddd = data['filename'].split(' - ')
                click.echo('Downloading thumbnail for episode {} of {}'.format(ddd[1].split('.')[0], ddd[0]))
                f.write(requests.get(data['thumb_url']).content)

def user_input(data):
    headers = ['SlNo', 'Title']
    count = -1
    table1 = []
    dats = []
    for hentai, value in data.items():
        count += 1
        table1.append([count, value['title']])
        dats.append(value['eps'])
    table = tabulate(table1, headers, tablefmt='psql')
    table = '\n'.join(table.split('\n')[::-1])
    click.echo(table)
    choice = input('Enter a number: [0]: ')
    choice = 0 if choice == '' else int(choice)

    return {'links': dats[choice], 'title': table1[choice][1]}

if __name__ == '__main__':
    @click.command()
    @click.option(
        '--search', '-s', 'search_query',
        required=False, default='',
        help='Makes a search using the provided query.',
        metavar='Title'
        )
    @click.option(
        '--download-all', '-da', 'download_all',
        required=False, is_flag=True,
        help='When used it will download all the hentai that hentagasm has, if its used in combination '
        'with --search/-s it will download all the results found using that search term.'
        )
    @click.option(
        '--external-downloader', '-xd', 'external_downloader',
        required=False, default='pySmartDL', type=click.Choice(['aria2', 'pySmartDL']),
        help='Downloads using the provided downloader.'
        )
    @click.option(
        '--download-thumbnails', '-dt', 'thumb_dl_flag',
        required=False, is_flag=True,
        help='When used it also download the thumbnails.'
        )
    @click.option(
        '--skip-download', '-sd', 'skip_download',
        required=False, is_flag=True,
        help='When used it will skip any video downloads.'
        )
    @click.option(
        '--stream',
        required=False, is_flag=True,
        help='When used it will stream instead of downloading.'
        )
    @click.option(
        '--download-dir', '-dd', 'download_dir',
        required=False, type=str,
        help='Download directory.', metavar='DIRECTORY',
        default=os.getcwd()
        )
    def main(search_query, download_all, external_downloader, thumb_dl_flag, skip_download, download_dir, stream):

        if bool(search_query) and bool(download_all):
            data = search(search_query)
            type_ = 'database'

        elif bool(search_query):
            data = search(search_query)
            type_='search'

        elif download_all:
            data = scrape_database()
            type_='database'
        else:
            type_ = None
            data = None
        if not bool(type_) or not bool(data):
            exit()
        elif type_ == 'search':
            prepare_download(user_input(data), 1, external_downloader, thumb_dl_flag, skip_download, download_dir, stream)
        
        else:
            prepare_download(data, 0, external_downloader, thumb_dl_flag, skip_download, download_dir, stream)
    main()
