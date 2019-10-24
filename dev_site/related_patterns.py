

if __name__ == "__main__":

    import re
    import logging
    import django
    import ast
    import os
    django.setup()
    from octo_tku_patterns.models import TkuPatterns


    log = logging.getLogger("octo.octologger")
    log.info("Run search RELATED PATTERNS")


    def select_parse_pattern(patt_folder_name=None):
        # patterns = TkuPatterns.objects.all().values()
        patterns_set = TkuPatterns.objects.filter(pattern_folder_name__exact=patt_folder_name).values()
        return patterns_set


    # patterns = select_parse_pattern(patt_folder_name='BEAWebLogicAppServer')
    # for pattern in patterns:
    #     log.info("patterns: %s", pattern)
    #     log.info("pattern.pattern_file_name: %s", pattern.get('pattern_file_name'))
    #     log.info("pattern.test_py_path: %s", pattern.get('test_py_path'))
    #     log.info("pattern.pattern_file_path: %s", pattern.get('pattern_file_path'))
    #
    # test_py_path = patterns[0].get('test_py_path')


    class TestRead:

        def __init__(self):
            # TODO: Allow to parse dev_tests and dml/ip data to use in TH mode

            self.pattern_import_all_r = re.compile(r'from\s+(.+?)\s+import')
            self.core_from_wd_r = re.compile(r"\S+tku_patterns\\CORE\\\\")

            self.tkn_core = os.environ.get("TKN_CORE")

        @staticmethod
        def _read_test(test_py):
            """
            Read test.py
            Return AST tree

            :param test_py: where pattern lies
            :return: ast tree
            """
            # test_py_file_dir = test_py + os.sep + "tests\\"
            if os.path.exists(test_py):
                log.debug("Folder tests for current patters - exist: " + str(test_py))

                log.debug("Reading: %s", test_py)

                try:
                    with open(test_py, "r", encoding="utf8") as f:
                        read_file = f.read()
                        test_tree = ast.parse(read_file)
                        return test_tree
                except UnicodeDecodeError as unicode_err:
                    log.critical("Error: Unable to parse {!r}".format(str(unicode_err)))

            else:
                log.warning("File test.py did not found. Please check_ide it in path: " + str(test_py))

        def test_patterns_list(self, setup_patterns, test_py_path):
            """
            Get raw list 'self.setupPatterns' from test.py and make it full path to each pattern

            :param setup_patterns: raw list of pattern items from test.py
            :param test_py_path: working dir of current pattern
            :return:
            """
            log.debug("Composing paths to patterns from test.py")
            patten_abs_path_list = []
            pattern_file_names_list = []

            # test_py_file_dir = test_py_path + os.sep + "tests\\"
            # /home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/CORE/BEAWebLogicAppServer/tests
            test_py_file_dir = os.path.abspath(os.path.join(test_py_path, os.pardir))
            log.info("test_py_file_dir: %s", test_py_file_dir)

            for p in setup_patterns:
                # Normalize pattern paths:
                pattern_path = os.path.normpath(p)
                # log.info("pattern_path: %s", pattern_path)

                normal_pattern_path = os.path.join(test_py_file_dir, pattern_path)
                # log.info("normal_pattern_path: %s", normal_pattern_path)
                # Join and verify pattern path for each composed path:

                abs_pattern_path = os.path.abspath(normal_pattern_path)
                log.info("abs_pattern_path: %s", abs_pattern_path)

                # Get only pattern file name:
                # TODO: Later re-invent it anew
                pattern_filename = os.path.splitext(os.path.basename(abs_pattern_path))[0]

                if os.path.exists(abs_pattern_path):
                    if abs_pattern_path not in patten_abs_path_list:
                        patten_abs_path_list.append(abs_pattern_path)
                    if pattern_filename not in pattern_file_names_list:
                        pattern_file_names_list.append(pattern_filename)
                else:
                    log.warning("Cannot find file in path"+str(abs_pattern_path))

            return dict(patten_abs_path_list=patten_abs_path_list,
                        pattern_file_names_list=pattern_file_names_list)

        def import_pattern_tests(self, test_py_path):
            """
            Get test.py tree with args from self.setupPatterns()
            Send list of patterns to import logic of imports.py

            :param test_py_path: str: path to patterns folder.
            :return: list of pattern to import for test
            """
            pattern_import_test = []
            log.debug("Reading import patterns from test.py")

            # Read the test.py:
            test_tree = self._read_test(test_py_path)
            if test_tree:
                # Walk in test.py file and get function arguments where import patterns lies:
                for node in ast.walk(test_tree):
                    '''
                    This is to extract list of patterns from test.py file.
                    In first case in modern test.py it will be a tuple which can be appended as it is.
                    In second case in older version of test.py this is a list, so we adding each from it. 
                    '''
                    if isinstance(node, ast.Call):
                        node_func = node.func
                        if isinstance(node_func, ast.Attribute):
                            if node_func.attr == "setupPatterns":
                                node_args = node.args
                                # DEBUG: Iter all nodes
                                # node_iter = ast.iter_fields(node)
                                # for i in node_iter:
                                #     print(i)
                                for arg in node_args:
                                    patterns = ast.literal_eval(arg)
                                    pattern_import_test.append(patterns)
                                    # pattern_import_test.append(arg.s)
                            if node_func.attr == "preProcessTpl":
                                node_args = node.args
                                # DEBUG: Iter all nodes
                                # node_iter = ast.iter_fields(node)
                                # for i in node_iter:
                                #     print(i)
                                for arg in node_args:
                                    patterns = ast.literal_eval(arg)
                                    for pattern in patterns:
                                        pattern_import_test.append(pattern)
                # make list of self.setupPatterns() to abs path to each pattern:

                if pattern_import_test:
                    # full_test_patterns_path = self.test_patterns_list(pattern_import_test, test_py_path, tku_patterns)
                    log.info("pattern_import_test: %s", pattern_import_test)
                    full_test_patterns_path = self.test_patterns_list(pattern_import_test, test_py_path)

                    return full_test_patterns_path
            else:
                log.warning("Cannot get test patterns. "
                            "File test.py is not found or not readable in this path: " + str(test_py_path))


    # test_imports = TestRead().import_pattern_tests(test_py_path=test_py_path)
    # log.info("test_imports: %s all: %s", len(test_imports), test_imports)
