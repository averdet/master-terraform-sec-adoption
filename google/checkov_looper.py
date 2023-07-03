import datetime

import requests
from tqdm import tqdm
import csv
import json
from git import Repo
from shutil import rmtree
import subprocess
import re
import logging

GITHUB_API_USER = 'averdet'
GITHUB_API_TOKEN = "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"
PATH_OF_TMP_DIRECTORY = './tmp/'
INPUT_FILE = "./csv/google_dataset_filtered.csv"
OUTPUT_FILE = "./csv/google_results.csv"
LOG_FILE = "./checkov_looper.log"
DEBUG = True

MAX_FILE_SIZE = 52645*10
CHECK_LIST = "CKV_GCP_1,CKV_GCP_2,CKV_GCP_3,CKV_GCP_6,CKV_GCP_8,CKV_GCP_11,CKV_GCP_15,CKV_GCP_16,CKV_GCP_18,CKV_GCP_19,CKV_GCP_23,CKV_GCP_25,CKV_GCP_26,CKV_GCP_28,CKV_GCP_29,CKV_GCP_31,CKV_GCP_32,CKV_GCP_36,CKV_GCP_37,CKV_GCP_38,CKV_GCP_40,CKV_GCP_42,CKV_GCP_44,CKV_GCP_45,CKV_GCP_51,CKV_GCP_52,CKV_GCP_53,CKV_GCP_54,CKV_GCP_55,CKV_GCP_56,CKV_GCP_57,CKV_GCP_60,CKV_GCP_61,CKV_GCP_62,CKV_GCP_63,CKV_GCP_64,CKV_GCP_74,CKV_GCP_75,CKV_GCP_76,CKV_GCP_79,CKV_GCP_80,CKV_GCP_81,CKV_GCP_83,CKV_GCP_84,CKV_GCP_85,CKV_GCP_86,CKV_GCP_87,CKV_GCP_88,CKV_GCP_89,CKV_GCP_90,CKV_GCP_91,CKV_GCP_92,CKV_GCP_93,CKV_GCP_94,CKV_GCP_96,CKV_GCP_97,CKV_GCP_98,CKV_GCP_99,CKV_GCP_100,CKV_GCP_101,CKV_GCP_102,CKV_GCP_103,CKV_GCP_104,CKV_GCP_105,CKV_GCP_106,CKV_GCP_107,CKV_GCP_108,CKV_GCP_109,CKV_GCP_111,CKV_GCP_112,CKV_GCP_113,CKV_GCP_114,CKV2_GCP_6,CKV2_GCP_7,CKV2_GCP_8,CKV2_GCP_9,CKV2_GCP_13,CKV2_GCP_14,CKV2_GCP_15,CKV2_GCP_16,CKV2_GCP_17,CKV2_GCP_18"

ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

headers = {'Authorization': 'token %s' % GITHUB_API_TOKEN}

repo_count = 0
passed_policies = {}
failed_policies = {}

visited_repo = {}
try:
    # Load existing Output file to mark already analyzed repositories
    with open(OUTPUT_FILE, 'r') as outfile:
        outfile.readline()
        file_rows = outfile.readlines()
        for row in file_rows:
            visited_repo[row.split(",")[0]] = True
    logging.info("Existing outfile loaded")
except:
    # No output file: create one with the labels first row
    with open(OUTPUT_FILE, 'w') as outfile:
        write_to_csv = csv.writer(outfile, delimiter=',')
        write_to_csv.writerow(["Repository Full Name", "Passed Check Count", "Failed Check Count", "Passed Checks", "Failed Checks", "Check Date"])

with open(INPUT_FILE, 'r') as f:
    # Retrieve the list of repositories to analyze
    f.readline()
    repo_list = f.readlines()
    repo_name_list = [repo.split(',')[0].strip('\n') for repo in repo_list]
    to_visit_repo = [repo for repo in repo_name_list if repo not in visited_repo]
    for repo_name in tqdm(to_visit_repo):

        if not visited_repo.get(repo_name, False):

            # Fetch repository size to ignore too large repos (above MAX_FILE_SIZE threshold), higher thresholds in other executions until all repositories analyzed
            with requests.get(url="https://api.github.com/repos/"+repo_name, headers=headers) as r_repo:
                try:
                    r_repo = r_repo.json()
                except:
                    logging.error("Unable to parse json from repository API response. See: {}".format(r_repo.text))
                if r_repo.get("size", 0) > MAX_FILE_SIZE:
                    logging.warning("{} is too large".format(repo_name))
                    continue

            # Downloading the repository files
            logging.info("Cloning repo {}".format(repo_name))
            try:
                repo = Repo.clone_from('https://'+GITHUB_API_USER+':'+GITHUB_API_TOKEN+'@github.com/'+repo_name+'.git', PATH_OF_TMP_DIRECTORY+repo_name)
            except:
                logging.warning("Repo {} error".format(repo_name))
                rmtree(PATH_OF_TMP_DIRECTORY+repo_name.split('/')[0])
                continue

            # Execute the checkov Static Code Analysis with the CHECK_LIST
            logging.info("Checkov start on {}".format(repo_name))
            #checkov.main.run(argv='--directory '+PATH_OF_TMP_DIRECTORY+repo_name+' --check ' + CHECK_LIST +' -o json') # >'+PATH_OF_JSONS_DIRECTORY+repo_name.replace('/', '_')+'_results.json'
            call_result = subprocess.run(["checkov", '--directory', PATH_OF_TMP_DIRECTORY+repo_name, "--check", CHECK_LIST, "-o", "json"], capture_output=True, text=True)

            # Handle checkov errors
            if call_result.returncode != 1:
                logging.warning('Checkov failed on {}. See {}'.format(repo_name, call_result.stderr.split('\n')[-1]))
                rmtree(PATH_OF_TMP_DIRECTORY + repo_name.split('/')[0])
                continue

            # Retrieve checkov results
            results = ansi_escape.sub('', call_result.stdout)
            if DEBUG:
                with open("debug.json", 'w') as outfile:
                    outfile.write(results)
                    #json.dump(r_json, outfile)
            r_json = json.loads(results)

            # Remove repositories files from disk
            logging.info("Erasing {} from disk".format(repo_name))
            rmtree(PATH_OF_TMP_DIRECTORY+repo_name.split('/')[0])

            # If checkov identifies and runs different test (ie Terraform and Terraform plan), output will be a list of results
            if type(r_json) == list:
                for item in r_json:
                    if item.get("check_type", "") == "terraform":
                        r_json = item
                        break
                if type(r_json) == list:
                    r_json = {}


            # Saving passed and failed checks in OUTPUT_FILE
            passed_string = ""
            failed_string = ""

            for passed_check in r_json.get("results", {}).get("passed_checks", []):
                passed_policies[passed_check["check_id"]] = passed_policies.get(passed_check["check_id"], 0) + 1
                passed_string += "{};".format(passed_check["check_id"])
            for failed_check in r_json.get("results", {}).get("failed_checks", []):
                failed_policies[failed_check["check_id"]] = failed_policies.get(failed_check["check_id"], 0) + 1
                failed_string += "{};".format((failed_check["check_id"]))

            with open(OUTPUT_FILE, 'a') as outfile:
                write_to_csv = csv.writer(outfile, delimiter=',')

                write_to_csv.writerow([repo_name, r_json.get("summary", {}).get("passed", 0), r_json.get("summary", {}).get("failed", 0), passed_string[:-1], failed_string[:-1], datetime.datetime.now()])

            repo_count += 1
            visited_repo[repo_name] = True

logging.info("Total number of repositories: {}".format(repo_count))
print("Total number of repositories: {}".format(repo_count))