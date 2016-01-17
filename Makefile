# Makefile for VideoTester
#

DIST     = dist
DOC      = doc
MAKEFILE = doc/sphinx/
BUILDDIR = doc/sphinx/_build

.PHONY: help clean doc sdist

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  doc        to make documentation"
	@echo "  sdist      to make source distribution"
	@echo "  clean      to clean"

clean:
	-rm -rf $(DIST)
	-rm -rf $(DOC)/html
	-rm -f MANIFEST

doc: clean
	-make -C $(MAKEFILE) html
	-cp -rf $(BUILDDIR)/* $(DOC)
	-rm -rf $(DOC)/doctrees
	-make -C $(MAKEFILE) clean
	@echo
	@echo "Doc rebuilt."

sdist: doc
	-cp -rf VT.conf README.md LICENSE scripts $(DOC)
	-python setup.py sdist
	@echo
	@echo "Build finished."
