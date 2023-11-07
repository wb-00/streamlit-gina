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
import altair as alt

st.set_page_config(
    page_title="GINA.sg Stats",
    page_icon=":whale:",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
    }
)

if st.session_state["authentication_status"] is False:
    st.error('Username/password is incorrect')
elif st.session_state["authentication_status"] is None:
    st.warning('Please enter your username and password')
elif st.session_state["authentication_status"]:
    st.markdown("# Purchaser - Addresses")

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
    
    def find_successive_line(input_string, phrase_to_find, i):
        # Find the starting index of the phrase
        start_index = input_string.find(phrase_to_find)
        
        # Check if the phrase was found
        if start_index != -1:
            # Find the end of the line starting from the position of the phrase
            end_index = input_string.find("\n", start_index)
        
            # Extract and print the characters until the new line
            if end_index != -1:
                result = input_string[start_index + len(phrase_to_find):end_index]
            else:
                result = input_string[start_index + len(phrase_to_find):]
        
            return result
        else:
            # print("Phrase not found in the input string: "+phrase_to_find+str(i))
            return ""
    
    def get_buyer_numbers(df, nums):
        # Find the phone number of of each person who bought a plan (from the list given)
        buyers = []
    
        for number in nums:
            buyer = False
            responses = df['Response Flow'].loc[df['User/Session ID'] == number]
            for resp in responses:
                if resp in ['Pay - Inforce Policy', 'Pay - Credit Card']:
                    buyer = True
            if buyer:
                buyers.append(number)
    
        return buyers
    
    buyers = get_buyer_numbers(df, numbers)
    
    @st.cache_data
    def get_addresses(df, nums):
        addresses = []
        for num in nums:
            found = False
            resps = df['Response Data'].loc[(df['User/Session ID'] == num) & (df['Response Flow'] == 'Buy - Travel - Confirm')]
            resps = [r for r in resps if isinstance(r, str)]
            for resp in resps:
                if "Policyholder address:" in resp:
                    found = (find_successive_line(resp, "Policyholder address: ", 0))
    
            if found:
                addresses.append(found)
        return addresses                      
    
    addresses = get_addresses(df, buyers)
    
    @st.cache_data
    def geocode_addresses(addresses):
        geolocator = Nominatim(user_agent="myGeocoder")
        coordinates = []
        for address in addresses:
            try:
                location = geolocator.geocode(address, timeout=10)
                if location:
                    coordinates.append((location.latitude, location.longitude))
            except GeocoderTimedOut:
                pass  # Handle timeouts by skipping this address or adding it to a retry queue
        return coordinates
    
    addresses = [a.split(",")[0]+","+a.split(",")[2][:-7] for a in addresses]
    coordinates = geocode_addresses(addresses)
    
    def display_map(coordinates):
        map = folium.Map(location=[1.3521, 103.8198], zoom_start=12)  # Use the center of Singapore as the starting location
    
        for coord in coordinates:
            folium.Marker(location=coord).add_to(map)
    
        map.save("address_map.html")
    
    display_map(coordinates)
    
    # Map
    st.markdown("## Address")
    HtmlFile = open("address_map.html", 'r', encoding='utf-8')
    source_code = HtmlFile.read()
    components.html(source_code, height = 600)