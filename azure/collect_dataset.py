import csv
import time
import requests
import urllib.parse
import logging
from tqdm import tqdm

LOG_FILE = "./github_collect.log"

search_string = 'provider azurerm extension:tf'

GITHUB_API_TOKENS = ["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"]

GITHUB_API_URL = 'https://api.github.com/search/code'
params = {'q': search_string,
          'sort': "indexed",
          'order': "desc"}
base_url = GITHUB_API_URL + "?" + urllib.parse.urlencode(params)

OUTPUT_FILE = "./csv/azure_dataset.csv"

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

visited_repo = {}
try:
    # Load to current output file to mark already collected repositories
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
        write_to_csv.writerow(["Repository Full Name", "Repository Description", "Star Count", "Fork Count", "Repository Licence", "Main Language", "Language Repartition"])

added_repo = 0
page_number = 1
pbar = tqdm(total=10)
# Iterate on the 10 pages of the Github Code Search results, with a rotation on the available Github API Tokens
while page_number < 11:
    next_call = base_url + '&page=' + str(page_number) + '&per_page=100'
    headers = {'Authorization': 'token %s' % GITHUB_API_TOKENS[page_number % len(GITHUB_API_TOKENS)]}

    with requests.get(url=next_call, headers=headers) as r:
        if r.status_code == 200:
            logging.info("Success on page number: " + str(page_number))

            for item in r.json().get("items", []):
                repo_full_name = item.get("repository", {}).get("full_name", None)
                if not visited_repo.get(repo_full_name, False):
                    logging.info("{} repo unvisited".format(repo_full_name))
                    # Get specific information about the repository
                    with requests.get(url=item.get("repository", {}).get("url", None), headers=headers) as r_repo:
                        try:
                            r_repo = r_repo.json()
                        except:
                            logging.error("Unable to parse json from repository API response. See: {}".format(r_repo.text))

                        # Ensure repository in orignial
                        if not r_repo.get("fork", False):
                            # Extract and save the metadata of the repository
                            with open(OUTPUT_FILE, "a") as outfile:
                                write_to_csv = csv.writer(outfile, delimiter=',')

                                repo_description = r_repo.get('description', "")
                                repo_stars = r_repo.get("stargazers_count", 0)
                                repo_forks = r_repo.get("forks_count", 0)
                                repo_main_language = r_repo.get('language', None)
                                repo_license = None
                                if r_repo['license']:
                                    repo_license = r_repo['license']['name']
                                else:
                                    repo_license = "NO LICENSE"

                                language_url = r_repo['url'] + '/languages'
                                language_response = requests.get(url=language_url, headers=headers).json()

                                repo_languages = {}

                                # Calculation for the percentage of all the languages present in the repository
                                count_value = sum([value for value in language_response.values()])
                                for key, value in language_response.items():
                                    key_value = round((value / count_value) * 100, 2)
                                    repo_languages[key] = key_value
                                write_to_csv.writerow([repo_full_name, repo_description, repo_stars, repo_forks, repo_license, repo_main_language, repo_languages])
                            added_repo += 1
                    visited_repo[repo_full_name] = True
            page_number += 1
            pbar.update(page_number-1)


        elif r.status_code == 403:
            duration = int(r.headers.get("Retry-After", 60))
            logging.warning("Limit exhausted. Sleep for {} secs\n{}\n{}".format(duration, r.text, GITHUB_API_TOKENS[page_number % len(GITHUB_API_TOKENS)][-4:]))
            time.sleep(duration)
        elif r.status_code == 422:
            logging.info(r.json().get("message", "422 Error"))
        else:
            logging.error("Query failed to run by returning code of {}. {}\n{}\n{}".format(r.status_code, next_call, r.text, GITHUB_API_TOKENS[page_number % len(GITHUB_API_TOKENS)][-4:]))
            raise Exception("Query failed to run by returning code of {}. {}\n{}".format(r.status_code, next_call, r.text))

pbar.close()
logging.info("{} repos added".format(added_repo))
print("{} repos added".format(added_repo))