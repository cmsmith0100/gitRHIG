#!/usr/bin/python


import argparse; # Script arguments.
import datetime; # Timestamp handling.
import getpass; # Get stdin without displaying.
import json; # JSON handling.
import modules.shared as shared; # Custom, shared functionality.
import os; # File, directory handling.
import requests; # HTTP requests.
import subprocess; # Git.
import sys; # Script name, termination.
import urlparse; # URL parsing.


### Global Variables ###

script_name = os.path.basename(os.path.splitext(sys.argv[0])[0]); # Name of this Python script (minus '.py').

args = argparse.ArgumentParser(); # Script arguments object.

session = requests.Session(); # Used to make authenticated GitHub web requests.


# Initialize script arguments object.
def init_args(argparser):
    
    argparser.add_argument('-s', '--sources', help="list of GitHub repo HTML URLs, or text file containing the same", type=str);
    argparser.add_argument('--host', help="GitHub host HTML URL", type=str);
    argparser.add_argument('-p', '--password', help="prompt for GitHub username and password", action='store_true');
    argparser.add_argument('-t', '--token', help="prompt for GitHub access token", action='store_true');
    #argparser.add_argument('--oauth', help="prompt for GitHub OAuth credentials", action='store_true');
    argparser.add_argument('-u', '--username', help="process public repos associated with provided GitHub user", type=str);
    argparser.add_argument('-q', '--query', help="process only repos whose GitHub HTML URL contains each keyword in provided query", type=str);
    argparser.add_argument('-r', '--retrieve', help="clone repos to local environment", action='store_true');
    argparser.add_argument('-b', '--bare', help="opt for bare repos when cloning", action='store_true');
    argparser.add_argument('-d', '--directory', help="local root directory for cloned repos", type=str);
    argparser.add_argument('-a', '--anonymize', help="anonymize the repo-identifying names in directory structure containing local clones", action='store_true');
    argparser.add_argument('--since', help="process only repos created after provided timestamp", type=str);
    argparser.add_argument('--until', help="process only repos created before provided timestamp", type=str);
    argparser.add_argument('-o', '--output', help="write list of GitHub repo HTML URLs or clone-paths to specified file", type=str);
    
    return argparser.parse_args();


# Determine whether or not user supplied GitHub authentication credentials.
def auth_provided():

    if (args.password):
        return True;
    elif (args.token):
        return True;
    #elif (args.oauth):
        # return True;

    return False;


# Construct GitHub host API URL from corresponding host HTML URL.
def construct_githubhost_api_url(githubhost_html_url):
    
    (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(githubhost_html_url);

    if (netloc == 'github.com'): # GitHub.com...
        netloc = 'api.' + netloc;
    else: # GitHub Enterprise...
        path = 'api/v3';
    
    githubhost_api_url = urlparse.urlunparse((scheme, netloc, path, params, query, fragment));
    
    return githubhost_api_url;


# Attempt to authenticate global HTTP Session object using user-provided GitHub authentication credentials.
# (Authenticated Session object will be used to make any GitHub API requests utilized throughout remainder of code.)
def authenticate(url):

    global session;

    while (True):
        
        if (args.password): # Basic authentication (username and password)
            username = raw_input("Username for \'" + args.host + "\': ");
            password = getpass.getpass("Password for \'" + args.host + "\': ");
            auth_type = 'username/password';
            request = requests.get(url, auth=(username, password));
        elif (args.token): #if (args.token): # Personal access token
            access_token = getpass.getpass("Access token for \'" + args.host + "\': ");
            auth_type = 'access token';
            request = requests.get(url, headers={'Authorization': 'token %s' % access_token});
        #elif (args.oauth): # OAuth
            # ... (code to support OAuth)
            #auth_type = 'OAuth';
            #request = requests.get(url, ...);
        
        try:
            request.raise_for_status(); # (If this clears, request did not raise status code 4xx or 5xx.)
            if (args.password):
                session.auth = (username, password);
                username = ''; # (Clear variable.)
                password = ''; # (Clear variable.)
            elif (args.token): #if (args.token):
                session.headers.update({'Authorization': 'token %s' % access_token});
                access_token = ''; # (Clear variable.)
            #elif (args.oauth):
                #session...;
                # ... (clear any OAuth variables)
            print("Authentication successful.");
            return True;
        except:
            print("Invalid " + auth_type + ".");
            print("Authentication failed!");
            again = raw_input("Try again? [y/N] ");
            if (again != 'y'):
                return False;


# Determine whether or not URI is a URL.
def is_url(uri):
    
    try:
        requests.get(uri);
        return True;
    except:
        return False;


# Determine whether or not URL refers to remote GitHub repository.
def is_repo_url(url):

    config = '-c color.ui=\'false\'';
    
    cmd_str = 'git %s ls-remote %s' % (config,url);
    #print(cmd_str);

    sp = subprocess.Popen(cmd_str,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          shell=True);
    
    sp.communicate();
    
    if (sp.returncode == 0):
        return True;
    else:
        return False;


# Get list of repo HTML URLs.
def get_repo_html_url_sources(sources_str):

    sources = list();

    if (sources_str): # String of semicolon-delimited list of sources...
        raw_sources = shared.get_unique_items_from_str(sources_str, ';'); # Get list of source strings.
        num_raw_sources = len(raw_sources);
        for i in range(0, num_raw_sources):
            source_str = raw_sources[i]; # Get source i...
            if (os.path.isfile(source_str)): # If source i is a file...
                file_contents_str = shared.get_filecontents_str(source_str);
                sources_from_file = get_repo_html_url_sources(file_contents_str);
                sources = sources + sources_from_file;
            else:
                if (is_url(source_str)):
                    if (is_repo_url(source_str)):
                        sources.append(source_str);
                    else:
                        print(shared.get_warning_str("\'" + source_str + "\' does not refer to a git repository"));
                else:
                    print(shared.get_warning_str("Malformed URI \'" + source_str + "\'"));

    return sources;


# Check script arguments.
def check_args(args):
    
    print("Checking script arguments...");
    
    # Require user to specify either --host or --sources.
    if (    not args.host
            and not args.sources    ):
        sys.exit("Must provide either a GitHub host HTML URL or repo HTML URL(s).");
    
    # GitHub hostname (assumes is a valid one).
    if (args.host):
        host = args.host;
        if (is_url(host)):
            if (auth_provided()):
                github_api_url = construct_githubhost_api_url(host);
                if (not authenticate(github_api_url)):
                    sys.exit("Authentication is required.");
            else:
                sys.exit("Must specify authentication prompt.");
        else:
            sys.exit("\'" + host + "\' is a bad URL");
    
    # Repo source URIs.
    args.sources = get_repo_html_url_sources(args.sources);
    
    # Working directory.
    args.directory = shared.get_wd(args.directory);
    if (not args.directory):
        sys.exit("Not proceeding.");
    
    # 'Since' timestamp string.
    since_timestamp_str = shared.parse_timestamp_str(args.since, 'since');
    args.since = since_timestamp_str if since_timestamp_str else shared.get_utcunixepoch_timestamp_str();
    
    # 'Until' timestamp string.
    until_timestamp_str = shared.parse_timestamp_str(args.until, 'until');
    args.until = until_timestamp_str if until_timestamp_str else shared.get_utcnow_timestamp_str();

    file_datetimenow_str = datetime.datetime.now().strftime('%Y%m%d-%H%M%S%f')[:-3]; # For default output filenames.

    # Output file.
    if (args.output):
        if (not shared.is_writable_file(args.output)):
            sys.exit("Not proceeding.");
    else:
        if (args.retrieve):
            args.output = './'+shared.TOOLSET_NAME+'-'+script_name+'_paths_' + file_datetimenow_str + '.txt';

    return args;
    

# Get username of currently-authenticated GtHub user.
def get_authenticated_user():

    githubhost_api_url = construct_githubhost_api_url(args.host);
    githubuser_api_url = githubhost_api_url + '/user';

    response = session.get(githubuser_api_url);

    user = json.loads(response.content);

    username = user['login'];
    
    return username;


# Write script argument configurations to stdout.
def echo_args(args):
   
    query = args.query if args.query else '';

    if (args.host):
        if (args.username):
            whose_repos = args.username;
        else:
            whose_repos = get_authenticated_user();
        print("GitHub username: " + whose_repos);
        print("Query: \'" + query + "\'");
        print("Since: " + args.since);
        print("Until: " + args.until);
    else:
        print("Query: \'" + query + "\'");


# Construct GitHub API user-repos URL from corresponding GitHub host API URL.
def construct_userrepos_api_url(githubhost_api_url):

    (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(githubhost_api_url);
    
    if (args.username):
        path = path + '/users/' + args.username + '/repos';
    else:
        path = path + '/user/repos';
    
    userrepos_api_url = urlparse.urlunparse((scheme, netloc, path, params, query, fragment));
    
    return userrepos_api_url;


# Obtain a list of user-repos SSH URLs.
def get_repo_html_urls():
    
    githubhost_api_url = construct_githubhost_api_url(args.host);
    userrepos_api_url = construct_userrepos_api_url(githubhost_api_url);
    
    since_unix_timestamp = shared.utc_timestamp_str_to_unix_timestamp(args.since);
    until_unix_timestamp = shared.utc_timestamp_str_to_unix_timestamp(args.until);

    repo_html_urls = list();
    
    MAX_RECORDS_PER_PAGE = 100;
    page_num = 1;
    response = session.get(userrepos_api_url,
                           params={'per_page': MAX_RECORDS_PER_PAGE,
                                   'page'    : page_num});

    repos_info = json.loads(response.content);
    if ('message' in repos_info): # Meaning response does not caintain repos info...
        return repo_html_urls;
    else: # Repos info was found...
        while (True):
            for repo in repos_info:
                createdat_unix_timestamp = shared.utc_timestamp_str_to_unix_timestamp(repo['created_at']);
                if (    createdat_unix_timestamp >= since_unix_timestamp
                        and createdat_unix_timestamp <= until_unix_timestamp   ): # If repo created-at date adheres to timestamp constraints...
                    repo_html_urls.append(repo['html_url']);
            page_num = page_num + 1;
            response = session.get(userrepos_api_url,
                                   params={'per_page': MAX_RECORDS_PER_PAGE,
                                           'page' : page_num});
            if (len(response.content) > len('[]')): # If page contains repos info...
                repos_info = json.loads(response.content);
            else: # No (more) repos info...
                return repo_html_urls; 


# Construct git repo SSH URL from corresponding repo HTML URL.
def construct_repo_ssh_url(repo_html_url):
    
    (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(repo_html_url);
    
    scheme = 'ssh';
    netloc = 'git@' + netloc;
    path = path + '.git';
    
    repo_ssh_url = urlparse.urlunparse((scheme, netloc, path, params, query, fragment));
    
    return repo_ssh_url;


# Determine whether or not repo is bare.
def is_bare_repo(repo_local_path):
    
    config = '-c color.ui=\'false\'';
    gd = '--git-dir=\'' + repo_local_path + '/.git/\'';
    ibr = '--is-bare-repository';

    cmd_str = 'git %s %s rev-parse %s' % (config,gd,ibr);
    #print(cmd_str); # (Useful for debugging when un-commented.)

    sp = subprocess.Popen(cmd_str,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          shell=True);
    
    (gitrevparse_str, _) = sp.communicate();
    
    bool_val = gitrevparse_str.strip();
    if (bool_val == 'true'):
        return True;
    else:
        return False;


# Download ("clone") repository to local working directory
# OR, if already exists, fetch latest changes.
def update_local_repo(repo_html_url):
    
    repo_remote_hostname, repo_owner, repo_name = shared.get_repo_id(repo_html_url);

    if (args.anonymize): # Anonymize repo id attributes...
        repo_remote_hostname = shared.get_anonymized_str(repo_remote_hostname);
        repo_owner           = shared.get_anonymized_str(repo_owner);
        repo_name            = shared.get_anonymized_str(repo_name);
    
    repo_local_path    = shared.add_path_to_uri(repo_remote_hostname, repo_owner);
    repo_local_path    = shared.add_path_to_uri(repo_local_path, repo_name);
    repo_local_path    = shared.add_path_to_uri(args.directory, repo_local_path); # Repo destination path will be of form "<local_path>/repo_remote_hostname/repo_owner/repo_name".
    repo_local_path = os.path.abspath(repo_local_path);

    clone_repo = False;
    if (not os.path.exists(repo_local_path)): # Local path to repo does not exist...
        os.makedirs(repo_local_path);
        clone_repo = True;
    elif (not shared.is_repo_root(repo_local_path)): # Local path exists but is not a repo directory...
        print(shared.get_warning_str("Destination path \'" + repo_local_path + "\' already exists and is not an empty directory"));
        return;
    
    url = construct_repo_ssh_url(repo_html_url);
    
    if (clone_repo): # Actions to perform when cloning repo...
        if (args.bare): # Clone bare repo...
            b = '--bare';
            p = '\'' + repo_local_path + '/.git/\'';
            cmd_str = 'git clone %s %s %s' % (b,url,p);
            #print(cmd_str); # (Useful for debugging when un-commented.)
            sp = subprocess.Popen(cmd_str,
                                  stdout=subprocess.PIPE,
                                  #stderr=subprocess.STDOUT, # (Useful for debugging when un-commented.)
                                  shell=True);
            sp.wait();
        else: # Clone non-bare repo...
            p = '\'' + repo_local_path + '\'';
            cmd_str = 'git clone %s %s' % (url,p);
            #print(cmd_str); # (Useful for debugging when un-commented.)
            sp = subprocess.Popen(cmd_str,
                                  stdout=subprocess.PIPE,
                                  #stderr=subprocess.STDOUT, # (Useful for debugging when un-commented.)
                                  shell=True);
            sp.wait();
    else: # Actions to perform when updating existing repo...
        gd = '--git-dir=\'' + repo_local_path + '/.git/\'';
        if (is_bare_repo(repo_local_path)): # Update existing bare repo...
            sys.stdout.write("\r");
            sys.stdout.write("Updating bare repo...");
            sys.stdout.flush();
            q = '-q origin';
            cmd_str = 'git %s fetch %s master:master' % (gd,q);
            #print(cmd_str); # (Useful for debugging when un-commented.)
            sp = subprocess.Popen(cmd_str,
                                  stdout=subprocess.PIPE,
                                  #stderr=subprocess.STDOUT, # (Useful for debugging when un-commented.)
                                  shell=True);
            sp.wait();
            sys.stdout.write("\r");
            sys.stdout.write("Updating bare repo... done.");
            print('');
        else: # Update existing non-bare repo...
            sys.stdout.write("\r");
            sys.stdout.write("Updating repo...");
            sys.stdout.flush();
            wt = '--work-tree=\'' + repo_local_path + '\'';
            h = '--hard HEAD';
            x = '-xffd';
            cmd_str = 'git %s %s reset %s' % (gd,wt,h);
            #print(cmd_str); # (Useful for debugging when un-commented.)
            sp = subprocess.Popen(cmd_str,
                                  stdout=subprocess.PIPE,
                                  #stderr=subprocess.STDOUT, # (Useful for debugging when un-commented.)
                                  shell=True);
            sp.wait();
            cmd_str = 'git %s %s clean %s' % (gd,wt,x);
            #print(cmd_str); # (Useful for debugging when un-commented.)
            sp = subprocess.Popen(cmd_str,
                                  stdout=subprocess.PIPE,
                                  #stderr=subprocess.STDOUT, # (Useful for debugging when un-commented.)
                                  shell=True);
            sp.wait();
            cmd_str = 'git %s %s pull' % (gd,wt);
            #print(cmd_str); # (Useful for debugging when un-commented.)
            sp = subprocess.Popen(cmd_str,
                                  stdout=subprocess.PIPE,
                                  #stderr=subprocess.STDOUT, # (Useful for debugging when un-commented.)
                                  shell=True);
            sp.wait();
            sys.stdout.write("\r");
            sys.stdout.write("Updating repo... done.");
            print('');
    
    print("Repo is at latest version.");
    
    return repo_local_path;


# Output list of filtered strings (i.e., only those containing each query string keyword). 
# (Case-insensitive.)
def filter_strs_by_keywords(strings, query_str):
    
    keywords = query_str.split(); # Split query str by space chars.

    filtered_strings = list();
    for string in strings:

        include_string = all(keyword.lower() in string.lower() for keyword in keywords); # Rvalue equates to True if all keywords occur in string; else False.
        if (include_string):
            filtered_strings.append(string);
        
    return filtered_strings;


# Write list of repo HTML URLs or cloned-repo local paths to file.
def write_items_to_file(items):

    outfile = open(args.output, 'w');
    outfile.write(';\n'.join(items));
    outfile.write(';');
    outfile.close();


# Driver.
def main():

    global args;
    global session;

    # Process script configurations ("arguments").
    args = init_args(args);
    args = check_args(args);
    print('');
    echo_args(args);
    print('');

    repo_html_urls = list();
    if (args.host):
        repo_html_urls = get_repo_html_urls();

    repo_html_urls = repo_html_urls + args.sources;
    
    if (args.query):
        repo_html_urls = filter_strs_by_keywords(repo_html_urls, args.query); # Return list of repos URLs that contain query keywords.
    
    t1 = datetime.datetime.now();
    if (repo_html_urls):
        num_repos = len(repo_html_urls);
        print("Found " + str(num_repos) + " repositories.");
        print('');
        if (args.retrieve):
            repo_local_paths = list();
            for i in range(0, num_repos):
                repo_html_url = repo_html_urls[i];
                print("Processing repository " + str(i+1) + " of " + str(num_repos) + "...");
                print("HTML URL: " + repo_html_url);
                repo_local_path = update_local_repo(repo_html_url);
                repo_local_paths.append(repo_local_path);
                print('');
            if (args.output):
                write_items_to_file(repo_local_paths);
                print("Cloned-repo local paths written to \'" + args.output + "\'.");
                print('');
        else: # Just write repo HTML URLS to stdout...
            print("Repo HTML URLs:");
            for i in range(0, num_repos):
                repo_html_url = repo_html_urls[i];
                print(repo_html_url);
            print('');
            if (args.output):
                write_items_to_file(repo_html_urls);
                print("Repo HTML URLs written to \'" + args.output + "\'.");
                print('');
    else:
        num_repos = len(repo_html_urls);
        print("Found " + str(num_repos) + " repositories.");
        print('');
        if (args.retrieve):
            print("No files written.");
            print('');
        else:
            print("Repo HTML URLs:");
            print("(none)")
            print('');
            if (args.output):
                print("No files written.");
                print('');

    del session; # (Because may contain sensitive data.)

    t2 = datetime.datetime.now();
    t = t2 - t1;
    print("Execution complete: done in " + str(t));
    
    return;


main();

