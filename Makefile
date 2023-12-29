# Search ontology, run as: make search ontology_id=mondo data_filename=TEST
search:
	@echo "** Search ontology: $(ontology_id)"
	python src/harmonize.py search $(ontology_id) '$(data_filename)'
