from rdflib import Graph, RDF, RDFS, OWL
from rdflib.plugins.sparql import prepareQuery
from oaklib import get_adapter
from oaklib.datamodels.search import SearchProperty, SearchConfiguration
import pandas as pd
from datetime import datetime


def get_owl_classes(ontology_file_path):
    """
    Use rdflib to query for classes.
    """
    formatted_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("Start RDFLib Query:", formatted_datetime)

    # Create a RDFLib graph
    g = Graph()

    # Load the ontology into the graph
    g.parse(ontology_file_path)

    # Query for all classes using SPARQL
    query = """
    SELECT DISTINCT ?class ?label
    WHERE {
        ?class a owl:Class .
        OPTIONAL { ?class rdfs:label ?label }
        FILTER (
            STRSTARTS(STR(?class), "http://purl.obolibrary.org/obo/MONDO_") &&
            !STRSTARTS(?label, "obsolete")
        )
    }
    """
    
    # Execute the query on the graph
    results = g.query(query, initNs={"owl": OWL, "rdfs": RDFS})

    # Extract the classes and labels from the query results
    # mondo_classes_with_labels = [(result['class'], result['label']) for result in results]
    mondo_classes_with_labels = [(str(result['class']), str(result['label'])) for result in results]

    formatted_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("End RDFLib Query:  ", formatted_datetime)

    return mondo_classes_with_labels


def search_ontology(adapter, df, config):
    """
    Search for exact matches to the ontology term label.
    :param adapter: The connector to the ontology database.
    :param df: Dataframe containing terms to search and find matches to the ontology.
    """
    formatted_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    exact_search_results = []

    # Get ontology metadata
    for ont in adapter.ontologies():
        ontology_metadata = adapter.ontology_metadata_map(ont)
        print(f"Ontology metadata: {ontology_metadata['id']}, {ontology_metadata['owl:versionIRI']}")
    

    print("Start OAK Search:", formatted_datetime)
    
    # for index, row in df.iloc[1:10].iterrows():
    for index, row in df.iterrows():
        for curie in adapter.basic_search(row.iloc[1], config=config):
            exact_search_results.append([row.iloc[1], curie, adapter.label(curie)])

    search_results_df = pd.DataFrame(exact_search_results)

    formatted_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("End OAK Search:", formatted_datetime)

    return search_results_df


def main(ontology_file_path):
    """
    Get all non-obsolete classes (ie class label starts with 'obsolete' using rdflib)
    and check if the class is in the semsql SQLite database for mondo.
    """
    ontology_id = 'mondo'
    # Get the ontology
    adapter = get_adapter(f"sqlite:obo:{ontology_id}")

    exact_label_search_config = SearchConfiguration(
        properties=[SearchProperty.LABEL],
        force_case_insensitive=True,
    )

    # (1) Get all classes and their labels using rdflib
    classes = get_owl_classes(ontology_file_path)
    data_df = pd.DataFrame(classes)
    print(data_df.head())
    
    # (2) Check if the class is in the semsql SQLite database
    search_results_df = search_ontology(adapter, data_df, exact_label_search_config)

    #(3) Write to file
    print('Saving search results to file...')
    search_results_df.to_csv('search_results.csv', index=False)



if __name__ == '__main__':
    ontology_file_path = "./ontologies/mondo.owl"

    main(ontology_file_path)
