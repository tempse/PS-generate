import os
import argparse
from typing import Union, Any
import tempfile
import wget
import shutil
import pandas as pd
import xml.etree.ElementTree as ET
from tabulate import tabulate
from decimal import Decimal

from psutils.psio import download_file, read_prescale_table, get_seeds_from_xml, \
        write_prescale_table
from psutils.pstable import find_table_value, make_empty_table


if __name__ == '__main__':

    # define CLI elements
    parser = argparse.ArgumentParser()
    parser.add_argument('PStable',
            help='Existing prescale table (xlsx format)',
            type=str)
    parser.add_argument('NewMenu',
            help='New L1 menu XML',
            type=str)
    parser.add_argument('-output', '--output',
            help='Name of the created output file (w/o file extension)',
            type=str,
            default='new_PStable',
            dest='output')

    args = parser.parse_args()

    # read all data and prepare the output
    PStable_in = read_prescale_table(args.PStable)
    PStable_out = make_empty_table(PStable_in)
    newSeeds, indices = get_seeds_from_xml(args.NewMenu)

    # variable to collect information about the missing PS values
    missing_PSvals = []

    # create new PS table according to the new menu and fill in values from the
    # old PS table, if possible
    for seed,index in zip(newSeeds, indices):
        newData = {}
        for col in PStable_out.columns:
            if col == 'Index':
                newData[col] = index
            elif col == 'Name':
                newData[col] = seed
            else:
                newData[col], exitcode = find_table_value(PStable_in, seed, col)
                if exitcode == 1:  # if the PS value was not found but estimated
                    try:
                        col_pretty = float(col)
                        col_pretty = '{:.2E}'.format(col_pretty)
                    except ValueError:
                        col_pretty = col
                    missing_PSvals.append([index, seed, col_pretty, newData[col]])
                    # missing_PSvals[seed] = {'col': col, 'index': index,
                    #         'value': newData[col]}

        line = pd.DataFrame(newData, index=[index])
        PStable_out = PStable_out.append(line, ignore_index=False, sort=True)

    # remove repeating content for better readability of the printout
    prev_index = -999
    prev_seed = ''
    for tab in missing_PSvals:
        if tab[0] == prev_index:
            tab[0] = ''  # clear index
            tab[1] = ''  # clear seed name
        else:
            prev_index = tab[0]
            prev_seed = tab[1]

    # print information about missing/estimated PS values
    print('\n{}\n   [WARNING] List of missing PS values\n{}\n'.format('#'*50, '#'*50))
    print(tabulate(missing_PSvals, headers=['Index', 'seed name', 'PS column', 'estimated value']))

    PStable_out = PStable_out.sort_index().reset_index(drop=True)

    # sort output table according to the old table column layout
    PStable_out = PStable_out[PStable_in.columns]
    
    # save new table to the disk
    write_prescale_table(PStable_out, filepath=args.output)
