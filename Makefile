# Makefile for VideoTester
#

DIST     = dist
BUILD 	 = build
DOC      = doc
MAKEFILE = doc/sphinx/
BUILDDIR = doc/sphinx/_build

.PHONY: help clean doc sdist bdist_rpm

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  doc        to make documentation"
	@echo "  sdist      to make source distribution"
	@echo "  bdist_rpm  to make RPM distribution"
	@echo "  clean      to clean"

clean:
	-rm -rf $(DIST) $(BUILD)
	-find $(DOC) -maxdepth 1 -mindepth 1 ! -name 'sphinx' -exec rm -rf {} +
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

bdist_rpm: doc
	-cp -rf VT.conf README.md LICENSE scripts $(DOC)
	-python setup.py bdist_rpm
	@echo
	@echo "Build finished."
