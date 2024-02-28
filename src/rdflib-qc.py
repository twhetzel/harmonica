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


def run_qc_check(ontology_file_path):
    """
    Execute QC SPARQL query
    """
    print('Running query...')

    # Create a RDFLib graph
    g = Graph()

    # Load the ontology into the graph
    g.parse(ontology_file_path)

    # Query for all classes using SPARQL
    query_1 = """
        PREFIX obo: <http://purl.obolibrary.org/obo/>
        PREFIX oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT DISTINCT ?entity ?property ?value
        WHERE {
        VALUES ?property1 {
            obo:IAO_0000118
            oboInOwl:hasExactSynonym
            rdfs:label
        }
        VALUES ?property2 {
            obo:IAO_0000118
            oboInOwl:hasExactSynonym
            rdfs:label
        }
        ?entity1 ?property1 ?value.
        ?entity2 ?property2 ?value .

        FILTER NOT EXISTS {
            ?axiom owl:annotatedSource ?entity1 ;
                owl:annotatedProperty ?property1 ;
                owl:annotatedTarget ?value ;
                oboInOwl:hasSynonymType <http://purl.obolibrary.org/obo/mondo#ABBREVIATION> .
        }

        FILTER NOT EXISTS {
            ?axiom owl:annotatedSource ?entity2 ;
                owl:annotatedProperty ?property2 ;
                owl:annotatedTarget ?value ;
                oboInOwl:hasSynonymType <http://purl.obolibrary.org/obo/mondo#ABBREVIATION> .
        }

        FILTER NOT EXISTS { ?entity1 owl:deprecated true }
        FILTER NOT EXISTS { ?entity2 owl:deprecated true }
        FILTER (?entity1 != ?entity2)
        FILTER (!isBlank(?entity1))
        FILTER (!isBlank(?entity2))
        BIND(CONCAT(CONCAT(REPLACE(str(?entity1),"http://purl.obolibrary.org/obo/MONDO_","MONDO:"),"-"), REPLACE(str(?entity2),"http://purl.obolibrary.org/obo/MONDO_","MONDO:")) as ?entity)
        BIND(CONCAT(CONCAT(REPLACE(REPLACE(str(?property1),"http://www.w3.org/2000/01/rdf-schema#","rdfs:"),"http://www.geneontology.org/formats/oboInOwl#","oboInOwl:"),"-"), REPLACE(REPLACE(str(?property1),"http://www.w3.org/2000/01/rdf-schema#","rdfs:"),"http://www.geneontology.org/formats/oboInOwl#","oboInOwl:")) as ?property)
        }
        ORDER BY DESC(UCASE(str(?value)))
    """
    
    
    query = """
        prefix owl: <http://www.w3.org/2002/07/owl#>
        prefix oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>
        prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        #description: No two Mondo IDs should ever point to the same external ID

        SELECT DISTINCT ?entity ?property ?value WHERE {
            ?entity oboInOwl:hasDbXref ?xref .
            
            ?entity2 oboInOwl:hasDbXref ?xref .
            
            ?xref_anno2 a owl:Axiom ;
                owl:annotatedSource ?entity ;
                owl:annotatedProperty oboInOwl:hasDbXref ;
                owl:annotatedTarget ?xref ;
                oboInOwl:source ?source1 .
                
                ?xref_anno a owl:Axiom ;
                owl:annotatedSource ?entity2 ;
                owl:annotatedProperty oboInOwl:hasDbXref ;
                owl:annotatedTarget ?xref ;
                oboInOwl:source ?source2 .

            FILTER (?entity2!=?entity)
            FILTER ((str(?source1)="MONDO:equivalentTo") || (str(?source1)="MONDO:obsoleteEquivalent") || (str(?source1)="MONDO:equivalentObsolete") || (str(?source1)="MONDO:obsoleteEquivalentObsolete"))
            FILTER ((str(?source2)="MONDO:equivalentTo") || (str(?source2)="MONDO:obsoleteEquivalent") || (str(?source2)="MONDO:equivalentObsolete") || (str(?source2)="MONDO:obsoleteEquivalentObsolete"))
            FILTER (isIRI(?entity) && STRSTARTS(str(?entity), "http://purl.obolibrary.org/obo/MONDO_"))
            FILTER (isIRI(?entity2) && STRSTARTS(str(?entity2), "http://purl.obolibrary.org/obo/MONDO_"))
            BIND(?xref as ?property)
            BIND(str(?entity2) as ?value)
        }
        ORDER BY ?entity
    """
    
    # Execute the query on the graph
    query_result = g.query(query, initNs={"owl": OWL, "rdfs": RDFS})
    print(query_result)

    print('Getting individual results...')
    mondo_clasess = [(result['entity'], result['property'], result['value']) for result in query_result]
    # mondo_clasess = [(result['entity']) for result in query_result]
    print(mondo_clasess[1])

    # Extract the classes and labels from the query results
    # mondo_classes_with_labels = [(result['class'], result['label']) for result in results]
    # mondo_classes_with_labels = [(str(result['class']), str(result['label'])) for result in results]

    # return mondo_classes_with_labels


if __name__ == '__main__':
    # Example usage
    ontology_file_path = "./ontologies/mondo.owl"

    run_qc_check(ontology_file_path)

    # Get all classes and their labels
    # classes = get_owl_classes(ontology_file_path)
    # # Print the extracted classes and labels
    # for owl_class, label in classes:
    #     print(f"Class: {owl_class}\nLabel: {label}\n")



    # # Get only count of classes. See sparql query for where clause details
    # count_of_mondo_classes = count_mondo_classes(ontology_file_path)
    # # Print the count of classes
    # print(f"Count of MONDO classes: {count_of_mondo_classes}")







