include ../../swh-docs/Makefile.sphinx

html: copy_md

copy_md:
	cp ../README-getting-started.md getting-started.md
	cp ../README.md spec-api.md
	cp ../README-injection.md spec-injection.md
	cp ../README-dev.md dev-info.md
	cp ../README-sys.md sys-info.md

clean:
	rm -f *.md
