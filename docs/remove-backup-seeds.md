# Backup seed identification script

A script that finds (most of) the seeds in a prescale (PS) table that are backup
seeds to other seeds and creates separate tables for backup and no-backup seeds
in different formats (inclusive / unprescaled / prescaled).

## Basic usage

In its simplest form, the script can be run as follows:
```
python remove_backup_seeds.py <PS-table>
```
where `<PS-table>` is a table containing seed names and prescale values in CSV
format (see [this example of a valid table](/tests/data/menu_v2_1_0_rate.csv)).

### Positional arguments (required)

- `filename`: Name/path of the CSV prescale table file

### Optional arguments

- `-h` / `--help`: Display a help message and exit
- `-m WRITE_MODE` / `--mode WRITE_MODE`: Specify which seeds to keep in the
  output files. Allowed options for `WRITE_MODE` are *inclusive* (default), *unprescaled* and
  *prescaled*
- `-b BACKUP_SEEDS` / `--backup-seeds BACKUP_SEEDS`: Give a filename containing
  a list of known backup seeds. All given seeds are consistently treated as
  backup seeds without any further checks.
- `--keep-zero-prescales`: Do *not* ignore seeds with zero prescales (default:
  False)
- `--no-prescale-checks`: Do not check whether backup seed prescales are larger
  than or equal to other seeds' prescales
- `-q` / `--quiet`: Make script less verbose

### Examples

- Run in "default mode" (i.e., ignore all PS=0 seeds, require backup seeds to
  always have at least the same prescales as their potential no-backup seed
  counterparts, create output tables allowing all prescale values):
  ```
  python remove_backup_seeds.py ../tests/data/menu_v2_1_0_rate.csv
  ```

- Run in "default mode" and only output a table with unprescaled (PS=1) seeds:
  ```
  python remove_backup_seeds.py ../tests/data/menu_v2_1_0_rate.csv --mode unprescaled
  ```

- Run in "default mode" and provide a list of seeds that are known to be
  backup seeds (but usually not identified as such by the script):
  ```
  python remove_backup_seeds.py ../tests/data/menu_v2_1_0_rate.csv -b ../tests/data/false-positive-signal-seeds.txt
  ```

## Backup seed identification logic

### Backup seed definition

A L1 seed is a backup seed to another L1 seed if one of the following conditions
applies:
- higher p<sub>T</sub> cut
  > Currently supported: single-, double-, triple- and quadruple-object seeds
    like L1_SingleMu3(\_\*), L1_DoubleMu0(\_\*), L1_DoubleMu_15_7(\_\*),
	L1_TripleMu3(\_\*), L1_TripleMu_5_3p5_2p5er1p2(\_\*),
	L1_QuadJet36er2p5(\_\*), L1_QuadJet_95_75_65_20(\_\*)
- lower "er" cut ("eta restriction": |eta| < X)
- lower "dR_Max" or higher "dR_Min" cut
- tighter "MassXtoY" range
- muon quality: SQ instead of DQ, DQ instead of OQ
  - "single", "double", "open" quality
  - default quantities (if quality not explicitly given): SQ for single-muon,
    DQ for multi-muon triggers
- isolation cut: "Iso" instead of "LooseIso", "LooseIso" instead of no isolation
  cut
- higher p<sub>T</sub> threshold in cases where XX is the only difference
  between two seeds, and XX applies to "EGXX", "ETMHFXX", "HTTXX" "_MtXX",
  "TauXX" or "Mass_MinXX" (regardless of where the condition shows up in the
  seed)

### Algorithm outline

1) Import a prescale table in CSV format.

1) Loop over the seeds, for each seed do...
    1) Create all possible pairings between the current seeds and all other
	   seeds.
	1) A backup seed is required to have a larger or equal prescale value than
	   a potential "main" (no-backup) seed, unless the option
	   `--no-prescale-checks` is given (in which case prescales are ignored
	   altogether).
    1) For each seed pair, require that at least one of the "backup seed
	   criteria" (see above) applies. If at least on criterion applies, the seed
	   is removed. If not, the seed remains in the table.
	   > (In order to be one the safe side, there must not be any other
	   differences between two seeds apart from the respective criteria,
	   otherwise a seed will not be classified as a backup seed!)

1) Output several result tables (as CSV+HTML):
    1) table of backup seeds
    1) table of "main" (i.e., no-backup) seeds
    1) summary of identified backup seeds (incl. their associated main seeds
	   and the criteria responsible for the respective decisions)
