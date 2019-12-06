class MyNameSpace {
  constructor() {
    this.someData = 55;
    this.caseData = new Object({
        addm_name: null,
    });
    this.excludeIds = [
        'addm_v_int',
        'test_items_prepared',
        'fails', 'error', 'passed', 'skipped',
        'action', 'actions', 'test_type', 'test_case_depot_path'
    ];
  }
}

export default (new MyNameSpace);