apertium_regtestdir = $(prefix)/share/apertium-regtest
apertium_regtest_DATA = apertium-regtest.py

staticdir = $(prefix)/share/apertium-regtest/static
static_DATA = static/index.html static/regtest.css static/regtest.js \
			  static/bootstrap.css static/bootstrap.js \
			  static/diff.js static/jquery.js

install-data-hook:
	$(MKDIR_P) $(DESTDIR)/$(prefix)/bin && \
	chmod +x $(DESTDIR)/$(apertium_regtestdir)/apertium-regtest.py && \
	ln -sf $(apertium_regtestdir)/apertium-regtest.py $(DESTDIR)/$(prefix)/bin/apertium-regtest
