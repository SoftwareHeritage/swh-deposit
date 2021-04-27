include ../../swh-docs/Makefile.sphinx

APIDOC_EXCLUDES += ../swh/*/settings/*

sphinx/html: images
sphinx/clean: clean-images

images:
	make -C images/
clean-images:
	make -C images/ clean

clean: clean-images

.PHONY: images clean-images
