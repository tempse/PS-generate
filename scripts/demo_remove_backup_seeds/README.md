# Demo: `remove_backup_seeds.py`

Used menu rate table: [menu_v2_1_0_rate.csv](/tests/data/menu_v2_1_0_rate.csv)

Run the following command in order to produce a first set of rate tables.
```
cd ..  # brings you back to the scripts/ directory
python remove_backup_seeds.py ../tests/data/menu_v2_1_0_rate.csv
```

This creates the following new files (click on the file names for a nice preview):
- [`backup_seeds.csv`](./backup_seeds.csv) / [`backup_seeds.html`](https://htmlpreview.github.io/?https://raw.githubusercontent.com/tempse/PS-tools/demo/remove-backup-seeds/scripts/demo_remove_backup_seeds/backup_seeds.html): the list of identified backup seeds
- [`signal_seeds.csv`](./signal_seeds.csv) / [`signal_seeds.html`](https://htmlpreview.github.io/?https://raw.githubusercontent.com/tempse/PS-tools/demo/remove-backup-seeds/scripts/demo_remove_backup_seeds/signal_seeds.html): the list of seeds without any found
  backup seeds (i.e., the signal seed candidates)
- [`backup_seeds_summary.html`](https://htmlpreview.github.io/?https://raw.githubusercontent.com/tempse/PS-tools/demo/remove-backup-seeds/scripts/demo_remove_backup_seeds/backup_seeds_summary.html): A table which contains information about the
  identified backup seeds (their names and prescales, their associated signal
  seeds as well as the criteria which were used to make the decisions)
