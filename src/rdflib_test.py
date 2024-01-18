from rdflib import Graph, RDF, RDFS, OWL
from rdflib.plugins.sparql import prepareQuery


def get_owl_classes(ontology_file_path):
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

    return mondo_classes_with_labels


def count_mondo_classes(ontology_file_path):
    # Create a RDFLib graph
    g = Graph()

    # Load the ontology into the graph
    g.parse(ontology_file_path)

    # Define a SPARQL query template with COUNT
    query_template = """
    SELECT (COUNT(DISTINCT ?class) as ?count)
    WHERE {
        ?class a owl:Class .
        OPTIONAL { ?class rdfs:label ?label }
        FILTER (
            STRSTARTS(STR(?class), "http://purl.obolibrary.org/obo/MONDO_") &&
            !STRSTARTS(?label, "obsolete")
        )
    }
    """

    # results = g.query(query, initNs={"owl": OWL, "rdfs": RDFS})
    # Prepare the SPARQL query
    query = prepareQuery(query_template, initNs={"owl": OWL, "rdfs": RDFS})

    # Execute the query on the graph and retrieve the count
    result = g.query(query).bindings[0]['count'].value

    return int(result)


# Example usage
ontology_file_path = "./ontologies/mondo.owl"

# Get all classes and their labels
classes = get_owl_classes(ontology_file_path)
# Print the extracted classes and labels
for owl_class, label in classes:
    print(f"Class: {owl_class}\nLabel: {label}\n")



# Get only count of classes. See sparql query for where clause details
count_of_mondo_classes = count_mondo_classes(ontology_file_path)
# Print the count of classes
print(f"Count of MONDO classes: {count_of_mondo_classes}")







