#!/usr/bin/env python
from libincrementalbackup import IncrementalBackup

IncrementalBackup(
    source='./testsource',
    destination='./testdest',
    exclude_patterns=['testsource/exclude-me.txt'],
    keep_days=5,
    keep_months=0
).do()

IncrementalBackup(
    source='root@example.com:/',
    destination='/mnt/backups/example.com',
    keep_days=10,
    keep_months=3
).do()
