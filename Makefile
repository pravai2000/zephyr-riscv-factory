PYTEST      ?= pytest
PYTEST_ARGS ?=
WS          := $(abspath $(CURDIR)/..)

.DEFAULT_GOAL := help
.PHONY: help doctor test quick unit smoke shell ztest fault clean

help:
	@echo "make doctor  check tools and workspace"
	@echo "make test    full suite (includes deliberate crash tests)"
	@echo "make quick   everything except crash tests"
	@echo "make unit    host-only tests, no QEMU (fast)"
	@echo "make smoke | shell | ztest | fault   one marker group"
	@echo "make clean   remove logs and cached test builds"
	@echo "Extra pytest options: make test PYTEST_ARGS='-k add -v'"

doctor:
	@./scripts/doctor.sh

test: doctor
	$(PYTEST) $(PYTEST_ARGS)

quick: doctor
	$(PYTEST) -m "not fault" $(PYTEST_ARGS)

unit:
	$(PYTEST) -m unit $(PYTEST_ARGS)

smoke: doctor
	$(PYTEST) -m smoke $(PYTEST_ARGS)

shell: doctor
	$(PYTEST) -m shell $(PYTEST_ARGS)

ztest: doctor
	$(PYTEST) -m ztest $(PYTEST_ARGS)

fault: doctor
	$(PYTEST) -m fault $(PYTEST_ARGS)

stress: doctor
	$(PYTEST) -m stress $(PYTEST_ARGS)

clean:
	rm -rf logs .pytest_cache $(WS)/build/pytest
