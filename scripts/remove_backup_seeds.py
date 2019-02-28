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
        # criterion_pT,
        # criterion_er,
        # criterion_dRmax,
        # criterion_dRmin,
        # criterion_MassXtoY,
        criterion_quality,
        # criterion_isolation,
    ]

    for otherseed,otherprescale in zip(all_seeds, all_prescales):
        for criterion in criterion_functions:
            if not all([type(s) == str for s in (seed,otherseed)]): continue
            is_backup_seed, identified_signal_seed = criterion(seed, prescale,
                    otherseed, otherprescale)

            if is_backup_seed:
                print('+++ backup: {};    signal: {}'.format(seed,otherseed))
            else:
                pass
                # print('--- backup: {};    signal: {}'.format(otherseed,seed))

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
    # TODO explain what SQ, DQ, OQ stand for
    # TODO check the following logic
    is_backup_candidate = False

    qualities = ('_SQ','_DQ','_OQ')

    seed_basename = get_seed_basename(seed)

    if seed_basename is None:
        return False, None

    if not otherseed.startswith(seed_basename):
        return False, None

    if 'singlemu' in seed_basename.lower():
        # if single muon seed has default quality (i.e., 'SQ'; not explicitly
        # given in the seed name) and the other seed has a looser quality
        # criterion (i.e., 'DQ' or 'OQ')
        if all([quality not in seed for quality in ('_SQ','_DQ','_OQ')]) and \
                any([quality in otherseed for quality in ('_DQ','_OQ')]):
            # check whether the rest of the seed names matches
            # TODO this will not recognize backup seeds if two qualities change at the same time (eg, pT cut and eta restriction)
            seed_stripped = seed
            otherseed_stripped = otherseed
            for substr in ((seed_basename,) + qualities):
                seed_stripped = seed_stripped.replace(substr,'')
                otherseed_stripped = otherseed_stripped.replace(substr,'')

            if seed_stripped == otherseed_stripped:
                is_backup_candidate = True

        if '_SQ' in seed and any([quality in otherseed for quality in ('_DQ','_OQ')]):
            seed_stripped = seed
            otherseed_stripped = otherseed
            for substr in ((seed_basename,) + qualities):
                seed_stripped = seed_stripped.replace(substr,'')
                otherseed_stripped = otherseed_stripped.replace(substr,'')

            if seed_stripped == otherseed_stripped:
                is_backup_candidate = True

        if '_DQ' in seed and '_OQ' in otherseed:
            seed_stripped = seed
            otherseed_stripped = otherseed
            for substr in ((seed_basename,) + qualities):
                seed_stripped = seed_stripped.replace(substr,'')
                otherseed_stripped = otherseed_stripped.replace(substr,'')

            if seed_stripped == otherseed_stripped:
                is_backup_candidate = True

    if 'doublemu' in seed_basename.lower():
        # if double muon seed has default quality (i.e., 'DQ'; not explicitly
        # given in the seed name) and the other seed has a looser quality
        # criterion (i.e., 'OQ')
        if '_SQ' in seed and all([quality not in otherseed for quality in ('_SQ','_DQ','_OQ')]):
        # if all([quality not in seed for quality in ('_SQ','_DQ','_OQ')]) and \
        #         '_OQ' in otherseed:
            # check whether the rest of the seed names matches
            # TODO this will not recognize backup seeds if two qualities change at the same time (eg, pT cut and eta restriction)
            seed_stripped = seed
            otherseed_stripped = otherseed
            for substr in ((seed_basename,) + qualities):
                seed_stripped = seed_stripped.replace(substr,'')
                otherseed_stripped = otherseed_stripped.replace(substr,'')

            if seed_stripped == otherseed_stripped:
                is_backup_candidate = True

        if '_SQ' in seed and any([quality in otherseed for quality in ('_DQ','_OQ')]):
            seed_stripped = seed
            otherseed_stripped = otherseed
            for substr in ((seed_basename,) + qualities):
                seed_stripped = seed_stripped.replace(substr,'')
                otherseed_stripped = otherseed_stripped.replace(substr,'')

            if seed_stripped == otherseed_stripped:
                is_backup_candidate = True

        if all([quality not in seed for quality in ('_SQ','_DQ','_OQ')]) and \
                '_OQ' in otherseed:
            seed_stripped = seed
            otherseed_stripped = otherseed
            for substr in ((seed_basename,) + qualities):
                seed_stripped = seed_stripped.replace(substr,'')
                otherseed_stripped = otherseed_stripped.replace(substr,'')

            if seed_stripped == otherseed_stripped:
                is_backup_candidate = True

        if '_DQ' in seed and '_OQ' in otherseed:
            seed_stripped = seed
            otherseed_stripped = otherseed
            for substr in ((seed_basename,) + qualities):
                seed_stripped = seed_stripped.replace(substr,'')
                otherseed_stripped = otherseed_stripped.replace(substr,'')

            if seed_stripped == otherseed_stripped:
                is_backup_candidate = True

    if 'triplemu' in seed_basename.lower():
        pass

    if 'quadmu' in seed_basename.lower():
        pass

    identified_signal_seed = otherseed if is_backup_candidate else None

    return is_backup_candidate, identified_signal_seed


def criterion_prescale(seed: str, prescale: int, otherseed: str, otherprescale: int) -> (bool, str):
    raise NotImplementedError


def criterion_isolation(seed: str, prescale: int, otherseed: str, otherprescale: int) -> (bool, str):
    raise NotImplementedError


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('filename',
            help='Name/path of the PS table file',
            type=str)

    args = parser.parse_args()

    table = read_table(args.filename)
    separate_signal_and_backup_seeds(table)
