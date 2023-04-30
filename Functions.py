
#Import Statements used

import pandas as pd
import re
from fuzzywuzzy import fuzz
from tqdm import tqdm



#Load Function
def load(path):
    data = pd.read_csv(path)
    return data



# Dictionary Function

# Define a function to replace abbreviations with their expanded form
def replace_abbreviations(text):
    '''
     creates USPS dictionary, and replaces abbreviatons
     '''

    abbrev_dict = {
    'aly': 'alley',
    'ave': 'avenue',
    'blvd': 'boulevard',
    'byp': 'bypass',
    'cir': 'circle',
    'ct': 'court',
    'dr': 'drive',
    'expy': 'expressway',
    'hwy': 'highway',
    'ln': 'lane',
    'pkwy': 'parkway',
    'pl': 'place',
    'pt': 'point',
    'rd': 'road',
    'sq': 'square',
    'st': 'street',
    'ter': 'terrace',
    'trl': 'trail',
    'ste':'suite',
    'e':'east',
    'w':'west',
    's':'south',
    'n':'north',
    'bldg':'building',
    'mlk':'martin luther king',
    'jfk':'john f kennedy',
    '1st':'first',
    '2nd':'second',
    '3rd':'third',
    '4th':'fourth',
    '5th':'fifth',
    '6th':'sixth',
    '7th':'seventh',
    '8th':'eighth',
    '9th':'ninth',
    '10th':'tenth'
    }

    for abbrev, full in abbrev_dict.items():
        pattern = r"\b{}\b".format(re.escape(abbrev))
        text = re.sub(pattern, full, text)
    return text



# Data Pre-processing Function

def left_preprocess(left_df):
    '''
     removes: unwanted columns, fixes postal code, puntuation,duplicates, and applied abbrev dict
    '''

    #removing unwanted columns
    left_df = left_df.drop(columns=['size'])

    #removing second zip code
    separator = "-"
    for i in range(len(left_df)):
        if separator in left_df.loc[i, "zip_code"]:
            left_df.at[i,"zip_code"] = left_df.at[i,"zip_code"].split(separator)[0]

    # Clean the "name", "address", and "city" columns in left dataset by removing punctuation and convert to lower case
    punctuation = r'[^\w\s\']'
    left_df['name'] = left_df['name'].apply(lambda x: re.sub(punctuation, '', str(x)).lower())
    left_df['address'] = left_df['address'].apply(lambda x: re.sub(punctuation, '', str(x)).lower())
    left_df['city'] = left_df['city'].apply(lambda x: re.sub(punctuation, '', str(x)).lower())

    # Replace abbreviations in the "address" column of left_df
    left_df['address'] = left_df['address'].apply(replace_abbreviations) #using the replace_abb func.

    # check whether there are duplicate values
    left_duplicates = left_df.duplicated(subset=["business_id"])
    num_left_duplicates = left_duplicates.sum()
    print(num_left_duplicates)

    return left_df


def right_preprocess(right_df):
     '''
     removes: unwanted columns, fixes postal code, puntuation,duplicates, and applied abbrev dict
     ''' 
     #removing unwanted columns
     right_df = right_df.drop(columns=['categories'])

     # Remove .0 in right dataset
     right_df['postal_code'] = right_df['postal_code'].astype(str)
     right_df['postal_code'] = right_df['postal_code'].apply(lambda x: x.split('.')[0])

     # Clean the "name", "address", and "city" columns in right dataset by removing punctuation and convert to lower case
     punctuation = r'[^\w\s\']'

     right_df['name'] = right_df['name'].apply(lambda x: re.sub(punctuation, '', str(x)).lower())
     right_df['address'] = right_df['address'].apply(lambda x: re.sub(punctuation, '', str(x)).lower())
     right_df['city'] = right_df['city'].apply(lambda x: re.sub(punctuation, '', str(x)).lower())

     # Replace abbreviations in the "address" column of right_df
     right_df['address'] = right_df['address'].apply(replace_abbreviations)

     # check whether there are duplicate values
     right_duplicates = right_df.duplicated(subset=["entity_id"])
     num_right_duplicates = right_duplicates.sum()
     print(num_right_duplicates)

     return right_df



# Merge left table and right_table


def merge_table(left_df,right_df):
    '''
     dfs are separated by states individually and merged together
    '''

    left_PA = left_df[left_df["state"] == "PA"]
    left_FL = left_df[left_df["state"] == "FL"]
    left_MO = left_df[left_df["state"] == "MO"]
    left_TN = left_df[left_df["state"] == "TN"]
    left_IN = left_df[left_df["state"] == "IN"]

    right_PA = right_df[right_df["state"] == "PA"]
    right_FL = right_df[right_df["state"] == "FL"]
    right_MO = right_df[right_df["state"] == "MO"]
    right_TN = right_df[right_df["state"] == "TN"]
    right_IN = right_df[right_df["state"] == "IN"]

    merged_PA = pd.merge(left_PA, right_PA, left_on=['address'], right_on=['address'],how="inner")
    merged_FL = pd.merge(left_FL, right_FL, left_on=['address'], right_on=['address'],how="inner")
    merged_MO = pd.merge(left_MO, right_MO, left_on=['address'], right_on=['address'],how="inner")
    merged_TN = pd.merge(left_TN, right_TN, left_on=['address'], right_on=['address'],how="inner")
    merged_IN = pd.merge(left_IN, right_IN, left_on=['address'], right_on=['address'],how="inner")

    merged_all = pd.concat([merged_PA, merged_FL, merged_MO, merged_TN, merged_IN])

    
    
    return merged_all



# FuzzyWuzzy Matching Method

def per_state_matcher(df):
    '''
     creates a new result df and iterates matching algorithm over the data set.
    '''
    matching_results = pd.DataFrame(columns=["business_id", "entity_id", "confidence_score"])

    dfs = []
    # Loop over all rows in the merged dataframe and find the confidence score for each pair of rows
    for i, row in tqdm(df.iterrows(), total=len(df)):
        text1 = (row["name_x"] if pd.notna(row['name_x']) else '') 
        text2 = (row["name_y"] if pd.notna(row['name_y']) else '')
        score = fuzz.partial_ratio(text1, text2)
        if score > 80:  # add the filter for the confidence score
            dfs.append(pd.DataFrame({"business_id": row["business_id"], "entity_id": row["entity_id"], "confidence_score": score}, index=[0]))

    if dfs:
        matching_results = pd.concat(dfs, ignore_index=True)
    return matching_results
    




# Import results to CSV

def csv_writer(df, file_name="Matching_result_Python_Warrior.csv"):
    df.to_csv(file_name, index=False)





