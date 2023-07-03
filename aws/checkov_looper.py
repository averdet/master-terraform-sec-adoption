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

GITHUB_API_USER = 'gh_user'
GITHUB_API_TOKEN = "ghp_XXXXXXX"
PATH_OF_TMP_DIRECTORY = './tmp/'
INPUT_FILE = "./csv/csv_data.csv"
OUTPUT_FILE = "./results/results.csv"
LOG_FILE = "./checkov_looper.log"
DEBUG = False

MAX_FILE_SIZE = 52645
CHECK_LIST = "CKV_AWS_1,CKV_AWS_2,CKV_AWS_3,CKV_AWS_5,CKV_AWS_6,CKV_AWS_8,CKV_AWS_16,CKV_AWS_17,CKV_AWS_18,CKV_AWS_19,CKV_AWS_20,CKV_AWS_22,CKV_AWS_24,CKV_AWS_25,CKV_AWS_26,CKV_AWS_27,CKV_AWS_29,CKV_AWS_30,CKV_AWS_31,CKV_AWS_32,CKV_AWS_33,CKV_AWS_34,CKV_AWS_35,CKV_AWS_38,CKV_AWS_39,CKV_AWS_40,CKV_AWS_41,CKV_AWS_42,CKV_AWS_43,CKV_AWS_44,CKV_AWS_45,CKV_AWS_46,CKV_AWS_47,CKV_AWS_48,CKV_AWS_49,CKV_AWS_50,CKV_AWS_53,CKV_AWS_54,CKV_AWS_55,CKV_AWS_56,CKV_AWS_57,CKV_AWS_58,CKV_AWS_59,CKV_AWS_60,CKV_AWS_61,CKV_AWS_62,CKV_AWS_63,CKV_AWS_64,CKV_AWS_67,CKV_AWS_68,CKV_AWS_69,CKV_AWS_71,CKV_AWS_72,CKV_AWS_73,CKV_AWS_76,CKV_AWS_77,CKV_AWS_79,CKV_AWS_83,CKV_AWS_84,CKV_AWS_87,CKV_AWS_88,CKV_AWS_91,CKV_AWS_92,CKV_AWS_94,CKV_AWS_96,CKV_AWS_97,CKV_AWS_98,CKV_AWS_99,CKV_AWS_100,CKV_AWS_101,CKV_AWS_102,CKV_AWS_103,CKV_AWS_105,CKV_AWS_106,CKV_AWS_107,CKV_AWS_108,CKV_AWS_110,CKV_AWS_111,CKV_AWS_112,CKV_AWS_113,CKV_AWS_117,CKV_AWS_118,CKV_AWS_119,CKV_AWS_126,CKV_AWS_130,CKV_AWS_131,CKV_AWS_136,CKV_AWS_140,CKV_AWS_142,CKV_AWS_155,CKV_AWS_156,CKV_AWS_168,CKV_AWS_169,CKV_AWS_173,CKV_AWS_201,CKV_AWS_202,CKV_AWS_204,CKV_AWS_208,CKV_AWS_209,CKV_AWS_212,CKV_AWS_213,CKV_AWS_214,CKV_AWS_215,CKV_AWS_226,CKV_AWS_227,CKV_AWS_229,CKV_AWS_230,CKV_AWS_231,CKV_AWS_232,CKV_AWS_250,CKV_AWS_251,CKV_AWS_260,CKV2_AWS_1,CKV2_AWS_2,CKV2_AWS_6,CKV2_AWS_7,CKV2_AWS_11,CKV2_AWS_12,CKV2_AWS_20,CKV2_AWS_28,CKV2_AWS_29"

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