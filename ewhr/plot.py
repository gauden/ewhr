from __future__ import (absolute_import, print_function,
                        division, unicode_literals)

import os
import json
from pprint import pprint, pformat
import cPickle as pickle

import requests
import pandas as pd
from pandas import DataFrame
from jinja2 import Environment, ChoiceLoader, FileSystemLoader

import delorean


SETTINGS = dict(raw_file = os.path.join('.', 'data', 'list_of_tables_for_summary.xlsx'),
                sheet = 'Sheet1',
                parse_cols = 'A:L',
                skiprows = 0,
                skip_footer = 4
                )


class FigureProperties(object):
    """Interface to access the properties for a given plot.

    Params:
    fid: str/int figure id equal to one of the fig_id entries in database
    settings: dict params for pandas read_excel print_function

    On inititalisation, a dataframe `_data` is created by reading an Excel
    worksheet in the pathname defined by `rawfile`. If the `fid` parameter
    points to a valid figure id, then the data for that figure is extracted
    and retained in the instance variable `rec` -- used then as the basis for
    extracting the value of specific properties. Valid property names are:

        u'fig_id', u'fig_no', u'fig_no_orig', u'title', u'subtitle',
        u'y_label', u'x_label', u'ref_no',
        u'source_label', u'source_link', u'source_accessed',
        u'draft_title', u'draft_page_no', u'note'

    Usage:

        rec = FigureProperties(2)
        print(rec.subtitle)  # -> 'Subtitle of Fig 2'
        print(rec.no_such_field)  # -> KeyError
        
    """

    def __init__(self, fid, settings=SETTINGS):
        self._settings = settings
        self._data = self._read_excel()  # dataframe of ALL plots
        self.rec = self._focus_on(fid)

    def __getattr__(self, attr):
        try:
            return self.rec[attr].iloc[0]
        except:
            error = 'Plot has no attribute called {}. Try one of these instead: {}'
            error = error.format(attr, ', '.join(self.rec.columns))
            raise KeyError(error)
        
    def _focus_on(self, fid):
        # Ensure fid is can be converted to integer
        try:
            fid = int(fid)
        except:
            error = 'Invalid figure ID: {} (must be integer)'
            raise KeyError(error.format(fid))
        
        rec = self._data.ix[self._data.fig_id == fid]
        if rec.empty:
            error = 'Invalid figure ID: {} (not found in database)'
            raise KeyError(error.format(fid))
        else:
            return rec

    def _read_excel(self):
        try:
            DF = pd.read_excel(self._settings['raw_file'],
                               sheetname=self._settings['sheet'],
                               parse_cols=self._settings['parse_cols'],
                               skiprows=self._settings['skiprows'],
                               skip_footer=self._settings['skip_footer'])
            DF['fig_no_orig'] = DF.draft_title.str.extract('Figure\s+(\d+\w*)')
            DF['title'] = DF.draft_title.str.extract('Figure\s+\d+\w*\.\s*(.+)')
            DF = DF[[u'fig_id', u'fig_no', u'fig_no_orig', u'title', u'subtitle',
                     u'y_label', u'x_label', u'ref_no',
                     u'source_label', u'source_link', u'source_accessed',
                     u'draft_title', u'draft_page_no', u'note']]
            return DF
        except IOError:
            raise IOError('Could not open the Excel sheet from data directory.')

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
            menu = menu_plot.render(pages=pages,
                                    keys=sorted(pages.keys()),
                                    title=title,
                                    current_fig=fig_no)
            # Construct the full page
            tpl_plot = self.tpl_env.get_template('plot.html')
            plot_page = tpl_plot.render(specs=specs,
                                        pages=pages,
                                        title=title,
                                        menu=menu)

            # Construct url 
            fn = 'fig_{}.html'.format(fig_no)
            pathname = os.path.join(self.STATIC, fn)
            self._save_page(pathname, plot_page)

            # Update the home page
            self._build_home(pages)

    def _build_home(self, pages):
        title = 'EWHR Graphics'
        keys = sorted(pages.keys())
        # Construct the home menu
        menu_plot = self.tpl_env.get_template('menu_with_dropdown.html')
        menu = menu_plot.render(pages=pages,
                                keys=keys,
                                title=title,
                                current_fig='00')
        # Construct the Home Page
        home_tpl = self.tpl_env.get_template('home.html')
        home = home_tpl.render(pages=pages,
                               keys=keys,
                               title=title,
                               menu=menu)
        pathname = os.path.join(self.STATIC, 'index.html')
        self._save_page(pathname, home)

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


if __name__ == '__main__':
    rec = FigureProperties(2)
    print(rec.title)
    print(rec.subtitle)
    print(rec.millipede)
