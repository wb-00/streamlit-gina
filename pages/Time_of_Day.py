import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from collections import Counter
import numpy as np
from country_named_entity_recognition import find_countries
import matplotlib.pyplot as plt
import datetime
import folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut


if st.session_state["authentication_status"] is False:
    st.error('Username/password is incorrect')
elif st.session_state["authentication_status"] is None:
    st.warning('Please enter your username and password')
elif st.session_state["authentication_status"]:
    st.markdown("# Time of Day")
    st.markdown("Note: in this page we present the total number of times a given action took place each hour over the course of the week")
    
    # Set up todays date and start and end dates for the dataframe
    today = datetime.date.today()
    dates_list = []
    for i in range(4): # We go back 4 weeks
        dates_list.append((str(today-datetime.timedelta(days = (i+1)*7)), str(today-datetime.timedelta(days = 1+(i*7)))))
    
    @st.cache_data
    def get_data_extraction(dates_list):
        df_list = []
        for date_start, date_end in dates_list:
            d = pd.read_excel(f'https://pd-gina.s3-ap-southeast-1.amazonaws.com/data_extraction/gina_{date_start}_{date_end}.xlsx')
            df_list.append(d)
        # Concatenate all dataframes into one
        #d = pd.concat(df_list, ignore_index=True)
        #d = d.sort_values(by=['Date','Time'])
        return df_list
        
    df_list = get_data_extraction(dates_list)
    st.sidebar.markdown(f"Data from {dates_list[-1][0]} to {dates_list[0][1]}.")

    number_of_weeks = st.slider("How many weeks back?", 1, 4, 1)
    df = pd.concat(df_list[:number_of_weeks], ignore_index=True)
    df = df.sort_values(by=['Date','Time'])
    
    numbers = df['User/Session ID'].unique()
    testernumbers = []
    # Finds all testers
    for number in numbers:
        messages = df['Typed Text'].loc[df['User/Session ID'] == number]
        messages = [elm for elm in messages if isinstance(elm, str)]
        for mes in messages:
            if "TESTERONLY" in mes or "Admin" in mes:
                testernumbers.append(number)
    
        resps = df['Response Flow'].loc[df['User/Session ID'] == number]
        resps = [elm for elm in resps if isinstance(elm, str)]
        for mes in resps:
            if "TESTERONLY" in mes or "Admin" in mes:
                testernumbers.append(number)
    
    testernumbers = pd.unique(testernumbers)
    
    # Drops testers from the dataframe
    dellist = []
    for i in range(len(numbers)):
        if numbers[i] in testernumbers:
            dellist.append(i)
    
    numbers = np.delete(numbers, dellist)
    
    # Define the start and end times
    start_time = datetime.datetime.strptime("00:00", "%H:%M")
    end_time = datetime.datetime.strptime("23:00", "%H:%M")
    
    # Define the time interval
    interval = datetime.timedelta(minutes=60)
    
    # Initialize an empty list to store the times
    times_list = []
    
    # Generate the list of times
    while start_time <= end_time:
        times_list.append(start_time.strftime("%H:%M"))
        start_time += interval
    
    # Overall traffic
    traffic = list(df['Time'])
    time_dict = {}
    for i in times_list:
        time_dict[i] = 0
    
    for time in traffic:
        time = str(time).split(":")[0][-2:]+':00'
        time_dict[time] += 1
    
    st.markdown("## Messages per hour")
    st.bar_chart(time_dict)
    
    # Quotes
    traffic = []
    quote_end_flows = ['Quote - '+e+' - Complete' for e in ['Travel', 'Motor', 'PA', 'Home', 'Maid']]
    for i in range(len(df.index)):
        if df['Response Flow'].iloc[i] in quote_end_flows:
            traffic.append(df['Time'].iloc[i])
            
    time_dict = {}
    for i in times_list:
        time_dict[i] = 0
    
    for time in traffic:
        time = str(time).split(":")[0][-2:]+':00'
        time_dict[time] += 1
    
    st.markdown("## Complete quotes per hour")
    st.bar_chart(time_dict)
    
    # Purchases
    traffic = []
    quote_end_flows = ['Pay - Inforce Policy', 'Pay - Credit Card']
    for i in range(len(df.index)):
        if df['Response Flow'].iloc[i] in quote_end_flows:
            traffic.append(df['Time'].iloc[i])
            
    time_dict = {}
    for i in times_list:
        time_dict[i] = 0
    
    for time in traffic:
        time = str(time).split(":")[0][-2:]+':00'
        time_dict[time] += 1
    
    st.markdown("## Purchases per day")
    st.markdown("Note: Due to technical limitations from the data extraction this chart actually shows the number of users who clicked pay by credit card plus the number of users who successfully purchased using PayNow.")
    st.bar_chart(time_dict)