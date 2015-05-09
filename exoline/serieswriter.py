import sys
from datetime import datetime
import re
import platform

import pytz
import tzlocal
import six

if sys.version_info < (3, 0):
    import unicodecsv as csv
else:
    import csv

try:
    from ..exoline.exocommon import ExoException
except:
    from exoline.exocommon import ExoException


class SeriesWriter:
    headers = None
    dw = None
    options = None

    def __init__(self, headers, options={}):
        '''options may include:
            format: csv|raw|human
            tz: Olson TZ name
            timeformat: unix|human|iso8601|excel'''
        self.headers = headers
        self.options = options
        self.recarriage = re.compile('\r(?!\\n)')

        if 'format' not in options:
            options['format'] = 'csv'
        tz = None
        if 'tz' not in options or options['tz'] == None:
            # default to UTC
            try:
                # this single call is slow if pytz is compressed
                # running pip unzip pytz fixes it
                tz = tzlocal.get_localzone()
            except pytz.UnknownTimeZoneError:
                # Unable to detect local time zone, defaulting to UTC
                tz = pytz.utc
        else:
            tz = options['tz']
            try:
                tz = pytz.timezone(tz)
            except Exception:
                #default to utc if error
                raise ExoException(
                    'Error parsing --tz option, defaulting to local timezone')
        options['tz'] = tz
        if 'timeformat' not in options:
            options['timeformat'] = 'human'

        if options['format'] == 'csv':
            self.dw = csv.DictWriter(sys.stdout, headers)
        if options['format'] == 'human' and len(headers) > 2:
            raise Exception('format: human only supported for single value output')


    def _write_raw(self, timestamp, values):
        if not six.PY3 and isinstance(values[0], six.string_types):
            # Beer bounty for anyone who can tell me how to make
            # both of these work without this awkward try: except:
            # $ ./testone.sh utf8_test -e py27
            # $ exoline/exo.py read myClient foo --format=raw | tail -100
            try:
                # this works with stdout piped to
                print(values[0])
            except UnicodeEncodeError:
                # this works from inside test using StringIO
                print(values[0].encode('utf-8'))
        else:
            print(values[0])

    def _write_other(self, timestamp, values):
        if self.options['timeformat'] == 'unix':
            dt = timestamp
        elif self.options['timeformat'] == 'iso8601':
            dt = datetime.isoformat(
                pytz.utc.localize(datetime.utcfromtimestamp(timestamp))
            )
        elif self.options['timeformat'] == 'excel':
            # This date format works for Excel scatter plots
            dt = pytz.utc.localize(
                datetime.utcfromtimestamp(timestamp)
            ).strftime('%m/%d/%y %H:%M:%S')
        else:
            dt = pytz.utc.localize(
                datetime.utcfromtimestamp(timestamp)
            ).astimezone(self.options['tz'])


        def stripcarriage(s):
            # strip carriage returns not followed
            if isinstance(s, six.string_types):
                return self.recarriage.sub('', s)
            else:
                return s

        if self.options['format'] == 'csv':
            row = {'timestamp': str(dt)}
            values_dict = dict(
                [(str(self.headers[i + 1]), stripcarriage(values[i]))
                    for i in range(len(self.headers) - 1)])
            row.update(values_dict)
            self.dw.writerow(row)
        else:
            # human
            nocolor = platform.system() == 'Windows'
            GRAY = '' if nocolor else '\033[1;30m'
            ENDC = '' if nocolor else '\033[0m'

            if self.options['timeformat'] == 'human':
                # sass style timestamp
                dt = '[' + GRAY + str(dt).split(' ')[1].split('-')[0] + ENDC + ']'

            print("{0} {1}".format(str(dt), values[0]))

    def write(self, timestamp, values):
        '''Write into a log'''
        if self.options['format'] == 'raw':
            self._write_raw(timestamp, values)
        else:
            self._write_other(timestamp, values)

    def write_headers(self):
        if self.options['format'] == 'csv':
            self.dw.writerow(dict([(h, h) for h in self.headers]))
