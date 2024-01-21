# Search ontology, run as: make search oid="mondo,hp" data_filename="test_data.xlsx"
search:
	@echo "** Search ontology: $(oid)"
	python src/harmonize.py search --oid $(oid) --data_filename $(data_filename)
