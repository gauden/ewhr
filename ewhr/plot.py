import json
from pprint import pprint, pformat
import requests
from pandas import DataFrame

class PlotRecord(object):

    def __init__(self, var_list):
        self.specs = {}

        # retrieve the values of the basic set of keys
        keys = ['title', 'subtitle',
                'X_LABEL', 'Y_LABEL', 'fig',
                'DF', 'filename',
                'plot_height', 'plot_width',
                'footnotes', 'caption']
        for key in keys:
            self.specs[key] = var_list.get(key, None)

        # retrieve and flatten the values of the source dict
        for key, val in var_list['source'].iteritems():
            new_key = 'source_{}'.format(key)
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
            val = self.specs.get(key, error)
            if isinstance(val, unicode) and val in ['NNN', '']:
                val = error
            elif isinstance(val, DataFrame) or isinstance(val, dict):
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
