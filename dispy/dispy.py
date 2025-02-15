import numpy as np
import pandas as pd

def convert_to_float(x):
    x = ''.join(char for char in str(x) if char.isdigit() or char == '.')
    if x == '':
        x = 'nan'
    return float(x)

def custom_sum(arr):
    if all(np.isnan(arr)):
        return np.nan
    else:
        return np.nansum(arr) 

class DIS:
    def __init__(self):
        self.read_udns()
        pass
        
    def load_extract(self, fpath):
        """Read file"""
        print('loading data...')
        
        chunksize=10000
        title = ' (DIS ENT - OU Activity Indicator Results Self-Service1)'

        fieldnames = ['Activity Code', 'Activity Name', 'Collection Period Frequency', 'Fiscal Year', 
                      'Indicator Code', 'Disaggregate Name','Disaggregate Code',
                      'Operating Unit', 'Reporting Organization', 'UDN', 'Actual Value','Target Value']

        # -- 
        # Iterate through the data to drop uneccesary data 
        # without loading everything into memory.
        # --
        data = []
        for chunk in pd.read_csv(fpath, usecols=[name+title for name in fieldnames], chunksize=chunksize):
            chunk = chunk[[name+title for name in fieldnames]]
            chunk.columns = fieldnames
            chunk = chunk.dropna(subset=['Actual Value','Target Value'], how='all')
            chunk['Actual Value'] = chunk['Actual Value'].map(convert_to_float)
            data.append(chunk)
            
        data = pd.concat(data, axis=0)
        
        # -- remote stupid test data and select only annual collection period
        data = data[(data['Operating Unit'] != 'DIS test bilateral (DIS-B)') & \
                    (data['Collection Period Frequency'] == 'Annual')
                   ]
        self.data = data
        print('Done loading data!')
        
    def get_aggregate_results(self, indicator):
        """Return annual aggregate results by RO and OU"""
        df = self.data[(self.data['Indicator Code'] == indicator) & (self.data['UDN'] == '3')] \
                    .groupby(['Reporting Organization','Operating Unit','Fiscal Year'])['Actual Value'].agg(custom_sum)
        df = pd.pivot_table(df.reset_index(), 
                            index=['Reporting Organization','Operating Unit'], 
                            columns=['Fiscal Year'], 
                            values='Actual Value')
        return df

    def read_udns(self, udn_path=None):
        """Read crosswalked UDN file"""
        if udn_path is None:
            #https://docs.google.com/spreadsheets/d/1JAI0TZQU8JkkPWhDKZkAYOhWJzrsdRvlZvh0lcP2590/edit?gid=292711258#gid=292711258
            udn_path = '../data/UDN to Disaggregate Crosswalk - Disaggregates and UDNs.csv'
        try:
            self.udns = pd.read_csv(udn_path)
        except:
            print('Error reading udn file')
            
    def get_udns(self, indicator):
        """Returns crosswalked udn disaggregate codes for an indicator"""
        udns = self.udns[self.udns['ic'] == indicator].dropna(how='all', axis=1)
        grpby = udns.columns[udns.columns.str.contains('order')].tolist()
        return udns.groupby(['ic']+grpby, as_index=False)['udn'].first()
    
    def get_matched_pairs(self):
        gender_gap_list = ['3.1.2.1','3.1.2.2','3.2.2.1', '3.2.2.2']
        
        # -- select data
        df = self.data[(self.data['Indicator Code'] == 'EG.3.2-27') & \
                       (self.data['UDN'].isin(gender_gap_list))]
                       
        # -- Select only the UDNs of only total value and number
        m_pairs = pd.pivot_table(df,
                                 index=['Operating Unit', 'Activity Name', 'Activity Code','Fiscal Year'], 
                                 columns='Disaggregate Code', 
                                 values='Actual Value').reset_index()

        m_pairs.columns = ['Operating Unit','Activity Name','Activity Code',
                           'Fiscal Year','value_males','value_females','num_males','num_females']

        # -- drop anything that does not have data for all four 
        return m_pairs.dropna(subset=m_pairs.columns[-4:])
    
    def compute_gender_gap(self):
        """Compute gender financing gap"""
        
        # -- select matched paris
        m_pairs = self.get_matched_pairs()
        
        # -- Compute OU level totals
        m_pairs = m_pairs.groupby(['Operating Unit', 'Fiscal Year'])[['value_males','value_females', 'num_males','num_females']].sum()
        df = m_pairs.eval('(value_females / num_females) / (value_males / num_males)').reset_index()
        return pd.pivot_table(df, index='Operating Unit', columns='Fiscal Year', values=0)
    
    def get_full_disaggs(self, indicator):
        udns = self.get_udns(indicator)
        index = pd.MultiIndex.from_frame(udns)

        results = []
        for i in udns['udn'].tolist():
            df = self.data[(self.data['Indicator Code'] == indicator) & \
                           (self.data['UDN'] == i) & \
                           (self.data['Fiscal Year'].isin(list(np.arange(2020, 2025))))]

            df = pd.pivot_table(df, index='UDN', columns='Fiscal Year', values=['Actual Value','Target Value'], aggfunc=custom_sum)
            results.append(df)
        return pd.concat(results).set_index(index)


        
