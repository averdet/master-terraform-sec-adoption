import csv
import os
import re

from langchain.chains.llm import LLMChain
from langchain_core.prompts import PromptTemplate
from langchain_openai import OpenAI, ChatOpenAI

import config

experiment_metadata = {
    "llm_model": "gpt-4o-mini",
    "llm_temperature": 0.2,
}

if config.OPEN_API_KEY:
    os.environ["OPENAI_API_KEY"] = config.OPEN_API_KEY
else:
    raise Exception("OPEN_API_KEY is not set")

PROMPT_CATEGORIZATION = """
    You're asked to classify a given policy based on one of the following categories. Please, select just one single category:

    Admin by default:  This smell is the recurring pattern of specifying default users as administrative users. The smell can violate the ‘principle of least privilege’ property, which recommends practitioners to design and implement a system in a manner so that by default the least amount of access necessary is provided to any entity.
    Hard-coded secret: This smell is the recurring pattern of revealing sensitive information such as user name and passwords as configurations in IaC scripts. IaC scripts provide the opportunity to specify configurations for the entire system, such as configuring user name and password, setting up SSH keys for users, specifying authentications files (creating keypair files for Amazon Web Services). However, in the process programmers can hard-code these pieces of information into scripts.
    IP Address binding: This smell is the recurring pattern of assigning the address 0.0.0.0 for a database server or a cloud service/instance. Binding to the address 0.0.0.0 may cause security concerns as this address can allow connections from every possible network. Such binding can cause security problems as the server, service, or instance will be exposed to all IP addresses for connection.
    Encryption in transit: This smell is the recurring pattern of using HTTP without the Transport Layer Security (TLS). Such use makes the communication between two entities less secure, as without TLS, use of HTTP is susceptible to man-in-the-middle attacks. Such usage of HTTP can be problematic, as the ‘admin-user’ will be connecting over a HTTP-based protocol. An attacker can eavesdrop on the communication channel and may guess the password of user ‘admin-user’.
    Encryption at rest: This smell is the recurring pattern of using weak cryptography algorithms, such as MD4 and SHA-1 for encryption purposes. MD5 suffers from security problems, as demonstrated by the Flame malware in 2012. MD5 is susceptible to collision attacks and modular differential attacks.
    Access Policy: The Access Policy category refers to any misconfiguration of Identity and Access Management Roles, as well as Access Control Lists. Managing Access policy is an important part of cloud infrastructure security, as it defines which resources can access one another.
    Logging/Monitoring: Policies in this category check if logs and detailed monitoring are enabled on the deployed resources. 
    Outdated feature: Cloud providers often implement new service versions and security fixes automatically with no need to modify the infrastructure definition. However, major changes may not be backward compatible, so some cloud practitioners disable automatic minor updates or stay with vulnerable versions.

    Policy: 
    Name: {title}

    Explanation
    {explanation}

    Possible Impact
    {impact}

    Suggested Resolution
    {solution}

    Report just the category, no further comments.
    Category: []"""

PROMPT_CATEGORIZATION_CHECKOV = """
    You're asked to classify a given policy based on one of the following categories. Please, select just one single category:

    Admin by default:  This smell is the recurring pattern of specifying default users as administrative users. The smell can violate the ‘principle of least privilege’ property, which recommends practitioners to design and implement a system in a manner so that by default the least amount of access necessary is provided to any entity.
    Hard-coded secret: This smell is the recurring pattern of revealing sensitive information such as user name and passwords as configurations in IaC scripts. IaC scripts provide the opportunity to specify configurations for the entire system, such as configuring user name and password, setting up SSH keys for users, specifying authentications files (creating keypair files for Amazon Web Services). However, in the process programmers can hard-code these pieces of information into scripts.
    IP Address binding: This smell is the recurring pattern of assigning the address 0.0.0.0 for a database server or a cloud service/instance. Binding to the address 0.0.0.0 may cause security concerns as this address can allow connections from every possible network. Such binding can cause security problems as the server, service, or instance will be exposed to all IP addresses for connection.
    Encryption in transit: This smell is the recurring pattern of using HTTP without the Transport Layer Security (TLS). Such use makes the communication between two entities less secure, as without TLS, use of HTTP is susceptible to man-in-the-middle attacks. Such usage of HTTP can be problematic, as the ‘admin-user’ will be connecting over a HTTP-based protocol. An attacker can eavesdrop on the communication channel and may guess the password of user ‘admin-user’.
    Encryption at rest: This smell is the recurring pattern of using weak cryptography algorithms, such as MD4 and SHA-1 for encryption purposes. MD5 suffers from security problems, as demonstrated by the Flame malware in 2012. MD5 is susceptible to collision attacks and modular differential attacks.
    Access Policy: The Access Policy category refers to any misconfiguration of Identity and Access Management Roles, as well as Access Control Lists. Managing Access policy is an important part of cloud infrastructure security, as it defines which resources can access one another.
    Logging/Monitoring: Policies in this category check if logs and detailed monitoring are enabled on the deployed resources. 
    Outdated feature: Cloud providers often implement new service versions and security fixes automatically with no need to modify the infrastructure definition. However, major changes may not be backward compatible, so some cloud practitioners disable automatic minor updates or stay with vulnerable versions.

    Policy: 
    Name: {title}

    Explanation
    {explanation}

    Report just the category, no further comments.
    Category: []"""

def find_target_md_file(directory, provider, service, check_name):
    expected_file = os.path.join(directory, provider, service, check_name, "index.md")
    if not os.path.exists(expected_file):
        return None
    return expected_file


def extract_info_from_md(file_path):
    # Initialize a dictionary to store the extracted information
    extracted_info = {
        'title': None,
        'description': None,
        'impact': None,
        'solution': None
    }

    # Open the markdown file and read its content
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # Use regular expressions to extract the required information
    # Assuming the structure follows consistent patterns

    title_match = re.search(r'title:\s*(.*)', content, re.IGNORECASE)
    description_match = re.search(r'### Explanation\s*(.*?)(###|$)', content, re.DOTALL)
    impact_match = re.search(r'### Possible Impact\s*(.*?)(###|$)', content, re.DOTALL)
    solution_match = re.search(r'### Suggested Resolution\s*(.*?)(###|$)', content, re.DOTALL)

    if title_match:
        extracted_info['title'] = title_match.group(1).strip()
    if description_match:
        extracted_info['description'] = description_match.group(1).strip()
    if impact_match:
        extracted_info['impact'] = impact_match.group(1).strip()
    if solution_match:
        extracted_info['solution'] = solution_match.group(1).strip()

    return extracted_info

def ask_for_categorization(info):

    chain = LLMChain(
        prompt=PromptTemplate.from_template(PROMPT_CATEGORIZATION),
        llm=ChatOpenAI(
            model_name=experiment_metadata["llm_model"],
            temperature=experiment_metadata["llm_temperature"],
        ),
    )

    category = chain.invoke({
        "title": info["title"],
        "explanation": info["description"],
        "impact": info["impact"],
        "solution": info["solution"]
    })["text"]

    return category

def ask_for_categorization_checkov(iac, policy):

    chain = LLMChain(
        prompt=PromptTemplate.from_template(PROMPT_CATEGORIZATION_CHECKOV),
        llm=ChatOpenAI(
            model_name=experiment_metadata["llm_model"],
            temperature=experiment_metadata["llm_temperature"],
        ),
    )

    category = chain.invoke({
        "title": policy,
        "explanation": iac,
    })["text"]

    return category


def extract_info_from_csv(file_path):
    i = 0
    categories = []

    with open(file_path, 'r', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            # Extract 'service' and 'check_name' from each row, if available
            service = row.get('service')
            check_name = row.get('check_name')
            category = row.get('Category')
            code = row.get('Code')

            if service and check_name:
                file = find_target_md_file(target_directory, "aws", service, check_name)
                if file is not None:
                    info = extract_info_from_md(file)
                    category_assigned = ask_for_categorization(info)
                    categories.append([code, category, category_assigned])
                    i += 1

    print(i)
    write_categories_to_csv(categories, "gpt-categorization-tfsec2.csv")

def extract_info_from_csv_checkov(file_path):
    i = 0
    categories = []

    with open(file_path, 'r', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            # Extract 'service' and 'check_name' from each row, if available
            iac = row.get('IaC')
            policy = row.get('Policy')
            category = row.get('Category')
            code = row.get('Type')

            if iac and policy:
                category_assigned = ask_for_categorization_checkov(iac, policy)
                categories.append([code, category, category_assigned])
                i += 1

    print(i)
    write_categories_to_csv(categories, "gpt-categorization-checkov2.csv")

def write_categories_to_csv(data, file_path):
    # Open the file for writing
    with open(file_path, 'w', newline='', encoding='utf-8') as csv_file:
        csv_writer = csv.writer(csv_file)

        # Write the header
        csv_writer.writerow(['code', 'original_category', 'assigned_category'])

        # Write the data
        for row in data:
            csv_writer.writerow(row)

target_directory = 'C:\\Users\leu_m\OneDrive\Documentos\postdoctoral\security\projects\\tfsec\docs\checks'
extract_info_from_csv("C:\\Users\leu_m\PycharmProjects\master-terraform-sec-adoption\\aws\csv\\policies-tfsec.csv")
#extract_info_from_csv_checkov("C:\\Users\leu_m\PycharmProjects\master-terraform-sec-adoption\\aws\csv\\policies.csv")