
# coding: utf-8

from __future__ import unicode_literals, print_function, division

import os

import pandas as pd

SETTINGS = dict(raw_file = os.path.join('.', 'data', 'list_of_tables_for_summary.xlsx'),
                sheet = 'Sheet1',
                parse_cols = 'A:L',
                skiprows = 0,
                skip_footer = 4
                )


class FigureProperties(object):
    def __init__(self, fid, settings=SETTINGS):
        self.settings = settings
        self.data = self._read_excel()  # dataframe of ALL plots
        self.rec = self._focus_on(fid)  # props of ONLY plot identified by fid

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
        
        rec = self.data.ix[self.data.fig_id == fid]
        if rec.empty:
            error = 'Invalid figure ID: {} (not found in database)'
            raise KeyError(error.format(fid))
        else:
            return rec

    def _read_excel(self):
        try:
            DF = pd.read_excel(self.settings['raw_file'],
                               sheetname=self.settings['sheet'],
                               parse_cols=self.settings['parse_cols'],
                               skiprows=self.settings['skiprows'],
                               skip_footer=self.settings['skip_footer'])
            DF['fig_no_orig'] = DF.draft_title.str.extract('Figure\s+(\d+\w*)')
            DF['title'] = DF.draft_title.str.extract('Figure\s+\d+\w*\.\s*(.+)')
            DF = DF[[u'fig_id', u'fig_no', u'fig_no_orig', u'title', u'subtitle',
                     u'y_label', u'x_label', u'ref_no',
                     u'source_label', u'source_link', u'source_accessed',
                     u'draft_title', u'draft_page_no', u'note']]
            return DF
        except IOError:
            raise IOError('Could not open the Excel sheet from data directory.')

if __name__ == '__main__':
    rec = FigureProperties(2)
    print(rec.title)
    print(rec.subtitle)
    print(rec.millipede)

