import json
from pprint import pprint, pformat
import requests

class PlotRecord(object):

    def __init__(self, var_list):
        keys = ['title', 'subtitle', 'source',
                'X_LABEL', 'Y_LABEL', 'fig',
                'DF', 'filename',
                'plot_height', 'plot_width']
        self.specs = {}
        for key in keys:
            self.specs[key] = var_list.get(key, None)
        self.specs['record'] = self._get_fig_record(var_list['filename'])

    def _get_fig_record(self, path):
        url = 'https://api.plot.ly/v2/files/lookup?user=gauden&path={}'
        url = url.format(path)
        r = requests.get(url)
        if r.status_code == requests.codes.ok:
            record = json.loads(r.content)
            return record
        else:
            _ = 'Could not retrieve file {}. Status code: {}'
            msg = _.format(path, r.status_code)
            raise IOError(msg)

    def _repr_html_(self):
        error = '<strong>Value not found. Check.</strong>'
        output = '<table>\n'
        for key in sorted(self.specs.keys()):
            row = '<tr><td>{}:</td><td>{}</td></tr>\n'
            val = self.specs.get(key, error)
            if not isinstance(val, unicode):
                val = '<pre>{}</pre>'.format(pformat(val))
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
