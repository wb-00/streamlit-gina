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

st.markdown("# Demographics - Quotes")

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
        return None

# Get quote peopel phoen numbers
quote_end_flows = ['Quote - '+e+' - Complete' for e in ['Travel', 'Motor', 'PA', 'Home', 'Maid']]
nums = []
for number in numbers:
    flows = list(df['Response Flow'].loc[df['User/Session ID'] == number])
    flows = [e for e in flows if isinstance(e, str)]
    flows = [e for e in flows if e in quote_end_flows]
    if len(flows) > 0:
        nums.append(number)


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

st.markdown("## Destination")
st.markdown("Note: we parse the destinations when the user types them rather than when the quote is completed so there may be a higher total than expected for this chart")
st.bar_chart(dests_new)

# Policy type
plantypes = []
coverages = []
purposes  = []
for num in nums:
    resps = list(df['Response Data'].loc[(df['Response Flow'] == 'Quote - Travel - Confirm') & (df['User/Session ID'] == num)])
    resps = [e for e in resps if isinstance(e, str)]
    for resp in resps:
        pt = find_successive_line(resp, "Trip type: ", 0)
        cv = find_successive_line(resp, "Coverage plan: ", 0)
        pp = find_successive_line(resp, "Trip purpose: ", 0)
        if pt:
            plantypes.append(pt)
        if cv:
            coverages.append(cv)
        if pp:
            purposes.append(pp)
    

st.markdown("## Plan type")
st.bar_chart(dict(Counter(plantypes)))

# Policy coverage


st.markdown("## Plan coverage")
st.bar_chart(dict(Counter(coverages)))

# Policy purpose


st.markdown("## Plan purpose")
st.bar_chart(dict(Counter(purposes)))

