# Data Import in Python

CSV files imported into Python using Pandas have NaN values for unwritten dataports if dataports were written at separate times. You can use the Pandas ffill (forward fill) or bfill (backward fill) to replace these NaN values.

```
$ exo read sensor1 humidity temperature gas event --limit=200 --header=name > sensor1.csv
$ ipython
In [1]: import pandas as pd
In [2]: import numpy as np
In [3]: sensor1 = pd.read_csv('sensor1.csv')
In [4]: sensor1
Out[4]:
                     timestamp  Humidity  Temperature  gas   event
0    2013-09-19 11:12:32-05:00      71.7           22  263  button
1    2013-09-19 11:12:24-05:00      71.8           22  262  button
2    2013-09-19 11:12:17-05:00      71.9           22  263  button
3    2013-09-19 11:12:09-05:00      71.8           22  261  button
4    2013-09-19 11:12:00-05:00      71.7           22  263  button
5    2013-09-19 11:11:52-05:00      71.8           22  263  button
6    2013-09-19 11:11:44-05:00      71.9           22  262  button
7    2013-09-19 11:11:37-05:00      71.9           22  263  button
8    2013-09-19 11:11:29-05:00      72.0           22  261  button
9    2013-09-19 11:11:22-05:00      72.0           22  261  button
10   2013-09-19 11:11:14-05:00      72.0           22  264  button
11   2013-09-19 11:10:13-05:00      72.1           22  262  button
12   2013-09-19 11:10:06-05:00      72.0           22  263  button
13   2013-09-19 11:09:58-05:00      72.0           22  263  button
14   2013-09-19 11:09:50-05:00      71.9           22  262  button
15   2013-09-19 11:09:43-05:00      71.9           22  265  button
16   2013-09-19 11:09:33-05:00      71.9           22  263  button
17   2013-09-19 11:09:26-05:00      71.9           22  263  button
18   2013-09-19 11:09:16-05:00      71.9           22  264  button
19   2013-09-19 11:09:07-05:00      71.9           22  263  button
20   2013-09-19 11:08:59-05:00      71.9           22  263  button
21   2013-09-19 11:08:52-05:00      71.9           22  263  button
22   2013-09-19 11:08:42-05:00      71.8           22  264  button
23   2013-09-19 11:08:33-05:00      71.7           22  264  button
24   2013-09-19 11:08:23-05:00      71.7           22  264  button
25   2013-09-19 11:08:05-05:00      71.9           22  264  button
26   2013-09-19 11:07:55-05:00      71.7           22  263  button
27   2013-09-19 11:07:48-05:00      71.8           22  262  button
28   2013-09-19 11:07:40-05:00      71.9           22  263  button
29   2013-09-19 11:07:33-05:00      71.9           22  263  button
..                         ...       ...          ...  ...     ...
370  2013-08-14 20:26:11-05:00       NaN          NaN  NaN  button
371  2013-08-14 20:09:41-05:00       NaN          NaN  NaN  button
372  2013-08-14 19:48:58-05:00       NaN          NaN  NaN  button
373  2013-08-14 19:28:15-05:00       NaN          NaN  NaN  button
374  2013-08-14 19:10:14-05:00       NaN          NaN  NaN  button
375  2013-08-14 10:59:32-05:00       NaN          NaN  NaN   setup
376  2013-08-11 20:53:23-05:00       NaN          NaN  NaN  button
377  2013-08-11 20:42:58-05:00       NaN          NaN  NaN  button
378  2013-08-11 20:00:51-05:00       NaN          NaN  NaN  button
379  2013-08-11 12:42:53-05:00       NaN          NaN  NaN  button
380  2013-08-11 11:09:40-05:00       NaN          NaN  NaN  button
381  2013-08-11 10:38:35-05:00       NaN          NaN  NaN  button
382  2013-08-11 09:46:51-05:00       NaN          NaN  NaN  button
383  2013-08-11 09:30:39-05:00       NaN          NaN  NaN  button
384  2013-08-11 09:26:02-05:00       NaN          NaN  NaN  button
385  2013-08-11 09:24:51-05:00       NaN          NaN  NaN  button
386  2013-08-11 06:27:00-05:00       NaN          NaN  NaN  button
387  2013-08-11 05:55:24-05:00       NaN          NaN  NaN  button
388  2013-08-11 04:57:23-05:00       NaN          NaN  NaN  button
389  2013-08-11 04:46:58-05:00       NaN          NaN  NaN  button
390  2013-08-11 03:44:52-05:00       NaN          NaN  NaN  button
391  2013-08-11 03:24:10-05:00       NaN          NaN  NaN  button
392  2013-08-11 02:57:28-05:00       NaN          NaN  NaN  button
393  2013-08-11 02:05:42-05:00       NaN          NaN  NaN  button
394  2013-08-11 01:38:58-05:00       NaN          NaN  NaN  button
395  2013-08-11 01:08:00-05:00       NaN          NaN  NaN  button
396  2013-08-10 23:49:29-05:00       NaN          NaN  NaN  button
397  2013-08-10 23:40:20-05:00       NaN          NaN  NaN  button
398  2013-08-10 22:20:43-05:00       NaN          NaN  NaN  button
399  2013-08-10 20:51:51-05:00       NaN          NaN  NaN  button

In [4]: sensor1_fill = sensor1.fillna(method='ffill').fillna(method='bfill')
In [5]: sensor1_fill
Out[4]:
                     timestamp  Humidity  Temperature  gas   event
0    2013-09-19 11:12:32-05:00      71.7           22  263  button
1    2013-09-19 11:12:24-05:00      71.8           22  262  button
2    2013-09-19 11:12:17-05:00      71.9           22  263  button
3    2013-09-19 11:12:09-05:00      71.8           22  261  button
4    2013-09-19 11:12:00-05:00      71.7           22  263  button
5    2013-09-19 11:11:52-05:00      71.8           22  263  button
6    2013-09-19 11:11:44-05:00      71.9           22  262  button
7    2013-09-19 11:11:37-05:00      71.9           22  263  button
8    2013-09-19 11:11:29-05:00      72.0           22  261  button
9    2013-09-19 11:11:22-05:00      72.0           22  261  button
10   2013-09-19 11:11:14-05:00      72.0           22  264  button
11   2013-09-19 11:10:13-05:00      72.1           22  262  button
12   2013-09-19 11:10:06-05:00      72.0           22  263  button
13   2013-09-19 11:09:58-05:00      72.0           22  263  button
14   2013-09-19 11:09:50-05:00      71.9           22  262  button
15   2013-09-19 11:09:43-05:00      71.9           22  265  button
16   2013-09-19 11:09:33-05:00      71.9           22  263  button
17   2013-09-19 11:09:26-05:00      71.9           22  263  button
18   2013-09-19 11:09:16-05:00      71.9           22  264  button
19   2013-09-19 11:09:07-05:00      71.9           22  263  button
20   2013-09-19 11:08:59-05:00      71.9           22  263  button
21   2013-09-19 11:08:52-05:00      71.9           22  263  button
22   2013-09-19 11:08:42-05:00      71.8           22  264  button
23   2013-09-19 11:08:33-05:00      71.7           22  264  button
24   2013-09-19 11:08:23-05:00      71.7           22  264  button
25   2013-09-19 11:08:05-05:00      71.9           22  264  button
26   2013-09-19 11:07:55-05:00      71.7           22  263  button
27   2013-09-19 11:07:48-05:00      71.8           22  262  button
28   2013-09-19 11:07:40-05:00      71.9           22  263  button
29   2013-09-19 11:07:33-05:00      71.9           22  263  button
..                         ...       ...          ...  ...     ...
370  2013-08-14 20:26:11-05:00      72.6           22  263  button
371  2013-08-14 20:09:41-05:00      72.6           22  263  button
372  2013-08-14 19:48:58-05:00      72.6           22  263  button
373  2013-08-14 19:28:15-05:00      72.6           22  263  button
374  2013-08-14 19:10:14-05:00      72.6           22  263  button
375  2013-08-14 10:59:32-05:00      72.6           22  263   setup

```

For other options to work around missing data, see:

http://pandas.pydata.org/pandas-docs/version/0.15.2/missing_data.html


