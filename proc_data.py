'''The following code processes GFW_point data as follows:

    1. Subset Patagonia shelf
    2. Create time stamp data
    3. Merge in GFW_public data
    4. Get unique MMSI ships for each day and save
    5. Organize columns
    
    Columns: 
    
    [['timestamp', 'year', 'month', 'day', 'hour', 'minute', 'second', 'mmsi', 'lat', 'lon', \
      'segment_id', 'message_id', 'type', 'speed', 'course', 'heading', 'shipname', 'callsign', \
      'destination', 'elevation_m', 'distance_from_shore_m', 'distance_from_port_m', 'nnet_score', \
      'logistic_score', 'flag', 'geartype', 'length', 'tonnage', 'engine_power', 'active_2012', \
      'active_2013', 'active_2014', 'active_2015', 'active_2016']]
'''                     

import pandas as pd
import numpy as np
import os as os
import glob
from joblib import Parallel, delayed
import multiprocessing
from datetime import datetime, timedelta
import sys
from math import radians, cos, sin, asin, sqrt

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """

    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    km = 6367 * c
    return km


def spherical_dist_populate(lat_lis, lon_lis, r=6371.0088):
    lat_mtx = np.array([lat_lis]).T * np.pi / 180
    lon_mtx = np.array([lon_lis]).T * np.pi / 180

    cos_lat_i = np.cos(lat_mtx)
    cos_lat_j = np.cos(lat_mtx)
    cos_lat_J = np.repeat(cos_lat_j, len(lat_mtx), axis=1).T

    lat_Mtx = np.repeat(lat_mtx, len(lat_mtx), axis=1).T
    cos_lat_d = np.cos(lat_mtx - lat_Mtx)

    lon_Mtx = np.repeat(lon_mtx, len(lon_mtx), axis=1).T
    cos_lon_d = np.cos(lon_mtx - lon_Mtx)

    mtx = r * np.arccos(cos_lat_d - cos_lat_i*cos_lat_J*(1 - cos_lon_d))
    return mtx


def NN_dist(data=None, lat_lis=None, lon_lis=None):

    # In miles
    # r = 3958.75

    # In km
    r = 6371.0088

    if data is not None:
        data = data.dropna()
        mmsi = data.mmsi
        data = data.sort_values('mmsi')
        lat_lis = data['lat']
        lon_lis = data['lon']
        timestamp = data['timestamp'].iat[0]

    #print(timestamp)

    lat_mtx = np.array([lat_lis]).T * np.pi / 180
    lon_mtx = np.array([lon_lis]).T * np.pi / 180

    cos_lat_i = np.cos(lat_mtx)
    cos_lat_j = np.cos(lat_mtx)
    cos_lat_J = np.repeat(cos_lat_j, len(lat_mtx), axis=1).T

    lat_Mtx = np.repeat(lat_mtx, len(lat_mtx), axis=1).T
    cos_lat_d = np.cos(lat_mtx - lat_Mtx)

    lon_Mtx = np.repeat(lon_mtx, len(lon_mtx), axis=1).T
    cos_lon_d = np.cos(lon_mtx - lon_Mtx)

    mtx = r * np.arccos(cos_lat_d - cos_lat_i*cos_lat_J*(1 - cos_lon_d))

    # Build data.frame
    matdat = pd.DataFrame(mtx)
    matdat.columns = mmsi[:]
    matdat = matdat.set_index(mmsi[:])

    # Stack and form three column data.frame
    tmatdat = matdat.stack()
    lst = tmatdat.index.tolist()
    vessel_A = pd.Series([item[0] for item in lst])
    vessel_B = pd.Series([item[1] for item in lst])
    distance = tmatdat.values

    # Get lat/lon per mmsi
    posdat = data[['mmsi', 'lat', 'lon']]
    posdat = posdat.sort_values('mmsi')

    # Build data frame
    odat = pd.DataFrame({'timestamp': timestamp, 'vessel_A': vessel_A,
                         'vessel_B': vessel_B, 'distance': distance})
    odat = odat.sort_values(['vessel_A', 'distance'])

    # Get 05-NN
    odat = odat.sort_values('distance').groupby(
        'vessel_A', as_index=False).nth([0, 1, 2, 3, 4, 5])
    odat = odat.sort_values(['vessel_A', 'distance'])

    # Merge in vessel_B lat/lon
    posdat.columns = ['mmsi', 'vessel_B_lat', 'vessel_B_lon']
    odat = odat.merge(posdat, how='left', left_on='vessel_B', right_on='mmsi')

    # Merge in vessel_A lat/lon
    posdat.columns = ['mmsi', 'vessel_A_lat', 'vessel_A_lon']
    odat = odat.merge(posdat, how='left', left_on='vessel_A', right_on='mmsi')

    odat['NN'] = odat.groupby(['vessel_A'], as_index=False).cumcount()
    odat = odat.reset_index(drop=True)
    odat = odat[['timestamp', 'vessel_A', 'vessel_B', 'vessel_A_lat',
                 'vessel_A_lon', 'vessel_B_lat', 'vessel_B_lon', 'NN', 'distance']]
    odat = odat.sort_values(['vessel_A', 'NN'])

    # Data check: Ensure have 5 NN
    nn5 = odat.sort_values('NN').groupby('vessel_A').tail(1)
    
    nn5 = nn5[nn5['NN'] == 5]
    
    unique_nn5 = nn5['vessel_A'].unique()

    odat = odat[odat.vessel_A.isin(unique_nn5)]

    return odat


def GFW_directories(GFW_DIR):
    """ Get GFW directory list """
    
    dirs = os.listdir(GFW_DIR)
    # Remove subfolders 'BK' and 'identities'
    if 'BK' in dirs:
        dirs.remove('BK')
    
    if 'identities' in dirs:
        dirs.remove('identities')
    
    return dirs



def calc_kph(data):
    """
    Calculate kph
    Args:
        data: DataFrame with datetime, lat, and lon
    Returns:
        Processed DataFrame
    """
    # Calculate distance traveled
    data = data.sort_values('timestamp')
    fobs_lat = data['lat'].iat[0]
    fobs_lon = data['lon'].iat[0]
    lat_lag = data['lat'].shift(1, fill_value=fobs_lat)
    lon_lag = data['lon'].shift(1, fill_value=fobs_lon)
    lat = data['lat'].values
    lon = data['lon'].values
    
    tlag = data['timestamp'].shift(1, fill_value=data['timestamp'].iat[0])
    
    outvalues = pd.Series()
    outvalues2 = pd.Series()
    for i in range(len(data)):
        # Calculate distance
        lat1 = lat_lag.iat[i]
        lat2 = lat[i]
        lon1 = lon_lag.iat[i]
        lon2 = lon[i]
        d = pd.Series(round(spherical_dist_populate([lat1, lat2], [lon1, lon2] )[0][1], 2))
        outvalues = outvalues.append(d, ignore_index=True)
        
        # Calculate travel time
        t1 = str(data.timestamp.iat[i])
        t2 = str(tlag.iat[i])
        
        t1 = datetime.strptime(t1, "%Y-%m-%d %H:%M:%S UTC")
        t2 = datetime.strptime(t2, "%Y-%m-%d %H:%M:%S UTC")
    
        tdiff = abs(t2 - t1)
        #print(tdiff)
        #tdiff = pd.Series(round(tdiff.seconds/60/60, 4))
        tdiff = pd.Series(round(tdiff.seconds/60/60, 4))
        outvalues2 = outvalues2.append(tdiff)
        
    data['dist'] = outvalues.values
    data['travel_time'] = outvalues2.values   
    data['kph'] = data['dist']/data['travel_time'] 
    data['kph'] = np.where(data['travel_time'] == 0, 0, data['kph'])
    return data



def interp_hr(data, start, end):

    indat = data

    # Sort data by timestamp
    data = data.sort_values('timestamp')
    data['timestamp'] = data['timestamp'].dt.round('min')

    # Get average lat/lon incase duplicate
    data = data.groupby('timestamp', as_index=False)[
        ['lat', 'lon']].agg('mean')

    # Merge and interpolate between start and end
    pdat = pd.DataFrame(
        {'timestamp': pd.date_range(start=start, end=end, freq='min')})

    # Merge and interpolate
    pdat = pdat.merge(data, on='timestamp', how='left')
    pdat['lat'] = pd.Series(pdat['lat']).interpolate()
    pdat['lon'] = pd.Series(pdat['lon']).interpolate()

    # Keep on the hour
    pdat = pdat[pd.Series(pdat['timestamp']).dt.minute ==
                0].reset_index(drop=True)

    # Back/Forward fill
    pdat = pdat.fillna(method='bfill')
    pdat = pdat.fillna(method='ffill')
    pdat['mmsi'] = indat['mmsi'].iat[0]
 

    pdat = pdat.reset_index(drop=True)
    # print(pdat)
    return pdat


#@ray.remote
def processGFW(i):
    '''Parallel function'''
    # print(f"{lon1} -> {lon2} : {lat1} -> {lat2}")
    # Get subdirectory list of files
    subdir = GFW_DIR + i
    # subdir = f"{GFW_DIR}"
    allFiles = glob.glob(subdir + "/*.csv")
    list_ = []
    # Append files in subdir
    for file_ in allFiles:
        df = pd.read_csv(file_, index_col=None, header=0, low_memory=False)
        list_.append(df)
        dat = pd.concat(list_, axis = 0, ignore_index = True)
   
    # Save unique mmsi for each day
    # unique_mmsi_data = outdat['mmsi'].unique()
    # unique_mmsi = pd.DataFrame({'mmsi':unique_mmsi_data})
    # unique_mmsi.to_feather('~/Data/GFW_point/Patagonia_Shelf/vessel_list/' + filename +  '_vessel_list'  + '.feather')

    # (1) Subset Region
    outdat = dat[(dat['lon'] >= lon1) & (dat['lon'] <= lon2)] 
    outdat = outdat[(outdat['lat'] >= lat1) & (outdat['lat'] <= lat2)]
  
    # (2) Keep vessels 1/2 kilometer from port or shore 
    # outdat = outdat[outdat['distance_from_shore_m'] >= 500]
    # outdat = outdat[outdat['distance_from_port_m'] >= 500]
    # outdat = outdat[outdat['elevation_m'] <= -100]
    
    # (3) Remove inconsistent tracks due to spoofing or noisy data
    # Results from calc_speed_dist.py
    #    quant      value
    #0    0.10   0.000000
    #1    0.20   0.000000
    #2    0.30   0.000000
    #3    0.40   0.000000
    #4    0.50   0.100000
    #5    0.60   0.400000
    #6    0.70   4.900000
    #7    0.80   9.100000
    #8    0.90  12.400000
    #9    0.95  14.400000
    #10   0.96  15.200000
    #11   0.97  16.299999
    #12   0.98  17.700001
    #13   0.99  19.900000   MPH
    #     Max 1.00   

    # Groupby mmsi and get distance and time between timestamps
    outdat = outdat.groupby('mmsi').apply(calc_kph).reset_index(drop=True)

    # print(f"311 :: {min(outdat.lon)} -> {max(outdat.lon)} : {min(outdat.lat)} -> {max(outdat.lat)}")

    # (4) Determine if stationary where distance_traveled > 1
    outdat['stationary'] = np.where(outdat['kph'] > 1, 0, 1)
    # outdat = outdat[outdat['stationary'] == 0]
    
    # Get max speed for each mmsi
    mmsi_kph = outdat.groupby('mmsi', as_index=False)['kph'].max()
    # mmsi_kph = mmsi_kph.reset_index()

    # Keep vessels travel less than 32kph but greater than 1 km
    mmsi_all = mmsi_kph['mmsi'].unique()
    mmsi_kph2 = mmsi_kph[mmsi_kph['kph'] <= MAX_SPEED]
    mmsi_keep = mmsi_kph2['mmsi'].unique()
    outdat = outdat[outdat['mmsi'].isin(mmsi_keep)]

    # print(f"325 :: {min(outdat.lon)} -> {max(outdat.lon)} : {min(outdat.lat)} -> {max(outdat.lat)}")

    # Get spoofing numbers
    # print(f"Start MMSI: {len(mmsi_all)} Keep MMSI: {len(mmsi_keep)} Percentage: {len(mmsi_keep)/len(mmsi_all)}")

    # SAVE FILE OUTPUT
        
    # (6) In/Out of EEZ (country)
    
    # (7) Calculate daily fishing effort
    # Incomplete
    # Fishing or not to calculate fishing effort
#------------------------------------------------------------------------------

    # Separate Year, month, day, hour, minute, second
    outdat.loc[:, 'timestamp'] = pd.to_datetime(outdat['timestamp'], format="%Y-%m-%d %H:%M:%S UTC")
    outdat.loc[:, 'year'] = pd.DatetimeIndex(outdat['timestamp']).year 
    outdat.loc[:, 'month'] = pd.DatetimeIndex(outdat['timestamp']).month
    outdat.loc[:, 'day'] = pd.DatetimeIndex(outdat['timestamp']).day
    outdat.loc[:, 'hour'] = pd.DatetimeIndex(outdat['timestamp']).hour
    outdat.loc[:, 'minute'] = pd.DatetimeIndex(outdat['timestamp']).minute
    outdat.loc[:, 'second'] = pd.DatetimeIndex(outdat['timestamp']).second
    
    # Merge GFW ID data (incomplete)
    #retdat = pd.merge(retdat, gfw_vessel_dat, how='left', on='mmsi')
    
    # Organize columns
    outdat = outdat[['timestamp', 'year', 'month', 'day', 'hour', 'minute', 'second', 'mmsi', 'lat', 'lon', \
                     'kph', 'dist', 'travel_time', 'stationary', \
                     'segment_id', 'message_id', 'type', 'speed', 'course', 'heading', 'shipname', 'callsign', \
                     'destination', 'elevation_m', 'distance_from_shore_m', 'distance_from_port_m']]
    
    # print(f"259 :: {min(outdat.lon)} -> {max(outdat.lon)} : {min(outdat.lat)} -> {max(outdat.lat)}")

    filename = f"{outdat['year'].iat[0]}-" + f"{outdat['month'].iat[0]}".zfill(2) + f"-" + f"{outdat['day'].iat[0]}".zfill(2)
    print(filename)
    outdat = outdat.reset_index(drop=True)
    outdat.to_feather(f"{GFW_OUT_DIR_FEATHER}{filename}.feather")
    outdat.to_csv(f"{GFW_OUT_DIR_CSV}{filename}.csv")
    # print(i)
    return 0




# -----------------------------
# Main run
# Get folder list

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

beg_date = '2016-01-01'
end_date = '2018-12-31'
region = 1
parallel=True
ncores=25


gfw_list_dirs = sorted(GFW_directories(GFW_DIR))


#results = ray.get([processGFW.remote(i) for i in folders])
pool = multiprocessing.Pool(ncores, maxtasksperchild=1)         
pool.map(processGFW, gfw_list_dirs)
pool.close()


print('Bind all feather files')
# Get feather files
feather_files = sorted(glob.glob(GFW_OUT_DIR_FEATHER + "*.feather"))
feather_files = [item.replace(f"{GFW_OUT_DIR_FEATHER}", '') for item in feather_files]
feather_files = [item.replace('.feather', '') for item in feather_files]
# start_index = [feather_files.index(i) for i in feather_files if f"{beg_date}" in i]
# end_index = [feather_files.index(i) for i in feather_files if f"{end_date}" in i]
# files = feather_files[start_index[0] - nmargin:end_index[0] + nmargin]

files = feather_files
print('bind data')
# Bind data
list_ = []
for file in files:
    df = pd.read_feather(f"{GFW_OUT_DIR_FEATHER}{file}.feather")
    #print(df.day.iat[0])
    #print(df.columns)
    list_.append(df)
    mdat = pd.concat(list_, sort=False)

mdat = mdat[(mdat['lon'] >= lon1) & (mdat['lon'] <= lon2)] 
mdat = mdat[(mdat['lat'] >= lat1) & (mdat['lat'] <= lat2)]

print("Saving bound feather files")
savedat = mdat.reset_index(drop=True)
savedat.to_feather(f"{PROC_DATA_LOC}{REGION}_{region}_{beg_date}_{end_date}.feather")
savedat.to_csv(f"{PROC_DATA_LOC}{REGION}_{region}_{beg_date}_{end_date}.csv")
