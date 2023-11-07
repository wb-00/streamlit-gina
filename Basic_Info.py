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
import streamlit as st
import plotly.express as px

st.markdown("# Basic Info")

def get_dates_dict(df, nums):
    ks = sorted(df['Date'].unique())
    dictstring = "{"
    for k in ks:
        dictstring += f"'{k}': 0, "
    dictstring = dictstring[:-2] + "}"
    dates_dict = eval(dictstring)

    for num in nums:
        found = False
        dates = pd.unique(df['Date'].loc[df['User/Session ID'] == num])
        keys = dates_dict.keys()
        date = dates[-1]
        if date in keys:
            dates_dict[date] += 1
        else:
            dates_dict[date] = 1

    return dates_dict

def get_dates_dict_all(df, nums):
    ks = sorted(df['Date'].unique())
    dictstring = "{"
    for k in ks:
        dictstring += f"'{k}': 0, "
    dictstring = dictstring[:-2] + "}"
    dates_dict = eval(dictstring)

    for num in nums:
        found = False
        dates = pd.unique(df['Date'].loc[df['User/Session ID'] == num])
        keys = dates_dict.keys()
        date = dates[-1]
        for date in dates:
            if date in keys:
                dates_dict[date] += 1
            else:
                dates_dict[date] = 1

    return dates_dict

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
# Set up todays date and start and end dates for the dataframe
today = datetime.date.today()
dates_list = []
for i in range(1): # We go back 4 weeks
    dates_list.append((str(today-datetime.timedelta(days = (i+1)*7)), str(today-datetime.timedelta(days = 1+(i*7)))))

@st.cache_data
def get_data_extraction(dates_list):
    df_list = []
    for date_start, date_end in dates_list:
        d = pd.read_excel(f'https://pd-gina.s3-ap-southeast-1.amazonaws.com/data_extraction/gina_{date_start}_{date_end}.xlsx')
        df_list.append(d)
    # Concatenate all dataframes into one
    d = pd.concat(df_list, ignore_index=True)
    d = d.sort_values(by=['Date','Time'])
    return d
    
df = get_data_extraction(dates_list)

st.sidebar.markdown(f"Data from {dates_list[-1][0]} to {dates_list[0][1]}.")

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


## Messages per day
dates = sorted([e[5:] for e in df['Date']])
dates_counted = dict(Counter(dates))
st.markdown("## Messages per day")
st.bar_chart(dates_counted)

## Users per day
users = []
for num in numbers:
    dates = list(df['Date'].loc[df['User/Session ID'] == num].unique())
    users = dates + users
users = sorted([e[5:] for e in users])
users_counted = dict(Counter(users))
st.markdown("## Users per day")
st.bar_chart(users_counted)

## Quotes started per day
quotes = {e[5:]:0 for e in list(df['Date'].unique())}
quote_start_flows = ['Input - Travel - Policy Type', 
                    'Input - Motor - Make', 
                    'Input - Maid - Policy Coverage', 
                    'Input - PA - Insured Persons',
                    'Input - Home - Usage'
                    ] + [f'Quote - {Travel} - Profile' for Travel in ['Travel', 'Motor', 'PA', 'Home', 'Maid']]
for date in list(df['Date'].unique()):
    resps = list(df['Response Flow'].loc[df['Date'] == date])
    resps = [e for e in resps if isinstance(e, str)]
    resps = [1 for e in resps if e in quote_start_flows]
    quotes[date[5:]] = np.sum(resps)

st.markdown("## Quotes started per day")
st.bar_chart(quotes)

## Quotes completed per day
quotes = {e[5:]:0 for e in list(df['Date'].unique())}
quote_end_flows = ['Quote - '+e+' - Complete' for e in ['Travel', 'Motor', 'PA', 'Home', 'Maid']]
for date in list(df['Date'].unique()):
    resps = list(df['Response Flow'].loc[df['Date'] == date])
    resps = [e for e in resps if isinstance(e, str)]
    resps = [1 for e in resps if e in quote_end_flows]
    quotes[date[5:]] = np.sum(resps)
    
st.markdown("## Quotes completed per day")
st.bar_chart(quotes)

## Purchases per day
quotes = {e[5:]:0 for e in list(df['Date'].unique())}
quote_end_flows = ['Pay - Inforce Policy', 'Pay - Credit Card']
for date in list(df['Date'].unique()):
    resps = list(df['Response Flow'].loc[df['Date'] == date])
    resps = [e for e in resps if isinstance(e, str)]
    resps = [1 for e in resps if e in quote_end_flows]
    quotes[date[5:]] = np.sum(resps)
    
st.markdown("## Purchases per day")
st.markdown("Note: Due to technical limitations from the data extraction this chart actually shows the number of users who clicked pay by credit card plus the number of users who successfully purchased using PayNow.")
st.bar_chart(quotes)

## User source
categories = ['Returning User',
 'Campaign - Kopi 2023 - Code',
 'Onboarding - No Voucher',
 'Onboarding - With Voucher']

first_flows = []
for num in numbers:
    first_flows.append(df['Response Flow'].loc[df['User/Session ID']==num].iloc[0])

first_flows = dict(pd.value_counts(first_flows))
first_flows_clean = {
    'Returning User':0
}
for i in first_flows.keys():
    if not i in categories:
        first_flows_clean['Returning User'] += first_flows[i]
    else:
        first_flows_clean[i] = first_flows[i]

# Create a DataFrame from the dictionary
data = {'Label': list(first_flows_clean.keys()), 'Value': list(first_flows_clean.values())}
df_ = pd.DataFrame(data)

# Create a pie chart using Plotly Express
fig = px.pie(df_, names='Label', values='Value')
st.markdown("## User Source")
st.markdown("Note: Returning users in this case are users who first messaged GINA over 7 days ago and have now messaged again within the last 7 days.")

# Display the pie chart using st.plotly_chart()
st.plotly_chart(fig)
