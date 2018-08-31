# gitRHIG Toolset

gitRHIG \(for **git** **R**epository **H**istory **I**nformation **G**rabber\) is a toolset that works with the [git](https://git-scm.com/) version control platform, and which can be used with [GitHub](https://github.com/) software repositories hosting source code and text-based files. The gitRHIG toolset consists of Python scripts designed to assist with tasks that involve the mining of git (or GitHub) repository commit activity. Currently, gitRHIG includes scripts that support batch-retrieving multiple GitHub repositories via a single command, and exporting repository (or 'project') development metrics to a data store for subsequent recall and processing. Additionally, for data stores containing the development information associated with a collection of repositories, this toolset also includes a script that enables cumulative analyses based on a corpus of commit records.



## collector.py

Batch-retrieve a set of user-provided GitHub repositories, or list the public repositories associated with a specific GitHub user account.

| argument           | type   | description |
|--------------------|--------|-------------|
| \-s, \-\-sources   | string | Semicolon\-delimited list of GitHub repository HTML URLs, or path to a local text file containing the same.<br>_Example:_ `-s "repo_url1; repo_url2; repo_url3"`<br>_Example:_ `-s "input.txt"` |
| \-\-host           | string | GitHub host HTML URL.<br>_Example:_ `--host "https://github.com"` |
| \-p, \-\-password  | flag   | Prompt for GitHub username and password. (This is an independent form of GitHub authentication.) |
| \-t, \-\-token     | flag   | Prompt for GitHub access token. (This is an independent form of GitHub authentication.) |
| \-u, \-\-username  | string | Process public repositories associated with the provided GitHub user account.<br>_Example:_ `-u "torvalds"` |
| \-q, \-\-query     | string | Process only repositories whose GitHub HTML URL contains each keyword in provided query.<br>_Example:_ `-q "some query"` |
| \-r, \-\-retrieve  | flag   | Download \(or "clone"\) repositories to local environment. |
| \-b, \-\-bare      | flag   | Opt for bare repositories when cloning. (A bare repository is one which does not contain a working directory.) |
| \-d, \-\-directory | string | Local root directory for cloned repositories.<br>_Example:_ `-d "path/to/some/dir"` |
| \-a, \-\-anonymize | flag   | Anonymize the repository-identifying names in directory structure (relative to `.`, or, if provided, `-d`) containing local clones. |
| \-\-since          | string | Process only repositories created after provided timestamp.<br>_Example:_ `--since "2017-06-17"` |
| \-\-until          | string | Process only repositories created before provided timestamp.<br>_Example:_ `--until "2018-03-26"` |
| \-o, \-\-output    | string | Write semicolon-delimited list of GitHub repository HTML URLs or clone-paths (depending) to specified file.<br>_Example:_ `-o "urls_or_local_paths.txt"` |

Notes:
- Independent forms of GitHub authentication are mutually exclusive.



## scraper.py

Parse and export the development metrics associated with a set of git repository logs as a collection of project [commit records](docs/data_store_attributes.md).

| argument           | type   | description |
|--------------------|--------|-------------|
| \-s, \-\-sources   | string | Semicolon\-delimited list of local paths to git repositories, or path to a local text file containing the same.<br>_Example:_ `-s "local_repo1; local_repo2; local_repo3"`<br>_Example:_ `-s "local_repo_paths.txt"` |
| \-a, \-\-anonymize | flag   | Enforce anonymization on personally identifiable information (PII) in resultant project commit records. |
| \-\-paths          | string | Semicolon-delimited list of paths to process in each repository, or path to a local text file containing the same. (A path can be either a file or a directory.) <br>_Example:_ `--paths "path1; path2; path3"` |
| \-\-labels         | string | Semicolon-delimited list of labels to apply on resultant commit records, or path to a local text file containing the same. (Labels can be employed to give context to a set of commit records.)<br>_Example:_ `--labels "label1; label2; label3"` |
| \-\-since          | string | Process only commits applied after provided timestamp.<br>_Example:_ `--since "2017-06-17"` |
| \-\-until          | string | Process only commits applied before provided timestamp.<br>_Example:_ `--until "2018-03-26"` |
| \-o, \-\-output    | string | Destination data store source ([SQLite](https://www.sqlite.org/index.html) or [MongoDB](https://www.mongodb.com/)) for resultant commit records.<br>_Example:_ `-o "data_store.db"`<br>_Example:_ `-o "mongodb://localhost:27017/"` |

Notes:
- Paths, labels, and since- and until-timestamps may be specified individually for each repository local source using [URL query string](https://en.wikipedia.org/wiki/Query_string)-like syntax.
  <br>_Example:_ `-s "local_repo1?path=path1; local_repo2?since="2017-06-17"&until="2018-03-26"; local_repo3?path=path2&label=label1&label=label2"`
- Data store sources may indicate the database (MongoDB only) or collection name to use for commit records using URL query string-like syntax.
  <br>_Example:_ `-o "data_store.db?collection=commits"`
  <br>_Example:_ `-o "mongodb://localhost:27017/?database=data_store&collection=commits"`



## analyzer.py

Generate cumulative statistics for a set of repositories (or projects) based on user-provided [features](https://en.wikipedia.org/wiki/Feature_(machine_learning)).

Statistics are presented through quantitative analytics \(project feature vector records and [frequency distribution data](docs/frequency_distribution_attributes.md), both in spreadsheet format\) and data visualizations \(distribution graphs in HTML format\).

Available project features (and corresponding labels used to reference them in script arguments):
- Total Number of Commits (`total_num_commits`)
- Total Number of Lines Changed (`total_num_lines_changed`)
- Total Number of Lines Inserted (`total_num_lines_inserted`)
- Total Number of Lines Deleted (`total_num_lines_deleted`)
- Total Number of Lines Modified (`total_num_lines_modified`)
- Total Number of Years Active (`total_num_years_active`)
- Total Number of Months Active (`total_num_months_active`)
- Total Number of Days Active (`total_num_days_active`)
- Total Number of Hours Active (`total_num_hours_active`)
- Total Number of Minutes Active (`total_num_minutes_active`)
- Total Number of Seconds Active (`total_num_seconds_active`)

| argument                | type   | description |
|-------------------------|--------|-------------|
| \-\-show-features       | flag   | Show available project features and exit. |
| \-f, \-\-features       | string | Semicolon\-delimited list of features (via labels) to activate in output analytics. (Default is all if not provided.)<br>_Example:_ `-f "feat1; feat2; feat3"` |
| \-s, \-\-source         | string | Source data store (SQLite or MongoDB) of commit records to be processed.<br>_Example:_ `-s "data_store.db"` |
| \-\-paths\-as\-projects | flag   | Treat each repository path as an individual project. |
| \-\-width-class         | string | Semicolon\-delimited list of (colon-delimited) key-value pairs of configurations for feature observations class _width_, or path to a local text file containing the same.<br>_Example:_ `--width-class "feat1:3; feat2:5; feat3:10"` |
| \-\-num\-classes        | string | Semicolon\-delimited list of (colon-delimited) key-value pairs of configurations for feature observations class _count_, or path to a local text file containing the same.<br>_Example:_ `--num-classes "feat1:3; feat2:2; feat3:3"` |
| \-\-labels              | string | Semicolon-delimited list of labels to consider when processing commit records, or path to a local text file containing the same.<br>_Example:_ `--labels "label1; label2; label3"` |
| \-\-since               | string | Consider only commits applied after provided timestamp.<br>_Example:_ `--since "2017-06-17"` |
| \-\-until               | string | Consider only commits applied before provided timestamp.<br>_Example:_ `--until "2018-03-26"` |
| \-\-spreadsheet         | string | Output (spreadsheet) file for tabulated quantitative analytics.<br>_Example:_ `--spreadsheet "quantitative_analytics.xlsx"` |
| \-\-html                | string | Output (HTML) file for data visualizations.<br>_Example:_ `--html "data_visualizations.html"` |

Notes:
- Data store sources may indicate the database (MongoDB only) or collection names that house commit records using URL query string-like syntax (examples above).


# Dependencies

## Python Modules:
- argparse
- ast
- [bokeh](https://pypi.python.org/pypi/bokeh)\*
- chardet
- collections
- datetime
- [dateutil](https://pypi.python.org/pypi/python-dateutil/)\*
- getpass
- hashlib
- io
- json
- math
- [numpy](https://pypi.python.org/pypi/numpy)\*
- os
- [pandas](https://pypi.python.org/pypi/pandas)\*
- [pymongo](https://pypi.org/project/pymongo/)\*
- re
- [requests](https://pypi.python.org/pypi/requests)\*
- subprocess
- sys
- textwrap
- time
- unicodedata
- urlparse
- [xlrd](https://pypi.python.org/pypi/xlrd)\*
- [xlsxwriter](https://pypi.python.org/pypi/XlsxWriter/)\*

\* May require install

## Environment Setup:
- [Create a GitHub user account](https://github.com/join)
- [Configure a GitHub account with Secure Shell \(SSH\)](https://help.github.com/articles/connecting-to-github-with-ssh/)
