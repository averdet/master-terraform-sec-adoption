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
INPUT_FILE = "./csv/azure_dataset_filtered.csv"
OUTPUT_FILE = "./csv/azure_results.csv"
LOG_FILE = "./checkov_looper.log"
DEBUG = True

MAX_FILE_SIZE = 52645
CHECK_LIST = "CKV_AZURE_1,CKV_AZURE_9,CKV_AZURE_10,CKV_AZURE_34,CKV_AZURE_48,CKV_AZURE_49,CKV_AZURE_53,CKV_AZURE_59,CKV_AZURE_68,CKV_AZURE_77,CKV_AZURE_89,CKV_AZURE_101,CKV_AZURE_104,CKV_AZURE_106,CKV_AZURE_108,CKV_AZURE_113,CKV_AZURE_120,CKV_AZURE_121,CKV_AZURE_124,CKV_AZURE_139,CKV_AZURE_160,CKV_AZURE_162,CKV_AZURE_204,CKV2_AZURE_6,CKV2_AZURE_8,CKV_AZURE_137,CKV_AZURE_141,CKV_AZURE_2,CKV_AZURE_73,CKV_AZURE_74,CKV_AZURE_93,CKV_AZURE_96,CKV_AZURE_97,CKV_AZURE_105,CKV_AZURE_117,CKV_AZURE_130,CKV_AZURE_151,CKV2_AZURE_1,CKV2_AZURE_14,CKV2_AZURE_15,CKV2_AZURE_16,CKV2_AZURE_17,CKV2_AZURE_18,CKV_AZURE_3,CKV_AZURE_14,CKV_AZURE_28,CKV_AZURE_29,CKV_AZURE_47,CKV_AZURE_70,CKV_AZURE_153,CKV_AZURE_161,CKV_AZURE_178,CKV_AZURE_197,CKV_AZURE_198,CKV_AZURE_45,CKV_AZURE_11,CKV_AZURE_118,CKV_AZURE_119,CKV_AZURE_143,CKV_AZURE_4,CKV_AZURE_30,CKV_AZURE_31,CKV_AZURE_33,CKV_AZURE_146,CKV_AZURE_156,CKV_AZURE_159,CKV2_AZURE_20,CKV2_AZURE_21,CKV_AZURE_15,CKV_AZURE_18,CKV_AZURE_44,CKV_AZURE_52,CKV_AZURE_54,CKV_AZURE_80,CKV_AZURE_81,CKV_AZURE_82,CKV_AZURE_83,CKV_AZURE_145,CKV_AZURE_147,CKV_AZURE_148,CKV_AZURE_154,CKV_AZURE_177,CKV_AZURE_200,CKV_AZURE_205"

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
    repo_name_list = [repo.split(',')[0] for repo in repo_list]
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