#!/usr/bin/env python3

import click
import logging
from oaklib import get_adapter
from oaklib.datamodels.search import SearchProperty, SearchConfiguration
import pandas as pd
import numpy as np
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
    # This _CAN NOT_ be done automatically. See https://incatools.github.io/ontology-access-kit/faq/troubleshooting.html#my-cached-sqlite-ontology-is-out-of-date
    adapter = get_adapter(f"sqlite:obo:{ontology_id}")
    
    for ont in adapter.ontologies():
        ontology_metadata = adapter.ontology_metadata_map(ont)
        logger.info(f"Ontology metadata: {ontology_metadata['id']}, {ontology_metadata['owl:versionIRI']}")
    
    return adapter


def search_ontology(ontology_id, adapter, df, config):
    """
    Search for exact matches to the ontology term label.
    :param adapter: The connector to the ontology database.
    :param df: Dataframe containing terms to search and find matches to the ontology.
    """
    exact_search_results = []
    
    for index, row in df.iterrows():
        # TODO: Parameterize search column
        for result in adapter.basic_search(row.iloc[2], config=config):
            logger.debug(f'{row.iloc[2]} --- {result}')
            exact_search_results.append([row.iloc[2], result, adapter.label(result)])

    search_results_df = pd.DataFrame(exact_search_results)
    
    # Add column headers
    search_results_df.columns = ['source_column_value', f'{ontology_id}_result_curie', f'{ontology_id}_result_label']
    
    # Add column to indicate type of search match
    search_results_df['type_of_result_match'] = np.where(
        search_results_df[f'{ontology_id}_result_curie'].notnull(), f'{ontology_id}_result_label', '')
    
    print(search_results_df.head())

    return search_results_df


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
    # TODO: parameterize Sheet name variable?
    data_df = pd.read_excel(xls, 'Sheet1') #condition_codes_v5
    logger.info(data_df.nunique())

    # Search for matching ontology terms
    exact_label_search_config = SearchConfiguration(
        properties=[SearchProperty.LABEL],
        force_case_insensitive=True,
    )

    exact_label_results_df = search_ontology(ontology_id, adapter, data_df, exact_label_search_config)
    
    # Join exact_label_results_df back to original input data
    overall_results_df = pd.merge(data_df, exact_label_results_df, how='left', on='source_column_value')

    # Copy search result values into their existing column, e.g. mondo_result_label --> mondoLabel
    if ontology_id == str('MONDO').lower():
        # Update values in the existing columns
        overall_results_df['mondoLabel'] = overall_results_df['mondo_result_label']
        overall_results_df['mondoCode'] = overall_results_df['mondo_result_curie']

        # Drop the search_results columns
        overall_results_df.drop(['mondo_result_label'], axis=1, inplace=True)
        overall_results_df.drop(['mondo_result_curie'], axis=1, inplace=True)

    
    # Save to file
    overall_results_df.to_excel('mondo_exact_label_results.xlsx')

    exit()

    exact_label_synonym_search_config = SearchConfiguration(
        properties=[SearchProperty.ALIAS],
        force_case_insensitive=True,
    )

    exact_label_synonym_results_df = search_ontology(adapter, data_df, exact_label_synonym_search_config)

    exact_label_synonym_results_df.to_excel('mondo_exact_label_synonym_results.xlsx')


@main.command("hello")
def hello():
    try:
        result = 1 / 0
    except Exception as e:
        logger.error("An error occurred: %s", str(e), exc_info=True)


if __name__ == "__main__":
    main()