# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, division
import pandas as pd

FEMALE_FILL = '#f4a582'
FEMALE_LINE = '#ca0020'
FEMALE_SYMBOL = 'circle'

MALE_FILL = '#92c5de'
MALE_LINE = '#0571b0'
MALE_SYMBOL = 'square'

NEUTRAL_FILL = '#986FB6'
NEUTRAL_LINE = '#602c85'
NEUTRAL_SYMBOL = 'diamond'

BREW_SEQ_FEM_1 = '#fee0d2'
BREW_SEQ_FEM_2 = '#fc9272'
BREW_SEQ_FEM_3 = '#de2d26'

BREW_DIV_1 = '#d7191c'
BREW_DIV_2 = '#fdae61'
BREW_DIV_3 = '#ffffbf'
BREW_DIV_4 = '#a6d96a'
BREW_DIV_5 = '#1a9641'

GREY_GRIDLINE = '#bbbbbb'

PLOT_HEIGHT = 1000
PLOT_WIDTH = 800


def clean_ms(df, field):
    # Remove rows with EU27
    for pattern in ['^EU27',]:
        df = df[ ~df[field].str.contains(pattern)]
    return df

def clean_mkd(df, field):
    # Standardise country label for MKD
    for pattern in ['^MKD','^TFYR']:
        df.loc[df[field].str.contains(pattern),field] = 'MKD ¶'
    return df

def check_mkd(df, field):
    footnote = '¶ The former Yugoslav Republic of Macedonia ' + \
               '(MKD is an abbreviation of the ISO).'
    if df[field].str.contains('MKD ¶').any():
        return footnote
    else:
        return ''
