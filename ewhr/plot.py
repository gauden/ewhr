from __future__ import (absolute_import, print_function,
                        division, unicode_literals)

import os
import json
from pprint import pprint, pformat
import cPickle as pickle

import requests
from pandas import DataFrame
from jinja2 import Environment, ChoiceLoader, FileSystemLoader

import delorean

class PlotRecord(object):

    TEMPLATE_DIR = os.path.join('.', 'tpl')
    PAGES = os.path.join('.', 'tpl', 'pages.pkl')
    STATIC = os.path.join('..')

    def __init__(self, var_list):
        self.specs = {}

        # retrieve the values of the basic set of keys
        keys = ['title', 'subtitle',
                'X_LABEL', 'Y_LABEL', 'fig',
                'DF', 'filename',
                'plot_height', 'plot_width',
                'footnotes', 'caption']
        for key in keys:
            val = var_list.get(key, None)
            if isinstance(val, unicode) and val in ['NNN', '']:
                val = None
            self.specs[key] = val

        # retrieve and flatten the values of the source dict
        for key, val in var_list['source'].iteritems():
            new_key = 'source_{}'.format(key)
            if val in ['NNN', '']:
                val = None
            self.specs[new_key] = val

        # retrieve the plotly record for the graph and the thumbnail
        self.specs['record'] = self._get_fig_record(var_list['filename'])
        url = self.specs['record']['image_urls']['block-thumb']
        src = '<img src="{}" alt="{}">'.format(url, self.specs['title'])
        self.specs['thumb'] = src

        # construct the url to the SVG file and get embed url
        fid = self.specs['record']['fid'].split(':')[1]
        url_svg = 'https://plot.ly/~gauden/{}.svg'.format(fid)
        self.specs['url_svg'] = url_svg

        url_embed = self.specs['record']['embed_url']
        self.specs['url_embed'] = url_embed

        # construct the figure number from filename ('vaw/fig_18' -> 'fig_18')
        self.specs['fig_no'] = self.specs['filename'][8:]

        # Get timestamp for current update (UTC time)
        d = delorean.Delorean()
        self.specs['time_epoch'] = d.epoch()
        self.specs['time_human'] = d.datetime.strftime('%a, %d %b %Y %H:%M:%S %Z')

        self.tpl_env = self._get_template_env()


    def _get_template_env(self):
        def _template_elim_none(val):
            if val:
                return val
            else:
                return'<strong>Value not found. Check.</strong>'

        env = Environment(loader=ChoiceLoader([FileSystemLoader('tpl')]),
                          finalize=_template_elim_none)
        return env


    def make_pages(self):
        # Update the list of pages (in order to construct menu etc)
        # -- the list of pages is a pickled dict held in templates directory
        #    with keys = self.specs['filename'] and vals = self.specs 
        try:
            pages = self._pickle_load_pages()
        except IOError:
            pages = {}
        
        pages[self.specs['fig_no']] = self.specs
        self._pickle_dump_pages(pages)

        self._rebuild_all_pages(pages)
        return True

    def _rebuild_all_pages(self, pages):
        for fig_no, specs in pages.iteritems():
            title=self._get_long_title(specs)
            # Construct the menu
            menu_plot = self.tpl_env.get_template('menu_with_dropdown.html')
            menu = menu_plot.render(specs=specs,
                                    pages=pages,
                                    keys=sorted(pages.keys()),
                                    title=title,
                                    current_fig=fig_no)
            # Construct the full page
            tpl_plot = self.tpl_env.get_template('plot.html')
            plot_page = tpl_plot.render(specs=specs,
                                        pages=pages,
                                        title=title,
                                        menu=menu)

            # Update the home page

            # Construct url 
            fn = 'fig_{}.html'.format(fig_no)
            pathname = os.path.join(self.STATIC, fn)
            self._save_page(pathname, plot_page)


    def _get_long_title(self, specs):
        title = '{}: {}'.format(specs['fig_no'], 
                                specs['title'])
        return title


    def _save_page(self, path, page):
        with open(path, 'wb') as fh:
            fh.write(page)

    def _pickle_load_pages(self):
        with open(self.PAGES, 'rb') as pkl_handle:
            pgs = pickle.load(pkl_handle)
        return pgs

    def _pickle_dump_pages(self, pages):
        with open(self.PAGES, 'wb') as pkl_handle:
            pickle.dump(pages, pkl_handle)

    def _get_fig_record(self, path):
        url = 'https://api.plot.ly/v2/files/lookup?user=gauden&path={}'
        url = url.format(path)
        r = requests.get(url)
        if r.status_code == requests.codes.ok:
            record = json.loads(r.content)
            return record
        else:
            tpl = 'Could not retrieve file {}. Status code: {}'
            msg = tpl.format(path, r.status_code)
            raise IOError(msg)

    def _repr_html_(self):
        error = '<strong>Value not found. Check.</strong>'
        output = '<table>\n'
        for key in sorted(self.specs.keys()):
            row = '<tr><td>{}:</td><td>{}</td></tr>\n'
            val = self.specs[key]
            if isinstance(val, DataFrame) or isinstance(val, dict):
                val = '<pre>{}</pre>'.format(pformat(val))
            elif val == None:
                val = error
            output += row.format(key, val)
        output += '</table>\n'
        return output

    def __str__(self):
        error = 'Value not found. CHECK!'
        output = ''
        for key in sorted(self.specs.keys()):
            row = '{}: {}\n'
            val = self.specs.get(key, error)
            if not isinstance(val, unicode):
                val = type(val)
            output += row.format(key, val)
        return output

