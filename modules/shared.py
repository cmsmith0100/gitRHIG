#!/usr/bin/python


import ast; # Interpret structure strings literally.
import chardet; # Detect string encoding.
import collections; # Ordered dictionary.
import datetime; # Datetime handling.
import dateutil.parser as dateutil_parser;
import hashlib; # Generate hash from string.
import os; # File, directory handling.
import pandas; # DataFrame handling.
import pymongo; # MongoDB support.
import subprocess; # Git commands.
import urlparse; # URI parsing.
import re; # Regular expressions.
import requests; # HTTP requests.
import sqlite3; # Database processing.


# Name of this Python toolset suite.
TOOLSET_NAME = 'gitRHIG';

# Data store (DataFrame) commit record attributes.
DATA_STORE_ATTRIBUTES = ['repo_remote_hostname', 'repo_owner', 'repo_name',
                         'path_in_repo',
                         'labels',
                         'commit_hash',
                         'author_name', 'author_email', 'author_unix_timestamp',
                         'committer_name', 'committer_email', 'committer_unix_timestamp',
                         'subject', 'len_subject',
                         'num_files_changed',
                         'num_lines_changed', 'num_lines_inserted', 'num_lines_deleted', 'num_lines_modified'];

DATA_STORE_ATTRIBUTE_DTYPES = collections.OrderedDict([('repo_remote_hostname', 'object'),
                                                       ('repo_owner', 'object'),
                                                       ('repo_name', 'object'),
                                                       ('path_in_repo', 'object'),
                                                       ('labels', 'object'),
                                                       ('commit_hash', 'object'),
                                                       ('author_name', 'object'),
                                                       ('author_email', 'object'),
                                                       ('author_unix_timestamp', 'float64'),
                                                       ('committer_name', 'object'),
                                                       ('committer_email', 'object'),
                                                       ('committer_unix_timestamp', 'float64'),
                                                       ('subject', 'object'),
                                                       ('len_subject', 'int64'),
                                                       ('num_files_changed', 'int64'),
                                                       ('num_lines_changed', 'int64'),
                                                       ('num_lines_inserted', 'int64'),
                                                       ('num_lines_deleted', 'int64'),
                                                       ('num_lines_modified', 'int64')]);

DEFAULT_MONGODB_URI = 'mongodb://localhost:27017/';

DEFAULT_DB_NAME = 'data_store';

DEFAULT_DB_COLLECTION_NAME = 'commits';

data_store_attributes = DATA_STORE_ATTRIBUTE_DTYPES.keys();


# Get unique list of items from string given some delimiter.
def get_unique_items_from_str(input_str, delimiter):

    items = list();
    
    if (input_str):
        raw_items = input_str.split(delimiter); # Split string by delimiter.
        num_raw_items = len(raw_items);
        for i in range(0, num_raw_items):
            item = raw_items[i].strip(); # Prune leading or trailing space chars.
            if (    item
                    and (item not in items)   ): # Ensure item, and no duplicates.
                items.append(item);
    
    return items;


# Get file contents as string.
def get_filecontents_str(infile):
    
    with open(infile, 'r') as f:
        file_contents_str = f.read().replace('\n', '');

    return file_contents_str;


# Return list based on l having duplicates eliminated, original order preserved.
# Inspired by: https://stackoverflow.com/a/480227  
def setlist(l):

    seen = set();
    
    setlist = list();
    for item in l:
        if (item not in seen):
            setlist.append(item);
            seen.add(item);
    
    return setlist;


# Get unique list of items from arg-string given some delimiter.
def get_unique_items_from_argstr(input_str, delimiter):

    items = list();

    if (input_str):
        raw_items = get_unique_items_from_str(input_str, delimiter);
        num_raw_items = len(raw_items);
        for i in range(0, num_raw_items):
            item = raw_items[i].strip();
            if (os.path.isfile(item)):
                filecontents_str = get_filecontents_str(item);
                items_from_file = get_unique_items_from_argstr(filecontents_str, delimiter);
                items = items + items_from_file;
            else:
                items.append(item);

    items = setlist(items);

    return items;


# Formulate user warning string.
def get_warning_str(defining_case, action='ignoring'):
    
    return ("(Warning: " + defining_case + " - " + action + ".)");
    

# Determine working directory for any runtime processing storage.
def get_wd(directory_str):
    
    if (directory_str):
        if (not os.path.exists(directory_str)): # If directory does not exists, make it.
            print("No such directory \'" + directory_str + "\'.");
            return '';#os.makedirs(directory_str);
        #directory = os.path.abspath(directory_str);
        directory = directory_str;
    else:
        #cwd = os.getcwd(); # Use the current working directory.
        directory = '.';#os.path.basename(os.path.normpath(cwd)); # Just get basename directory.
    
    return directory;


# Determine whether or not it is okay to proceed.
def confirm(question=""):
    
    answer = raw_input(question + "[y/N] ");
    if (answer == 'y'):
        return True;
    else:
        return False;


# Determine whether or not destination is writable file.
def is_writable_file(destination):
    
    # Case: Destination already exists.
    if (os.path.exists(destination)):    
        if (os.path.isfile(destination)):    
            if (not confirm("File \'"+destination+"\' already exists! Overwrite? ")):
                return False;
    
    # Case: Destination path does not exist.
    dirname_destination = os.path.dirname(destination); # Get destination path.
    if (dirname_destination): # If destination string contained a path...
        if (not os.path.isdir(dirname_destination)): # Path does not exist...
            print("No such directory \'" + dirname_destination + "\'.");
            return False;
    
    # Case: Destination is a directory.
    if (    os.path.isdir(destination)
            or destination.endswith('/')    ): # Destination is a directory (existing or not existing)...
        print("Not a file \'" + destination + "\'.");
        return False;
    
    return True;


# Parse string to see if it adheres to some timestamp format.
def parse_timestamp_str(timestamp_str, descriptor=''):
    
    if (timestamp_str):
        try:
            timestamp_datetime = dateutil_parser.parse(timestamp_str);
            timestamp_str = datetime.datetime.strftime(timestamp_datetime, '%Y-%m-%dT%H:%M:%SZ'); # Force timestamp format.
        except:
            descriptor = '\''+descriptor+'\'' if descriptor else ''; # If provided, wrap in single quotation marks.
            print(get_warning_str("Malformed " + descriptor + " timestamp \'" + timestamp_str + "\'"));
            timestamp_str = '';
    
    return timestamp_str;


# Get UTC timestamp string equivalent of UNIX epoch.
def get_utcunixepoch_timestamp_str():
    
    utcunixepoch_str = datetime.datetime(1970,1,1).strftime('%Y-%m-%dT%H:%M:%SZ');
    
    return utcunixepoch_str;


# Get UTC-now timestamp string.
def get_utcnow_timestamp_str():
    
    utcnow_str = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ');
    
    return utcnow_str;


# Convert UTC timestamp string to UNIX timestamp.
def utc_timestamp_str_to_unix_timestamp(utc_timestamp_str):
    
    # ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ
    utc_timestamp_datetime = datetime.datetime.strptime(utc_timestamp_str, '%Y-%m-%dT%H:%M:%SZ');
    unix_timestamp = (utc_timestamp_datetime - datetime.datetime(1970,1,1)).total_seconds();
    
    return unix_timestamp;


# Extract GitHub hostname, repo owner, and repo name from repo remote origin URL.
def get_repo_id(remote_origin_url):
    
    url = re.findall(r'^.+[://|@].+[:|/].+/.+', remote_origin_url);

    (repo_remote_hostname, repo_owner, repo_name) = re.findall(r'^.+[://|@](.+)[:|/](.+)/(.+)', url[0])[0];
    
    if (repo_name.endswith('.git')):
        repo_name = repo_name[:-4]; # Remove the '.git' from repo name.

    return repo_remote_hostname, repo_owner, repo_name;


# Generate SHA-1 hash string for input string.
def get_anonymized_str(in_str):
    
    in_str = in_str.encode('utf-8', 'replace');

    hash_obj = hashlib.sha1(in_str);
    hex_digit = hash_obj.hexdigest();
    salt_val = str(hex_digit);

    hash_obj = hashlib.sha1(in_str+salt_val);
    hex_digit = hash_obj.hexdigest();
    anonymized_str = str(hex_digit);
    
    return anonymized_str;


# Update basepath in URI path.
def add_path_to_uri(uri, path):
    
    if (uri and path):
        if (uri.endswith('/')):
            return uri + path;
        else:
            return uri + '/' + path;
    elif (uri):
        return uri;
    elif (path):
        return path;
    else:
        return '';


# Determine whether or not local repository is corrupt.
def is_corrupt_repo(path_to_repo):
    
    config = '-c color.ui=\'false\'';
    gd = '--git-dir=\'' + path_to_repo + '/.git/\'';
    wt = '--work-tree=\'' + path_to_repo + '\'';
    
    cmd_str = 'git %s %s %s log' % (config,gd,wt);
    #print(cmd_str);
    
    sp = subprocess.Popen(cmd_str,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          shell=True);
    
    (gitlog_str, _) = sp.communicate();
    
    if (    gitlog_str == "fatal: bad default revision \'HEAD\'\n"
            or (("fatal: your current branch" in gitlog_str)
                and ("does not have any commits yet\n" in gitlog_str))   ):
        return True;
    else:
        return False;


# Determine whether or not local path refers to git repository.
def is_repo_root(local_path):
    
    if (os.path.exists(add_path_to_uri(local_path, '.git'))):
        if (not is_corrupt_repo(local_path)):
            return True;
        else:
            return False;
    else:
        return False;


# Parse data store source string as dict.
def parse_data_store_source(data_store_source_str):

    source_dict = dict.fromkeys(['uri', 'database', 'collection']);

    uri = '';
    databases = list();
    collections = list();
    
    try:
        
        (scheme, netloc, path, _, query, _) = urlparse.urlparse(data_store_source_str);

        if (netloc):
            uri = scheme+'://'+netloc if scheme else netloc;
        elif (path):
            uri = path;

        query_dict = urlparse.parse_qs(query);
        for field in query_dict: # For each query field...

            value = query_dict[field];
            if (field == 'database'):
                databases = value;
            elif (field == 'collection'):
                collections = value;
        
        source_dict['uri']        = uri;
        source_dict['database']   = databases[-1] if databases else DEFAULT_DB_NAME;
        source_dict['collection'] = collections[-1] if collections else DEFAULT_DB_COLLECTION_NAME;
        
        return source_dict;

    except:

        print(shared.get_warning_str("Malformed data store source string \'" + data_store_source_str + "\'"));
        return dict();


# Determine whether or not filename is an SQLite3 database.
# Inspired by: https://stackoverflow.com/a/15355790.
def is_sqlite3(filepath):

    if (not os.path.isfile(filepath)):
        return False;

    if (os.path.getsize(filepath) < 100):
        return False;

    with open(filepath, 'rb') as f:
        file_header = f.read(100); # Get file header.
    if (file_header[:16] == 'SQLite format 3\x00'): # If first 16 chars in file header are...
        return True;
    else:
        return False;


# Get SQLite storage class name from Pandas dtype name. 
def pandas_dtype_name_to_sqlite_storage_class_name(pandas_dtype_name):

    SQLITE_STORAGE_CLASSES = {'int64' : 'INTEGER',
                              'float64' : 'REAL',
                              'object' : 'TEXT'};

    if (pandas_dtype_name in SQLITE_STORAGE_CLASSES):
        return SQLITE_STORAGE_CLASSES[pandas_dtype_name];
    
    return '';


# Determine whether or not DataFrame has format expected of data store DataFrame.
def is_data_store_df(df):

    if (not df.columns.empty):
        for attribute in data_store_attributes: # Ensure each column name in DataFrame is what is expected in commits data store...
            if (attribute not in df.columns):
                return False;
    else:
        return False;

    df_copy = df.copy(); # Use copy to avoid modifying original.
    df_copy = df_copy[data_store_attributes];
    
    if (not df_copy.empty):
        
        data_store_df_skeleton = pandas.DataFrame(columns=data_store_attributes);
        data_store_dtypes = DATA_STORE_ATTRIBUTE_DTYPES.values();
        for attribute, dtype_name in zip(data_store_attributes, data_store_dtypes):
            data_store_df_skeleton[attribute] = pandas.Series(dtype=dtype_name);
        if (not (df_copy.dtypes.equals(data_store_df_skeleton.dtypes))): # Ensure each column is of the expected dtype.
            return False;
        
        if (df_copy.isnull().values.any()): # If any cells are NULL...
            return False;

    return True;


# If SQLite table does not exists (DNE), create it.
# Inspired by: https://stackoverflow.com/a/1604121
# Inspired by: https://stackoverflow.com/a/5205530
def create_sqlite_table_if_dne(table_name, db_connection):

    try:

        db_cursor = db_connection.cursor();
        
        db_cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\" AND name=\"'+table_name+'\";');
        result = db_cursor.fetchone();
        if (not result):

            sqlite_storage_class_names = list();
            for attribute in data_store_attributes:
                dtype_name = DATA_STORE_ATTRIBUTE_DTYPES[attribute];
                sqlite_storage_class_name = pandas_dtype_name_to_sqlite_storage_class_name(dtype_name);
                sqlite_storage_class_names.append(sqlite_storage_class_name);
            
            data_store_sqlite_table_attributes = zip(data_store_attributes, sqlite_storage_class_names);
            sqlite_attribute_str = ', '.join(['\"'+dssa[0]+'\" '+dssa[1] for dssa in data_store_sqlite_table_attributes]);

            db_cursor.execute('CREATE TABLE IF NOT EXISTS \"'+table_name+'\" ('+sqlite_attribute_str+');');
            db_connection.commit();

            while True: # Essentially, wait until table has successfully been created.

                db_cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\" AND name=\"'+table_name+'\";');
                result = db_cursor.fetchone();
                if (result):
                    break;
        
        return True;

    except:

        return False;


# Import data from SQLite data store into DataFrame.
def sqlite_data_store_to_df(uri, table_name):

    try:
        
        db_connection = sqlite3.connect(uri);

        if (create_sqlite_table_if_dne(table_name, db_connection)):
            
            table_df = pandas.read_sql_query('SELECT * FROM \"'+table_name+'\";', db_connection);

            if (is_data_store_df(table_df)):
                df = table_df.copy(); # Use copy to avoid modifying original.
                df['labels'] = df['labels'].apply(lambda cell_val: ast.literal_eval(cell_val)); # Interpret cell values (strings) as tuples.
                return df;

        return pandas.DataFrame();
    
    except:
        
        return pandas.DataFrame();


# Determine whether or not MongoDB connection is good.
def is_mongodb(uri):

    try:
       
        SERVER_TIMEOUT = 1; # Server timeout value in seconds.

        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=SERVER_TIMEOUT);

        client.server_info();

        client.close();

        return True;

    except:

        return False;


# Import data from MongoDB to DataFrame.
def mongodb_data_store_to_df(uri, db_name, collection_name):

    try:

        df = pandas.DataFrame();
    
        client = pymongo.MongoClient(uri);

        db = client[db_name];

        collection = db[collection_name];

        collection_df = pandas.DataFrame(list(collection.find()));

        if (is_data_store_df(collection_df)):
            df = collection_df.copy(); # Use copy to avoid modifying original. 
            df['labels'] = df['labels'].apply(lambda cell_val: tuple(cell_val)); # Convert cell values (lists) to tuples.
            client.close();
            return df;
            
        client.close();
        return pandas.DataFrame();
    
    except:

        return pandas.DataFrame();


# Get DataFrame of data store source.
def get_df_from_data_store_source(data_store_source_dict):

    uri = data_store_source_dict['uri'];
    collection = data_store_source_dict['collection']; # (Shorter variable name.)
    if (is_sqlite3(uri)):
        db_info_str = 'TABLE=\''+collection+'\'';
        df = sqlite_data_store_to_df(uri, collection);
    elif (is_mongodb(uri)):
        database = data_store_source_dict['database']; # (Shorter variable name.)
        db_info_str = 'DATABASE=\''+database+'\', COLLECTION=\''+collection+'\'';
        df = mongodb_data_store_to_df(uri, database, collection);
    else:
        db_info_str = '';
        df = pandas.DataFrame();

    return (df, db_info_str);


