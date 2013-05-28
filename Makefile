# Makefile for VideoTester
#

DIST     = dist
DOC      = doc
MAKEFILE = tools/sphinx/
BUILDDIR = tools/sphinx/_build

.PHONY: help clean doc sdist

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  doc        to make documentation"
	@echo "  sdist      to make source distribution"
	@echo "  clean      to clean"

clean:
	-rm -rf $(DIST)
	-rm -f MANIFEST

doc:
	-rm -rf $(DOC)/*
	-make -C $(MAKEFILE) html
	-cp -rf $(BUILDDIR)/* $(DOC)
	-rm -rf $(DOC)/doctrees
	-make -C $(MAKEFILE) clean
	@echo
	@echo "Doc rebuilt."

sdist:
	-cp VT.conf doc
	-cp README.md doc/
	-cp LICENSE doc/
	-cp -rf test doc
	-python setup.py sdist
	-rm doc/VT.conf doc/README.md doc/LICENSE
	-rm -rf doc/test
	@echo
	@echo "Build finished."
