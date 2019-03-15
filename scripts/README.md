# Scripts

Collection of various scripts for prescale and rate table operations.

## Backup seed identification script

> [`remove_backup_seeds.py`](./remove_backup_seeds.py)

A script that finds (most of) the seeds in a rate table that are backup seeds to
other seeds and creates separate rate tables for backup and no-backup seeds in
different formats (inclusive / unprescaled / prescaled).

For detailed information about this script and its intended use cases, see the
[dedicated documention page](/docs/remove-backup-seeds.md).
