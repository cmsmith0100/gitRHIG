#!/usr/bin/python


import argparse; # Script arguments.
import datetime; # Datetime handling.
import itertools; # To count items in generator.
import modules.shared as shared; # Custom, shared functionality.
import os; # File system handling.
import pandas; # DataFrame handling.
import pymongo; # MongoDB support.
import re; # Regular expressions.
import subprocess; # Invoke git applications.
import sys; # Script name, termination.
import sqlite3; # Database processing.
import urlparse; # URL parsing.


### Global Variables ###

script_name = os.path.basename(os.path.splitext(sys.argv[0])[0]); # Name of this Python script (minus '.py').

# Initial commit field labels.
COMMIT_FIELD_LABELS = ['commit_hash',
                       'author_name', 'author_email', 'author_unix_timestamp',
                       'committer_name', 'committer_email', 'committer_unix_timestamp',
                       'subject',
                       'patch_str'];

db_info_str = ''; # String of info regarding database name and collection name.

args = argparse.ArgumentParser(); # Script arguments object.

data_store_df = pandas.DataFrame(); # Data store DataFrame.

data_store_source_dict = dict(); # Data store source dict.

repo_local_path = ''; # Local environment path to repository.

commitssince_timestamp_str = ''; # Commits-since timestamp string.

commitsuntil_timestamp_str = ''; # Commits-until timestamp string.

# Commit record attributes.
repo_remote_hostname = ''; # Identifier for GitHub service.
repo_owner = ''; # Identifier for repository owner.
repo_name = ''; # Identifier for repository name.
path_in_repo = ''; # Path in repository commit log refers to.
labels = list(); # Commit record labels.

produced_atleast_one_commit_record = False; # Flag to specify whether at least one commit record was produced during execution.

# Initialize script arguments object.
def init_args(argparser):
    
    argparser.add_argument('-s', '--sources', help="list of local paths to git repos, or text file containing the same", type=str);
    argparser.add_argument('-a', '--anonymize', help="enforce anonymization on resultant commit records", action='store_true');
    argparser.add_argument('--paths', help="list of paths to process in each repo", type=str);
    argparser.add_argument('--labels', help="list of labels to apply on resultant commit records", type=str);
    argparser.add_argument('--since', help="process only commits applied after provided timestamp", type=str);
    argparser.add_argument('--until', help="process only commits applied before provided timestamp", type=str);
    argparser.add_argument('-o', '--output', help="destination data store for resultant commit records", type=str);
    
    return argparser.parse_args();


# Parse local path source str.
def parse_local_path_source(source_str):
    
    source_dict = dict.fromkeys(['uri', 'paths', 'labels', 'sinces', 'untils']);

    uri = ''; # Repo local paths.
    paths = list(); # Paths in repo.
    labels = list(); # Labels for each commit record.
    sinces = list(); # If len(sinces) == 1, sinces[0] is commits date-range-start timestamp.
    untils = list(); # If len(untils) == 1, untils[0] is commits date-range-end timestamp.

    try:
        
        parsed_uri = urlparse.urlparse(source_str);

        uri = parsed_uri.path;

        query_dict = urlparse.parse_qs(parsed_uri.query);
        for field in query_dict: # For each query field...

            value = query_dict[field];
            if (field == 'path'):
                paths = value;
            elif (field == 'label'):
                labels = value;
            elif (field == 'since'):
                sinces = value;
            elif (field == 'until'):
                untils = value;
        
        source_dict['uri']    = uri;
        source_dict['paths']  = shared.setlist(paths); # (Also, eliminate duplicates.)
        source_dict['labels'] = shared.setlist(labels); # (Also, eliminate duplicates.)
        source_dict['sinces'] = shared.setlist(sinces); # (Also, eliminate duplicates.)
        source_dict['untils'] = shared.setlist(untils); # (Also, eliminate duplicates.)

        return source_dict;
    
    except:
        
        print(shared.get_warning_str("Malformed repository source string \'" + source_str + "\'"));
        return dict();


# Get list of repo local path source dicts.
def get_repo_local_path_sources(sources_str):
    
    sources = list();
    
    if (sources_str): # String of semicolon-delimited list of sources...
        raw_sources = shared.get_unique_items_from_str(sources_str, ';'); # Get list of source strings.
        num_raw_sources = len(raw_sources);
        for i in range(0, num_raw_sources):
            source_str = raw_sources[i]; # Get source i...
            source_dict = parse_local_path_source(source_str);
            if (source_dict):
                uri = source_dict['uri'];
                if (os.path.isfile(uri)): # If source i is a file...
                    filecontents_str = shared.get_filecontents_str(source_str);
                    sources_from_file = get_repo_local_path_sources(filecontents_str);
                    num_sources_from_file = len(sources_from_file);
                    for j in range(0, num_sources_from_file):
                        sources_from_file[j]['paths']  = sources_from_file[i]['paths'] + source_dict['paths'];
                        sources_from_file[j]['labels'] = sources_from_file[i]['labels'] + source_dict['labels'];
                    sources = sources + sources_from_file;
                else:
                    if (os.path.isdir(uri)):
                        if (shared.is_repo_root(uri)):
                            if (source_dict not in sources):
                                sources.append(source_dict);
                        else:
                            print(shared.get_warning_str("\'" + uri + "\' does not refer to a git repository"));
                    else:
                        print(shared.get_warning_str("Malformed URI \'" + uri + "\'"));

    return sources;
 

# Determine whether or not URI has characteristics of a filename.
def is_filenameish(uri):


    path = urlparse.urlparse(uri).path;

    if (path):
        return True;
    else:
        return False;


# Check script arguments.
def check_args(args):
   
    global data_store_source_dict;
    global data_store_df;
    
    print("Checking script arguments...");
    
    # Repo sources (URIs, and corresponding paths and date-range timestamps).
    if (args.sources):
        args.sources = get_repo_local_path_sources(args.sources);
    
    if (not args.sources):
        sys.exit("Must provide at least one valid repository URI.");
    
    # Paths IN repo.
    args.paths = shared.get_unique_items_from_argstr(args.paths, ';');
    
    # Commit record labels for user-defined context.
    args.labels = shared.get_unique_items_from_argstr(args.labels, ';');
    
    # 'Since' timestamp string.
    since_timestamp_str = shared.parse_timestamp_str(args.since, 'since');
    args.since = since_timestamp_str if since_timestamp_str else shared.get_utcunixepoch_timestamp_str();
    
    # 'Until' timestamp string.
    until_timestamp_str = shared.parse_timestamp_str(args.until, 'until');
    args.until = until_timestamp_str if until_timestamp_str else shared.get_utcnow_timestamp_str();

    file_datetimenow_str = datetime.datetime.now().strftime('%Y%m%d-%H%M%S%f')[:-3]; # For default output filenames.

    # Initialize output data store object.
    if (args.output):
        data_store_source_dict = shared.parse_data_store_source(args.output);
        uri = data_store_source_dict['uri'];
        if (is_filenameish(uri)):
            if (shared.is_writable_file(uri)): # If destination data store is cleared for writing...
                if (os.path.isfile(uri)): # Because might not, in which case there's no need to retrieve DataFrame (if uri refers to SQLite3 source)...
                    if (shared.is_sqlite3(uri)):
                        collection = data_store_source_dict['collection'];
                        df = shared.sqlite_data_store_to_df(uri, collection); # Get existing SQLite db collection as DataFrame.
                        if (    (df.empty and df.columns.empty)
                                or (   df.columns.size != len(shared.data_store_attributes)    )   ):
                            sys.exit("Bad data store source \'" + args.output + "\'.");
                        else:
                            data_store_df = df;
                    elif (shared.is_mongodb(uri)):
                        pass;
                    else:
                        sys.exit("Could not connect to data store source \'" + args.output + "\'.");
            else:
                sys.exit("Not proceeding.");
        elif (shared.is_mongodb(uri)):
            pass;
        else:
            sys.exit("Could not connect to data store source \'" + args.output + "\'.");
    else:
        uri = './'+shared.TOOLSET_NAME+'-'+script_name+'_data-store_' + file_datetimenow_str + '.db'; # Default data store destination if none specified.
        data_store_source_dict = shared.parse_data_store_source(uri);
    
    return args;
    

# Write script argument configurations to stdout.
def echo_args(args):
   
    str_paths = ", ".join(["\'" + p + "\'" for p in args.paths]) if (args.paths) else "\'.\'";
    str_labels = ", ".join(["\'" + l + "\'" for l in args.labels]) if (args.labels) else "\'\'";

    print("all repositories: Paths: " + str_paths);
    print("all repositories: Since: " + args.since);
    print("all repositories: Until: " + args.until);
    print("all commit records: Anonymize: " + str(args.anonymize));
    print("all commit records: Labels: " + str_labels);


# Get repo remote origin URL.
def get_remote_origin_url(path_to_repo):
    
    config = '-c color.ui=\'false\'';
    gd = '--git-dir=\'' + path_to_repo + '/.git/\'';
    wt = '--work-tree=\'' + path_to_repo + '\'';
    
    wd = '--word-diff';
    
    cmd_str = 'git %s %s %s config --get remote.origin.url' % (config,gd,wt);
    #print(cmd_str);
    
    sp = subprocess.Popen(cmd_str,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          shell=True);
    
    (remote_origin_url, _) = sp.communicate();
    
    remote_origin_url = remote_origin_url.strip('\n'); # Remove newline '\n'.
    
    return remote_origin_url;


# Get commits-range timestamp string.
def get_commitsdaterange_timestamp_str(timestamps, default_timestamp_str, descriptor):
    
    timestamp_str = '';
    
    if (len(timestamps) > 1): # May be more than one because this was part of URL-like query string...
        print(shared.get_warning_str("Too many \'" + descriptor + "\' timestamps"));
        return default_timestamp_str;
    elif (len(timestamps) == 1):
        timestamp_str = timestamps[0]; # Get the only one.
        timestamp_str = shared.parse_timestamp_str(timestamp_str, descriptor);
    
    timestamp_str = timestamp_str if timestamp_str else default_timestamp_str;

    return timestamp_str;


# Formulate UTF-8 string from input string. 
def decode_str(input_str):
    
    output_str = input_str.decode('utf-8', 'replace');
    
    return output_str;


# Parse information on files affected in a single commit.
def get_commit_filenames(files_str):
    
    filenames_regex = r'\s+(.*[^\s]+)\s+\|\s+[a-zA-Z0-9]+'; # Regex for git-log '--stats' filenames output.
    
    filenames = re.findall(filenames_regex, files_str);
    
    return filenames;


# Determine commit number of file lines inserted, deleted, modified.
def get_changedlines_info(patch_str):
    
    WORDADDITION_REGEX = re.compile(ur'\x1B\[32m\{\+(.+?)\+\}\x1B\[m',
                                    re.UNICODE);
    LOOKSLIKELINEADDITION_REGEX = re.compile(ur'^\x1B\[32m\{\+(.+?)\+\}\x1B\[m$',
                                             re.UNICODE);
    WORDREMOVAL_REGEX = re.compile(ur'\x1B\[31m\[-(.+?)-\]\x1B\[m',
                                   re.UNICODE);
    LOOKSLIKELINEREMOVAL_REGEX = re.compile(ur'^\x1B\[31m\[-(.+?)-\]\x1B\[m$',
                                            re.UNICODE);
    
    num_lines_inserted = 0;
    num_lines_deleted = 0;
    num_lines_modified = 0;

    patch_str = patch_str.split('\n'); # Get string lines.

    for line in patch_str:
        
        line = line.strip(); # Prune leading, trailing space chars.
        
        word_additions = re.findall(WORDADDITION_REGEX, line);
        word_additions = [a for a in word_additions if (a.strip() is not '')]; # Prune space-char-only list elems.

        word_removals = re.findall(WORDREMOVAL_REGEX, line);
        word_removals = [r for r in word_removals if (r.strip() is not '')]; # Prune space-char-only list elems.

        if (    word_additions
                and word_removals   ): # Both word additions AND word removals...
            num_lines_modified = num_lines_modified + 1;
        elif (  word_additions
                and not word_removals   ): # Word additions ONLY...
            if (LOOKSLIKELINEADDITION_REGEX.search(line)):
                if (len(word_additions) > 1): # If there was more than one word addition...
                    num_lines_modified = num_lines_modified + 1;
                else:
                    num_lines_inserted = num_lines_inserted + 1;
            else:
                num_lines_modified = num_lines_modified + 1;
        elif (  not word_additions
                and word_removals   ): # Word removals ONLY...
            if (LOOKSLIKELINEREMOVAL_REGEX.search(line)):
                if (len(word_removals) > 1): # If there was more than one word removal...
                    num_lines_modified = num_lines_modified + 1;
                else:
                    num_lines_deleted = num_lines_deleted + 1;
            else:
                num_lines_modified = num_lines_modified + 1;
    
    return (num_lines_inserted, num_lines_deleted, num_lines_modified);


# Get git-log output str for a particular repository.
def get_gitlog_str():
    
    # git-log placeholders (commit fields).
    GITLOG_PLACEHOLDERS = ['%H',
                           '%an', '%ae', '%at',
                           '%cn', '%ce', '%ct',
                           '%s'];
    
    gitlog_format = '\x1e\x1e\x1e' + '\x1f\x1f\x1f'.join(GITLOG_PLACEHOLDERS) + '\x1f\x1f\x1f'; # Last '\x1f\x1f\x1f' accounts for files info field string.
    
    config = '-c color.diff.plain=\'normal\' -c color.diff.meta=\'normal bold\' -c color.diff.old=\'red\' -c color.diff.new=\'green\' -c color.diff.whitespace=\'normal\' -c color.ui=\'always\'';
    gd = '--git-dir=\'' + repo_local_path + '/.git/\'';
    wt = '--work-tree=\'' + repo_local_path + '\'';
    a = '--since=\'' + commitssince_timestamp_str + '\'';
    b = '--until=\'' + commitsuntil_timestamp_str + '\'';
    refs = '--all'
    fh = '--full-history';
    s = '--stat';
    STAT_WIDTH = 1000; # Length of git-log output. (Using insanely-high value to ensure "long" filenames are captured in their entirety.)
    sw = '--stat-width=' + str(STAT_WIDTH);
    f = '--format=' + gitlog_format;
    patch = '-p';
    wd = '--word-diff=plain';
    p = '-- \'' + path_in_repo + '\'';
    
    cmd_str = 'git %s %s %s log %s %s %s %s %s %s %s %s %s %s' % (config,gd,wt,a,b,refs,fh,s,sw,f,patch,wd,p);
    #print(cmd_str);

    sp = subprocess.Popen(cmd_str,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          shell=True);
    
    (gitlog_str, _) = sp.communicate();
    
    return gitlog_str;


# Parse git-log output str and store info in DataFrame.
# Inspired by a blog post by Steven Kryskalla: http://blog.lost-theory.org/post/how-to-parse-git-log-output/
def get_commit_records_df():

    sys.stdout.write("\r");
    sys.stdout.write("[git] Retrieving commit log...");
    sys.stdout.flush();
    t1 = datetime.datetime.now();
    gitlog_str = get_gitlog_str();
    t2 = datetime.datetime.now();
    t = t2 - t1;
    sys.stdout.write("\r");
    sys.stdout.write("[git] Retrieving commit log... done in " + str(t));
    print('');

    if (gitlog_str):

        commit_groups = (commit_group.strip('\x1e\x1e\x1e') for commit_group in gitlog_str.split('\n\x1e\x1e\x1e')); # Split commit records.

        (commit_groups, commit_groups_copy) = itertools.tee(commit_groups, 2); # Copy the commit groups iter so that we can use the copy to obtain the commits count.
        num_commits = sum(1 for cg in commit_groups_copy); # Obtain the commits count.
        
        row_labels = [r for r in range(0, num_commits)];
        df = pandas.DataFrame(index=row_labels, columns=shared.data_store_attributes);
        
        t1 = datetime.datetime.now();
        j = 0; # Number of records processed.
        k = 0.0; # Probability of records processed.
        for i in range(0, num_commits):

            commit_group = commit_groups.next();
            
            commit_fields = commit_group.split('\x1f\x1f\x1f');
            commit = dict(zip(COMMIT_FIELD_LABELS, commit_fields)); # Make commit dict.

            path = path_in_repo;

            commit_hash              = decode_str(commit['commit_hash']);
            author_name              = decode_str(commit['author_name']);
            author_email             = decode_str(commit['author_email']);
            author_unix_timestamp    = float(commit['author_unix_timestamp']);
            committer_name           = decode_str(commit['committer_name']);
            committer_email          = decode_str(commit['committer_email']);
            committer_unix_timestamp = float(commit['committer_unix_timestamp']);
            subject                  = decode_str(commit['subject']);
            len_subject              = len(subject); # (Preserve original len in case subject gets anonymized.)
            
            patch_str = commit['patch_str'];
            files_str = patch_str.split('diff --git a/')[0];
            
            filenames = get_commit_filenames(files_str);

            (num_lines_inserted, num_lines_deleted, num_lines_modified) = get_changedlines_info(patch_str);
            num_lines_changed = num_lines_inserted + num_lines_deleted + num_lines_modified;
        
            if (args.anonymize):
                path            = shared.get_anonymized_str(path);
                commit_hash     = shared.get_anonymized_str(commit_hash);
                author_name     = shared.get_anonymized_str(author_name);
                author_email    = shared.get_anonymized_str(author_email);
                committer_name  = shared.get_anonymized_str(committer_name);
                committer_email = shared.get_anonymized_str(committer_email);
                subject         = shared.get_anonymized_str(subject);
            
            row = df.iloc[i];

            row['repo_remote_hostname']     = repo_remote_hostname;
            row['repo_owner']               = repo_owner;
            row['repo_name']                = repo_name;
            row['path_in_repo']             = path;
            row['labels']                   = tuple(labels);
            row['commit_hash']              = commit_hash;
            row['author_name']              = author_name;
            row['author_email']             = author_email;
            row['author_unix_timestamp']    = author_unix_timestamp;
            row['committer_name']           = committer_name;
            row['committer_email']          = committer_email;
            row['committer_unix_timestamp'] = committer_unix_timestamp;
            row['subject']                  = subject;
            row['len_subject']              = len_subject;
            row['num_files_changed']        = len(filenames);
            row['num_lines_changed']        = num_lines_changed;
            row['num_lines_inserted']       = num_lines_inserted;
            row['num_lines_deleted']        = num_lines_deleted;
            row['num_lines_modified']       = num_lines_modified;
            
            j = j + 1;
            k = float(j) / float(num_commits);
            sys.stdout.write("\r");
            sys.stdout.write("Generating commit records: " + str(int(100.0*k)) + "% (" + str(j) + "/" + str(num_commits) + ")");
            sys.stdout.flush();
        
        t2 = datetime.datetime.now();
        t = t2 - t1;
        sys.stdout.write("\r");
        sys.stdout.write("Generating commit records: " + str(int(100.0*k)) + "% (" + str(j) + "/" + str(num_commits) + "), done in " + str(t));

        print('');

        return df;
    else:
        return pandas.DataFrame();


# Update data store DataFrame with project commit records.
def update_data_store_df(data_store_df, commit_records_df):

    if (data_store_df.empty): # If destination already exists...
        df = commit_records_df;
    else:
        df = pandas.concat([data_store_df, commit_records_df]); # Add project commit records to data store DataFrame.
        groupby_attributes = list(shared.data_store_attributes); # Work with copy NOT original list.
        groupby_attributes.remove('labels'); # Exclude attribute 'labels'.
        df = df.groupby(groupby_attributes).sum(); # Sum 'labels' in grouped rows.
        df = df.reset_index(); # Reset DataFrame rows indices.
        df = pandas.DataFrame(df, columns=shared.data_store_attributes); # To enforce original column order.
        df['labels'] = df['labels'].apply(lambda cell_val: tuple(shared.setlist(cell_val))); # Eliminate duplicate tuple elements in cell values.
    
    return df;


# Prepare data store DataFrame for export.
def data_store_df_to_sqlite(data_store_df, uri, table_name):

    try:
        
        df = data_store_df.copy(); # Use copy to avoid modifying original.

        df['labels'] = df['labels'].astype('str'); # Interpret cell values as strings (because sqlite does not support tuple structures in cells).

        db_conn = sqlite3.connect(uri);
        
        df.to_sql(table_name, db_conn, if_exists='replace', index=False);
        
        db_conn.close();
        
        return True;
    
    except:
        
       return False;


# Export data store DataFrame to MongoDB.
def data_store_df_to_mongodb(data_store_df, uri, db_name, collection_name):

    try:

        df = data_store_df.copy(); # Use copy to avoid modifying original.
        
        df['labels'] = df['labels'].apply(lambda cell_val: list(cell_val)); # Convert cell values to list structure.

        data_store_dicts_list = df.T.to_dict().values(); # Convert data store DataFrame structure to list of dicts.
        
        client = pymongo.MongoClient(uri);

        db = client[db_name];

        collection = db[collection_name];

        collection.insert_many(data_store_dicts_list);

        client.close();

        return True;

    except:

        return False;


# Export data store DataFrame to data store object.
def export_records_to_data_store(data_store_df):

    global db_info_str;
    global produced_atleast_one_commit_record;

    uri = data_store_source_dict['uri'];
    collection = data_store_source_dict['collection'];
    if (    is_filenameish(uri)
            and (not shared.is_mongodb(uri))): # (SQLite is only other option...)
        db_info_str = 'TABLE=\''+collection+'\'';
        data_store_df_to_sqlite(data_store_df, uri, collection);
    elif (shared.is_mongodb(uri)): # Easier to check if is MongoDB because SQLite file may not exists yet.
        database = data_store_source_dict['database'];
        db_info_str = 'DATABASE=\''+database+'\', COLLECTION=\''+collection+'\'';
        data_store_df_to_mongodb(data_store_df, uri, database, collection);

    produced_atleast_one_commit_record = True;

    return;


# Process info for single project.
def process_project():

    global data_store_df;

    commit_records_df = get_commit_records_df();
        
    if (commit_records_df.empty):
        print("No relevant commits found.");
    else:
        data_store_df = update_data_store_df(data_store_df, commit_records_df);
        sys.stdout.write("\r");
        sys.stdout.write("Exporting commit records into data store...");
        sys.stdout.flush();
        t1 = datetime.datetime.now();
        export_records_to_data_store(data_store_df);
        t2 = datetime.datetime.now();
        t = t2 - t1;
        sys.stdout.write("\r");
        sys.stdout.write("Exporting commit records into data store... done in " + str(t));
        print('');


# Driver.
def main():
    
    global args;
    global repo_local_path;
    global repo_remote_hostname;
    global repo_owner;
    global repo_name;
    global labels;
    global commitssince_timestamp_str;
    global commitsuntil_timestamp_str;
    global path_in_repo;

    # Process script configurations ("arguments").
    args = init_args(args);
    args = check_args(args);
    print('');
    echo_args(args);
    print('');
    
    t1 = datetime.datetime.now();
    num_repos = len(args.sources);
    for i in range(0, num_repos):
        
        print("Processing repository " + str(i+1) + " of " + str(num_repos) + "...");
        
        source_dict = args.sources[i];
        
        repo_local_path = source_dict['uri'];
        print("Location: \'" + repo_local_path + '\'');
        repo_local_path = os.path.abspath(repo_local_path);
        
        remote_origin_url = get_remote_origin_url(repo_local_path);
        repo_remote_hostname, repo_owner, repo_name = shared.get_repo_id(remote_origin_url);
        if (args.anonymize):
            repo_remote_hostname = shared.get_anonymized_str(repo_remote_hostname);
            repo_owner           = shared.get_anonymized_str(repo_owner);
            repo_name            = shared.get_anonymized_str(repo_name);

        paths = args.paths + source_dict['paths'];
        paths = shared.setlist(paths); # Eliminate duplicates.
        paths = paths if paths else ['.'];
        
        labels = args.labels + source_dict['labels'];
        labels = shared.setlist(labels); # (Also, eliminate duplicates).
        str_labels = ", ".join(["\'" + l + "\'" for l in labels]) if (labels) else "\'\'";

        commitssince_timestamp_str = get_commitsdaterange_timestamp_str(source_dict['sinces'], args.since, 'since');
        
        commitsuntil_timestamp_str = get_commitsdaterange_timestamp_str(source_dict['untils'], args.until, 'until');

        num_paths = len(paths);
        for j in range(0, num_paths): # For each path in repo...
            
            path_in_repo = paths[j];
            print("Processing repository path " + str(j+1) + " of " + str(num_paths) + "...");
            print("repository: Path: \'" + path_in_repo + "\'");
            print("repository: Since: " + commitssince_timestamp_str);
            print("repository: Until: " + commitsuntil_timestamp_str);
            print("commit records: Labels: " + str_labels);
            process_project();
        
        print('');

    uri = data_store_source_dict['uri'];
    if (produced_atleast_one_commit_record):
        print("Commit records written to \'"+uri+"\' ("+db_info_str+").");
        print('');
    else:
        print("No commit records written.");
        print('');
    
    t2 = datetime.datetime.now();
    t = t2 - t1;
    print("Execution complete: done in " + str(t));

    return;


main();

