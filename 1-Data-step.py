import spatialIUU.processGFW as siuu
import os

# Set global constants
global GFW_DIR, GFW_OUT_DIR_CSV, GFW_OUT_DIR_FEATHER, PROC_DATA_LOC, MAX_SPEED, REGION, lon1, lon2, lat1, lat2

siuu.GFW_DIR = '/data2/GFW_point/'
siuu.GFW_OUT_DIR_CSV = '/home/server/pi/homes/woodilla/Data/GFW_point/OregonCoast/csv/'
siuu.GFW_OUT_DIR_FEATHER = '/home/server/pi/homes/woodilla/Data/GFW_point/OregonCoast/feather/'
siuu.PROC_DATA_LOC = '/home/server/pi/homes/woodilla/Projects/Oregon-Coast-GFW-Data/data/'
siuu.REGION = 'OregonCoast'
siuu.MAX_SPEED = 32

# Check if dir exists and create
os.makedirs(siuu.PROC_DATA_LOC, exist_ok=True) 

siuu.region = 1
siuu.lon1 = -135
siuu.lon2 = -123
siuu.lat1 = 42
siuu.lat2 = 49


# Oregon Coast 2016-2018
siuu.compileData('2018-01-01', '2018-01-03', 1, parallel=True, ncores=30)

lon1 = -135
lon2 = -123
lat1 = 42
lat2 = 49

GFW_DIR = '/data2/GFW_point/'
GFW_OUT_DIR_CSV = '/home/server/pi/homes/woodilla/Data/GFW_point/OregonCoast/csv/'
GFW_OUT_DIR_FEATHER = '/home/server/pi/homes/woodilla/Data/GFW_point/OregonCoast/feather/'
PROC_DATA_LOC = '/home/server/pi/homes/woodilla/Projects/Oregon-Coast-GFW-Data/data/'
REGION = 'OregonCoast'
MAX_SPEED = 32

beg_date = '2018-01-01'
end_date = '2018-01-03'
region = 1
parallel=False
ncores=None