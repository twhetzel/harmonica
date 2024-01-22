#!/usr/bin/env python3

import click
from datetime import datetime
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

    ontology_prefix = 'hpo' if ontology_id.lower() == 'hp' else ontology_id
    exact_search_results = []

    # Create a tqdm instance to display search progress
    progress_bar = tqdm(total=len(df), desc="Processing Rows", unit="row")

    for index, row in df.iterrows():
        # TODO: Parameterize search column value
        for result in adapter.basic_search(row.iloc[2], config=config):
            logger.debug(f'{row["UUID"]} -- {row.iloc[2]} ---> {result} - {adapter.label(result)}')
            exact_search_results.append([row["UUID"], result, adapter.label(result)])
            # Update the progress bar
            progress_bar.update(1)

    # Close the progress bar
    progress_bar.close()

    # Convert search results to dataframe
    results_df = pd.DataFrame(exact_search_results)

    # Add column headers
    results_df.columns = ['UUID', f'{ontology_prefix}_result_curie', f'{ontology_prefix}_result_label']

    # Filter rows to keep those where '{ontology}_result_curie' starts with the "ontology_id", keep in mind hp vs. hpo
    # TODO: Decide whether these results should still be filtered out
    results_df = results_df[results_df[f'{ontology_prefix}_result_curie'].str.startswith(f'{ontology_id}'.upper())]

    # Group by 'UUID' and aggregate curie and label into lists
    search_results_df = results_df.groupby('UUID').agg({
        f'{ontology_prefix}_result_curie': list,
        f'{ontology_prefix}_result_label': list
    }).reset_index()

    # Convert lists to strings
    search_results_df[f'{ontology_prefix}_result_curie'] = search_results_df[f'{ontology_prefix}_result_curie'].astype(str).str.strip('[]').str.replace("'", "")
    search_results_df[f'{ontology_prefix}_result_label'] = search_results_df[f'{ontology_prefix}_result_label'].astype(str).str.strip('[]').str.replace("'", "")

    # TODO: Maintain individual columns of result_match_type for each ontology searched!
    # Add column to indicate type of search match
    if str(config.properties[0]) == 'LABEL':
        search_results_df[f'{ontology_prefix}_result_match_type'] = np.where(
            search_results_df[f'{ontology_prefix}_result_curie'].notnull(), f'{ontology_prefix.upper()}_EXACT_LABEL', '')
    
    if str(config.properties[0]) == 'ALIAS':
        search_results_df[f'{ontology_prefix}_result_match_type'] = np.where(
            search_results_df[f'{ontology_prefix}_result_curie'].notnull(), f'{ontology_prefix.upper()}_EXACT_ALIAS', '')

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
    ontology_prefix = 'hpo' if ontology_id.lower() == 'hp' else ontology_id

    # Handle clean-up after a second round of synonym search
    if f'{ontology_prefix}_result_match_type_x' in df.columns and f'{ontology_prefix}_result_match_type_y' in df.columns:
        # Copy result label values to original df column and then drop result column
        df[f'{ontology_prefix}Label'] = np.where(df[f'{ontology_prefix}_result_label'].notnull(), df[f'{ontology_prefix}_result_label'], df[f'{ontology_prefix}Label'])
        df.drop([f'{ontology_prefix}_result_label'], axis=1, inplace=True)

        # Copy result curie values to original df column and then drop result column
        df[f'{ontology_prefix}Code'] = np.where(df[f'{ontology_prefix}_result_curie'].notnull(), df[f'{ontology_prefix}_result_curie'], df[f'{ontology_prefix}Code'])
        df.drop([f'{ontology_prefix}_result_curie'], axis=1, inplace=True)

        # Copy type of result match to original df column and then drop result column and rename original df column
        df[f'{ontology_prefix}_result_match_type_x'] = np.where(df[f'{ontology_prefix}_result_match_type_y'].notnull(), df[f'{ontology_prefix}_result_match_type_y'], df[f'{ontology_prefix}_result_match_type_x'])
        df.drop([f'{ontology_prefix}_result_match_type_y'], axis=1, inplace=True)
        df = df.rename(columns={f'{ontology_prefix}_result_match_type_x': f'{ontology_prefix}_result_match_type'})
    else:
        # Update values in the existing columns
        df[f'{ontology_prefix}Label'] = df[f'{ontology_prefix}_result_label']
        df[f'{ontology_prefix}Code'] = df[f'{ontology_prefix}_result_curie']
    
        # Drop the search_results columns
        df.drop([f'{ontology_prefix}_result_label'], axis=1, inplace=True)
        df.drop([f'{ontology_prefix}_result_curie'], axis=1, inplace=True)


    return df


@main.command("search")
@click.option('--oid', '-o', help='Ontology IDs separated by commas')
@click.option('--data_filename', '-d')
def search(oid: tuple, data_filename: str):
    """
    Search an ontology for matches to terms in a data file.
    :param ontology_id: The OBO identifier of the ontology.
    :param data_filename: The name of the file with terms to search for ontology matches.
    """
    oid = tuple(oid.split(',')) if oid else ()
    filename_prefix = '_'.join(oid)
    output_data_directory = './data/output/'

    # Get the current formatted timestamp
    timestamp = datetime.now()
    formatted_timestamp = timestamp.strftime("%Y%m%d-%H%M%S")


    all_final_results_dict = {}

    # Read in the data file
    file_path = Path(f'data/input/{data_filename}')
    xls = pd.ExcelFile(file_path)
    # TODO: parameterize Sheet name variable?
    data_df = pd.read_excel(xls, 'Sheet1') #condition_codes_v5
    
    # Add a new column 'UUID' with unique identifier values
    # TODO: Add the UUID column if it does not already exist
    data_df['UUID'] = data_df.apply(lambda row: generate_uuid(), axis=1)
    logger.debug(data_df.nunique())
    logger.info("Number of total rows in dataframe: %s", len(data_df))

    # Exact LABEL Search configuration
    exact_label_search_config = SearchConfiguration(
            properties=[SearchProperty.LABEL],
            force_case_insensitive=True,
        )
    
    # Exact LABEL and SYNONYM Search configuration
    exact_label_synonym_search_config = SearchConfiguration(
            properties=[SearchProperty.ALIAS],
            force_case_insensitive=True,
        )


    for ontology_id in oid:
        ontology_prefix = 'hpo' if ontology_id.lower() == 'hp' else ontology_id

        # Get the ontology
        adapter = fetch_ontology(ontology_id)

        # Search for matching ontology terms to LABEL
        exact_label_results_df = search_ontology(ontology_id, adapter, data_df, exact_label_search_config)
        # Join exact_label_results_df back to original input data
        overall_exact_label_results_df = pd.merge(data_df, exact_label_results_df, how='left', on='UUID')
        # Clean up dataframe to remove original search columns
        overall_exact_label_results_df = _clean_up_columns(overall_exact_label_results_df, ontology_id)

        # Filter out rows that have results to prepare for synonym search
        filtered_df = overall_exact_label_results_df[overall_exact_label_results_df[f'{ontology_prefix}_result_match_type'].isnull()]

        # Search for matching terms to SYNONYM
        overall_exact_synonym_results_df = search_ontology(ontology_id, adapter, filtered_df, exact_label_synonym_search_config)
        # Join overall_exact_synonym_results_df back to overall_results_df
        overall_final_results_df = pd.merge(overall_exact_label_results_df, overall_exact_synonym_results_df, how='left', on='UUID')
        # Clean up dataframe to remove original search columns
        overall_final_results_df = _clean_up_columns(overall_final_results_df, ontology_id)

        # Save ontology search results to a dict
        all_final_results_dict[ontology_id] = overall_final_results_df



    # Finally, combine all results and save to file!
    # Concatenate all DataFrames into a single DataFrame
    result_df = pd.concat(all_final_results_dict.values(), ignore_index=True)

    # Replace NaN values with empty string
    df_cleaned = result_df.fillna('')

    # Define a custom aggregation function to join non-empty values
    def custom_join(series):
        non_empty_values = [value for value in series if value != '']
        return ', '.join(non_empty_values)
    

    # Add columns dynamically to the "agg" function _if_ they exist within the dataframe
    columns_to_groupby = ['UUID', 'study', 'source_column', 'source_column_value', 'conditionMeasureSourceText']
    columns_to_agg = [col for col in df_cleaned.columns if col in [
        'hpoLabel', 'hpoCode', 'hpo_result_match_type',
        'mondoLabel', 'mondoCode', 'mondo_result_match_type', 
        'maxoLabel', 'maxoCode', 'maxo_result_match_type',
        'otherLabel', 'otherCode', 'Trish Notes']
    ]

    # Perform the groupby and aggregation
    agg_dict = {col: custom_join for col in columns_to_agg}
    combined_df = df_cleaned.groupby(columns_to_groupby).agg(agg_dict).reset_index()


    # Save combined results to file
    combined_df.to_excel(f'{output_data_directory}{filename_prefix}-combined_ontology_annotations-{formatted_timestamp}.xlsx', index=False)


@main.command("hello")
def hello():
    try:
        result = 1 / 0
    except Exception as e:
        logger.error("An error occurred: %s", str(e), exc_info=True)


if __name__ == "__main__":
    main()