#!/usr/bin/env python
# coding: utf-8

# # Part I. ETL Pipeline for Pre-Processing the Files

# ## PLEASE RUN THE FOLLOWING CODE FOR PRE-PROCESSING THE FILES

# #### Import Python packages 

# In[1]:


# Import Python packages 
import pandas as pd
import cassandra
import re
import os
import glob
import numpy as np
import json
import csv


# #### Creating list of filepaths to process original event csv data files

# In[2]:


# checking your current working directory
print(os.getcwd())

# Get your current folder and subfolder event data
filepath = os.getcwd() + '/event_data'

# Create a for loop to create a list of files and collect each filepath
for root, dirs, files in os.walk(filepath):
    
# join the file path and roots with the subdirectories using glob
    file_path_list = glob.glob(os.path.join(root,'*'))
    print(file_path_list)


# #### Processing the files to create the data file csv that will be used for Apache Casssandra tables

# In[3]:


# initiating an empty list of rows that will be generated from each file
full_data_rows_list = [] 
    
# for every filepath in the file path list 
for f in file_path_list:

# reading csv file 
    with open(f, 'r', encoding = 'utf8', newline='') as csvfile: 
        # creating a csv reader object 
        csvreader = csv.reader(csvfile) 
        next(csvreader)
        
 # extracting each data row one by one and append it        
        for line in csvreader:
            #print(line)
            full_data_rows_list.append(line) 
            
# creating a smaller event data csv file called event_datafile_full csv that will be used to insert data into the \
# Apache Cassandra tables
csv.register_dialect('myDialect', quoting=csv.QUOTE_ALL, skipinitialspace=True)

with open('event_datafile_new.csv', 'w', encoding = 'utf8', newline='') as f:
    writer = csv.writer(f, dialect='myDialect')
    writer.writerow(['artist','firstName','gender','itemInSession','lastName','length',                'level','location','sessionId','song','userId'])
    for row in full_data_rows_list:
        if (row[0] == ''):
            continue
        writer.writerow((row[0], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[12], row[13], row[16]))


# In[4]:


# check the number of rows in your csv file
with open('event_datafile_new.csv', 'r', encoding = 'utf8') as f:
    print(sum(1 for line in f))


# # Part II. Complete the Apache Cassandra coding portion of your project. 
# 
# ## Now you are ready to work with the CSV file titled <font color=red>event_datafile_new.csv</font>, located within the Workspace directory.  The event_datafile_new.csv contains the following columns: 
# - artist 
# - firstName of user
# - gender of user
# - item number in session
# - last name of user
# - length of the song
# - level (paid or free song)
# - location of the user
# - sessionId
# - song title
# - userId
# 
# The image below is a screenshot of what the denormalized data should appear like in the <font color=red>**event_datafile_new.csv**</font> after the code above is run:<br>
# 
# <img src="images/image_event_datafile_new.jpg">

# ## Begin writing your Apache Cassandra code in the cells below

# #### Creating a Cluster

# In[5]:


from cassandra.cluster import Cluster
cluster = Cluster()

session = cluster.connect()


# #### Create Keyspace

# In[6]:


try:
    session.execute("""
    CREATE KEYSPACE IF NOT EXISTS apachecassandra 
    WITH REPLICATION = 
    { 'class' : 'SimpleStrategy', 'replication_factor' : 1 }"""
)

except Exception as e:
    print(e)


# #### Set Keyspace

# In[7]:


try:
    session.set_keyspace('apachecassandra')
except Exception as e:
    print(e)


# ### Now we need to create tables to run the following queries. Remember, with Apache Cassandra you model the database tables on the queries you want to run.

# ## Create queries to ask the following three questions of the data
# 
# ### 1. Give me the artist, song title and song's length in the music app history that was heard during  sessionId = 338, and itemInSession  = 4
# 
# 
# ### 2. Give me only the following: name of artist, song (sorted by itemInSession) and user (first and last name) for userid = 10, sessionid = 182
#     
# 
# ### 3. Give me every user name (first and last) in my music app history who listened to the song 'All Hands Against His Own'
# 
# 
# 

# **Drop Session Table**

# In[8]:


qry = "DROP TABLE IF EXISTS session_table"
try:
    rows = session.execute(qry)
except Exception as e:
    print(e)


# **Create Session Table**
# 
# The session table is constructed to return the artist, song title and song's length during sessionId 338 and intemInSession 4.<br>The unique primary key is a composed of sessionId and itemInSession. This will facilitate filtering the data.

# In[9]:


qry = "CREATE TABLE IF NOT EXISTS session_table " 
qry = qry + "(sessionId int, itemInSession int, artist text, song text, length float, "
qry = qry + "PRIMARY KEY(sessionId,itemInSession))"

try:
    session.execute(qry)
except Exception as e:
    print(e)


# **Insert Data into Session Table**

# In[10]:


file = 'event_datafile_new.csv'

with open(file, encoding = 'utf8') as f:
    csvreader = csv.reader(f)
    next(csvreader) # skip header
    for line in csvreader:
        query = "INSERT INTO session_table(sessionId, itemInSession, artist, song, length)"
        query = query + "VALUES(%s,%s,%s,%s,%s)"
        session.execute(query, (int(line[8]), int(line[3]), line[0], line[9], float(line[5])))


# #### Do a SELECT to verify that the data have been inserted into Session table

# In[11]:


qry = "SELECT artist,song,length FROM session_table WHERE sessionId = 338 AND itemInSession = 4"
try:
    rows = session.execute(qry)
except Exception as e:
    print(e)

for row in rows:
    print(row.artist,row.song,row.length)


# **Drop User Table**
# 

# In[12]:


qry = "DROP TABLE IF EXISTS user_table"
try:
    rows = session.execute(qry)
except Exception as e:
    print(e)


# **Create User Table**
# 
# The User table is constructed to return the name of artist, song (sorted by itemInSession) and user (first and last name) for userid = 10 and sessionid = 182. To facilitate the query a unique primary key consisting of sessionID and userId is created  with itemInSession as a clustering column to fulfill the sorting requirement.

# In[13]:


qry = "CREATE TABLE IF NOT EXISTS user_table " 
qry = qry + "(sessionId int, userId int, itemInSession int, artist text, song text, firstname text, lastname text, "
qry = qry + "PRIMARY KEY((sessionId,userid ),itemInSession))"

try:
    session.execute(qry)
except Exception as e:
    print(e)


# **Insert Data into User Table**

# In[14]:


file = 'event_datafile_new.csv'

with open(file, encoding = 'utf8') as f:
    csvreader = csv.reader(f)
    next(csvreader) # skip header
    for line in csvreader:
        query = "INSERT INTO user_table(sessionId, userId, itemInSession, artist, song, firstname, lastname)"
        query = query + "VALUES(%s,%s,%s,%s,%s,%s,%s)"
        session.execute(query, (int(line[8]), int(line[10]), int(line[3]),line[0], line[9], line[1], line[4]))


# #### Do a SELECT to verify that the data have been inserted into User table

# In[15]:


qry = "SELECT artist, song, firstname, lastname FROM user_table WHERE sessionId = 182 AND userId = 10"
try:
    rows = session.execute(qry)
except Exception as e:
    print(e)

for row in rows:
    print(row.artist,row.song,row.firstname, row.lastname)


# **Drop Song Table**

# In[16]:


qry = "DROP TABLE IF EXISTS song_table"
try:
    rows = session.execute(qry)
except Exception as e:
    print(e)


# **Create Song Table**
# 
# The Song table is created to give every user name (first and last) in the music app history who listened to the song 'All Hands Against His Own'. The unique primary key consisting of userId and song was created to facilitate extracting the relevant data.

# In[17]:


qry = "CREATE TABLE IF NOT EXISTS song_table " 
qry = qry + "(userId int, song text, artist text, firstname text, lastname text, "
qry = qry + "PRIMARY KEY(userId,song))"

try:
    session.execute(qry)
except Exception as e:
    print(e)


# **Insert Data into Song Table**

# In[18]:


file = 'event_datafile_new.csv'

with open(file, encoding = 'utf8') as f:
    csvreader = csv.reader(f)
    next(csvreader) # skip header
    for line in csvreader:
        query = "INSERT INTO song_table(userId, song, artist, firstname, lastname)"
        query = query + "VALUES(%s,%s,%s,%s,%s)"
        session.execute(query, (int(line[10]), line[9], line[0], line[1], line[4]))


# #### Do a SELECT to verify that the data have been inserted into Song table

# In[19]:



qry = "SELECT artist, song, firstname, lastname FROM song_table WHERE song = 'All Hands Against His Own' ALLOW FILTERING "
try:
    rows = session.execute(qry)
except Exception as e:
    print(e)

for row in rows:
    print(row.firstname, row.lastname)


# ### Drop the tables before closing out the sessions

# In[20]:


qry = "DROP TABLE IF EXISTS session_table"
try:
    rows = session.execute(qry)
except Exception as e:
    print(e)

qry = "DROP TABLE IF EXISTS user_table"
try:
    rows = session.execute(qry)
except Exception as e:
    print(e) 
    
qry = "DROP TABLE IF EXISTS song_table"
try:
    rows = session.execute(qry)
except Exception as e:
    print(e)   
    
    


# ### Close the session and cluster connection¶

# In[21]:


session.shutdown()
cluster.shutdown()


# In[ ]:





# In[ ]:




