DEPOSIT_ID=1
ARCHIVE=../../swh-deposit.zip
ARCHIVE2=../../swh-model.zip
STATUS=--no-partial
PARTIAL_STATUS=--partial
UPDATE_STATUS='done'
ATOM_ENTRY=../../atom-entry.xml
EXTERNAL_ID='external-id'

create-archives:
	7z a $(ARCHIVE) $(FOLDER)
	7z a $(ARCHIVE2) $(FOLDER2)

new:
	./create_deposit.sh $(ARCHIVE) $(STATUS)

new-complete:
	./create_deposit_with_metadata.sh $(ARCHIVE) $(ATOM_ENTRY) $(STATUS) $(EXTERNAL_ID)

new-partial:
	make new STATUS=$(PARTIAL_STATUS) ARCHIVE=$(ARCHIVE)

update:
	./update-deposit-with-another-archive.sh $(DEPOSIT_ID) $(ARCHIVE2) $(STATUS)

update-partial:
	make update DEPOSIT_ID=$(DEPOSIT_ID) ARCHIVE2=$(ARCHIVE2) STATUS=$(PARTIAL_STATUS)

replace:
	./replace-deposit-archive.sh $(ARCHIVE2) $(DEPOSIT_ID)

download:
	./download-deposit-archive.sh $(DEPOSIT_ID)

status:
	./status.sh $(DEPOSIT_ID)

service-document:
	./service-document.sh

home:
	./home.sh

update-status:
	./update-status.sh $(DEPOSIT_ID) $(UPDATE_STATUS)
