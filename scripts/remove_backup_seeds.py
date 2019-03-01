import os
import argparse
import csv
import re
import pandas as pd


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


def separate_signal_and_backup_seeds(table: pd.DataFrame) -> (pd.DataFrame,
        pd.DataFrame):
    # TODO add docstring

    name_col_idx = get_name_col_idx(table)
    PS_col_idx = get_PS_col_idx(table)

    for idx,row in table.iterrows():
        seed = row[name_col_idx]
        prescale = row[PS_col_idx]

        is_backup_seed, signal_seed = has_signal_seed(seed, prescale,
                table.iloc[:,name_col_idx].tolist(), table.iloc[:,PS_col_idx].tolist())

        # if is_backup_seed:
        #     # add this backup seed to backup seed collection
        #     # remove this backup seed
        
        # else:
        #     # add this seed to signal seed collection


def has_signal_seed(seed: str, prescale: int, all_seeds: list,
        all_prescales: list) -> (bool, str):
    # TODO add docstring

    # collection of functions that define backup-seed criteria
    criterion_functions = [
        criterion_prescale,
        # criterion_pT,
        # criterion_er,
        # criterion_dRmax,
        # criterion_dRmin,
        # criterion_MassXtoY,
        # criterion_quality,
        # criterion_isolation,
    ]

    for otherseed,otherprescale in zip(all_seeds, all_prescales):
        for criterion in criterion_functions:
            if not all([type(s) == str for s in (seed,otherseed)]): continue
            is_backup_seed, identified_signal_seed = criterion(seed, prescale,
                    otherseed, otherprescale)

            if is_backup_seed:
                print('+++ backup: {} (PS: {});    signal: {} (PS: {})'.format(seed,prescale,otherseed,otherprescale))
                pass
            else:
                # print('--- backup: {};    signal: {}'.format(otherseed,seed))
                pass

            # TODO assign seed depending on whether it is a backup seed

    return True, 'false' # TODO correct this


def criterion_pT(seed: str, prescale: int, otherseed: str, otherprescale: int) -> (bool, str):
    raise NotImplementedError


def criterion_er(seed: str, prescale: int, otherseed: str, otherprescale: int) -> (bool, str):
    raise NotImplementedError

    
def criterion_dRmax(seed: str, prescale: int, otherseed: str, otherprescale: int) -> (bool, str):
    raise NotImplementedError


def criterion_dRmin(seed: str, prescale: int, otherseed: str, otherprescale: int) -> (bool, str):
    raise NotImplementedError


def criterion_MassXtoY(seed: str, prescale: int, otherseed: str, otherprescale: int) -> (bool, str):
    raise NotImplementedError


def criterion_quality(seed: str, prescale: int, otherseed: str, otherprescale: int) -> (bool, str):
    """
    Checks whether 'otherseed' has a looser quality criterion than 'seed'.

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

    Returns
    -------
    (bool, str)
        True if 'seed' is a backup seed to 'otherseed' or False otherwise,
        the name of the other seed if 'otherseed' is a signal seed to 'seed' or
        None otherwise

    """

    is_backup_candidate = False

    qualities = ('_SQ','_DQ','_OQ')

    seed_basename = get_seed_basename(seed)

    if seed_basename is None:
        return False, None

    if not any([muontype in seed_basename.lower() for muontype in ('singlemu',
            'doublemu', 'triplemu', 'quadmu')]):
        return False, None

    if not otherseed.startswith(seed_basename):
        return False, None

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

    if do_further_checks:
        # require exact matches for the rest of the seed names
        seed_stripped = seed
        otherseed_stripped = otherseed
        for substr in ((seed_basename,) + qualities):
            seed_stripped = seed_stripped.replace(substr,'')
            otherseed_stripped = otherseed_stripped.replace(substr,'')

        if seed_stripped == otherseed_stripped:
            is_backup_candidate = True


    identified_signal_seed = otherseed if is_backup_candidate else None

    return is_backup_candidate, identified_signal_seed


def criterion_prescale(seed: str, prescale: int, otherseed: str, otherprescale: int) -> (bool, str):
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

    Returns
    -------
    (bool, str)
        True if 'seed' is a backup seed to 'otherseed' or False otherwise,
        the name of the other seed if 'otherseed' is a signal seed to 'seed' or
        None otherwise

    """

    is_backup_candidate = False
    identified_signal_seed = None
    if seed == otherseed and prescale > otherprescale:
        is_backup_candidate = True
        identified_signal_seed = otherseed

    return is_backup_candidate, identified_signal_seed


def criterion_isolation(seed: str, prescale: int, otherseed: str, otherprescale: int) -> (bool, str):
    raise NotImplementedError


if __name__ == '__main__':
    print('\n*** WARNING: This script is under development. Use with caution! ***\n')

    parser = argparse.ArgumentParser()
    parser.add_argument('filename',
            help='Name/path of the PS table file',
            type=str)

    args = parser.parse_args()

    table = read_table(args.filename)
    separate_signal_and_backup_seeds(table)
