library(readr)
library(dplyr)

dat = read_csv("~/Projects/Oregon-Coast-GFW-Data/data/OregonCoast_2016-01-01_2018-12-31.csv")

# Number obs
nrow(dat)
# 67,851,615

# Number of Vessels
length(unique(dat$mmsi))
# 21904

