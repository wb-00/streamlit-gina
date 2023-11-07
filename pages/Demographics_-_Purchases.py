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
    st.markdown("# Demographics - Purchases")

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
    
    @st.cache_data
    def display_map(coordinates):
        map = folium.Map(location=[1.3521, 103.8198], zoom_start=12)  # Use the center of Singapore as the starting location
    
        for coord in coordinates:
            folium.Marker(location=coord).add_to(map)
    
        map.save("address_map.html")
    
    display_map(coordinates)
    
    @st.cache_data
    def get_demodata(df, nums):
        demodata = {}
        for number in nums:
            demodata[number] = (" ", 0)
            dates = df['Date'].loc[df['User/Session ID'] == number].unique()
            for date in dates:
                respdata = df['Response Data'].loc[(df['User/Session ID'] == number) & (df['Date'] == date)]
                for resp in respdata:
                    if isinstance(resp, str):
                        if "Policyholder address: " in resp:
                            demodata[number] = (resp+"\n"+demodata[number][0], date)
                if demodata[number] == 0:
                    print(respdata)
            
        buyerinfo = []
        for i in demodata:
            buyerdict = {
                "Date of Birth": "Unknown",
                "Gender": "Unknown",
                "Plan Type": "Unknown",
                "Lead Time": -1
            }
        
            dob = find_successive_line(demodata[i][0], "Policyholder date of birth: ", i)
            gender = find_successive_line(demodata[i][0], "Policyholder gender: ", i)
            plantype = find_successive_line(demodata[i][0], "Coverage plan: ", i)
            depdate = find_successive_line(demodata[i][0], "Departure date: ", i)
            searchdate = demodata[i][1]
            if depdate != "":
                depdate = pd.to_datetime(depdate, dayfirst=True)
                searchdate = pd.to_datetime(searchdate, dayfirst=False)
                buyerdict["Lead Time"] = (depdate - searchdate).days
                if int((depdate-searchdate).days) < 0:
                    print(depdate)
                    print(searchdate)
                    print(i)
            if dob != "":
                buyerdict["Date of Birth"] = pd.to_datetime(dob, dayfirst=True)
            if gender != "":
                buyerdict["Gender"] = gender
            if plantype != "":
                buyerdict["Plan Type"] = plantype
            buyerinfo.append(buyerdict)
        
        return pd.DataFrame(buyerinfo)
    
    nums = buyers
    df_ = get_demodata(df, nums)
    
    # Decade of Birth
    dob_list = df_['Date of Birth'].tolist()
    birth_years = [int(datetime.datetime.strptime(str(date)[:10], '%Y-%m-%d').year) for date in dob_list]
    birth_years = dict(Counter([(e // 10)*10 for e in birth_years]))
    
    st.markdown("## Birth decade (policyholder)")
    st.bar_chart(birth_years)
    
    # Gender
    labels = list(df_['Gender'].unique())
    values = [len(df_.loc[df_['Gender']==e]) for e in labels]
    gender_dict = {labels[i]:values[i] for i in range(len(labels))}
    
    st.markdown("## Gender (policyholder)")
    st.bar_chart(gender_dict)
    
    # Destination
    def find_destinations(df, nums):
        destinations = []
        for num in nums:
            inputs = df['Input Value'].loc[(df['User/Session ID'] == num) & ((df['Response Flow'] == 'Input - Travel - Departure Date') | (df['Response Flow'] == 'Input - Travel - Arrival Date'))]
            for i in inputs:
                destinations.append(i)
        return destinations
    
    dests = find_destinations(df, nums)
    dests = [x for x in dests if isinstance(x, str)]
    dests_new = []
    dest_dict = {
        'Taiwan, Province of China':'Taiwan',
        'Korea, Republic of':'South Korea',
        'Viet Nam':'Vietnam'
    }
    
    for dest in dests:
        listed = find_countries(dest)
        for i in listed:
            name = i[0].name
            if name in list(dest_dict.keys()):
                name = dest_dict[name]
            dests_new.append(name)
    
    dests_new = pd.Series(Counter(dests_new)).sort_values(ascending=False).to_dict()
    print(dests_new)
    st.markdown("## Destination")
    st.bar_chart(dests_new)
    
    # Policy type (single, annual)
    def find_numbers(df, nums, col, flow_string):
        result = []
        for num in nums:
            found = False
            flows = df[col].loc[df['User/Session ID'] == num]
            for flow in flows:
                if isinstance(flow, str):
                    if flow == flow_string:
                        found = True
            if found:
                result.append(num)
        return result
    
    plantype = []
    for i in find_numbers(df, numbers, 'Clicked Text', 'Single trip'):
        plantype.append('Single trip')
        
    for i in find_numbers(df, numbers, 'Clicked Text', 'Annual plan'):
        plantype.append('Annual plan')
    
    plantype = dict(Counter(plantype))
    
    st.markdown("## Plan type")
    st.bar_chart(plantype)
    
    # Policy coverage (family etc.)
    labels = list(df_['Plan Type'].unique())
    values = [len(df_.loc[df_['Plan Type']==e]) for e in labels]
    gender_dict = {labels[i]:values[i] for i in range(len(labels))}
    
    st.markdown("## Policy coverage")
    st.bar_chart(gender_dict)
    
    # Map
    st.markdown("## Address")
    HtmlFile = open("address_map.html", 'r', encoding='utf-8')
    source_code = HtmlFile.read()
    components.html(source_code, height = 600)