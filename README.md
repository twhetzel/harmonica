# Harmonica
Harmonize data to ontology terms.

## Usage
### Python
`python src/harmonize.py -vv search mondo 'YOUR FILENAME'`

### Make
`make search ontology_id=mondo data_filename="YOUR FILENAME"`


## Ontology SQLite Database
Using `get_adapter(f"sqlite:obo:{ontology_id}")` the ontology database is saved at `~/.data/oaklib/`.

NOTE: This method downloads a version of an ontolgy from a AWS S3 bucket managed by BBOP. It seems only one version of an ontology is present in the S3 bucket and it is not known when this version is updated to the latest ontology version published.

TODO: Sort out how to download a new version of an ontology when an older version already exists in `~/.data/oaklib/`.
Note: This can not be done automatically. See https://incatools.github.io/ontology-access-kit/faq/troubleshooting.html#my-cached-sqlite-ontology-is-out-of-date


TODO: Include other methods to download ontology content and convert to a SQLite database using [semsql](https://github.com/INCATools/semantic-sql).


## Data File
Currently, the script assumes that the data file is an Excel file that has ~~one sheet~~ multiple sheets (TODO: paramterize Sheet name) and that the column with terms to search for matches to an ontology are in the first column.

TODO: Consider whether the input data file formatting assumptions need to be paramterized in the code to handle other varieties of files, e.g. CSV or Excel files where the search data is in another sheet or the first sheet but another column.

The input data file is expected to be stored locally at `data/input/` and the results of the ontology harmonization are stored at `data/ouput/`.