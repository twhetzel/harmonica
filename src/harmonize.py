#!/usr/bin/env python3

import click
import logging
from oaklib import get_adapter
from oaklib.datamodels.search import SearchProperty, SearchConfiguration
import pandas as pd
from pathlib import Path

__all__ = [
    "main",
]

# Configure logger
logger = logging.getLogger("harmonize")

logging.basicConfig(
    level=logging.DEBUG,  # Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format="%(asctime)s.%(msecs)03d [%(levelname)s] (%(module)s) (%(name)s): %(message)s",
    datefmt='%Y-%m-%d,%H:%M:%S',
    handlers=[
        logging.FileHandler("error.log"),  # Log to a file named error.log
        logging.StreamHandler()  # Also log to the console
    ],
    force=True
)


@click.group()
@click.option("-v", "--verbose", count=True)
@click.option("-q", "--quiet")
# @click.version_option(__version__)
def main(verbose: int, quiet: bool):
    """
    The main click group containing with parameters for logging levels.
    :param verbose: Levels of log messages to display.
    :param quiet: Boolean to be quiet or verbose.
    """
    if verbose >= 2:
        logger.setLevel(level=logging.DEBUG)
    elif verbose == 1:
        logger.setLevel(level=logging.INFO)
    else:
        logger.setLevel(level=logging.WARNING)
    if quiet:
        logger.setLevel(level=logging.ERROR)


def fetch_ontology(ontology_id):
    """
    Download ontology of interest and convert to SQLite database.
    :param ontology_id: The OBO identifier of the ontology.
    :returns adapter: The connector to the ontology database.
    """
    logger.info('** Fetching ontology')
    # TODO: Sort out how to download new ontology version if file already at ~/.data/oaklib
    # This can not be done automatically. See https://incatools.github.io/ontology-access-kit/faq/troubleshooting.html#my-cached-sqlite-ontology-is-out-of-date
    adapter = get_adapter(f"sqlite:obo:{ontology_id}")
    
    for ont in adapter.ontologies():
        ontology_metadata = adapter.ontology_metadata_map(ont)
        logger.info(f"Ontology metadata: {ontology_metadata['id']}, {ontology_metadata['owl:versionIRI']}")
    
    return adapter


def search_ontology(adapter, df, config):
    """
    Search for exact matches to the ontology term label.
    :param adapter: The connector to the ontology database.
    :param df: Dataframe containing terms to search and find matches to the ontology.
    """
    exact_search_results = []
    
    for index, row in df.iterrows():
        for result in adapter.basic_search(row.iloc[0], config=config):
            exact_search_results.append([row.iloc[0], result, adapter.label(result)])

    search_results_df = pd.DataFrame(exact_search_results)
    logger.debug(search_results_df)


@main.command("search")
@click.argument('ontology_id')
@click.argument('data_filename')
def search(ontology_id, data_filename):
    """
    Search an ontology for matches to terms in a data file.
    :param ontology_id: The OBO identifier of the ontology.
    :param data_filename: The name of the file with terms to search for ontology matches.
    """
    # Get the ontology
    adapter = fetch_ontology(ontology_id)

    # Read in the data file
    file_path = Path(f'data/input/{data_filename}')
    xls = pd.ExcelFile(file_path)
    # TODO: parameterize sheet name?
    data_df = pd.read_excel(xls, 'Sheet1') #condition_codes_v5
    logger.info(data_df.nunique())

    # Configure the search -- KEEP!
    # config = SearchConfiguration(syntax=SearchTermSyntax.STARTS_WITH) # Example from: https://github.com/INCATools/ontology-access-kit/blob/main/notebooks/Developers-Tutorial.ipynb

    # Configure the search -- KEEP!
    # config = SearchConfiguration(
    #     # properties=[SearchProperty.ALIAS], # matches to label and synonyms
    #     properties=[SearchProperty.LABEL], #matches label only
    #     force_case_insensitive=True,
    #     # is_complete=True,
    #     # is_partial=True, # does not seem to work even with single token label, e.g. ureteroc MONDO:0008628
    #     # is_fuzzy=True, # does not seem to work for fuzzy match to labels (ureteroc MONDO:0008628) or synonyms (intertricular commcation MONDO:0002070)
    # )

    # Search for matching ontology terms
    exact_label_search_config = SearchConfiguration(
        # TODO: Find out how to use object_source to limit results to an ontology as well as 
        # object_source_match and snippet from SearchResult. 
        # See https://incatools.github.io/ontology-access-kit/datamodels/search/ and 
        # https://incatools.github.io/ontology-access-kit/datamodels/search/SearchResult.html 
        properties=[SearchProperty.LABEL],
        force_case_insensitive=True,
    )

    exact_label_synonym_search_config = SearchConfiguration(
        properties=[SearchProperty.ALIAS],
        force_case_insensitive=True,
    )

    exact_matches = search_ontology(adapter, data_df, exact_label_search_config)
    


@main.command("hello")
def hello():
    try:
        result = 1 / 0
    except Exception as e:
        logger.error("An error occurred: %s", str(e), exc_info=True)


if __name__ == "__main__":
    main()