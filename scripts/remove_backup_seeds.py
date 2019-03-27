import os
from typing import Union
import argparse
import csv
import re
import pandas as pd
from tabulate import tabulate


def read_table(filepath: str) -> pd.DataFrame:
    """
    Reads an existing prescale table file from a local path.

    Parameters
    ----------
    filepath : str
        Local path of the input file

    Returns
    -------
    pandas.DataFrame
        Imported prescale table as a DataFrame

    """

    if not os.path.exists(filepath):
        raise RuntimeError('Error opening the file {}'.format(filepath))

    table = pd.DataFrame()

    if filepath.endswith('.csv'):
        with open(filepath, 'r') as csv_table:
            table = pd.read_csv(filepath, sep=None, header=0, engine='python')

    else:
        raise RuntimeError('Unsupported input file format')

    return table


def get_PS_col_idx(table: pd.DataFrame) -> int:
    """
    Find and return the index of the prescale column in a PS table.

    Parameters
    ----------
    table : pandas.DataFrame
        PS table from which the prescale column index should be determined

    Returns
    -------
    int
        The index of the identified prescale column.

    """

    identifiers = ['prescale','ps']
    ps_header_bool = [col.lower() in identifiers for col in table.columns.values]

    # make sure the PS column naming is unique
    if (ps_header_bool).count(True) != 1:
        raise RuntimeError('None or more than one prescale columns '
                'identified - check the table column names')

    return ps_header_bool.index(True)


def get_name_col_idx(table: pd.DataFrame) -> int:
    """
    Find and return the index of the seed name colum in a prescale table.

    The seed name column is determined to be the columns with the most
    occurrences of the string pattern "L1_*".

    Parameters
    ----------
    table : pandas.DataFrame
        PS table from which the prescale column index should be determined

    Returns
    -------
    int
        The index of the identified seed name column.

    """

    cnt_L1occurences = [0 for col in table.columns.values]
    for __,row in table.iterrows():
        for idx,col in enumerate(table.columns.values):
            if type(row[col]) == str and  row[col].startswith('L1_'):
                cnt_L1occurences[idx] += 1

    if all([col == 0 for col in cnt_L1occurences]):
        raise RuntimeError('Error identifying the seed name column - make sure '
                'that the seed names start with \'L1_\'')

    return cnt_L1occurences.index(max(cnt_L1occurences))


def get_all_seed_basenames(seeds: list) -> list:
    # TODO add docstring

    basenames = []

    for seed in seeds:
        if type(seed) != str:
            print('Invalid type: {} ({})'.format(seed,type(seed)))
            continue
        if not seed.startswith('L1_'):
            print('Invalid seed: {}'.format(seed))
            continue

        temp_basename = seed.replace('L1_','')
        temp_basename = temp_basename.split('_')[0]  # only keep until first "_"
        digits = re.search('\d', temp_basename)
        if digits: temp_basename = temp_basename[0:digits.start()]

        if temp_basename not in basenames: basenames.append('L1_'+temp_basename)

    return basenames


def get_seed_basename(seed: str) -> str:
    # TODO add docstring

    if not seed.startswith('L1_'):
        return None

    basename = seed.replace('L1_','')  # temporarily remove this prefix
    basename = basename.split('_')[0]  # strip the part after the first "_"
    digits = re.search('\d', basename)
    if digits: basename = basename[0:digits.start()]  # keep until first digit

    return 'L1_'+basename


def convert_to_float(val: str) -> Union[float,None]:
    """
    Takes a string and tries to convert it to a float.

    Parameters
    ----------
    val : str
        String holding the float number, examples of allowed format are '1.2'
        and '1p2'.

    Returns
    -------
    float, None
        The converted number as a float, None if the conversion was unsuccessful

    """

    return_val = None

    if val is None: return return_val

    val = val.replace('_','')  # just to be sure
    if 'p' in val: val = val.replace('p','.')
    try:
        return_val = float(val)
    except ValueError:
        pass

    return return_val



def separate_signal_and_backup_seeds(table: pd.DataFrame,
        check_prescales : bool = True, keep_zero_prescales : bool = False,
        write_mode : str ='inclusive', force_backup_seeds : list = None,
        verbose : bool = True) -> (pd.DataFrame,
                pd.DataFrame):
    # TODO add docstring

    allowed_modes = ['inclusive','unprescaled','prescaled']
    if ([m == write_mode for m in allowed_modes]).count(True) != 1:
        raise RuntimeError('Expect exactly one of the following modes: {} '
                '(got {})'.format(', '.join(allowed_modes), write_mode))

    signal_seeds = pd.DataFrame(columns=table.columns)
    backup_seeds = pd.DataFrame(columns=table.columns)

    signal_seeds.set_index(table.columns[0], inplace=True)
    backup_seeds.set_index(table.columns[0], inplace=True)

    backup_seeds_info = []

    name_col_idx = get_name_col_idx(table)
    PS_col_idx = get_PS_col_idx(table)

    for idx,row in table.iterrows():
        seed = row[name_col_idx]
        prescale = row[PS_col_idx]

        if type(seed) != str: continue
        if not seed.startswith('L1_'): continue

        if write_mode == 'unprescaled' and prescale != 1:
            continue  # write only unprescaled seeds
            
        elif write_mode == 'prescaled' and prescale <= 1:
            continue  # write only prescaled seeds

        elif write_mode == 'inclusive':
            pass  # write all seeds

        # ignore seeds that don't add to the total rate
        if not keep_zero_prescales and prescale == 0: continue

        if seed in force_backup_seeds:
            is_backup_seed = True
            identified_signal_seeds = []

        if seed not in force_backup_seeds:
            is_backup_seed, identified_signal_seeds, criteria = has_signal_seed(
                    seed, prescale, table.iloc[:,name_col_idx].tolist(),
                    table.iloc[:,PS_col_idx].tolist(),
                    check_prescales=check_prescales,
                    keep_zero_prescales=keep_zero_prescales)

            signal_seeds_prescales = [(table[table.iloc[:,name_col_idx]==s].iloc[:,
                PS_col_idx]) for s in identified_signal_seeds]
            signal_seeds_prescales = [int(ps) for ps in signal_seeds_prescales]

            identified_signal_seeds = ['{} (PS: {})'.format(s,str(ps)) for s,ps in \
                    zip(identified_signal_seeds,signal_seeds_prescales)]

        else:
            is_backup_seed = True
            identified_signal_seeds = ['[NaN - backup seed set manually]']
            criteria = []

        if is_backup_seed:
            backup_seeds = backup_seeds.append(table.iloc[idx,:])
            backup_seeds_info.append([seed, prescale,
                ', '.join(identified_signal_seeds), ', '.join(criteria)])

        else:
            signal_seeds = signal_seeds.append(table.iloc[idx,:])

    backup_seeds_info_headers = ['Identified backup seed',
            'prescale value',
            'corresponding signal seeds (incl. prescales)',
            'used criteria (in signal seed order)']
    if verbose:
        print(tabulate(backup_seeds_info, headers=backup_seeds_info_headers))

    backup_seeds_summary_fname = 'backup_seeds_summary.html'
    with open(backup_seeds_summary_fname,'w') as f_summary:
        f_summary.write(tabulate(backup_seeds_info,
            headers=backup_seeds_info_headers, tablefmt='html'))
        if verbose:
            print('\nFile created: {} (contains the above backup seeds '
                    'summary)'.format(backup_seeds_summary_fname))

    return signal_seeds, backup_seeds


def has_signal_seed(seed: str, prescale: int, all_seeds: list,
        all_prescales: list, check_prescales : bool = True,
        keep_zero_prescales : bool = False) -> (bool,
                list, list):
    # TODO add docstring

    # collection of functions that define backup-seed criteria, together with
    # an option string
    criterion_functions = [
        (criterion_prescale,  ''),
        (criterion_pT,        ''),
        (criterion_pT_extra,  ''),
        (criterion_er,        ''),
        (criterion_dRmax,     ''),
        (criterion_dRmin,     ''),
        (criterion_MassXtoY,  ''),
        (criterion_quality,   ''),
        (criterion_isolation, ''),
    ]

    is_backup_seed = False
    identified_signal_seeds = []
    criteria = []

    for otherseed,otherprescale in zip(all_seeds, all_prescales):
        for (criterion,options) in criterion_functions:
            if not all([type(s) == str for s in (seed,otherseed)]): continue
            is_backup_candidate, identified_signal_seed, identified_criterion = criterion(
                    seed, prescale, otherseed, otherprescale,
                    lazy=(True if 'lazy' in options else False),
                    check_prescales=(True if check_prescales else False),
                    ignore_zero_prescales=(True if keep_zero_prescales else False))

            if is_backup_candidate:
                is_backup_seed = True
                identified_signal_seeds.append(identified_signal_seed)
                criteria.append(identified_criterion)

    return is_backup_seed, identified_signal_seeds, criteria


def criterion_pT(seed: str, prescale: int, otherseed: str, otherprescale: int,
        ignore_zero_prescales : bool = False, check_prescales : bool = True,
        lazy : bool = False) -> (bool, str, str):
    """
    Checks whether 'seed' has a tigher pT cut than 'otherseed'.

    Supported formats (all formats allow for an optional single underscore
    before the first threshold value, all further threshold values must be
    separated by '_'):
    - single object seeds of the form L1_[NAME][THRESHOLD]*
    - double object seeds of the form L1_*double*[THRESHOLD] or
      L1_*double*[THRESHOLD1]_[THRESHOLD2]
    - triple object seeds of the form L1_*triple*[THRESHOLD]* or
      L1_*triple*[THRESHOLD1]_[THRESHOLD2]_[THRESHOLD3]
    - quadruple object seeds of the form L1_*quad*[THRESHOLD]* or
      L1_*quad*[THRESHOLD1]_[THRESHOLD2]_[THRESHOLD3]_[THRESHOLD4]

    In case of multi-object seeds, all given thresholds of 'otherseed' must
    individually be greater than or equal to the respective thresholds of
    'seed' in order for the latter to be considered as a backup seed candidate
    (i.e., 'seed' is not immediately discarded).

    If 'seed' and 'otherseed' have any differences apart from their pT cuts,
    this function will not process them.

    Note: This function does not yet work for seeds with an eta criterion
    directly attached to the pT threshold (e.g., L1_SingleMu6er1p5).

    Parameters
    ---------
    seed : str
        Name of the seed which is checked for its 'backup seed' properties
    precale : int
        Prescale value for 'seed'
    otherseed : str
        Name of the algorithm which 'seed' is checked against
    otherprescale : int
        Prescale value for 'otherseed'

    Optional parameters
    -------------------
    ignore_zero_prescales : bool
        Ignore if the two seeds have different prescale values (default: False)
    check_prescales : bool
        If True, make sure that the prescale value of 'seed' is not smaller
        than the one of 'otherseed' (default: True)
    lazy : bool
        If True, do not consider seeds which differ from 'seed' in more aspects
        than the current criterion (default: False)

    Returns
    -------
    (bool, str, str)
        True if 'seed' is a backup seed to 'otherseed' or False otherwise,
        the name of the other seed if 'otherseed' is a signal seed to 'seed' or
        None otherwise, name of the criterion (None if 'seed' is not a backup
        seed)

    """

    if check_prescales and prescale < otherprescale:
        return False, None, None

    if not ignore_zero_prescales and otherprescale == 0:
        return False, None, None

    is_backup_candidate = False

    seed_basename = get_seed_basename(seed)
    otherseed_basename = get_seed_basename(otherseed)

    if seed_basename is None or otherseed_basename is None:
        return False, None, None

    # distinguish between single, double, triple and quadruple seed objects

    # process single-object case first
    if not any([t in seed_basename.lower() for t in ('double','triple','quad')]):
        # pattern = r'{}(_*?)(\d+p\d+|\d+)($|\_[a-zA-Z]+)'.format(seed_basename)
        pattern = r'{}*?(\d+p\d+|\d+)'.format(seed_basename)
        # GROUPS        (    #1     )

        search_res = re.search(pattern, seed)
        if search_res:
            seed_stripped = seed.replace(search_res.group(0), '')
            seed_pt_threshold = convert_to_float(search_res.group(1))
        else:
            seed_stripped = seed
            seed_pt_threshold = None

        search_res = re.search(pattern, otherseed)
        if search_res:
            otherseed_stripped = otherseed.replace(search_res.group(0), '')
            otherseed_pt_threshold = convert_to_float(search_res.group(1))
        else:
            otherseed_stripped = otherseed
            otherseed_pt_threshold = None

        # skip if seeds are different apart from their pT criterion
        if not lazy and seed_stripped != otherseed_stripped:
            return False, None, None

        if seed_pt_threshold is not None and otherseed_pt_threshold is not None \
                and seed_pt_threshold > otherseed_pt_threshold:
            is_backup_candidate = True

    # process double-object seeds
    elif 'double' in seed_basename.lower():
        pattern = r'({})(_*?(\d+p\d+|\d+)(er\d+p\d+|\d+)?)(_*?(\d+p\d+|\d+)(er\d+p\d+|er\d+)?)?'.format(seed_basename)
        # GROUPS:   (#1)(   (    #3     )(     #4      ) )(   (    #6     )(      #7       ) )
        # GROUPS:   (#1)(               #2               )(               #5                 )

        search_res = re.search(pattern, seed)
        if search_res:
            substr_stripped = search_res.group(1)
            temp_str = search_res.group(2).replace(
                    search_res.group(3), '', 1) if search_res.group(2) else ''
            if temp_str.startswith('_'):
                temp_str = temp_str[1:]

            substr_stripped += temp_str
            if search_res.group(5):
                temp_str = search_res.group(5).replace(search_res.group(6),'',1)
                substr_stripped += temp_str

            seed_stripped = seed.replace(search_res.group(0), substr_stripped)
            seed_pt_threshold_1 = convert_to_float(search_res.group(3))
            seed_pt_threshold_2 = convert_to_float(search_res.group(6))

        else:
            seed_stripped = seed
            seed_pt_threshold_1 = None
            seed_pt_threshold_2 = None

        search_res = re.search(pattern, otherseed)
        if search_res:
            substr_stripped = search_res.group(1)
            temp_str = search_res.group(2).replace(
                    search_res.group(3),'',1) if search_res.group(2) else ''
            if temp_str.startswith('_'):
                temp_str = temp_str[1:]

            substr_stripped += temp_str
            if search_res.group(5):
                temp_str = search_res.group(5).replace(search_res.group(6),'',1)
                substr_stripped += temp_str

            otherseed_stripped = otherseed.replace(search_res.group(0),
                    substr_stripped)
            otherseed_pt_threshold_1 = convert_to_float(search_res.group(3))
            otherseed_pt_threshold_2 = convert_to_float(search_res.group(6))

        else:
            otherseed_stripped = otherseed
            otherseed_pt_threshold_1 = None
            otherseed_pt_threshold_2 = None

        # skip if seeds are different apart from their pT criteria
        if not lazy and seed_stripped != otherseed_stripped:
            return False, None, None

        seed_types = [type(t) for t in (seed_pt_threshold_1,
            seed_pt_threshold_2)]
        otherseed_types = [type(t) for t in (otherseed_pt_threshold_1,
            otherseed_pt_threshold_2)]

        allowed_types = ([float, type(None)], [float, float])

        if any([types not in allowed_types for types in \
                (seed_types, otherseed_types)]):
            return False, None, None

        if all([types == [float, type(None)] for types in \
                (seed_types, otherseed_types)]):
            if seed_pt_threshold_1 > otherseed_pt_threshold_1:
                is_backup_candidate = True

        if all([types == [float, float] for types in \
                (seed_types, otherseed_types)]):
            if seed_pt_threshold_1 >= otherseed_pt_threshold_1 and \
                    seed_pt_threshold_2 >= otherseed_pt_threshold_2 and \
                    (seed_pt_threshold_1 > otherseed_pt_threshold_1 or \
                    seed_pt_threshold_2 > otherseed_pt_threshold_2):
                is_backup_candidate = True

    # process triple-object seeds
    elif 'triple' in seed_basename.lower():
        pattern = r'({})(_*?(\d+p\d+|\d+)(er\d+p\d+|\d+)?)(_(\d+p\d+|\d+)(er\d+p\d+|er\d+)?_(\d+p\d+|\d+)(er\d+p\d+|er\d+)?)?'.format(seed_basename)
        # GROUPS:   (#1)(   (    #3     )(     #4      ) )( (    #6     )(      #7       )  (    #8     )(      #9       ) )
        # GROUPS:   (#1)(               #2               )(                               #5                               )

        search_res = re.search(pattern, seed)
        if search_res:
            substr_stripped = search_res.group(1)
            temp_str = search_res.group(2).replace(
                    search_res.group(3), '', 1) if search_res.group(2) else ''
            if temp_str.startswith('_'):
                temp_str = temp_str[1:]

            substr_stripped += temp_str
            if search_res.group(5):
                temp_str = search_res.group(5).replace(search_res.group(6),'',1)
                temp_str = temp_str.replace(search_res.group(8), '', 1)
                substr_stripped += temp_str

            seed_stripped = seed.replace(search_res.group(0), substr_stripped)
            seed_pt_threshold_1 = convert_to_float(search_res.group(3))
            seed_pt_threshold_2 = convert_to_float(search_res.group(6))
            seed_pt_threshold_3 = convert_to_float(search_res.group(8))

        else:
            seed_stripped = seed
            seed_pt_threshold_1 = None
            seed_pt_threshold_2 = None
            seed_pt_threshold_3 = None

        search_res = re.search(pattern, otherseed)
        if search_res:
            substr_stripped = search_res.group(1)
            temp_str = search_res.group(2).replace(
                    search_res.group(3),'',1) if search_res.group(2) else ''
            if temp_str.startswith('_'):
                temp_str = temp_str[1:]

            substr_stripped += temp_str
            if search_res.group(5):
                temp_str = search_res.group(5).replace(search_res.group(6),'',1)
                temp_str = temp_str.replace(search_res.group(8), '', 1)
                substr_stripped += temp_str

            otherseed_stripped = otherseed.replace(search_res.group(0),
                    substr_stripped)
            otherseed_pt_threshold_1 = convert_to_float(search_res.group(3))
            otherseed_pt_threshold_2 = convert_to_float(search_res.group(6))
            otherseed_pt_threshold_3 = convert_to_float(search_res.group(8))

        else:
            otherseed_stripped = otherseed
            otherseed_pt_threshold_1 = None
            otherseed_pt_threshold_2 = None
            otherseed_pt_threshold_3 = None

        # skip if seeds are different apart from their pT criteria
        if seed_stripped != otherseed_stripped:
            return False, None, None

        seed_types = [type(t) for t in (seed_pt_threshold_1,
            seed_pt_threshold_2)]
        otherseed_types = [type(t) for t in (otherseed_pt_threshold_1,
            otherseed_pt_threshold_2)]

        allowed_types = ([float, type(None)], [float, float])

        if any([types not in allowed_types for types in \
                (seed_types, otherseed_types)]):
            return False, None, None

        if all([types == [float, type(None)] for types in \
                (seed_types, otherseed_types)]):
            if seed_pt_threshold_1 > otherseed_pt_threshold_1:
                is_backup_candidate = True

        if all([types == [float, float] for types in \
                (seed_types, otherseed_types)]):
            if seed_pt_threshold_1 >= otherseed_pt_threshold_1 and \
                    seed_pt_threshold_2 >= otherseed_pt_threshold_2 and \
                    (seed_pt_threshold_1 > otherseed_pt_threshold_1 or \
                    seed_pt_threshold_2 > otherseed_pt_threshold_2):
                is_backup_candidate = True

        # skip if seeds are different apart from their pT criteria
        if not lazy and seed_stripped != otherseed_stripped:
            return False, None, None

        seed_types = [type(t) for t in (seed_pt_threshold_1,
            seed_pt_threshold_2, seed_pt_threshold_3)]
        otherseed_types = [type(t) for t in (otherseed_pt_threshold_1,
            otherseed_pt_threshold_2, otherseed_pt_threshold_3)]

        allowed_types = ([float, type(None), type(None)], [float, float, float])

        if any([types not in allowed_types for types in \
                (seed_types, otherseed_types)]):
            return False, None, None

        if all([types == [float, type(None), type(None)] for types in \
                (seed_types, otherseed_types)]):
            if seed_pt_threshold_1 > otherseed_pt_threshold_1:
                is_backup_candidate = True

        if all([types == [float, float, float] for types in \
                (seed_types, otherseed_types)]):
            if seed_pt_threshold_1 >= otherseed_pt_threshold_1 and \
                    seed_pt_threshold_2 >= otherseed_pt_threshold_2 and \
                    seed_pt_threshold_3 >= otherseed_pt_threshold_3 and \
                    (seed_pt_threshold_1 > otherseed_pt_threshold_1 or \
                    seed_pt_threshold_2 > otherseed_pt_threshold_2 or \
                    seed_pt_threshold_3 > otherseed_pt_threshold_3):
                is_backup_candidate = True

    # process quadruple-object seeds
    elif 'quad' in seed_basename.lower():
        pattern = r'({})(_*?(\d+p\d+|\d+)(er\d+p\d+|\d+)?)(_(\d+p\d+|\d+)(er\d+p\d+|er\d+)?_(\d+p\d+|\d+)(er\d+p\d+|er\d+)?_(\d+p\d+|\d+)(er\d+p\d+|er\d+)?)?'.format(seed_basename)
        # GROUPS:   (#1)(   (    #3     )(     #4      ) )( (    #6     )(      #7       )  (    #8     )(      #9       )  (   #10     )(      #11      ) )
        # GROUPS:   (#1)(               #2               )(                                              #5                                                )

        search_res = re.search(pattern, seed)
        if search_res:
            substr_stripped = search_res.group(1)
            temp_str = search_res.group(2).replace(
                    search_res.group(3), '', 1) if search_res.group(2) else ''
            if temp_str.startswith('_'):
                temp_str = temp_str[1:]

            substr_stripped += temp_str
            if search_res.group(5):
                temp_str = search_res.group(5).replace(search_res.group(6),'',1)
                temp_str = temp_str.replace(search_res.group(8), '', 1)
                temp_str = temp_str.replace(search_res.group(10), '', 1)
                substr_stripped += temp_str

            seed_stripped = seed.replace(search_res.group(0), substr_stripped)
            seed_pt_threshold_1 = convert_to_float(search_res.group(3))
            seed_pt_threshold_2 = convert_to_float(search_res.group(6))
            seed_pt_threshold_3 = convert_to_float(search_res.group(8))
            seed_pt_threshold_4 = convert_to_float(search_res.group(10))

        else:
            seed_stripped = seed
            seed_pt_threshold_1 = None
            seed_pt_threshold_2 = None
            seed_pt_threshold_3 = None
            seed_pt_threshold_4 = None

        search_res = re.search(pattern, otherseed)
        if search_res:
            substr_stripped = search_res.group(1)
            temp_str = search_res.group(2).replace(
                    search_res.group(3),'',1) if search_res.group(2) else ''
            if temp_str.startswith('_'):
                temp_str = temp_str[1:]

            substr_stripped += temp_str
            if search_res.group(5):
                temp_str = search_res.group(5).replace(search_res.group(6),'',1)
                temp_str = temp_str.replace(search_res.group(8), '', 1)
                temp_str = temp_str.replace(search_res.group(10), '', 1)
                substr_stripped += temp_str

            otherseed_stripped = otherseed.replace(search_res.group(0),
                    substr_stripped)
            otherseed_pt_threshold_1 = convert_to_float(search_res.group(3))
            otherseed_pt_threshold_2 = convert_to_float(search_res.group(6))
            otherseed_pt_threshold_3 = convert_to_float(search_res.group(8))
            otherseed_pt_threshold_4 = convert_to_float(search_res.group(10))

        else:
            otherseed_stripped = otherseed
            otherseed_pt_threshold_1 = None
            otherseed_pt_threshold_2 = None
            otherseed_pt_threshold_3 = None
            otherseed_pt_threshold_4 = None

        # skip if seeds are different apart from their pT criteria
        if not lazy and seed_stripped != otherseed_stripped:
            return False, None, None

        seed_types = [type(t) for t in (seed_pt_threshold_1, seed_pt_threshold_2,
            seed_pt_threshold_3, seed_pt_threshold_4)]
        otherseed_types = [type(t) for t in (otherseed_pt_threshold_1,
            otherseed_pt_threshold_2, otherseed_pt_threshold_3,
            otherseed_pt_threshold_4)]

        allowed_types = ([float, type(None), type(None), type(None)],
                [float, float, float, float])

        if any([types not in allowed_types for types in (seed_types, otherseed_types)]):
            return False, None, None

        if all([types == [float, type(None), type(None), type(None)] for types \
                in (seed_types, otherseed_types)]):
            if seed_pt_threshold_1 > otherseed_pt_threshold_1:
                is_backup_candidate = True

        if all([types == [float, float, float, float] for types in \
                (seed_types, otherseed_types)]):
            if seed_pt_threshold_1 >= otherseed_pt_threshold_1 and \
                    seed_pt_threshold_2 >= otherseed_pt_threshold_2 and \
                    seed_pt_threshold_3 >= otherseed_pt_threshold_3 and \
                    seed_pt_threshold_4 >= otherseed_pt_threshold_4 and \
                    (seed_pt_threshold_1 > otherseed_pt_threshold_1 or \
                    seed_pt_threshold_2 > otherseed_pt_threshold_2 or \
                    seed_pt_threshold_3 > otherseed_pt_threshold_3 or \
                    seed_pt_threshold_4 > otherseed_pt_threshold_4):
                is_backup_candidate = True

    return is_backup_candidate, (otherseed if is_backup_candidate else None), \
            ('pT' if is_backup_candidate else None)


def criterion_pT_extra(seed: str, prescale: int, otherseed: str, otherprescale: int,
        ignore_zero_prescales : bool = False, check_prescales : bool = True,
        lazy : bool = False) -> (bool, str, str):
    """
    Checks whether 'seed' has a tigher pT restriction cut than 'otherseed' for
    some special cases in which the pT threshold is in the middle of the name.

    Extra checks: Apply the pT threhold criteria in cases where the number XX
    is the only difference between two seeds, and XX applies to one of
    - EGXX
    - ETMHFXX
    - HTTXX
    - _MtXX
    - TauXX
    - Mass_MinXX

    If 'seed' and 'otherseed' have any differences apart from their extra pT
    restrictions, this function will pass on them.

    Parameters
    ---------
    seed : str
        Name of the seed which is checked for its 'backup seed' properties
    precale : int
        Prescale value for 'seed'
    otherseed : str
        Name of the algorithm which 'seed' is checked against
    otherprescale : int
        Prescale value for 'otherseed'

    Optional parameters
    -------------------
    ignore_zero_prescales : bool
        Ignore if the two seeds have different prescale values (default: False)
    check_prescales : bool
        If True, make sure that the prescale value of 'seed' is not smaller
        than the one of 'otherseed' (default: True)
    lazy : bool
        If True, do not consider seeds which differ from 'seed' in more aspects
        than the current criterion (default: False)

    Returns
    -------
    (bool, str)
        True if 'seed' is a backup seed to 'otherseed' or False otherwise,
        the name of the other seed if 'otherseed' is a signal seed to 'seed' or
        None otherwise, name of the criterion function (None if 'seed' is not a
        backup seed)

    """

    if check_prescales and prescale < otherprescale:
        return False, None, None

    if not ignore_zero_prescales and otherprescale == 0:
        return False, None, None

    is_backup_candidate = False

    seed_basename = get_seed_basename(seed)
    otherseed_basename = get_seed_basename(otherseed)

    # skip invalid seeds
    if any([basename is None for basename in (seed_basename,
            otherseed_basename)]):
        return False, None, None

    # remove seed basenames such that the algorithm does not focus on the
    # beginnings of the seeds and does not process seeds which have already been
    # treated by the criterion_pT function (e.g., L1_SingleEG40er2p5)
    seed_stripped = seed.replace(seed_basename, '')
    otherseed_stripped = otherseed.replace(otherseed_basename, '')

    # collection of patterns to look out for
    patterns = (
            (r'EG(\d+)',       'EG'),
            (r'ETMHF(\d+)',    'ETMHF'),
            (r'HTT(\d+)',      'HTT'),
            (r'_Mt(\d+)',      'Mt'),
            (r'Tau(\d+)',      'Tau'),
            (r'Mass_Min(\d+)', 'Mass_Min'),
    )

    for pattern,cond in patterns:
        search_res_seed = re.search(pattern, seed_stripped)
        search_res_otherseed = re.search(pattern, otherseed_stripped)

        # if the respective pattern is found in both seeds, make sure that there
        # are no other differences between the seeds
        if search_res_seed and search_res_otherseed:
            seed_threshold = search_res_seed.group(1)
            otherseed_threshold = search_res_otherseed.group(1)

            seed_stripped = seed_stripped.replace(
                    cond + seed_threshold, cond)
            otherseed_stripped = otherseed_stripped.replace(
                    cond + otherseed_threshold, cond)

            # skip if there are any further differences
            if seed_stripped != otherseed_stripped:
                continue

            if convert_to_float(seed_threshold) > convert_to_float(
                    otherseed_threshold):
                is_backup_candidate = True
                condition = cond

    return is_backup_candidate, (otherseed if is_backup_candidate else None), \
        ('pT' if is_backup_candidate else None)


def criterion_er(seed: str, prescale: int, otherseed: str, otherprescale: int,
        ignore_zero_prescales : bool = False, check_prescales : bool = True,
        lazy : bool = False) -> (bool, str, str):
    """
    Checks whether 'seed' has a tigher eta restriction cut than 'otherseed'.

    Eta restriction: |eta| < threshold. If not explicitly specified, no eta
    restrictions are applied.

    This function does not process any seeds which involve more than one eta
    restriction (e.g., cross-triggers). Further, if 'seed' and 'otherseed' have
    any differences apart from their eta restrictions, this function will pass
    on them as well.

    Parameters
    ---------
    seed : str
        Name of the seed which is checked for its 'backup seed' properties
    precale : int
        Prescale value for 'seed'
    otherseed : str
        Name of the algorithm which 'seed' is checked against
    otherprescale : int
        Prescale value for 'otherseed'

    Optional parameters
    -------------------
    ignore_zero_prescales : bool
        Ignore if the two seeds have different prescale values (default: False)
    check_prescales : bool
        If True, make sure that the prescale value of 'seed' is not smaller
        than the one of 'otherseed' (default: True)
    lazy : bool
        If True, do not consider seeds which differ from 'seed' in more aspects
        than the current criterion (default: False)

    Returns
    -------
    (bool, str)
        True if 'seed' is a backup seed to 'otherseed' or False otherwise,
        the name of the other seed if 'otherseed' is a signal seed to 'seed' or
        None otherwise, name of the criterion function (None if 'seed' is not a
        backup seed)

    """

    if check_prescales and prescale < otherprescale:
        return False, None, None

    if not ignore_zero_prescales and otherprescale == 0:
        return False, None, None

    is_backup_candidate = False

    seed_basename = get_seed_basename(seed)
    otherseed_basename = get_seed_basename(otherseed)

    # do not process further if there are multiple eta restrictions in a seed
    pattern = r'er(\d+)p(\d+)|er(\d+)'
    if any([len(re.findall(pattern, s)) > 1 for s in (seed, otherseed)]):
        return False, None, None

    # do not process further if neither seed has an eta restriction
    if all([len(re.findall(pattern, s)) == 0 for s in (seed, otherseed)]):
        return False, None, None

    # extract the eta restriction substring for 'seed'
    seed_er_str = re.search(pattern, seed)
    if seed_er_str:
        seed_er_str = seed_er_str.group(0)
        seed_stripped = seed.replace(seed_er_str,'')
    else:
        seed_stripped = seed

    # extract the eta restriction substring for 'otherseed'
    otherseed_er_str = re.search(pattern, otherseed)
    if otherseed_er_str:
        otherseed_er_str = otherseed_er_str.group(0)
        otherseed_stripped = otherseed.replace(otherseed_er_str,'')
    else:
        otherseed_stripped = otherseed

    # do not process further if the seeds are different (apart from their ER)
    if not lazy and seed_stripped != otherseed_stripped:
        return False, None, None

    if seed_er_str is not None:
        seed_er_val = convert_to_float(seed_er_str.replace('er',''))
    else:
        seed_er_val = None

    if otherseed_er_str is not None:
        otherseed_er_val = convert_to_float(otherseed_er_str.replace('er',''))
    else:
        otherseed_er_val = None

    if seed_er_val is not None and otherseed_er_val is not None and \
            seed_er_val < otherseed_er_val:
        is_backup_candidate = True

    if seed_er_val is not None and otherseed_er_val is None and \
            seed_er_val > 0.0:
        is_backup_candidate = True

    return is_backup_candidate, (otherseed if is_backup_candidate else None), \
            ('eta restriction' if is_backup_candidate else None)


def criterion_dRmax(seed: str, prescale: int, otherseed: str,
        otherprescale: int, ignore_zero_prescales : bool = False,
        check_prescales : bool = True, lazy : bool = False) -> (bool, str, str):
    """
    Checks whether 'seed' has a tigher dRmax restriction cut than 'otherseed'.

    If not explicitly specified, no dRmax restriction is applied.

    This function does not process any seeds which involve more than one dRmax
    restriction (e.g., cross-triggers). Further, if 'seed' and 'otherseed' have
    any differences apart from their dRmax restrictions, this function will pass
    on them as well.

    Parameters
    ---------
    seed : str
        Name of the seed which is checked for its 'backup seed' properties
    precale : int
        Prescale value for 'seed'
    otherseed : str
        Name of the algorithm which 'seed' is checked against
    otherprescale : int
        Prescale value for 'otherseed'

    Optional parameters
    -------------------
    ignore_zero_prescales : bool
        Ignore if the two seeds have different prescale values (default: False)
    check_prescales : bool
        If True, make sure that the prescale value of 'seed' is not smaller
        than the one of 'otherseed' (default: True)
    lazy : bool
        If True, do not consider seeds which differ from 'seed' in more aspects
        than the current criterion (default: False)

    Returns
    -------
    (bool, str)
        True if 'seed' is a backup seed to 'otherseed' or False otherwise,
        the name of the other seed if 'otherseed' is a signal seed to 'seed' or
        None otherwise, name of the criterion (None if 'seed' is not a backup
        seed)

    """

    if check_prescales and prescale < otherprescale:
        return False, None, None

    if not ignore_zero_prescales and otherprescale == 0:
        return False, None, None

    is_backup_candidate = False

    seed_basename = get_seed_basename(seed)
    otherseed_basename = get_seed_basename(otherseed)

    # do not process further if there are multiple dRmax restrictions
    pattern = r'dR_Max(\d+)p(\d+)|dR_Max(\d+)'
    if any([len(re.findall(pattern, s)) > 1 for s in (seed, otherseed)]):
        return False, None, None

    # do not process further if neither seed has a dRmax restriction
    if all([len(re.findall(pattern, s)) == 0 for s in (seed, otherseed)]):
        return False, None, None

    # extract the dRmax restriction substring for 'seed'
    seed_dRmax_str = re.search(pattern, seed)
    if seed_dRmax_str:
        seed_dRmax_str = seed_dRmax_str.group(0)
        seed_stripped = seed.replace(seed_dRmax_str,'')
    else:
        seed_stripped = seed

    # extract the dRmax restriction substring for 'otherseed'
    otherseed_dRmax_str = re.search(pattern, otherseed)
    if otherseed_dRmax_str:
        otherseed_dRmax_str = otherseed_dRmax_str.group(0)
        otherseed_stripped = otherseed.replace(otherseed_dRmax_str,'')
    else:
        otherseed_stripped = otherseed

    # do not process further if the seeds are different (apart from their dRmax)
    if not lazy and seed_stripped != otherseed_stripped:
        return False, None, None

    if seed_dRmax_str is not None:
        seed_dRmax_val = convert_to_float(seed_dRmax_str.replace('dR_Max',''))
    else:
        seed_dRmax_val = None

    if otherseed_dRmax_str is not None:
        otherseed_dRmax_val = convert_to_float(otherseed_dRmax_str.replace('dR_Max',''))
    else:
        otherseed_dRmax_val = None

    if seed_dRmax_val is not None and otherseed_dRmax_val is not None and \
            seed_dRmax_val < otherseed_dRmax_val:
        is_backup_candidate = True

    if seed_dRmax_val is not None and otherseed_dRmax_val is None and \
            seed_dRmax_val > 0.0:
        is_backup_candidate = True

    return is_backup_candidate, (otherseed if is_backup_candidate else None), \
            ('dR_Max' if is_backup_candidate else None)


def criterion_dRmin(seed: str, prescale: int, otherseed: str,
        otherprescale: int, ignore_zero_prescales : bool = False,
        check_prescales : bool = True, lazy : bool = False) -> (bool, str, str):
    """
    Checks whether 'seed' has a tigher dRmin restriction cut than 'otherseed'.

    If not explicitly specified, no dRmin restriction is applied.

    This function does not process any seeds which involve more than one dRmin
    restriction (e.g., cross-triggers). Further, if 'seed' and 'otherseed' have
    any differences apart from their dRmin restrictions, this function will pass
    on them as well.

    Parameters
    ---------
    seed : str
        Name of the seed which is checked for its 'backup seed' properties
    precale : int
        Prescale value for 'seed'
    otherseed : str
        Name of the algorithm which 'seed' is checked against
    otherprescale : int
        Prescale value for 'otherseed'

    Optional parameters
    -------------------
    ignore_zero_prescales : bool
        Ignore if the two seeds have different prescale values (default: False)
    check_prescales : bool
        If True, make sure that the prescale value of 'seed' is not smaller
        than the one of 'otherseed' (default: True)
    lazy : bool
        If True, do not consider seeds which differ from 'seed' in more aspects
        than the current criterion (default: False)

    Returns
    -------
    (bool, str)
        True if 'seed' is a backup seed to 'otherseed' or False otherwise,
        the name of the other seed if 'otherseed' is a signal seed to 'seed' or
        None otherwise, the name of the criterion (None if 'seed' is not a
        backup seed)

    """

    if check_prescales and prescale < otherprescale:
        return False, None, None

    if not ignore_zero_prescales and otherprescale == 0:
        return False, None, None

    is_backup_candidate = False

    seed_basename = get_seed_basename(seed)
    otherseed_basename = get_seed_basename(otherseed)

    # do not process further if there are multiple dRmin restrictions
    pattern = r'dR_Min(\d+)p(\d+)|dR_Min(\d+)'
    if any([len(re.findall(pattern, s)) > 1 for s in (seed, otherseed)]):
        return False, None, None

    # do not process further if neither seed has a dRmin restriction
    if all([len(re.findall(pattern, s)) == 0 for s in (seed, otherseed)]):
        return False, None, None

    # extract the dRmin restriction substring for 'seed'
    seed_dRmin_str = re.search(pattern, seed)
    if seed_dRmin_str:
        seed_dRmin_str = seed_dRmin_str.group(0)
        seed_stripped = seed.replace(seed_dRmin_str,'')
    else:
        seed_stripped = seed

    # extract the dRmin restriction substring for 'otherseed'
    otherseed_dRmin_str = re.search(pattern, otherseed)
    if otherseed_dRmin_str:
        otherseed_dRmin_str = otherseed_dRmin_str.group(0)
        otherseed_stripped = otherseed.replace(otherseed_dRmin_str,'')
    else:
        otherseed_stripped = otherseed

    # do not process further if the seeds are different (apart from their dRmin)
    if not lazy and seed_stripped != otherseed_stripped:
        return False, None, None

    if seed_dRmin_str is not None:
        seed_dRmin_val = convert_to_float(seed_dRmin_str.replace('dR_Min',''))
    else:
        seed_dRmin_val = None

    if otherseed_dRmin_str is not None:
        otherseed_dRmin_val = convert_to_float(otherseed_dRmin_str.replace('dR_Min',''))
    else:
        otherseed_dRmin_val = None

    if seed_dRmin_val is not None and otherseed_dRmin_val is not None and \
            seed_dRmin_val > otherseed_dRmin_val:
        is_backup_candidate = True

    if seed_dRmin_val is not None and otherseed_dRmin_val is None and \
            seed_dRmin_val > 0.0:
        is_backup_candidate = True

    return is_backup_candidate, (otherseed if is_backup_candidate else None), \
            ('dR_Min' if is_backup_candidate else None)


def criterion_MassXtoY(seed: str, prescale: int, otherseed: str,
        otherprescale: int, ignore_zero_prescales : bool = False,
        check_prescales : bool = True, lazy : bool = False) -> (bool, str, str):
    """
    Checks whether 'seed' has a tigher mass cut than 'otherseed'.

    If not explicitly specified, no mass cuts are applied.

    This function does not process any seeds which involve more than one mass
    cut (e.g., cross-triggers). Further, if 'seed' and 'otherseed' have
    any differences apart from their mass restrictions, this function will pass
    on them as well.

    Parameters
    ---------
    seed : str
        Name of the seed which is checked for its 'backup seed' properties
    precale : int
        Prescale value for 'seed'
    otherseed : str
        Name of the algorithm which 'seed' is checked against
    otherprescale : int
        Prescale value for 'otherseed'

    Optional parameters
    -------------------
    ignore_zero_prescales : bool
        Ignore if the two seeds have different prescale values (default: False)
    check_prescales : bool
        If True, make sure that the prescale value of 'seed' is not smaller
        than the one of 'otherseed' (default: True)
    lazy : bool
        If True, do not consider seeds which differ from 'seed' in more aspects
        than the current criterion (default: False)

    Returns
    -------
    (bool, str)
        True if 'seed' is a backup seed to 'otherseed' or False otherwise,
        the name of the other seed if 'otherseed' is a signal seed to 'seed' or
        None otherwise, name of the criterion (None if 'seed' is not a backup
        seed)

    """

    if check_prescales and prescale < otherprescale:
        return False, None, None

    if not ignore_zero_prescales and otherprescale == 0:
        return False, None, None

    is_backup_candidate = False

    seed_basename = get_seed_basename(seed)
    otherseed_basename = get_seed_basename(otherseed)

    # do not process further if there are multiple mass restrictions in a seed
    pattern = r'Mass(_*?)(\d+p\d+|\d+)to(\d+p\d+|\d+)'
    if any([len(re.findall(pattern, s)) > 1 for s in (seed, otherseed)]):
        return False, None, None

    # do not process further if neither seed has an mass restriction
    if all([len(re.findall(pattern, s)) == 0 for s in (seed, otherseed)]):
        return False, None, None

    # extract the mass restriction substring for 'seed'
    seed_mass_str = re.search(pattern, seed)
    if seed_mass_str:
        seed_mass_str = seed_mass_str.group(0)
        seed_stripped = seed.replace(seed_mass_str,'')
        if seed_stripped.endswith('_'): seed_stripped = seed_stripped[:-1]
    else:
        seed_stripped = seed

    # extract the mass restriction substring for 'otherseed'
    otherseed_mass_str = re.search(pattern, otherseed)
    if otherseed_mass_str:
        otherseed_mass_str = otherseed_mass_str.group(0)
        otherseed_stripped = otherseed.replace(otherseed_mass_str,'')
        if otherseed_stripped.endswith('_'): otherseed_stripped = otherseed_stripped[:-1]
    else:
        otherseed_stripped = otherseed

    # do not process further if the seeds are different (apart from their mass cuts)
    if not lazy and seed_stripped != otherseed_stripped:
        return False, None, None

    if seed_mass_str is not None:
        search_res = re.search('\d', seed_mass_str)
        seed_mass_str = seed_mass_str[search_res.start():]
        seed_mass_str = seed_mass_str.split('to')
        seed_mass_range = [convert_to_float(val) for val in seed_mass_str]
    else:
        seed_mass_range = None

    if otherseed_mass_str is not None:
        search_res = re.search('\d', otherseed_mass_str)
        otherseed_mass_str = otherseed_mass_str[search_res.start():]
        otherseed_mass_str = otherseed_mass_str.split('to')
        otherseed_mass_range = [convert_to_float(val) for val in otherseed_mass_str]
    else:
        otherseed_mass_range = None

    if seed_mass_range is not None and otherseed_mass_range is not None and \
            seed_mass_range[1]-seed_mass_range[0] < otherseed_mass_range[1]-otherseed_mass_range[0]:
        is_backup_candidate = True

    if seed_mass_range is not None and otherseed_mass_range is None:
        is_backup_candidate = True

    return is_backup_candidate, (otherseed if is_backup_candidate else None), \
            ('MassXtoY' if is_backup_candidate else None)


def criterion_quality(seed: str, prescale: int, otherseed: str,
        otherprescale: int, ignore_zero_prescales : bool = False,
        check_prescales : bool = True, lazy : bool = False) -> (bool, str, str):
    """
    Checks whether 'seed' has a tighter quality criterion than 'otherseed'.

    This will only check SingleMu, DoubleMu, TripleMu and QuadMu seeds.

    Known muon quality criteria are (ordered from 'tighter' to 'looser' cuts):
    - SQ: 'single' quality
    - DQ: 'double' quality
    - OQ: 'open' quality

    Default qualities (if not explicitly given in the seed name):
    - SQ for single muon seeds
    - DQ for multi-muon seeds

    Parameters
    ---------
    seed : str
        Name of the seed which is checked for its 'backup seed' properties
    precale : int
        Prescale value for 'seed'
    otherseed : str
        Name of the algorithm which 'seed' is checked against
    otherprescale : int
        Prescale value for 'otherseed'

    Optional parameters
    -------------------
    ignore_zero_prescales : bool
        Ignore if the two seeds have different prescale values (default: False)
    check_prescales : bool
        If True, make sure that the prescale value of 'seed' is not smaller
        than the one of 'otherseed' (default: True)
    lazy : bool
        If True, do not consider seeds which differ from 'seed' in more aspects
        than the current criterion (default: False)

    Returns
    -------
    (bool, str)
        True if 'seed' is a backup seed to 'otherseed' or False otherwise,
        the name of the other seed if 'otherseed' is a signal seed to 'seed' or
        None otherwise, the name of the criterion (None if 'seed' is not a
        backup seed)

    """

    if check_prescales and prescale < otherprescale:
        return False, None, None

    if not ignore_zero_prescales and otherprescale == 0:
        return False, None, None

    is_backup_candidate = False

    qualities = ('_SQ','_DQ','_OQ')

    seed_basename = get_seed_basename(seed)

    if seed_basename is None:
        return False, None, None

    if not any([muontype in seed_basename.lower() for muontype in ('singlemu',
            'doublemu', 'triplemu', 'quadmu')]):
        return False, None, None

    do_further_checks = False

    if 'singlemu' in seed_basename.lower():
        # if single muon seed has default quality (i.e., 'SQ'; not explicitly
        # given in the seed name) and the other seed has a looser quality
        # criterion (i.e., 'DQ' or 'OQ')
        if all([quality not in seed for quality in qualities]) or '_SQ' in seed:
            is_SQ_seed = True
        else:
            is_SQ_seed = False

        if is_SQ_seed and any([quality in otherseed for quality in ('_DQ','_OQ')]):
            do_further_checks = True

        if '_DQ' in seed and '_OQ' in otherseed:
            do_further_checks = True

    # the default quality is 'DQ' for all of these seed types, so they can be
    # treated equally here
    if any([muontype in seed_basename.lower() for muontype in ('doublemu',
            'triplemu', 'quadmu')]):
        # if double muon seed has default quality (i.e., 'DQ'; not explicitly
        # given in the seed name) and the other seed has a looser quality
        # criterion (i.e., 'OQ')
        if all([quality not in seed for quality in qualities]) or '_DQ' in seed:
            is_DQ_seed = True
        else:
            is_DQ_seed = False

        if all([quality not in otherseed for quality in qualities]) or \
                '_DQ' in otherseed:
            is_DQ_otherseed = True
        else:
            is_DQ_otherseed = False

        if '_SQ' in seed and (is_DQ_otherseed or '_OQ' in otherseed):
            do_further_checks = True

        if is_DQ_seed and '_OQ' in otherseed:
            do_further_checks = True

    if not lazy and do_further_checks:
        # require exact matches for the rest of the seed names
        seed_stripped = seed
        otherseed_stripped = otherseed
        for substr in ((seed_basename,) + qualities):
            seed_stripped = seed_stripped.replace(substr,'')
            otherseed_stripped = otherseed_stripped.replace(substr,'')

        if seed_stripped == otherseed_stripped:
            is_backup_candidate = True

    identified_signal_seed = otherseed if is_backup_candidate else None

    return is_backup_candidate, identified_signal_seed, \
            ('muon quality' if is_backup_candidate else None)


def criterion_prescale(seed: str, prescale: int, otherseed: str,
        otherprescale: int, ignore_zero_prescales : bool = False,
        check_prescales : bool = True, lazy : bool = False) -> (bool, str, str):
    """
    Checks whether 'seed' has a higher prescale value than 'otherseed'.

    Only checks for different prescale values. If the seed names are different,
    this function will not process them.

    Parameters
    ----------
    seed : str
        Name of the seed which is checked for its 'backup seed' properties
    precale : int
        Prescale value for 'seed'
    otherseed : str
        Name of the algorithm which 'seed' is checked against
    otherprescale : int
        Prescale value for 'otherseed'

    Optional parameters
    -------------------
    ignore_zero_prescales : bool
        Ignore if the two seeds have different prescale values (default: False)
    check_prescales : bool
        If True, make sure that the prescale value of 'seed' is not smaller
        than the one of 'otherseed' (default: True)
    lazy : bool
        This parameter has no function in this case, but exists only for
        reasons of compatibility.

    Returns
    -------
    (bool, str)
        True if 'seed' is a backup seed to 'otherseed' or False otherwise,
        the name of the other seed if 'otherseed' is a signal seed to 'seed' or
        None otherwise, the name of the criterion (None if 'seed' is not a
        backup seed)

    """

    if check_prescales and prescale < otherprescale:
        return False, None, None

    if not ignore_zero_prescales and otherprescale == 0:
        return False, None, None

    is_backup_candidate = False
    identified_signal_seed = None
    if seed == otherseed and prescale > otherprescale:
        is_backup_candidate = True
        identified_signal_seed = otherseed

    return is_backup_candidate, identified_signal_seed, \
            ('prescale' if is_backup_candidate else None)


def criterion_isolation(seed: str, prescale: int, otherseed: str,
        otherprescale: int, ignore_zero_prescales : bool = False,
        check_prescales : bool = True, lazy : bool = False) -> (bool, str, str):
    """
    Checks whether 'seed' has a tigher isolation cut than 'otherseed'.

    Isolation criteria, ordered from tightest to loosest: 'Iso' -> 'LooseIso' ->
    no isolation criterion given.

    If not explicitly specified, no isolation cuts are applied.

    This function does not process any seeds which involve more than one
    isolation cut (e.g., cross-triggers). Further, if 'seed' and 'otherseed'
    have any differences apart from their isolation requirements, this function
    will pass on them as well.

    Parameters
    ---------
    seed : str
        Name of the seed which is checked for its 'backup seed' properties
    precale : int
        Prescale value for 'seed'
    otherseed : str
        Name of the algorithm which 'seed' is checked against
    otherprescale : int
        Prescale value for 'otherseed'

    Optional parameters
    -------------------
    ignore_zero_prescales : bool
        Ignore if the two seeds have different prescale values (default: False)
    check_prescales : bool
        If True, make sure that the prescale value of 'seed' is not smaller
        than the one of 'otherseed' (default: True)
    lazy : bool
        If True, do not consider seeds which differ from 'seed' in more aspects
        than the current criterion (default: False)

    Returns
    -------
    (bool, str)
        True if 'seed' is a backup seed to 'otherseed' or False otherwise,
        the name of the other seed if 'otherseed' is a signal seed to 'seed' or
        None otherwise, the name of the criterion (None if 'seed' is not a
        backup seed)

    """

    if check_prescales and prescale < otherprescale:
        return False, None, None

    if not ignore_zero_prescales and otherprescale == 0:
        return False, None, None

    is_backup_candidate = False

    seed_basename = get_seed_basename(seed)
    otherseed_basename = get_seed_basename(otherseed)

    # do not process further if there are multiple isolation criteria in a seed
    pattern = r'Iso|LooseIso'
    if any([len(re.findall(pattern, s)) > 1 for s in (seed, otherseed)]):
        return False, None, None

    # do not process further if neither seed has an isolation restriction
    if all([len(re.findall(pattern, s)) == 0 for s in (seed, otherseed)]):
        return False, None, None

    # extract the isolation substring from 'seed'
    seed_iso_str = re.search(pattern, seed)
    if seed_iso_str:
        seed_iso_str = seed_iso_str.group(0)
        seed_stripped = seed.replace(seed_iso_str,'')
        if seed_stripped.endswith('_'): seed_stripped = seed_stripped[:-1]

    else:
        seed_stripped = seed

    # extract the iso restriction substring from 'otherseed'
    otherseed_iso_str = re.search(pattern, otherseed)
    if otherseed_iso_str:
        otherseed_iso_str = otherseed_iso_str.group(0)
        otherseed_stripped = otherseed.replace(otherseed_iso_str,'')
        if otherseed_stripped.endswith('_'): otherseed_stripped = otherseed_stripped[:-1]

    else:
        otherseed_stripped = otherseed

    # do not process further if the seeds are different (apart from their
    # isolation criteria)
    if not lazy and seed_stripped != otherseed_stripped:
        return False, None, None

    if seed_iso_str == 'Iso' and otherseed_iso_str == 'LooseIso':
        is_backup_candidate = True

    if seed_iso_str == 'Iso' and otherseed_iso_str is None:
        is_backup_candidate = True

    if seed_iso_str == 'LooseIso' and otherseed_iso_str is None:
        is_backup_candidate = True

    return is_backup_candidate, (otherseed if is_backup_candidate else None), \
            ('isolation' if is_backup_candidate else None)


if __name__ == '__main__':
    print('\n*** WARNING: This script is under development. Use with caution! ***\n')

    parser = argparse.ArgumentParser()
    parser.add_argument('filename',
            help='Name/path of the PS table file',
            type=str)
    parser.add_argument('-q', '--quiet',
            help='Make script less verbose',
            action='store_true',
            dest='quietmode')
    parser.add_argument('--no-prescale-checks',
            help='Do not check whether backup seed prescales are larger than or equal to other prescales',
            action='store_true',
            dest='no_prescale_checks')
    parser.add_argument('-m', '--mode',
            help='Specifiy which seeds to keep in the output files. Allowed options are \'inclusive\', \'unprescaled\' and \'prescaled\' (default: inclusive)',
            action='store',
            default='inclusive',
            dest='write_mode')
    parser.add_argument('--keep-zero-prescales',
            help='Do not ignore seeds with zero prescales (default: False)',
            action='store_true',
            dest='keep_zero_prescales')
    parser.add_argument('-b', '--backup-seeds',
            help='Give a filename containing a list of known backup seeds (optional)',
            action='store',
            default=None,
            dest='backup_seeds')

    args = parser.parse_args()

    outfile_signal = 'signal_seeds'
    outfile_backup = 'backup_seeds'

    # extract seed names line by line from the file with known backup seeds
    known_backup_seeds = []
    if args.backup_seeds:
        with open(args.backup_seeds, 'r') as f:
            raw_content = [s.strip('\n') for s in f.readlines()]
            for l in raw_content:
                search_res = re.search(r'(L1_\S+)', l)
                if search_res: known_backup_seeds.append(search_res.group(1))

    table = read_table(args.filename)
    signal_seeds, backup_seeds = separate_signal_and_backup_seeds(table,
            check_prescales=(False if args.no_prescale_checks else True),
            keep_zero_prescales=(True if args.keep_zero_prescales else False),
            write_mode=args.write_mode,
            force_backup_seeds=known_backup_seeds,
            verbose=(False if args.quietmode else True))

    signal_seeds.to_csv(outfile_signal+'.csv')
    signal_seeds.to_html(outfile_signal+'.html')
    if not args.quietmode:
        print('\nFiles created: {}[.csv/.html] (each contains {} signal seeds)'.format(
            outfile_signal, signal_seeds.shape[0]))

    backup_seeds.to_csv(outfile_backup+'.csv')
    backup_seeds.to_html(outfile_backup+'.html')
    if not args.quietmode:
        print('Files created: {}[.csv/.html] (each contains {} backup seeds)'.format(
            outfile_backup, backup_seeds.shape[0]))
