## Data Store Attributes

The output of gitRHIG-scraper includes a database table of commit records. The table below describes the attributes that appears in each project commit record.

| column                     | type    | description |
|----------------------------|---------|-------------|
| `repo_remote_hostname`     | string  | Identifier for GitHub hostname |
| `repo_owner`               | string  | Identifier for repository owner |
| `repo_name`                | string  | Identifier for repository name |
| `path_in_repo`             | string  | Identifier for path that was processed in repository |
| `labels`                   | list*   | User-defined labels for commit record |
| `commit_hash`              | string  | SHA-1 hash string used to identify commit |
| `author_name`              | string  | Identifier for commit author |
| `author_email`             | string  | Identifier for email address of commit author |
| `author_unix_timestamp`    | float   | UNIX timestamp when commit was written |
| `committer_name`           | string  | Identifier for committer |
| `committer_email`          | string  | Identifier for email address of committer |
| `committer_unix_timestamp` | float   | UNIX timestamp when commit was applied |
| `subject`                  | string  | Identifier for commit message |
| `len_subject`              | integer | Number of characters in commit message |
| `num_files_changed`        | integer | Number of repository files affected by commit |
| `num_lines_changed`        | integer | Number of repository file lines affected by commit |
| `num_lines_inserted`       | integer | Number of repository file lines inserted by commit |
| `num_lines_deleted`        | integer | Number of repository file lines deleted by commit |
| `num_lines_modified`       | integer | Number of repository file lines modified by commit |

\* For SQLite data stores, lists objects are stored as 'stringified' tuples.