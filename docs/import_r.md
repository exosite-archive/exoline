# Data Import in R

CSV files imported into R have NA values when all dataports aren't written at once. To work around this, you can use the [zoo package](http://cran.r-project.org/web/packages/zoo/index.html) to carry the last observation forward.

```
$ exo read sensor1 humidity temperature gas event --limit=200 --header=name > sensor1.csv
$ r
> install.packages("zoo")
> library("zoo")
> sensor1 = read.csv('sensor1.csv')
> sensor1 = read.csv('export.csv', na.strings=c('n/a','')) 

> sensor1
                    timestamp Humidity Temperature gas  event
...
195 2013-09-19 10:44:41-05:00     72.6          22 265   <NA>
196 2013-09-19 10:44:33-05:00     72.7          22 264   <NA>
197 2013-09-19 10:44:25-05:00     72.7          22 266   <NA>
198 2013-09-19 10:44:18-05:00     72.7          22 265   <NA>
199 2013-09-19 10:44:10-05:00     72.6          22 264   <NA>
200 2013-09-19 10:44:03-05:00     72.6          22 263   <NA>
201 2013-09-19 07:32:19-05:00       NA          NA  NA button
202 2013-09-18 19:12:58-05:00       NA          NA  NA button
203 2013-09-17 18:27:55-05:00       NA          NA  NA  setup
...
> sensor1_locf = na.locf(na.locf(sensor1), fromLast = TRUE)
> sensor1_locf
                    timestamp Humidity Temperature gas  event
...
195 2013-09-19 10:44:41-05:00     72.6          22 265 button
196 2013-09-19 10:44:33-05:00     72.7          22 264 button
197 2013-09-19 10:44:25-05:00     72.7          22 266 button
198 2013-09-19 10:44:18-05:00     72.7          22 265 button
199 2013-09-19 10:44:10-05:00     72.6          22 264 button
200 2013-09-19 10:44:03-05:00     72.6          22 263 button
201 2013-09-19 07:32:19-05:00     72.6          22 263 button
202 2013-09-18 19:12:58-05:00     72.6          22 263 button
203 2013-09-17 18:27:55-05:00     72.6          22 263  setup
...

```
