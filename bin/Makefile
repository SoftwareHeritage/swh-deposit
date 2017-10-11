DEPOSIT_ID=1
ARCHIVE=../../swh-deposit.zip
ARCHIVE2=../../swh-model.zip
STATUS=false
PARTIAL_STATUS=true

create-archives:
	7z a $(ARCHIVE) $(FOLDER)
	7z a $(ARCHIVE2) $(FOLDER2)

new:
	./create_deposit.sh $(ARCHIVE) $(STATUS)

new-partial:
	make new STATUS=$(PARTIAL_STATUS) ARCHIVE=$(ARCHIVE)

update:
	./update-deposit-with-another-archive.sh $(DEPOSIT_ID) $(ARCHIVE_2) $(STATUS)

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
