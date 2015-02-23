#!/usr/bin/env python
import os
import os.path
import sys
import time
import glob
import re


RETRIES_MAX = 10
RETRY_WAIT = 5  # seconds


def _recursive_delete(dir):
    os.system("chmod 700 -R \"%s\"" % dir)
    os.system("rm -rf \"%s\"" % dir)


class IncrementalBackup:
    """
    Example usage:
    backup = IncrementalBackup(source='tom@myserver.org:/home/tom/',
                               destination='/mnt/backups/myserver.org',
                               keep_days=30,
                               keep_months=2)
    backup.do()
    """
    def __init__(self, source, destination,
                 keep_days=31, keep_months=3, exclude_patterns=[], preCmd="", postCmd=""):
        self.backup_target = destination
        self.backupOriginalLocation = source
        self.keep_days = keep_days
        self.keep_months = keep_months
        self.preCmd = preCmd
        self.postCmd = postCmd
        self.exclude_patterns = exclude_patterns

        self.check_stuff()

    def check_stuff(self):
        if (not os.path.isdir(self.backup_target)):
            print("ERROR in backup of {0} to {1}: {1} does not exist.".format(self.backupOriginalLocation, self.backup_target))
            sys.exit(-1)

    def GetDailyTarget(self, num):
        g = glob.glob(self.backup_target+"/daily%03d-*" % num)
        if len(g) == 0:
            return "", ""
        else:
            bname = os.path.basename(g[0])
            m = re.match("daily(\d\d\d)-([A-Za-z\s\d:\._]*)", bname)
            if not m:
                return "", ""
            else:
                return g[0], m.group(2)

    def GetNewDailyTarget(self, num):
        return (self.backup_target+"/daily%03d-" % num) + \
            time.strftime("%b_%d_%Y_%H.%M.%S", time.gmtime())

    def GetThisDailyTarget(self, num, date):
        return (self.backup_target+"/daily%03d-%s" % (num, date))

    def GetMonthlyTarget(self, year, month):
        return (self.backup_target+"/year%d-month%02d") % (year, month)

    def DoDailyBackups(self):
        # bump the old shit up a day
        path, date = self.GetDailyTarget(self.keep_days-1)
        if path:
            _recursive_delete(path)
        for i in xrange(self.keep_days-1, -1, -1):
            a, aDate = self.GetDailyTarget(i)
            b = self.GetThisDailyTarget(i+1, aDate)
            if a and b:
                # print "mv \"%s\" \"%s\"" % (a, b)
                os.system("mv \"%s\" \"%s\"" % (a, b))
        newDaily = self.GetNewDailyTarget(0)
        # make hard link cp
        # print "cp -al \"%s\" \"%s\"" % (self.GetDailyTarget(1)[0], newDaily)
        os.system("cp -al \"%s\" \"%s\"" % (self.GetDailyTarget(1)[0], newDaily))
        # build excluded paths arguments
        excludes = " ".join(
            ["--exclude '{0}'".format(i) for i in self.exclude_patterns]
        )
        # update latest copy
        cmd = "rsync -avzxP %s --delete \"%s\" \"%s/\"" % (excludes, self.backupOriginalLocation, newDaily)
        print cmd

        # retry rsync command on failure
        for i in xrange(0, RETRIES_MAX):
            if os.system(cmd) == 0:
                break
            time.sleep(RETRY_WAIT)

        if i == RETRIES_MAX:
            print("FAILURE: Maximum retries ({0}) reached.".format(RETRIES_MAX))
        else:
            print("SUCCESS: {0} retries.".format(i))

    def GetMonthYear(self):
        t = time.gmtime()
        return (t[1], t[0])

    def ExpireMonthlies(self):
        curMonth, curYear = self.GetMonthYear()
        curCanonical = 12*curYear + (curMonth-1)
        allmonthlies = glob.glob(self.backup_target+"/year*")
        for b in allmonthlies:
            m = re.match("year(\d\d\d\d)-month(\d\d)", os.path.basename(b))
            if (m):
                year = int(m.group(1))
                month = int(m.group(2))
                canonical = 12*year + (month-1)
                if (curCanonical - canonical >= self.keep_months):
                    print b, "is too old. deleting"
                    _recursive_delete(b)

    def DoMonthlyBackups(self):
        if self.keep_months == 0:
            return
        # first check none are too old
        self.ExpireMonthlies()
        month, year = self.GetMonthYear()
        # make hard link cp
        dir = self.GetMonthlyTarget(year, month)
        if (not os.path.isdir(dir)):
            print "Doing monthly backup"
            os.system("cp -al \"%s\" \"%s\"" % (self.GetDailyTarget(0)[0], self.GetMonthlyTarget(year, month)))

    def do(self):
        print("Starting backup of {0} to {1}".format(self.backupOriginalLocation, self.backup_target))
        if self.preCmd and (os.system(self.preCmd) != 0):
            print self.backup_target, "Error executing precommand", self.preCmd
            if self.postCmd and (os.system(self.postCmd) != 0):
                print self.backup_target, "Error executing postcommand", self.postCmd
            return
        # make sure backup dir exists
        if (not os.path.isdir(self.backup_target)):
            os.mkdir(self.backup_target)
        self.DoDailyBackups()
        self.DoMonthlyBackups()

        if self.postCmd and (os.system(self.postCmd) != 0):
            print self.backup_target, "Error executing postcommand", self.postCmd
            return
