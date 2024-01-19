#!/usr/bin/env python3

import click
import uuid
import logging
from oaklib import get_adapter
from oaklib.datamodels.search import SearchProperty, SearchConfiguration
from oaklib.implementations.sqldb.sql_implementation import SqlImplementation
import pandas as pd
import numpy as np
from pathlib import Path
from tqdm import tqdm

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


def fetch_ontology(ontology_id: str) -> SqlImplementation:
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


def search_ontology(ontology_id: str, adapter: SqlImplementation, df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Search for exact matches to the ontology term label.
    :param adapter: The connector to the ontology database.
    :param df: Dataframe containing terms to search and find matches to the ontology.
    """
    exact_search_results = []

    # Create a tqdm instance
    progress_bar = tqdm(total=len(df), desc="Processing Rows", unit="row")
    
    for index, row in df.iterrows():
        # TODO: Parameterize search column
        # TODO: Fix bug when multiple synonym results!
        for result in adapter.basic_search(row.iloc[2], config=config):
            logger.debug(f'{row["UUID"]} -- {row.iloc[2]} ---> {result}')
            exact_search_results.append([row["UUID"], result, adapter.label(result)])
            # Update the progress bar
            progress_bar.update(1)

    # Close the progress bar
    progress_bar.close()

    # Convert search results to dataframe
    search_results_df = pd.DataFrame(exact_search_results)
    
    # Add column headers
    search_results_df.columns = ['UUID', f'{ontology_id}_result_curie', f'{ontology_id}_result_label']

    # Filter rows to keep those where '{ontology}_result_curie' starts with 'MONDO'
    search_results_df = search_results_df[search_results_df[f'{ontology_id}_result_curie'].str.startswith(f'{ontology_id}'.upper())]

    # Add column to indicate type of search match
    if str(config.properties[0]) == 'LABEL':
        search_results_df['type_of_result_match'] = np.where(
            search_results_df[f'{ontology_id}_result_curie'].notnull(), f'{ontology_id.upper()}_EXACT_LABEL', '')
    
    if str(config.properties[0]) == 'ALIAS':
        search_results_df['type_of_result_match'] = np.where(
            search_results_df[f'{ontology_id}_result_curie'].notnull(), f'{ontology_id.upper()}_EXACT_ALIAS', '')

    return search_results_df


def generate_uuid() -> str:
    """Function to generate UUID"""
    return str(uuid.uuid4())


def _clean_up_columns(df: pd.DataFrame, ontology_id: str) -> pd.DataFrame:
    """
    Copy over the search results to the columns from the input dataframe
    amd remove the extra columns added with the search results.
    :param df: The dataframe from the merge of the search results with the original dataframe.
    :param ontology_id: The ontology identifier, ie. the ontology being searched  
    """
    # Handle clean-up after a second round of synonym search
    if ontology_id == str('MONDO').lower():
        if 'type_of_result_match_x' in df.columns and 'type_of_result_match_y' in df.columns:
            df['mondoLabel'] = np.where(df['mondo_result_label'].notnull(), df['mondo_result_label'], df['mondoLabel'])
            df.drop(['mondo_result_label'], axis=1, inplace=True)

            df['mondoCode'] = np.where(df['mondo_result_curie'].notnull(), df['mondo_result_curie'], df['mondoCode'])
            df.drop(['mondo_result_curie'], axis=1, inplace=True)

            df['type_of_result_match_x'] = np.where(df['type_of_result_match_y'].notnull(), df['type_of_result_match_y'], df['type_of_result_match_x'])
            df.drop(['type_of_result_match_y'], axis=1, inplace=True)
            df = df.rename(columns={'type_of_result_match_x': 'type_of_result_match'})
        else:
            # Update values in the existing columns
            df['mondoLabel'] = df['mondo_result_label']
            df['mondoCode'] = df['mondo_result_curie']
        
            # Drop the search_results columns
            df.drop(['mondo_result_label'], axis=1, inplace=True)
            df.drop(['mondo_result_curie'], axis=1, inplace=True)


    return df


@main.command("search")
@click.argument('ontology_id')
@click.argument('data_filename')
def search(ontology_id: str, data_filename: str):
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
    
    # Add a new column 'UUID' with UUID values
    data_df['UUID'] = data_df.apply(lambda row: generate_uuid(), axis=1)
    logger.info(data_df.nunique())

    # Search for matching ontology terms to LABEL
    exact_label_search_config = SearchConfiguration(
        properties=[SearchProperty.LABEL],
        force_case_insensitive=True,
    )
    exact_label_results_df = search_ontology(ontology_id, adapter, data_df, exact_label_search_config)
    
    # Join exact_label_results_df back to original input data
    overall_exact_label_results_df = pd.merge(data_df, exact_label_results_df, how='left', on='UUID')

    # Clean up dataframe to remove original search columns
    overall_exact_label_results_df = _clean_up_columns(overall_exact_label_results_df, ontology_id)

    # Filter out rows that have results to prepare for synonym search
    filtered_df = overall_exact_label_results_df[overall_exact_label_results_df['type_of_result_match'].isnull()]


    # Search for matching terms to SYNONYM
    exact_label_synonym_search_config = SearchConfiguration(
        properties=[SearchProperty.ALIAS],
        force_case_insensitive=True,
    )
    overall_exact_synonym_results_df = search_ontology(ontology_id, adapter, filtered_df, exact_label_synonym_search_config)

    # Join overall_exact_synonym_results_df back to overall_results_df
    overall_final_results_df = pd.merge(overall_exact_label_results_df, overall_exact_synonym_results_df, how='left', on='UUID')

    # Clean up dataframe to remove original search columns
    overall_final_results_df = _clean_up_columns(overall_final_results_df, ontology_id)

    # Save to file
    overall_final_results_df.to_excel('mondo_exact_label_and_synonym_results.xlsx', index=False)


@main.command("hello")
def hello():
    try:
        result = 1 / 0
    except Exception as e:
        logger.error("An error occurred: %s", str(e), exc_info=True)


if __name__ == "__main__":
    main()