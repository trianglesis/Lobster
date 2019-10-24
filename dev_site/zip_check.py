

if __name__ == "__main__":

    import zipfile
    import os

    # noinspection PyShadowingNames,PyShadowingNames,PyShadowingNames,PyShadowingNames,PyShadowingNames
    def zipwalk(zippath):
        tempdir = os.environ.get('TEMP', os.environ.get('TMP', os.environ.get('TMPDIR', '/tmp')))

        # noinspection PyUnusedLocal,PyUnusedLocal
        try:
            with zipfile.ZipFile(zippath, 'r') as z:
                for info in z.infolist():
                    fname = info.filename
                    data = z.read(fname)
                    # noinspection PyUnusedLocal
                    extn = (os.path.splitext(fname)[1]).lower()
                    # if extn == '.zip':
                    if fname == 'TKU-Product-Content-2019-03-2-ADDM-11.3+.zip':

                        tmpfpath = os.path.join(tempdir, os.path.basename(fname))

                        if 'TKU-Product-Content' in tmpfpath:
                            print(tmpfpath)
                            try:
                                open(tmpfpath, 'w+b').write(data)
                            except (IOError, OSError)as e:
                                print(e)

                            prod_c = zipfile.ZipFile(tmpfpath, 'r')
                            prod_c_info_List = prod_c.infolist()
                            for item in prod_c_info_List:
                                print(item)

                    # noinspection PyBroadException
                    try:
                        os.remove(tmpfpath)
                    except:
                        pass
                    else:
                        pass
        except RuntimeError as e:
            print('Runtime Error')
        except zipfile.error as e:
            raise


    tku_zip = '/home/user/TH_Octopus/UPLOAD/HUB/RELEASED/TKN/TKN_release_2019-03-2-159/publish/tkn/11.3/tku/Technology-Knowledge-Update-2019-03-2-ADDM-11.3+.zip'
    zips = zipwalk(zippath=tku_zip)
    for item in zips:
        print(item)
