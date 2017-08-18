#! 1.Create new organization(see: https://github.com/OpenConceptLab/oclapi/wiki/orgs#create-new-organization)
#! 2.Create new source in organization(see: https://github.com/OpenConceptLab/oclapi/wiki/sources#create-source)
#! 3.Create new version of created source(see: https://github.com/OpenConceptLab/oclapi/wiki/sources#create-new-version-of-a-source)
#! 4.Replace token in commands below with Your admin token
#! 5.Replace source in commands below with created source uuid
python manage.py import_concepts_to_source --source 572343325162890014a3424b --token 8ad61f7fd1c3a5429aa23266056d37b4b40ff659 --retire-missing-records demo-data/ciel_20160328_concepts_2k.json
python manage.py import_concepts_to_source --source 572343325162890014a3424b --token 8ad61f7fd1c3a5429aa23266056d37b4b40ff659 --retire-missing-records demo-data/ciel_20160328_mappings_2k.json
