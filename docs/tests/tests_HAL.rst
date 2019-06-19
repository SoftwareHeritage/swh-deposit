Tests scenarios for client
==========================

Scenarios for HAL- on HAL's platform
------------------------------------

The same procedure is used for all tests:

Software Author:

#. prepare content
#. fill out form
#. submit

HAL moderator:

#. review content submitted
#. check metadata fields on HAL
#. validate submission

SWH side:

1. check content in SWH:

  - directory was created
  - revision was created
  - release was created when releaseNotes and softwareVersion was included (new feature!)
  - origin corresponds to HAL url

2. check metadata fields on SWH (in revision)
3. check directory
4. check swh-id on HAL
5. check browsability when entering SWH artifact from HAL
6. check vault artifact recreation
7. access deposit's origin from SWH

+-------------+-------------------------------------------+----------+---------+-----------------------------------------+
| scenario    | test case                                 | data     | result  | exceptions or specific checks           |
+=============+===========================================+==========+=========+=========================================+
| submit code | content: .tar.gz                          | .zip     | success |                                         |
+-------------+-------------------------------------------+----------+---------+-----------------------------------------+
| submit code | content: .zip                             | .tar.gz  | success |                                         |
+-------------+-------------------------------------------+----------+---------+-----------------------------------------+
| submit code | content: no content                       | empty    | fail    | blocked on HAL                          |
+-------------+-------------------------------------------+----------+---------+-----------------------------------------+
| submit code | content: double compression (.zip in .zip)| .zip x 2 | fail    | status `failed` on SWH                  |
+-------------+-------------------------------------------+----------+---------+-----------------------------------------+
| submit code | all metadata-single entry                 | metadata | success | check that all metadata is transmitted  |
+-------------+-------------------------------------------+----------+---------+-----------------------------------------+
| submit code | multiple entries                          | metadata | success | languages / authors / descriptions      |
+-------------+-------------------------------------------+----------+---------+-----------------------------------------+
| new version | new content- same metadata                | content  | success | check new swh-id in SWH and HAL         |
+-------------+-------------------------------------------+----------+---------+-----------------------------------------+
| new version | same content- new metadata                | metadata | ?       | dead angle- doesn't arrives to SWH      |
+-------------+-------------------------------------------+----------+---------+-----------------------------------------+
| new version | new content-new metadata                  | C & M    | success | check artifacts history in revisions    |
+-------------+-------------------------------------------+----------+---------+-----------------------------------------+
| submit code | deposit on another hal platform           | C & M    | success |                                         |
+-------------+-------------------------------------------+----------+---------+-----------------------------------------+

Past known bugs:

- v2 problem, where swh-id from first version is kept in the second version
  instead of the new swh-id.
- when deposit workers are down- error 500 is returned on HAL without real
  explanation (because there is no error on SWH- deposit status
  stays `deposited`).
