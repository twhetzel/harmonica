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

## Other files
- `compare_oak2rdflib.py` - added to check that all classes obtained used rdflib are also found in the semsql database. This was created because there was a confusion about which Mondo version was downloaded and a difference was seen between the content of the semsql database and rdflib using the latest Mondo release. It turns out the semsql database had not been updated when testing to provide the latest release of Mondo.

`rdflib_test.py` - extract classes from Mondo using rdflib


## Further Investigation

### Sort out if/how other parameters work for OAK Search
 # Configure the search -- KEEP!
    # config = SearchConfiguration(syntax=SearchTermSyntax.STARTS_WITH) # Example from: https://github.com/INCATools/ontology-access-kit/blob/main/notebooks/Developers-Tutorial.ipynb

    # Configure the search -- KEEP!
    # config = SearchConfiguration(
    # TODO: Find out how to use object_source to limit results to an ontology as well as 
    # object_source_match and snippet from SearchResult. 
    # See https://incatools.github.io/ontology-access-kit/datamodels/search/ and 
    # https://incatools.github.io/ontology-access-kit/datamodels/search/SearchResult.html 
    #     # properties=[SearchProperty.ALIAS], # matches to label and synonyms
    #     properties=[SearchProperty.LABEL], #matches label only
    #     force_case_insensitive=True,
    #     # is_complete=True,
    #     # is_partial=True, # does not seem to work even with single token label, e.g. ureteroc MONDO:0008628
    #     # is_fuzzy=True, # does not seem to work for fuzzy match to labels (ureteroc MONDO:0008628) or synonyms (intertricular commcation MONDO:0002070)
    # )
