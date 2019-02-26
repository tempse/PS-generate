from typing import Union
import pandas as pd

def estimate_value(name: str):
    # TODO extend functionality of this method
    return None 


def find_table_value(pstable: pd.DataFrame, seed: str,
        col: str) -> Union[int, float, str]:
    """
    Retrieve a specific value corresponding to a given seed and column name.

    Parameters
    ----------
    pstable : pandas.DataFrame
        PS table from which the value should be obtained
    seed : str
        Name of the desired seed
    col : str
        Name of the desired column

    Returns
    -------
    Cell content corresponding to seed and col, as well as an exit code (0 if
    the cell content was found and copied; 1 if the cell content was not found
    and therefore estimated). If cell is not found, the function estimate_value
    is called and its return value is forwarded.

    """

    if 'Name' not in pstable.columns:
        raise RuntimeError('PS table does not have a column \'Name\'')

    if seed in pstable['Name'].values:
        return (pstable.loc[pstable['Name'] == seed])[col].values[0], 0
    else:
        return estimate_value(seed), 1


def make_empty_table(pstable: pd.DataFrame) -> pd.DataFrame:
    """
    Create a new, empty dataframe with the structure of a given one.

    Parameters
    ----------
    pstable : pandas.DataFrame
        DataFrame that serves as a template for the new DataFrame

    Returns
    -------
    pandas.DataFrame
        DataFrame that has the same column structure as the input DataFrame, but
        is empty.

    """

    empty_table = pd.DataFrame(columns=pstable.columns)
    return empty_table

