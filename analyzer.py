#!/usr/bin/python


import argparse; # Script arguments
import ast; # Interpret structure strings literally.
import bokeh.io; # Interactive graphs in Jupyter Notebook.
import bokeh.layouts; # Output HTML column layout.
import bokeh.models; # Graph y-range, Hover Tool.
import bokeh.palettes; # Graph color palettes.
import bokeh.plotting; # Graph plot handling.
import collections; # Ordered dictionary.
import datetime; # Datetime handling.
import io; # File writing.
import math; # Math equations.
import modules.shared as shared; # Custom, shared functionality.
import os; # File, directory handling.
import pandas; # DataFrame handling.
import sys; # Script name, termination.
import time; # Time processing.
import unicodedata; # Unicode strings.


### Global Variables ###

script_name = os.path.basename(os.path.splitext(sys.argv[0])[0]); # Name of this Python script (minus '.py').

# Dict of datetime delta feature codes.
DATETIME_DELTA_FEATURE_CODES_DICT = collections.OrderedDict([('total_num_years_active', 'Y'),
                                                             ('total_num_months_active', 'm'),
                                                             ('total_num_days_active', 'd'),
                                                             ('total_num_hours_active', 'H'),
                                                             ('total_num_minutes_active', 'M'),
                                                             ('total_num_seconds_active', 'S')]);

# Dict of project attribute titles.
PROJECT_ATTRIBUTE_TITLES_DICT = collections.OrderedDict([('num_commits' , 'Number of Commits'),
                                                         ('num_lines_changed', 'Number of Lines Changed'),
                                                         ('num_lines_inserted', 'Number of Lines Inserted'),
                                                         ('num_lines_deleted' , 'Number of Lines Deleted'),
                                                         ('num_lines_modified', 'Number of Lines Modified')]);

# Dict of feature titles.
FEATURE_TITLES_DICT = collections.OrderedDict([('total_num_commits'       , 'Total Number of Commits'),
                                               ('total_num_lines_changed' , 'Total Number of Lines Changed'),
                                               ('total_num_lines_inserted', 'Total Number of Lines Inserted'),
                                               ('total_num_lines_deleted' , 'Total Number of Lines Deleted'),
                                               ('total_num_lines_modified', 'Total Number of Lines Modified'),
                                               ('total_num_years_active'  , 'Total Number of Years Active'),
                                               ('total_num_months_active' , 'Total Number of Months Active'),
                                               ('total_num_days_active'   , 'Total Number of Days Active'),
                                               ('total_num_hours_active'  , 'Total Number of Hours Active'),
                                               ('total_num_minutes_active', 'Total Number of Minutes Active'),
                                               ('total_num_seconds_active', 'Total Number of Seconds Active')]);

args = argparse.ArgumentParser(); # Script arguments object.

data_store_source_dict = dict(); # Data store source dict.

db_info_str = ''; # String of info regarding database name and collection name.

width_class_dict = dict(); # Dict of feature observations classification width configurations.
num_classes_dict = dict(); # Dict of feature observations classification count configurations.

PLOT_TEXT_FONT_SIZE = '12pt'; # Font size for text in output graphs.


# Initialize script arguments object.
def init_args(argparser):
    
    argparser.add_argument('--show-features', help="show available project features and exit", action='store_true');
    argparser.add_argument('-f', '--features', help="list of features (via labels) to activate in output analytics", type=str);
    argparser.add_argument('-s', '--source', help="source data store of commit records to be processed", type=str);
    argparser.add_argument('--paths-as-projects', help="treat each repo path as an individual project", action='store_true');
    argparser.add_argument('--width-class', help="list of key-value pairs of configurations for feature observations class width", type=str);
    argparser.add_argument('--num-classes', help="list of key-value pairs of configurations for feature observations classes count", type=str);
    argparser.add_argument('--labels', help="list of labels to consider when processing commit records", type=str);
    argparser.add_argument('--since', help="consider only commits applied after provided timestamp", type=str);
    argparser.add_argument('--until', help="consider only commits applied before provided timestamp", type=str);
    argparser.add_argument('--spreadsheet', help="output (spreadsheet) file for tabulated quantitative analytics", type=str);
    argparser.add_argument('--html', help="output (HTML) file for data visualizations", type=str);
    
    return argparser.parse_args();


# Get dict from string of semicolon-delimited key-value pairs representing user-provided feature observations classification configurations.
def get_class_configurations_dict(class_configurations_str):
    
    class_configurations_dict = dict();
    
    if (class_configurations_str): # Attempt to populate class_configurations_dict...
        class_configurations = shared.get_unique_items_from_argstr(class_configurations_str, ';');

        if (class_configurations):
            for class_configuration_str in class_configurations:
                class_configuration_keyvalue = class_configuration_str.split(':');
                if (len(class_configuration_keyvalue) == 2):
                    class_configurations_dict[class_configuration_keyvalue[0]] = class_configuration_keyvalue[1];
    
    return class_configurations_dict;


# Parse user-provided features.
def get_project_features(features_str):

    project_features = list();

    if (features_str):
        features = shared.get_unique_items_from_argstr(features_str, ';');
        for feature in features:
            if (feature in FEATURE_TITLES_DICT): # If 'feature' is one of the keys...
                project_features.append(feature);
            else:
                print(shared.get_warning_str("Unrecognized project feature \'" + feature + "\'"));

    return project_features;


# Eliminate data store DataFrame duplicate rows.
def eliminate_data_store_df_duplicate_rows(data_store_df):

    df = data_store_df.copy(); # Use copy to avoid modifying original.
    df['labels'] = df['labels'].astype('str'); # Interpret cell values as strings (input DataFrame cell values will be tuples). (Required in order for drop_duplicates() to work correctly.)
    df = df.drop_duplicates(); # Eliminate duplicate DataFrame rows.
    df = df.reset_index(drop=True); # Reset DataFrame row indices.
    df['labels'] = df['labels'].apply(lambda cell_val: ast.literal_eval(cell_val)); # Convert cell values (strings) back to tuples.

    return df;


# Check script arguments.
def check_args(args):

    global data_store_source_dict;
    global data_store_df;
    global db_info_str;

    # Features.
    if (args.show_features):
        print("Available project features (and corresponding labels used to reference them in script arguments):");
        for label in FEATURE_TITLES_DICT:
            title = FEATURE_TITLES_DICT[label];
            print("- " + title + " (`" + label + "`)");
        sys.exit();

    print("Checking script arguments...");
    
    args.features = get_project_features(args.features) if args.features else FEATURE_TITLES_DICT.keys();
    if (not args.features):
        print("(Warning: No valid project features to process.)");

    if (args.source):
        data_store_source_dict = shared.parse_data_store_source(args.source);
        (df, db_info_str) = shared.get_df_from_data_store_source(data_store_source_dict);
        if (df.empty):
            sys.exit('Bad data store source \'' + args.source + '\'.');
        else:
            data_store_df = df.copy(); # Use copy to avoid modifying original.
            data_store_df = data_store_df[shared.data_store_attributes];
            data_store_df = eliminate_data_store_df_duplicate_rows(data_store_df);
    else:
        sys.exit("Must specify a data store source.");
    
    args.width_class = get_class_configurations_dict(args.width_class);
    
    args.num_classes = get_class_configurations_dict(args.num_classes);
    
    # Commit record labels for user-defined context.
    args.labels = shared.get_unique_items_from_argstr(args.labels, ';');
 
    # 'Since' timestamp string.
    since_timestamp_str = shared.parse_timestamp_str(args.since, 'since');
    args.since = since_timestamp_str if since_timestamp_str else shared.get_utcunixepoch_timestamp_str();
    
    # 'Until' timestamp string.
    until_timestamp_str = shared.parse_timestamp_str(args.until, 'until');
    args.until = until_timestamp_str if until_timestamp_str else shared.get_utcnow_timestamp_str();

    file_datetimenow_str = datetime.datetime.now().strftime('%Y%m%d-%H%M%S%f')[:-3]; # For default output filenames.

    # Output spreadsheet.
    if (args.spreadsheet):
        spreadsheet = args.spreadsheet; # (Shorter variable name.)
        spreadsheet = spreadsheet if (spreadsheet.endswith('.xlsx')) else spreadsheet+'.xlsx';
        if (shared.is_writable_file(spreadsheet)):
            args.spreadsheet = os.path.abspath(spreadsheet);
        else:
            sys.exit("Not proceeding.");
    else: # Default output spreadsheet.
        args.spreadsheet = './'+shared.TOOLSET_NAME+'-'+script_name+'_quantitative-analytics_' + file_datetimenow_str + '.xlsx';
    
    # Output spreadsheet.
    if (args.html):
        html = args.html; # (Shorter variable name.)
        html = html if (html.endswith('.html')) else html+'.html';
        if (shared.is_writable_file(html)):
            args.html = os.path.abspath(html);
        else:
            sys.exit("Not proceeding.");
    else: # Default output HTML.
        args.html = './'+shared.TOOLSET_NAME+'-'+script_name+'_data-visualizations_' + file_datetimenow_str + '.html';
    
    return args;


# Write script argument configurations to stdout.
def echo_args(args):
    
    data_store_uri = data_store_source_dict['uri'];
    str_labels = ", ".join(["\'" + l + "\'" for l in args.labels]) if (args.labels) else "\'\'";
    
    print("Data store: \'" + data_store_uri + "\' ("+db_info_str+")");
    print("Labels: " + str_labels);
    print("Since: " + args.since);
    print("Until: " + args.until);


# Identify and prune unneeded commit records from DataFrame.
def filter_commit_records(commit_records_df):

    since = shared.utc_timestamp_str_to_unix_timestamp(args.since);
    until = shared.utc_timestamp_str_to_unix_timestamp(args.until);

    drop_indices = list(); # Keep track of which DataFrame rows (by indices) are not necessary in df.
    init_num_records = commit_records_df.shape[0];
    for i in range(0, init_num_records): # For each project commit record (row) in data store DataFrame...
        
        commit_record = commit_records_df.iloc[i];
        
        author_unix_timestamp = float(commit_record['author_unix_timestamp']);
        committer_unix_timestamp = float(commit_record['committer_unix_timestamp']);
        if (    author_unix_timestamp < since 
                or author_unix_timestamp > until
                or committer_unix_timestamp < since
                or committer_unix_timestamp > until   ):
            drop_indices.append(i);
        elif (args.labels):
            commit_record_labels_tuple = commit_record['labels'];
            include_commit_record = False;
            for label in args.labels: # For EACH user-supplied label...
                if (label in commit_record_labels_tuple): # If commit record has label... 
                    include_commit_record = True; # Indicate to include this commit record in resulting DataFrame.
            if (include_commit_record):
                pass; # Fine, commit record has at least one desired label.
            else:
                drop_indices.append(i);
    
    commit_records_df = commit_records_df.drop(drop_indices); # Drop DataFrame rows (given indices specifed).
    commit_records_df = commit_records_df.reset_index(drop=True); # Reset DataFrame row indices.

    return commit_records_df;


# Get DataFrame of project IDs based on some combination of commit record columns.
def get_project_ids_df(commit_records_df):

    if (args.paths_as_projects):
        project_ids_df = commit_records_df[['repo_remote_hostname', 'repo_owner', 'repo_name', 'path_in_repo']];
    else:
        project_ids_df = commit_records_df[['repo_remote_hostname', 'repo_owner', 'repo_name']];
    
    project_ids_df = project_ids_df.drop_duplicates(); # Eliminate duplicate DataFrame rows.
    project_ids_df = project_ids_df.reset_index(drop=True); # Reset DataFrame row indices.
    
    return project_ids_df;


# Process plot for project attribute patterns.
def process_project_attributebased_plot(plot, project_attribute_records_df, xsource_df_column, ysource_df_column, palette_index=0):
        
    project_attribute_records_dict = dict(project_attribute_records_df);
    
    project_attribute_records_data_source = bokeh.plotting.ColumnDataSource(data=project_attribute_records_dict);

    plot_color = bokeh.palettes.Dark2_5[palette_index];
    
    plot.circle(xsource_df_column,
                ysource_df_column,
                source=project_attribute_records_data_source,
                line_color=plot_color,
                fill_color=plot_color);
    plot.line(xsource_df_column,
              ysource_df_column,
              source=project_attribute_records_data_source,
              line_color=plot_color);
    
    return plot;


# Get plot for project commit patterns.
def get_commit_patterns_plot(project_ids_df, commit_records_df):
   
    copy_commit_records_df = commit_records_df.copy(); # Use copy to avoid modifying original.
    
    num_projects = project_ids_df.shape[0];
    
    num_commit_records = copy_commit_records_df.shape[0];
    committer_datetimes = list();
    committer_local_timestamp_strs = list();
    for i in range(0, num_commit_records): # Need data for committer datetimes (as timestamps) and committer datetime strings (hover tooltips)...

        commit_record = commit_records_df.iloc[i];

        committer_unix_timestamp = float(commit_record['committer_unix_timestamp']);
        
        committer_datetime = datetime.datetime.fromtimestamp(committer_unix_timestamp);
        committer_datetimes.append(committer_datetime);
        
        committer_local_timestamp_str = datetime.datetime.fromtimestamp(committer_unix_timestamp).strftime('%Y-%m-%d %H:%M:%S '+time.tzname[1]);
        committer_local_timestamp_strs.append(committer_local_timestamp_str);
    
    # Add new columns to DataFrame.
    copy_commit_records_df['committer_datetime'] = committer_datetimes;
    copy_commit_records_df['committer_local_timestamp_str'] = committer_local_timestamp_strs;
    
    hover = bokeh.models.HoverTool(tooltips=[('repo_remote_hostname', '@repo_remote_hostname'),
                                             ('repo_owner', '@repo_owner'),
                                             ('repo_name', '@repo_name'),
                                             ('path_in_repo', '@path_in_repo'),
                                             ('timestamp', '@committer_local_timestamp_str'),
                                             ('subject', '@subject'),
                                             ('num_lines_changed', '@num_lines_changed'),
                                             ('num_lines_inserted', '@num_lines_inserted'),
                                             ('num_lines_deleted', '@num_lines_deleted'),
                                             ('num_lines_modified', '@num_lines_modified')]);
    
    plot_title = "Commit Patterns (N=" + str(num_projects) + ")";
    
    plot = bokeh.plotting.figure(tools=[hover, 'wheel_zoom', 'box_zoom', 'pan', 'save', 'reset'],
                                 title=plot_title,
                                 x_axis_label="Date",
                                 x_axis_type='datetime',
                                 y_axis_label="Project");
    
    plot.title.align = 'center';
    plot.title.text_font_size = PLOT_TEXT_FONT_SIZE;
    plot.xaxis.major_label_text_font_size = PLOT_TEXT_FONT_SIZE;
    plot.xaxis.axis_label_text_font_size = PLOT_TEXT_FONT_SIZE;
    plot.yaxis.major_label_text_font_size = '0pt';
    plot.yaxis.axis_label_text_font_size = PLOT_TEXT_FONT_SIZE;

    for i in range(0, num_projects): # For each project...

        if (args.paths_as_projects): # Treat each repo path as an individual project...
            project_commit_records_df = copy_commit_records_df[(copy_commit_records_df['repo_remote_hostname'] == project_ids_df.iloc[i]['repo_remote_hostname']) &
                                                               (copy_commit_records_df['repo_owner']           == project_ids_df.iloc[i]['repo_owner']) &
                                                               (copy_commit_records_df['repo_name']            == project_ids_df.iloc[i]['repo_name']) &
                                                               (copy_commit_records_df['path_in_repo']         == project_ids_df.iloc[i]['path_in_repo']) ];
        else:
            project_commit_records_df = copy_commit_records_df[(copy_commit_records_df['repo_remote_hostname'] == project_ids_df.iloc[i]['repo_remote_hostname']) &
                                                               (copy_commit_records_df['repo_owner']           == project_ids_df.iloc[i]['repo_owner']) &
                                                               (copy_commit_records_df['repo_name']            == project_ids_df.iloc[i]['repo_name']) ];
        
        num_commits = project_commit_records_df.shape[0];
        ycoords = [(i+1) for j in range(0, num_commits)]; # To ensure same y-coodinates for all project commit points.
        project_commit_records_df = project_commit_records_df.assign(ycoordinates=ycoords); # Add new column for plot y-coordinates data.
        
        plot = process_project_attributebased_plot(plot, project_commit_records_df, 'committer_datetime', 'ycoordinates');

    return plot;


# Get plot for project attribute cumulative growth.
def get_project_attribute_cumulative_growth_plot(project_ids_df, commit_records_df, attribute):
   
    copy_commit_records_df = commit_records_df.copy(); # Use copy to avoid modifying original.
    if (attribute != 'num_commits'):
        copy_commit_records_df = copy_commit_records_df[(copy_commit_records_df[attribute] > 0)]; # Select only records where attribute value > 0.
        project_ids_df = get_project_ids_df(copy_commit_records_df); # Because some projects may have had no records where attribute value > 0.
    
    num_projects = project_ids_df.shape[0];
    
    num_commit_records = copy_commit_records_df.shape[0];
    committer_datetimes = list();
    committer_local_timestamp_strs = list();
    for i in range(0, num_commit_records): # Need data for committer datetimes (as timestamps) and committer datetime strings (hover tooltips)...

        commit_record = commit_records_df.iloc[i];

        committer_unix_timestamp = float(commit_record['committer_unix_timestamp']);
        
        committer_datetime = datetime.datetime.fromtimestamp(committer_unix_timestamp);
        committer_datetimes.append(committer_datetime);
        
        committer_local_timestamp_str = datetime.datetime.fromtimestamp(committer_unix_timestamp).strftime('%Y-%m-%d %H:%M:%S '+time.tzname[1]);
        committer_local_timestamp_strs.append(committer_local_timestamp_str);
    
    # Add new columns to DataFrame.
    copy_commit_records_df['committer_datetime'] = committer_datetimes;
    copy_commit_records_df['committer_local_timestamp_str'] = committer_local_timestamp_strs;

    MODEL_TOOLTIPS = [('repo_remote_hostname', '@repo_remote_hostname'),
                      ('repo_owner', '@repo_owner'),
                      ('repo_name', '@repo_name'),
                      ('path_in_repo', '@path_in_repo'),
                      ('timestamp', '@committer_local_timestamp_str'),
                      ('subject', '@subject')];
    model_tooltips = MODEL_TOOLTIPS if (attribute == 'num_commits') else MODEL_TOOLTIPS+[(attribute, '@'+attribute)];

    hover = bokeh.models.HoverTool(tooltips=model_tooltips);
    
    plot_title = "Growth (N=" + str(num_projects) + ")";
    
    plot = bokeh.plotting.figure(tools=[hover, 'wheel_zoom', 'box_zoom', 'pan', 'save', 'reset'],
                                 title=plot_title,
                                 x_axis_label="Date",
                                 x_axis_type='datetime',
                                 y_axis_label=PROJECT_ATTRIBUTE_TITLES_DICT[attribute]);
    
    plot.title.align = 'center';
    plot.title.text_font_size = PLOT_TEXT_FONT_SIZE;
    plot.xaxis.major_label_text_font_size = PLOT_TEXT_FONT_SIZE;
    plot.xaxis.axis_label_text_font_size = PLOT_TEXT_FONT_SIZE;
    plot.yaxis.major_label_text_font_size = PLOT_TEXT_FONT_SIZE;
    plot.yaxis.axis_label_text_font_size = PLOT_TEXT_FONT_SIZE;

    for i in range(0, num_projects): # For each project...

        if (args.paths_as_projects): # Treat each repo path as an individual project...
            project_commit_records_df = copy_commit_records_df[(copy_commit_records_df['repo_remote_hostname'] == project_ids_df.iloc[i]['repo_remote_hostname']) &
                                                               (copy_commit_records_df['repo_owner']           == project_ids_df.iloc[i]['repo_owner']) &
                                                               (copy_commit_records_df['repo_name']            == project_ids_df.iloc[i]['repo_name']) &
                                                               (copy_commit_records_df['path_in_repo']         == project_ids_df.iloc[i]['path_in_repo']) ];
        else:
            project_commit_records_df = copy_commit_records_df[(copy_commit_records_df['repo_remote_hostname'] == project_ids_df.iloc[i]['repo_remote_hostname']) &
                                                               (copy_commit_records_df['repo_owner']           == project_ids_df.iloc[i]['repo_owner']) &
                                                               (copy_commit_records_df['repo_name']            == project_ids_df.iloc[i]['repo_name']) ];
        
        project_commit_records_df = project_commit_records_df.sort_values('committer_datetime', ascending=True); # (Smallest values at top.)
        
        num_commits = project_commit_records_df.shape[0];
        cumulative_value = 0;
        ycoords = list();
        if (attribute == 'num_commits'):
            for j in range(0, num_commits):
                cumulative_value = cumulative_value + 1;
                ycoords.append(cumulative_value);
        else:
            for j in range(0, num_commits):
                cumulative_value = cumulative_value + project_commit_records_df.iloc[j][attribute];
                ycoords.append(cumulative_value);
        project_commit_records_df = project_commit_records_df.assign(ycoordinates=ycoords); # Add new column for plot y-coordinates data.
        
        palette_index = i % (len(bokeh.palettes.Dark2_5));
        
        plot = process_project_attributebased_plot(plot, project_commit_records_df, 'committer_datetime', 'ycoordinates', palette_index);

    return plot;


# Get datetime delta strftime-like string.
def get_datetime_delta_str(datetime_obj, code):

    if (code == 'Y'):
        return datetime_obj.strftime('%Y');
    elif (code == 'm'):
        return datetime_obj.strftime('%Y-%m');
    elif (code == 'd'):
        return datetime_obj.strftime('%Y-%m-%d');
    elif (code == 'H'):
        return datetime_obj.strftime('%Y-%m-%d %H:00:00');
    elif (code == 'M'):
        return datetime_obj.strftime('%Y-%m-%d %H:%M:00');
    elif (code == 'S'):
        return datetime_obj.strftime('%Y-%m-%d %H:%M:%S');


# Given list of UNIX timestamps, get number of unique datetime-delta-based timestamps.
def get_num_datetime_delta_local_timestamps(unix_timestamps, datetime_delta_code):

    datetime_delta_local_timestamps = list();
    
    for unix_timestamp in unix_timestamps:

        local_timestamp = time.localtime(unix_timestamp);
        datetime_obj = datetime.datetime.fromtimestamp(time.mktime(local_timestamp));
        datetime_delta_str = get_datetime_delta_str(datetime_obj, datetime_delta_code);
        datetime_delta_local_timestamps.append(datetime_delta_str);

    datetime_delta_local_timestamps = shared.setlist(datetime_delta_local_timestamps); # Eliminate duplicates.

    num_datetime_delta_local_timestamps = len(datetime_delta_local_timestamps);

    return num_datetime_delta_local_timestamps;


# Get DataFrame of project feature vectors.
def get_project_feature_vectors_df(features, project_ids_df, commit_records_df):
    
    project_labels = ['repo_remote_hostname',
                      'repo_owner',
                      'repo_name',
                      'paths_in_repo'];

    num_projects = project_ids_df.shape[0];
    
    num_features = len(features);
    
    row_labels = [r for r in range(0, num_projects)];
    column_labels = project_labels + features;
    df = pandas.DataFrame(index=row_labels, columns=column_labels);
    
    for i in range(0, num_projects): # For each project...
        
        project_id = project_ids_df.iloc[i]; # Get project ID i.

        # Retrieve project commit records.
        if (args.paths_as_projects): # Treat each repo path as an individual project...
            project_commit_records_df = commit_records_df[(commit_records_df['repo_remote_hostname'] == project_ids_df.iloc[i]['repo_remote_hostname']) &
                                                          (commit_records_df['repo_owner']           == project_ids_df.iloc[i]['repo_owner']) &
                                                          (commit_records_df['repo_name']            == project_ids_df.iloc[i]['repo_name']) &
                                                          (commit_records_df['path_in_repo']         == project_ids_df.iloc[i]['path_in_repo']) ];
        else:
            project_commit_records_df = commit_records_df[(commit_records_df['repo_remote_hostname'] == project_ids_df.iloc[i]['repo_remote_hostname']) &
                                                          (commit_records_df['repo_owner']           == project_ids_df.iloc[i]['repo_owner']) &
                                                          (commit_records_df['repo_name']            == project_ids_df.iloc[i]['repo_name']) ];

        num_project_commit_records = project_commit_records_df.shape[0];

        paths_in_repo = list();
        commit_hashes = list();
        unix_timestamps = list();
        num_lines_changed = 0;
        num_lines_inserted = 0;
        num_lines_deleted = 0;
        num_lines_modified = 0;

        for j in range(0, num_project_commit_records): # For each project commit record...

            commit_record = project_commit_records_df.iloc[j]; # Get commit record j.
            
            paths_in_repo.append(str(commit_record['path_in_repo'])); # (Cast to string to keep value from registering as unicode.)

            commit_hashes.append(commit_record['commit_hash']);
             
            unix_timestamps = unix_timestamps + [commit_record['author_unix_timestamp'], commit_record['committer_unix_timestamp']];
                
            num_lines_changed = num_lines_changed + commit_record['num_lines_changed'];
            num_lines_inserted = num_lines_inserted + commit_record['num_lines_inserted'];
            num_lines_deleted = num_lines_deleted + commit_record['num_lines_deleted'];
            num_lines_modified = num_lines_modified + commit_record['num_lines_modified'];

        df.iloc[i]['repo_remote_hostname']     = project_id['repo_remote_hostname'];
        df.iloc[i]['repo_owner']               = project_id['repo_owner'];
        df.iloc[i]['repo_name']                = project_id['repo_name'];
        df.iloc[i]['paths_in_repo']            = tuple(shared.setlist(paths_in_repo));
        df.iloc[i]['total_num_commits']        = len(shared.setlist(commit_hashes));
        df.iloc[i]['total_num_lines_changed']  = num_lines_changed;
        df.iloc[i]['total_num_lines_inserted'] = num_lines_inserted;
        df.iloc[i]['total_num_lines_deleted']  = num_lines_deleted;
        df.iloc[i]['total_num_lines_modified'] = num_lines_modified;
        
        for k in range(0, num_features): # For each datetime delta code (or feature, essentially)...

            feature = features[k]; # Get feature k...
            if (feature in DATETIME_DELTA_FEATURE_CODES_DICT):

                datetime_delta_code = DATETIME_DELTA_FEATURE_CODES_DICT[feature]; # Get datetime delta code.
                num_datetime_delta_local_timestamps = get_num_datetime_delta_local_timestamps(unix_timestamps, datetime_delta_code); # Get number of unique datetime-delta-based timestamps from all commit records.
                df.iloc[i][feature] = num_datetime_delta_local_timestamps;

    return df;


# Determine whether or not s is numeric.
# Inspired by: https://www.pythoncentral.io/how-to-check-if-a-string-is-a-number-in-python-including-unicode/
def is_numeric(s):

    try:
        float(s);
        return True;
    except:
        pass;

    try:
        unicodedata.numeric(s);
        return True;
    except:
        pass;
    
    return False;


# Get dict of valid user-provided feature observations classification configurations.
def get_checked_class_configurations_dict(class_configurations_dict, features, class_configuration_type):

    checked_class_configurations_dict = dict();
    
    if (class_configurations_dict):
        for key in class_configurations_dict:
            if (key in features):
                feature = key;
                s = class_configurations_dict[feature];
                if (is_numeric(s)):
                    if (isinstance(s, float)):
                        print("Warning: value in \'" + class_configuration_type + "\' for feature \'" + feature + "\' is type \'float\' - converting to \'int\'.");
                    s = int(s);
                    if (s > 0):
                        checked_class_configurations_dict[feature] = s;
                    else:
                        print(shared.get_warning_str("Value in \'" + class_configuration_type + "\' for feature \'" + feature + "\' must be non-negative"));
                else:
                    print(shared.get_warning_str("Value in \'" + class_configuration_type + "\' for feature \'" + feature + "\' is not numeric"));
            else:
                print(shared.get_warning_str("Feature \'" + key + "\' for \'" + class_configuration_type + "\' does not exist"));

    return checked_class_configurations_dict;


# Get feature observations classifications DataFrame, each class being a single unit wide.
def get_singleunitwide_classes_df(feature, project_feature_vectors_df):

    observations = project_feature_vectors_df[feature].tolist(); # Get feature values.
    num_classes = len(observations);
    width_class = 1;
    
    row_labels = [r for r in range(0, num_classes)];
    COLUMN_LABELS = ['>=', '<'];
    df = pandas.DataFrame(index=row_labels, columns=COLUMN_LABELS);
    df.fillna(0.0);
    
    # For each class, define start and end values.
    for i in range(0, num_classes):

        observation = project_feature_vectors_df.iloc[i][feature]; # Get feature value for project i.
        start = observation;
        end = start + width_class;
        df.iloc[i]['>='] = start;
        df.iloc[i]['<'] = end;

    df = df.drop_duplicates(); # Eliminate duplicate DataFrame rows.
    df = df.reset_index(drop=True); # Reset DataFrame row indices.

    return df;


# Find smallest, non-negative value of k such that 2^(k) > n.
def get_k_smallest_pow2k_greater_than_n(n):

    k = 0;
    while (True):

        current_pow2k_value = math.pow(2, k);
        if (current_pow2k_value > n):
            return k;
        else:
            k = k + 1;


# Get number of classes based on 2^k rule.
def get_num_classes(observations):

    num_observations = len(observations);
    min_observation = min(observations);
    max_observation = max(observations);
    range_observations = max_observation - min_observation;
    k = get_k_smallest_pow2k_greater_than_n(num_observations);
    
    observations.sort();
    observations = shared.setlist(observations); # List of unique observations only (no duplicate values).
    while (True):

        if (k == 1):
            return k;
        
        num_classes = k;
        width_class = int(range_observations / num_classes) + 1;
        #width_class = int(round((range_observations/num_classes)));
        num_classes = num_classes + 1;

        include_classes = [False] * num_classes; # List where each index signifies whether or not to include class i.
        for i in range(0, num_classes): # For each class...

            start = min_observation + (i * width_class);
            end = start + width_class;

            for o in observations: # For each unique observation...
                if (    o >= start
                        and o < end): # If observation o is in class i...
                    include_classes[i] = True; # Mark class i as includable.
                    break;

        if (False in include_classes): # If any class shall not be included...
            k = k - 1; # Try smaller value of k.
        else:
            return k;

    return k;


# If x is out of range, return either begin or end (depending).
def rangify(x, begin, end):

    if (x < begin):
        return begin;
    elif (x > end):
        return end;
    else: # Case where start <= x <= end...
        return x;


# Get feature observations classifications DataFrame, each class based on user-provided specifications.
def get_userdefined_classes_df(feature, project_feature_vectors_df):
    
    observations = project_feature_vectors_df[feature].tolist(); # Get feature values.
    num_observations = len(observations);
    min_observation = min(observations);
    max_observation = max(observations);
    range_observations = max_observation - min_observation; # Calc width of range of observations.

    min_num_classes = 1;
    max_num_classes = 1 + int(3.3 * math.log10(num_observations)); # Inspired by: https://en.wikipedia.org/wiki/Frequency_distribution#Construction_of_frequency_distributions.

    min_width_class = 1;
    max_width_class = range_observations + 1; # Add 1 to satisfy [min_observation,max_observation+1).
    
    if (feature in num_classes_dict): # (Priority for defining number of classes.)
        num_classes = num_classes_dict[feature];
        num_classes = rangify(num_classes, min_num_classes, max_num_classes);
        width_class = int(range_observations / num_classes) + 1;
    elif (feature in width_class_dict):
        width_class = width_class_dict[feature];
        width_class = rangify(width_class, min_width_class, max_width_class);
        num_classes = int(range_observations / width_class);
        num_classes = num_classes + 1; # Do this for safety.
    else:
        num_classes = get_num_classes(observations);
        width_class = int(range_observations / num_classes);
        width_class = rangify(width_class, min_width_class, max_width_class);
        num_classes = num_classes + 1; # Do this for safety.

    row_labels = [r for r in range(0, num_classes)];
    COLUMN_LABELS = ['>=', '<'];
    df = pandas.DataFrame(index=row_labels, columns=COLUMN_LABELS);
    df.fillna(0.0);
    
    # For each class, define start (inclusive) and end (non-inclusive) values.
    for i in range(0, num_classes):

        start = min_observation + (i * width_class);
        end = start + width_class;
        df.iloc[i]['>='] = start;
        df.iloc[i]['<'] = end;

    df = df.drop_duplicates(); # Eliminate duplicate DataFrame rows.
    df = df.reset_index(drop=True); # Reset DataFrame row indices.

    return df;


# Get particular feature observations classifications DataFrame (depending).
def get_classes_df(feature, project_feature_vectors_df, use_singleunitwide_classes=True):

    if (use_singleunitwide_classes):
        df = get_singleunitwide_classes_df(feature, project_feature_vectors_df);
    else:
        df = get_userdefined_classes_df(feature, project_feature_vectors_df);

    return df;


# Get preliminary feature observations frequency distribution DataFrame.
def get_frequency_distribution_df(feature, project_feature_vectors_df, classes_df):
   
    classes_df = classes_df.sort_values(by=['>=']); # Sort DataFrame rows by class begin-value.
    classes_df = classes_df.reset_index(drop=True); # Reset DataFrame row indices.
    
    num_projects = project_feature_vectors_df.shape[0];
    
    num_classes = classes_df.shape[0];
    
    row_labels = [r for r in range(0, num_classes)];
    COLUMN_LABELS = [feature,
                     '>=',
                     '<',
                     'frequency',
                     'cumulative_frequency',
                     'percentage',
                     'cumulative_percentage'];
    df = pandas.DataFrame(index=row_labels, columns=COLUMN_LABELS);
    df = df.fillna(0.0);
    
    drop_indices = list(); # Keep track of which DataFrame rows (by indices) are not necessary in df.
    for i in range(0, num_classes): # For each interval...
        
        feature_class = classes_df.iloc[i];
        df.iloc[i]['>='] = feature_class['>='];
        df.iloc[i]['<']  = feature_class['<'];
        
        relevant_project_feature_vectors = project_feature_vectors_df[(project_feature_vectors_df[feature] >= feature_class['>=']) &
                                                                      (project_feature_vectors_df[feature] <  feature_class['<'])];
        
        if (relevant_project_feature_vectors.empty):
            drop_indices.append(i);
        else:
            num_relevant_projects = relevant_project_feature_vectors.shape[0];
            for j in range(0, num_relevant_projects): # For each relevant project...
            
                relevant_project_feature_vector = relevant_project_feature_vectors.iloc[j]; # Get relevant project feature vector j...
                observation = relevant_project_feature_vector[feature];
            
                df.iloc[i][feature] = observation;
                
                frequency = df.iloc[i]['frequency'];
                df.iloc[i]['frequency'] = frequency + 1;
                
                frequencies = [df.iloc[k]['frequency'] for k in range(0, i+1)]; # Get frequency totals (up to and including this one) as a list.
                df.iloc[i]['cumulative_frequency'] = sum(frequencies);
                
                frequency = df.iloc[i]['frequency'];
                df.iloc[i]['percentage'] = (float(frequency) / float(num_projects)) * 100.0;
                
                cumulative_frequency = df.iloc[i]['cumulative_frequency'];
                df.iloc[i]['cumulative_percentage'] = (float(cumulative_frequency) / float(num_projects)) * 100.0;

    df = df.drop(drop_indices); # Drop DataFrame rows at specified indices.
    df = df.reset_index(drop=True); # Reset DataFrame row indices.

    return df;


# Get feature frequency distribution DataFrame containing a record (row) or each project.
def get_feature_frequency_distribution_df(feature, project_feature_vectors_df, use_singleunitwide_classes):
    
    project_feature_vectors_df = project_feature_vectors_df.sort_values(by=[feature]); # Ensure DataFrame rows are sorted by feature observations.
    project_feature_vectors_df = project_feature_vectors_df.reset_index(drop=True); # Reset DataFrame row indices.
    
    num_projects = project_feature_vectors_df.shape[0];
    row_labels = [r for r in range(0, num_projects)];
    COLUMN_LABELS = ['repo_remote_hostname',
                     'repo_owner',
                     'repo_name',
                     'paths_in_repo',
                     feature,
                     '>=',
                     '<',
                     'frequency',
                     'cumulative_frequency',
                     'percentage',
                     'cumulative_percentage'];
    df = pandas.DataFrame(index=row_labels, columns=COLUMN_LABELS);
    df.fillna(0.0);
    
    classes_df = get_classes_df(feature, project_feature_vectors_df, use_singleunitwide_classes);
    
    frequency_distribution_df = get_frequency_distribution_df(feature, project_feature_vectors_df, classes_df);
    
    num_classes = frequency_distribution_df.shape[0];
    for i in range(0, num_projects): # For each project feature vector...
        
        project_summary = project_feature_vectors_df.iloc[i]; # Get project feature vector i.
        observation = project_summary[feature]; # Get value in project feature.
        
        for j in range(0, num_classes): # For each class...
            
            feature_class = frequency_distribution_df.iloc[j]; # Get class j.
            
            if (    float(observation) >= float(feature_class['>='])
                    and float(observation) < float(feature_class['<'])   ):
                df.iloc[i]['repo_remote_hostname']  = project_summary['repo_remote_hostname'];
                df.iloc[i]['repo_owner']            = project_summary['repo_owner'];
                df.iloc[i]['repo_name']             = project_summary['repo_name'];
                df.iloc[i]['paths_in_repo']         = project_summary['paths_in_repo'];
                df.iloc[i][feature]                 = observation;
                df.iloc[i]['>=']                    = feature_class['>='];
                df.iloc[i]['<']                     = feature_class['<'];
                df.iloc[i]['frequency']             = feature_class['frequency'];
                df.iloc[i]['cumulative_frequency']  = feature_class['cumulative_frequency'];
                df.iloc[i]['percentage']            = feature_class['percentage'];
                df.iloc[i]['cumulative_percentage'] = feature_class['cumulative_percentage'];
    
    df = df.sort_values(by=[feature]); # Ensure DataFrame rows are sorted by feature observations.
    df = df.reset_index(drop=True); # Reset DataFrame row indices.

    return df;


# Process feature cumulative distribution function (CDF) plot.
def process_feature_cdf_plot(plot, feature_frequency_distribution_df, feature):
        
    feature_frequency_distribution_dict = dict(feature_frequency_distribution_df);
    
    feature_frequency_distribution_data_source = bokeh.plotting.ColumnDataSource(data=feature_frequency_distribution_dict);
    
    plot.circle(feature,
                'cumulative_probability',
                source=feature_frequency_distribution_data_source,
                line_color='red',
                fill_color='red');
    plot.line(feature,
              'cumulative_probability',
              source=feature_frequency_distribution_data_source,
              line_color='red');
    
    return plot;


# Get feature cumulative distribution function (CDF) plot.
def get_feature_cdf_plot(feature, feature_frequency_distribution_df):
    
    copy_feature_frequency_distribution_df = feature_frequency_distribution_df.copy(); # Use copy to avoid modifying original.
    
    num_projects = copy_feature_frequency_distribution_df.shape[0];
    
    num_feature_frequency_distribution = feature_frequency_distribution_df.shape[0];
    
    num_classes = feature_frequency_distribution_df.shape[0];
    cumulative_probabilities = list();
    for i in range(0, num_classes): # Need data for cumulative probability because CDF not in terms of percent...

        feature_frequency_distribution_df_row = feature_frequency_distribution_df.iloc[i];

        cumulative_percentage = float(feature_frequency_distribution_df_row['cumulative_percentage']);
        cumulative_probability = cumulative_percentage / 100.0;
        cumulative_probabilities.append(cumulative_probability);

    # Add new column to DataFrame.
    copy_feature_frequency_distribution_df['cumulative_probability'] = cumulative_probabilities;
    
    hover = bokeh.models.HoverTool(tooltips=[('repo_remote_hostname', '@repo_remote_hostname'),
                                             ('repo_owner', '@repo_owner'),
                                             ('repo_name', '@repo_name'),
                                             ('paths_in_repo', '@paths_in_repo'),
                                             (feature, '@'+feature)]);
    
    plot_title = "Cumulative Distribution Function (N=" + str(num_projects) + ")";
    
    feature_title = FEATURE_TITLES_DICT[feature];

    plot = bokeh.plotting.figure(tools=[hover, 'wheel_zoom', 'box_zoom', 'pan', 'save', 'reset'],
                                 title=plot_title,
                                 x_axis_label=feature_title,
                                 y_axis_label='Probability',
                                 y_range=bokeh.models.Range1d(0, 1, bounds='auto'));
    
    plot.title.align = 'center';
    plot.title.text_font_size = PLOT_TEXT_FONT_SIZE;
    plot.xaxis.major_label_text_font_size = PLOT_TEXT_FONT_SIZE;
    plot.xaxis.axis_label_text_font_size = PLOT_TEXT_FONT_SIZE;
    plot.yaxis.major_label_text_font_size = PLOT_TEXT_FONT_SIZE;
    plot.yaxis.axis_label_text_font_size = PLOT_TEXT_FONT_SIZE;

    plot = process_feature_cdf_plot(plot, copy_feature_frequency_distribution_df, feature);

    return plot;


# Process feature histogram plot.
def process_feature_histogram_plot(plot, feature_frequency_distribution_df):
    
    feature_frequency_distribution_dict = dict(feature_frequency_distribution_df);
    
    feature_frequency_distribution_data_source = bokeh.plotting.ColumnDataSource(data=feature_frequency_distribution_dict);
    
    plot.quad(top='frequency',
              bottom='bottom',
              left='>=',
              right='<',
              source=feature_frequency_distribution_data_source,
              line_color='black',
              fill_color='blue');

    return plot;


# Get feature histogram plot.
def get_feature_histogram_plot(feature, feature_frequency_distribution_df):
    
    copy_feature_frequency_distribution_df = feature_frequency_distribution_df.copy(); # Use copy to avoid modifying original.
    
    num_projects = copy_feature_frequency_distribution_df.shape[0];
    bottoms = list();
    for i in range(0, num_projects): # Need data for bottom sides of histogram bins (y-values)...

        bottoms.append(0);

    # Add new column to DataFrame.
    copy_feature_frequency_distribution_df['bottom'] = bottoms;
    
    hover = bokeh.models.HoverTool(tooltips=[('repo_remote_hostname', '@repo_remote_hostname'),
                                             ('repo_owner', '@repo_owner'),
                                             ('repo_name', '@repo_name'),
                                             ('paths_in_repo', '@paths_in_repo'),
                                             (feature, '@'+feature)]);

    num_classes = len(set(copy_feature_frequency_distribution_df['>='].tolist()));

    width_class = int(copy_feature_frequency_distribution_df.iloc[0]['<'] - copy_feature_frequency_distribution_df.iloc[0]['>=']);

    plot_title = "Histogram (N=" + str(num_projects) + ", num_classes=" + str(num_classes) + ", width_class=" + str(width_class) + ")";
    
    feature_title = FEATURE_TITLES_DICT[feature];

    plot = bokeh.plotting.figure(tools=[hover, 'wheel_zoom', 'box_zoom', 'pan', 'save', 'reset'],
                                 title=plot_title,
                                 x_axis_label=feature_title,
                                 y_axis_label='Number of Projects',);
    
    plot.title.align = 'center';
    plot.title.text_font_size = PLOT_TEXT_FONT_SIZE;
    plot.xaxis.major_label_text_font_size = PLOT_TEXT_FONT_SIZE;
    plot.xaxis.axis_label_text_font_size = PLOT_TEXT_FONT_SIZE;
    plot.yaxis.major_label_text_font_size = PLOT_TEXT_FONT_SIZE;
    plot.yaxis.axis_label_text_font_size = PLOT_TEXT_FONT_SIZE;

    plot = process_feature_histogram_plot(plot, copy_feature_frequency_distribution_df);

    return plot;


# Construct output filename having provided attributes.
def construct_output_filename(data_store_location, dirname, desc, ext):

    (path, _) = os.path.splitext(data_store_location);
    
    dirname = dirname if dirname else os.path.dirname(path);
    dirname = os.path.abspath(dirname);
    
    basename = os.path.basename(path) + '-' + desc + '.' + ext;

    output_filename = shared.add_path_to_uri(dirname, basename);

    return output_filename;


# Write DataFrame to file.
def write_dataframes_to_file(dataframes, destination):
    
    df_writer = pandas.ExcelWriter(destination, engine='xlsxwriter');

    num_dataframes = len(dataframes);
    for i in range(0, num_dataframes):

        (df, sheet_name, index) = dataframes[i]; # Get DataFrame i...
        df.to_excel(df_writer, sheet_name, index=index);
    
    df_writer.save();

    return;


# Driver.
def main():
    
    global args;
    global data_store_df;
    global width_class_dict;
    global num_classes_dict;
    
    # Process script configurations ("arguments").
    args = init_args(args);
    args = check_args(args);
    print('');
    echo_args(args);
    print('');

    commit_records_df = filter_commit_records(data_store_df); # Filter commit records based on time range.
    commit_records_df.sort_values('committer_unix_timestamp', ascending=False); # (Largest values at top.)

    t1 = datetime.datetime.now();
    if (commit_records_df.empty):
        print("No relevant commits records to process.");
    else:
        xlsx_sheets = list();
        plots = list();
        
        features = args.features;
        
        sys.stdout.write("\r");
        sys.stdout.write("Identifying projects...");
        sys.stdout.flush();
        project_ids_df = get_project_ids_df(commit_records_df);
        sys.stdout.write("\r");
        sys.stdout.write("Identifying projects... done.");
        print('');
        
        sys.stdout.write("\r");
        sys.stdout.write("Processing project commit-patterns data...");
        sys.stdout.flush();
        commit_patterns_plot = get_commit_patterns_plot(project_ids_df, commit_records_df);
        sys.stdout.write("\r");
        sys.stdout.write("Processing project commit-patterns data... done.");
        print('');
        plots.append(commit_patterns_plot);

        project_attributes = PROJECT_ATTRIBUTE_TITLES_DICT.keys();
        
        num_project_attributes = len(project_attributes);
        for i in range(0, num_project_attributes):
            attribute = project_attributes[i];
            sys.stdout.write("\r");
            sys.stdout.write("Processing project data for attribute `" + attribute + "`...");
            sys.stdout.flush();
            project_attribute_cumulative_growth_plot = get_project_attribute_cumulative_growth_plot(project_ids_df, commit_records_df, attribute);
            sys.stdout.write("\r");
            sys.stdout.write("Processing project data for attribute `" + attribute + "`... done.");
            print('');
            plots.append(project_attribute_cumulative_growth_plot);

        if (features):
            sys.stdout.write("\r");
            sys.stdout.write("Generating project feature vectors...");
            sys.stdout.flush();
            project_feature_vectors_df = get_project_feature_vectors_df(features, project_ids_df, commit_records_df);
            sys.stdout.write("\r");
            sys.stdout.write("Generating project feature vectors... done.");
            print('');

            num_projects = project_feature_vectors_df.shape[0];
            
            xlsx_sheets.append((project_feature_vectors_df, 'project_feature_vectors', False));
            
            width_class_dict = args.width_class;
            width_class_dict = get_checked_class_configurations_dict(width_class_dict, features, class_configuration_type='width-class');
            num_classes_dict = args.num_classes;
            num_classes_dict = get_checked_class_configurations_dict(num_classes_dict, features, class_configuration_type='num-classes');

            num_features = len(features);
            for i in range(0, num_features):
                
                feature = features[i];

                sys.stdout.write("\r");
                sys.stdout.write("Processing analytics for feature `" + feature + "`...");
                sys.stdout.flush();
                cdf_feature_frequency_distribution_df = get_feature_frequency_distribution_df(feature, project_feature_vectors_df, use_singleunitwide_classes=True);
                feature_cdf_plot = get_feature_cdf_plot(feature, cdf_feature_frequency_distribution_df);
                plots.append(feature_cdf_plot);
                
                if (num_projects > 1):
                    if (    (feature not in width_class_dict)
                            and (feature not in num_classes_dict)   ):
                        histogram_feature_frequency_distribution_df = get_feature_frequency_distribution_df(feature, project_feature_vectors_df, use_singleunitwide_classes=False);
                        xlsx_feature_frequency_distribution_df = cdf_feature_frequency_distribution_df;
                    else:
                        if (    (feature in width_class_dict)
                                and (width_class_dict[feature] == 1)):
                            histogram_feature_frequency_distribution_df = get_feature_frequency_distribution_df(feature, project_feature_vectors_df, use_singleunitwide_classes=True);
                        else:
                            histogram_feature_frequency_distribution_df = get_feature_frequency_distribution_df(feature, project_feature_vectors_df, use_singleunitwide_classes=False);
                        xlsx_feature_frequency_distribution_df = histogram_feature_frequency_distribution_df;
                else:
                    histogram_feature_frequency_distribution_df = cdf_feature_frequency_distribution_df;
                    xlsx_feature_frequency_distribution_df = cdf_feature_frequency_distribution_df;

                feature_histogram_plot = get_feature_histogram_plot(feature, histogram_feature_frequency_distribution_df);
                sys.stdout.write("\r");
                sys.stdout.write("Processing analytics for feature `" + feature + "`... done.");
                print('');
                plots.append(feature_histogram_plot);
                
                xlsx_sheets.append((xlsx_feature_frequency_distribution_df, feature, False));

        xlsx_output_filename = args.spreadsheet;
        html_output_filename = args.html;
        
        print('');
        
        # Output qualitative data.
        if (features):
            write_dataframes_to_file(xlsx_sheets, xlsx_output_filename);
            print("Quantitative analytics written to \'"+xlsx_output_filename+"\'.");
        
        # Output visual data.
        bokeh.plotting.output_file(html_output_filename, title="Projects' Statistics");
        bokeh.io.save(bokeh.layouts.column(plots));
        print("Data visualizations written to \'"+html_output_filename+"\'.");
        print('');
    
    t2 = datetime.datetime.now();
    t = t2 - t1;
    print("Execution complete: done in " + str(t));


main();

