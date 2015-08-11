# -*- coding: utf-8 -*-
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
                parse_cols = 'A:S',
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

                       u'file_id',          u'fig_no',           u'title',
                      u'subtitle',   u'draft_page_no',       u'footnotes',       u'caption',
                           u'mkd',       u'hovermode',         u'y_label',
                       u'x_label',      u'plot_width',     u'plot_height',
                        u'ref_no',    u'source_label',     u'source_link',
               u'source_accessed', u'isabel_comments', u'vivian_comments'

    Usage:

        rec = FigureProperties(2)
        print(rec.subtitle)  # -> 'Subtitle of Fig 2'
        print(rec.no_such_field)  # -> KeyError
        
    """

    def __init__(self, notebook, settings=SETTINGS):
        self._settings = settings
        self._data = self._read_excel()  # dataframe of ALL plots
        self.rec = self._focus_on(notebook)

    def __getattr__(self, attr):
        try:
            return self.rec[attr].iloc[0]
        except:
            error = 'Plot has no attribute called {}. Try one of these instead: {}'
            error = error.format(attr, ', '.join(self.rec.columns))
            raise KeyError(error)

    def __getitem__(self, attr):
        try:
            return self.rec[attr].iloc[0]
        except:
            error = 'Plot has no attribute called {}. Try one of these instead: {}'
            error = error.format(attr, ', '.join(self.rec.columns))
            raise KeyError(error)
        
    def _focus_on(self, notebook):
        # Ensure notebook is can be converted to integer
        try:
            notebook = int(notebook)
        except:
            error = 'Invalid notebook id: {} (must be integer)'
            raise KeyError(error.format(notebook))
        
        rec = self._data.ix[self._data.notebook == notebook]
        if rec.empty:
            error = 'Invalid notebook id: {} (not found in database)'
            raise KeyError(error.format(notebook))
        else:
            return rec

    def _read_excel(self):
        try:
            DF = pd.read_excel(self._settings['raw_file'],
                               sheetname=self._settings['sheet'],
                               parse_cols=self._settings['parse_cols'],
                               skiprows=self._settings['skiprows'],
                               skip_footer=self._settings['skip_footer']
                               )
            DF = DF.fillna('')
            return DF
        except IOError:
            raise IOError('Could not open the Excel sheet from data directory.')


class PlotRecord(object):

    TEMPLATE_DIR = os.path.join('.', 'tpl')
    PAGES = os.path.join('.', 'tpl', 'pages.pkl')
    STATIC = os.path.join('..')

    def __init__(self, var_list):
        
        self.specs = {}

        keys = ['fig', 'DF', 'filename']
        for key in keys:
            self.specs[key] = var_list.get(key, None)

        # retrieve the values of the basic set of keys
        props = var_list['props']
        keys = ['fig_no', 'title', 'subtitle', 'x_label', 'y_label',
                'plot_height', 'plot_width', 'footnotes', 'caption',
                'source_label', 'source_link', 'source_accessed', 'ref_no']
        for key in keys:
            val = props[key]
            if isinstance(val, unicode) and val in ['NNN', '']:
                val = None
            self.specs[key] = val

        # Check for MKD in the DataFrame and adjust the footnotes accordingly
        mkd_note = self._check_mkd_footnote()
        if mkd_note:
            if self.specs['footnotes']:
                self.specs['footnotes'] += '\n' + mkd_note
            else:
                self.specs['footnotes'] = mkd_note
        if self.specs['footnotes']:
            self.specs['footnotes'] = '\n<br>'.join(self.specs['footnotes'].split('\n'))

        # retrieve the plotly record for the graph and the thumbnail
        self.specs['record'] = self._get_fig_record(var_list['filename'])
        url = self.specs['record']['image_urls']['block-thumb']
        src = '<img src="{}" alt="{}">'.format(url, self.specs['title'])
        self.specs['thumb'] = src

        # construct the url to the SVG file and get embed url
        plotly_id = self.specs['record']['fid'].split(':')[1]
        url_svg = 'https://plot.ly/~gauden/{}.svg'.format(plotly_id)
        self.specs['url_svg'] = url_svg

        url_embed = self.specs['record']['embed_url']
        self.specs['url_embed'] = url_embed

        # Get timestamp for current update (UTC time)
        d = delorean.Delorean()
        self.specs['time_epoch'] = d.epoch()
        self.specs['time_human'] = d.datetime.strftime('%a, %d %b %Y %H:%M:%S %Z')

        self.tpl_env = self._get_template_env()


    def _check_mkd_footnote(self):
        mkd_note = '¶ The former Yugoslav Republic of Macedonia ' + \
                   '(MKD is an abbreviation of the ISO).'
        fields = self.specs['DF'].columns
        for field in fields:
            try:
                if self.specs['DF'][field].str.contains('MKD ¶').any():
                    return mkd_note
            except AttributeError:
                pass
        return ''


    def _get_template_env(self):
        def _template_elim_none(val):
            if val:
                return val
            else:
                return'<strong>Value not found. Please double-check (a blank value may be valid).</strong>'

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
        self._save_dataset()
        return True

    def _save_dataset(self):
        data = self.specs['DF']
        fig_no = self.specs['fig_no']
        datasets_dir = os.path.join('data', 'datasets')

        xlsx_path = os.path.join(datasets_dir, 'dataset_{}.xlsx'.format(fig_no))
        data.to_excel(excel_writer=xlsx_path, 
                      sheet_name='fig_{}'.format(self.specs['fig_no']))

        csv_path = os.path.join(datasets_dir, 'dataset_{}.csv'.format(fig_no))
        data.to_csv(csv_path, encoding='utf-8')

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
        page = page.encode('utf-8')
        with open(path, 'w') as fh:
            fh.write(page)

    def _pickle_load_pages(self):
        with open(self.PAGES, 'r') as pkl_handle:
            pgs = pickle.load(pkl_handle)
        return pgs

    def _pickle_dump_pages(self, pages):
        with open(self.PAGES, 'w') as pkl_handle:
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
            if key == 'footnotes':
                # TDOD skip footnotes as for some reason causing UnicodeDecodeError
                continue
            output += row.format(key, val)
        return output


if __name__ == '__main__':
    rec = FigureProperties(2)
    print(rec.title)
    print(rec.subtitle)
    print(rec.millipede)
