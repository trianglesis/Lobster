import re


OUTPUT = 'Archive:  /home/user/TH_Octopus/UPLOAD/HUB/tkn_main_continuous/12.0/edp/Extended-Data-Pack-2070-06-1-ADDM-12.0+.zip\n extracting: release.txt             \n812009\n\n'

release_re = re.compile(r'.*extracting:\srelease\.txt.*\\n(\d+)')


release_search = release_re.search(OUTPUT)
print(release_search)
if release_search:
    release = release_search.group(1)
    print(release)