import pandas as pd
from collections import Counter
import numpy as np
from country_named_entity_recognition import find_countries
import matplotlib.pyplot as plt
import datetime
import folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import streamlit as st
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
    st.markdown("# Shop Comparison")
    
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

    
    df_ = pd.DataFrame({"Coffee Shop Name":[
                        "Coffee Break @ Amoy",
                        "Aunty Fatso",
                        "Coffee to Go @ International Plaza",
                        "Coffee Hive @ Ocean Financial Centre",
                        "Coffee Hive @ 110 Robinson Road",
                        "Marina Food House @ Phillip Street",
                        "Marina Food House @ Shenton House",
                        "Sunrise Traditional Coffee & Toast @ Market Street Hawker"],
                        "Store Code":[
    "0278",
    "0101",
    "0175",
    "0304",
    "8901",
    "8694",
    "8805",
    "0215"]})
    st.write(df_)
    
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
    
    dates_list = sorted(df['Date'].unique())
    dates_dict = {}
    kopinumbers = []
    for number in numbers:
        kopiq = False
        flows = df['Response Data'].loc[(df['User/Session ID'] == number)]
        for flow in flows:
            if isinstance(flow, str):
                if 'Cool! You have successfully redeemed your Kopi/Teh' in flow:
                    kopiq = True
    
        if kopiq:
            kopinumbers.append(number)
    
    nonkopinumbers = [e for e in numbers if not e in kopinumbers]
    
    @st.cache_data
    def find_shop_code(df, nums):
        destinations = {}
        for num in nums:
            inputs = df['Input Value'].loc[(df['User/Session ID'] == num) & (((df['Response Flow'] == 'Campaign - Kopi 2023 - Broadcast')|(df['Response Flow'] == 'Campaign - Kopi 2023 - Redeem'))|(df['Response Flow'] == 'Generic Error'))]
            for i in inputs:
                if isinstance(i, str):
                    if i.isnumeric():
                        if i in list(destinations.keys()):
                            destinations[i] += [num]
                        else:
                            destinations[i] = [num]
        return destinations
    
    shop_code_to_phone = find_shop_code(df, kopinumbers)
    code_dict = {}
    for i in shop_code_to_phone.keys():
        code_dict[i] = len(shop_code_to_phone[i])
    
    st.markdown("## Redemptions per shop")
    #st.bar_chart(code_dict)

    data = code_dict
    c = (
        alt.Chart(pd.DataFrame({'Shop code':list(data.keys()), 'Number':list(data.values())}))
                  .mark_bar()
                  .encode(x="Shop code", y="Number")
                 )
    st.altair_chart(c, use_container_width=True)
    
    @st.cache_data
    def get_voucher_dict(df, shop_code_to_phone):
        voucher_dict = {}
        for k in shop_code_to_phone.keys():
            total = 0
            for num in shop_code_to_phone[k]:
                found = False
                flows = df['Response Flow'].loc[df['User/Session ID'] == num]
                for flow in flows:
                    if isinstance(flow, str):
                        if flow == 'Campaign - Kopi 2023 - Broadcast Voucher':
                            found = True
                if found:
                    total += 1
            voucher_dict[k] = total
        return voucher_dict
    
    voucher_dict = get_voucher_dict(df, shop_code_to_phone)
    
    st.markdown("## Vouchers per shop")
    #st.bar_chart(voucher_dict)

    data = voucher_dict
    c = (
        alt.Chart(pd.DataFrame({'Shop code':list(data.keys()), 'Number':list(data.values())}))
                  .mark_bar()
                  .encode(x="Shop code", y="Number")
                 )
    st.altair_chart(c, use_container_width=True)
    
    quote_code_dict = {}
    quote_start_flows = ['Input - Travel - Policy Type', 
                            'Input - Motor - Make', 
                            'Input - Maid - Policy Coverage', 
                            'Input - PA - Insured Persons',
                            'Input - Home - Usage'
                        ] + [f'Quote - {Travel} - Profile' for Travel in ['Travel', 'Motor', 'PA', 'Home', 'Maid']]
    for i in shop_code_to_phone.keys():
        quote_code_dict[i] = 0
        for num in shop_code_to_phone[i]:
            resps = list(df['Response Flow'].loc[df['User/Session ID'] == num])
            resps = [e for e in resps if isinstance(e, str)]
            resps = [1 for e in resps if e in quote_start_flows]
            quote_code_dict[i] += np.sum(resps)
        
    st.markdown("## Quotes started per shop")
    #st.bar_chart(quote_code_dict)

    data = quote_code_dict
    c = (
        alt.Chart(pd.DataFrame({'Shop code':list(data.keys()), 'Number':list(data.values())}))
                  .mark_bar()
                  .encode(x="Shop code", y="Number")
                 )
    st.altair_chart(c, use_container_width=True)
    
    quote_code_dict = {}
    quote_end_flows = ['Quote - '+e+' - Complete' for e in ['Travel', 'Motor', 'PA', 'Home', 'Maid']]
    for i in shop_code_to_phone.keys():
        quote_code_dict[i] = 0
        for num in shop_code_to_phone[i]:
            resps = list(df['Response Flow'].loc[df['User/Session ID'] == num])
            resps = [e for e in resps if isinstance(e, str)]
            resps = [1 for e in resps if e in quote_end_flows]
            quote_code_dict[i] += np.sum(resps)
        
    
    st.markdown("## Quotes completed per shop")
    #st.bar_chart(quote_code_dict)

    data = quote_code_dict
    c = (
        alt.Chart(pd.DataFrame({'Shop code':list(data.keys()), 'Number':list(data.values())}))
                  .mark_bar()
                  .encode(x="Shop code", y="Number")
                 )
    st.altair_chart(c, use_container_width=True)
    
    quote_code_dict = {}
    quote_end_flows = ['Pay - Inforce Policy', 'Pay - Credit Card']
    for i in shop_code_to_phone.keys():
        quote_code_dict[i] = 0
        for num in shop_code_to_phone[i]:
            resps = list(df['Response Flow'].loc[df['User/Session ID'] == num])
            resps = [e for e in resps if isinstance(e, str)]
            resps = [1 for e in resps if e in quote_end_flows]
            quote_code_dict[i] += np.sum(resps)
        
    
    st.markdown("## Puchases per shop")
    st.markdown("Note: Due to technical limitations from the data extraction this chart actually shows the number of users who clicked pay by credit card plus the number of users who successfully purchased using PayNow.")
    #st.bar_chart(quote_code_dict)

    data = quote_code_dict
    c = (
        alt.Chart(pd.DataFrame({'Shop code':list(data.keys()), 'Number':list(data.values())}))
                  .mark_bar()
                  .encode(x="Shop code", y="Number")
                 )
    st.altair_chart(c, use_container_width=True)