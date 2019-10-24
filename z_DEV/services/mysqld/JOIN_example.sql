SELECT 
    octo_test_cases.id, 
    octo_test_cases.test_py_path
FROM octopus_dev_copy.octo_test_cases
    INNER JOIN octopus_dev_copy.octo_test_cases_details_test_cases 
    ON octo_test_cases_details_test_cases.testcases_id = octo_test_cases.id
WHERE octo_test_cases_details_test_cases.testcasesdetails_id = $testcases_id


select octo_test_cases.id, octo_test_cases.test_py_path
from octopus_dev_copy.octo_test_cases inner join octo_test_cases_details_test_cases
on octo_test_cases_details_test_cases.testcases_id=octo_test_cases.id
where octo_test_cases_details_test_cases.testcases_id=$octo_test_cases.id


SELECT 
    octo_test_cases.id, octo_test_cases.test_py_path
FROM
    octopus_dev_copy.octo_test_cases_details_test_cases octopus_dev_copy.octo_test_cases
        INNER JOIN
    actors_movies am ON m.id = am.movie_id
        INNER JOIN
    actors a ON am.actor_id = a.id
WHERE
    a.name = 'Christopher Walken'