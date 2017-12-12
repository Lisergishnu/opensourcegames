"""
    Counts the number of records each subfolder and updates the overview. Sorts the entries in the contents files of
    each subfolder alphabetically.

    This script runs with Python 3, it could also with Python 2 with some minor tweaks probably, but that's not important.

    TODO print all games without license or code information
    TODO get number of games with github or bitbucket repository and list those who have neither
    TODO list those with exotic licenses (not GPL, zlib, MIT, BSD) or without licenses
    TODO Which C, C++ projects do not use CMake
    TODO list those inactive (sort by year backwards)
    TODO for those games with github repositories get activity, number of open issues, number of merge requests and display in a health monitor file
"""

import os
import re
import urllib.request
import http.client
import datetime

def get_category_paths():
    """
    Returns all sub folders of the games path.
    """
    return [os.path.join(games_path, x) for x in os.listdir(games_path) if os.path.isdir(os.path.join(games_path, x))]

def get_entry_paths(category_path):
    """
    Returns all files of a category path, except for '_toc.md'.
    """
    return [os.path.join(category_path, x) for x in os.listdir(category_path) if x != '_toc.md' and os.path.isfile(os.path.join(category_path, x))]

def read_first_line_from_file(file):
    """
    Convenience function because we only need the first line of a category overview really.
    """
    with open(file, 'r') as f:
        line = f.readline()
    return line

def read_interesting_info_from_file(file):
    """
    Parses a file for some interesting fields and concatenates the content. To be displayed after the game name in the
    category overview.
    """
    with open(file, 'r') as f:
        text = f.read()

    output = [None, None, None]

    # language
    regex = re.compile(r"- Language\(s\): (.*)")
    matches = regex.findall(text)
    if matches:
        output[0] = matches[0]

    # license
    regex = re.compile(r"- License: (.*)")
    matches = regex.findall(text)
    if matches:
        output[1] = matches[0]

    # state
    regex = re.compile(r"- State: (.*)")
    matches = regex.findall(text)
    if matches:
        output[2] = matches[0]

    output = [x for x in output if x] # eliminate empty entries

    output = ", ".join(output)

    return output


def update_readme():
    """
    Recounts entries in subcategories and writes them to the readme. Needs to be performed regularly.
    """
    print('update readme file')

    # read readme
    with open(readme_path) as f:
        readme_text = f.read()

    # compile regex for identifying the building blocks
    regex = re.compile(r"(# Open Source Games\n\n)(.*)(\nA collection.*)", re.DOTALL)

    # apply regex
    matches = regex.findall(readme_text)
    matches = matches[0]
    start = matches[0]
    end = matches[2]

    # get sub folders
    category_paths = get_category_paths()

    # get number of files (minus 1) in each sub folder
    n = [len(os.listdir(path)) - 1 for path in category_paths]

    # assemble paths
    paths = [os.path.join(path, '_toc.md') for path in category_paths]

    # get titles (discarding first two ("# ") and last ("\n") characters)
    titles = [read_first_line_from_file(path)[2:-1] for path in paths]

    # combine titles, category names, numbers in one list
    info = zip(titles, [os.path.basename(path) for path in category_paths], n)

    # sort according to title
    info = sorted(info, key=lambda x:x[0])

    # assemble output
    update = ['- **[{}](games/{}/_toc.md)** ({})\n'.format(*entry) for entry in info]
    update = "{} entries".format(sum(n)) + "".join(update)

    # insert new text in the middle
    text = start + "[comment]: # (start of autogenerated content, do not edit)\n" + update + "\n[comment]: # (end of autogenerated content)" + end

    # write to readme
    with open(readme_path, 'w') as f:
        f.write(text)

def update_category_tocs():
    """
    Lists all entries in all sub folders and generates the list in the toc file. Needs to be performed regularly.
    """
    # get category paths
    category_paths = get_category_paths()

    # for each category
    for category_path in category_paths:
        print('generate toc for {}'.format(os.path.basename(category_path)))

        # read toc header line
        toc_file = os.path.join(category_path, '_toc.md')
        toc_header = read_first_line_from_file(toc_file)

        # get paths of all entries in this category
        entry_paths = get_entry_paths(category_path)

        # get titles (discarding first two ("# ") and last ("\n") characters)
        titles = [read_first_line_from_file(path)[2:-1] for path in entry_paths]

        # get more interesting info
        more = [read_interesting_info_from_file(path) for path in entry_paths]

        # combine name and file name
        info = zip(titles, [os.path.basename(path) for path in entry_paths], more)

        # sort according to title
        info = sorted(info, key=lambda x:x[0])

        # assemble output
        update = ['- **[{}]({})** ({})\n'.format(*entry) for entry in info]
        update = "".join(update)

        # combine toc header
        text = toc_header + '\n' + "[comment]: # (start of autogenerated content, do not edit)\n" + update + "\n[comment]: # (end of autogenerated content)"

        # write to toc file
        with open(toc_file, 'w') as f:
            f.write(text)

def check_validity_external_links():
    """
    Checks all external links it can find for validity. Prints those with non OK HTTP responses. Does only need to be run
    from time to time.
    """
    # regex for finding urls (can be in <> or in () or a whitespace
    regex = re.compile(r"[\s\n]<(http.+?)>|\]\((http.+?)\)|[\s\n](http[^\s\n]+)")

    # count
    number_checked_links = 0

    # get category paths
    category_paths = get_category_paths()

    # for each category
    for category_path in category_paths:
        print('check links for {}'.format(os.path.basename(category_path)))

        # get entry paths
        entry_paths = get_entry_paths(category_path)

        # for each entry
        for entry_path in entry_paths:
            # read entry
            with open(entry_path, 'r') as f:
                content = f.read()

            # apply regex
            matches = regex.findall(content)

            # for each match
            for match in matches:

                # for each possible clause
                for url in match:

                    # if there was something
                    if url:
                        try:
                            # without a special headers, frequent 403 responses occur
                            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64)'})
                            urllib.request.urlopen(req)
                        except urllib.error.HTTPError as e:
                            print("{}: {} - {}".format(os.path.basename(entry_path), url, e.code))
                        except http.client.RemoteDisconnected:
                            print("{}: {} - disconnected without response".format(os.path.basename(entry_path), url))

                        number_checked_links += 1

                        if number_checked_links % 50 == 0:
                            print("{} links checked".format(number_checked_links))

    print("{} links checked".format(number_checked_links))

def fix_notation():
    """
    Changes notation, quite special. Only run when needed.
    """
    regex = re.compile(r"- License details:(.*)")

    # get category paths
    category_paths = get_category_paths()

    # for each category
    for category_path in category_paths:
        # get paths of all entries in this category
        entry_paths = get_entry_paths(category_path)

        for entry_path in entry_paths:
            # read it line by line
            with open(entry_path) as f:
                content = f.readlines()

            # apply regex on every line
            matched_lines = [regex.findall(line) for line in content]

            # loop over all the lines
            for line, match in enumerate(matched_lines):
                if match:
                    match = match[0]

                    # patch content
                    content[line] = "- Code license details:{}\n".format(match)

            # write it line by line
            with open(entry_path, "w") as f:
                f.writelines(content)

def regular_replacements():
    """
    Replacing some stuff by shortcuts. Can be run regularly
    """
    # get category paths
    category_paths = get_category_paths()

    # for each category
    for category_path in category_paths:
        # get paths of all entries in this category
        entry_paths = get_entry_paths(category_path)

        for entry_path in entry_paths:
            # read it line by line
            with open(entry_path) as f:
                content = f.read()

            # now the replacements
            content = content.replace('?source=navbar', '') # sourceforge specific
            content = content.replace('single player', 'SP')
            content = content.replace('multi player', 'MP')

            # write it line by line
            with open(entry_path, "w") as f:
                f.write(content)

def check_template_leftovers():
    """
    Checks for template leftovers.
    """
    check_strings = ['# {NAME}', '_{One line description}_', '- Home: {URL}', '- Media: {URL}', '- Download: {URL}', '- State: beta, mature (inactive since)', '- Keywords: SP, MP, RTS, TBS (if none, remove the line)', '- Code: primary repository (type if not git), other repositories (type if not git)', '- Language(s): {XX}', '- License: {XX} (if special, include link)', '{XXX}']

    # get category paths
    category_paths = get_category_paths()

    # for each category
    for category_path in category_paths:
        # get paths of all entries in this category
        entry_paths = get_entry_paths(category_path)

        for entry_path in entry_paths:
            # read it line by line
            with open(entry_path) as f:
                content = f.read()

            for check_string in check_strings:
                if content.find(check_string) >= 0:
                    print('{}: found {}'.format(os.path.basename(entry_path), check_string))

def parse_entry(content):
    """
    Returns a dictionary of the features of the content
    """

    info = {}

    # language
    regex = re.compile(r"- Language\(s\): (.*)")
    matches = regex.findall(content)
    if matches:
        languages = matches[0].split(',')
        languages = [x.strip() for x in languages]
        info['language'] = languages

    # license
    regex = re.compile(r"- License: (.*)")
    matches = regex.findall(content)
    if matches:
        info['license'] = matches[0]

    return info


def generate_statistics():
    """

    """
    statistics_path = os.path.join(games_path, 'statistics.md')
    statistics = '[comment]: # (autogenerated content, do not edit)\n# Statistics\n\n'

    # get category paths
    category_paths = get_category_paths()

    # for each category
    infos = []
    for category_path in category_paths:
        # get paths of all entries in this category
        entry_paths = get_entry_paths(category_path)

        for entry_path in entry_paths:
            # read it line by line
            with open(entry_path) as f:
                content = f.read()

            info = parse_entry(content)
            info['file'] = os.path.basename(entry_path)
            infos.append(info)

    # total number
    number_entries = len(infos)
    statistics += 'analyzed {} entries on {}\n\n'.format(number_entries, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


    # Language
    statistics += '## Languages\n\n'
    number_no_language = sum(1 for x in infos if 'language' not in x)
    if number_no_language > 0:
        statistics += 'Without language tag: {} ({:.1f}%)\n\n'.format(number_no_language, number_no_language / number_entries * 100)
        entries_no_language = [x['file'][:-3] for x in infos if 'language' not in x] # [:-3] to cut off the .md
        entries_no_language.sort()
        statistics += ', '.join(entries_no_language) + '\n\n'

    # get all languages together
    languages = []
    for info in infos:
        if 'language' in info:
            languages.extend(info['language'])

    unique_languages = set(languages)
    unique_languages = [(l, languages.count(l) / len(languages)) for l in unique_languages]
    unique_languages.sort(key=lambda x: -x[1])
    unique_languages = ['- {} ({:.1f}%)\n'.format(x[0], x[1]*100) for x in unique_languages]
    statistics += 'Used languages:\n' + ''.join(unique_languages) + '\n'

    # Licenses
    statistics += '## Licenses\n\n'
    number_no_license = sum(1 for x in infos if 'license' not in x)
    if number_no_license > 0:
        statistics += 'Without license tag: {} ({:.1f}%)\n\n'.format(number_no_license, number_no_license / number_entries * 100)
        entries_no_license = [x['file'][:-3] for x in infos if 'license' not in x] # [:-3] to cut off the .md
        entries_no_license.sort()
        statistics += ', '.join(entries_no_license) + '\n\n'

    # get all licenses together
    licenses = []
    for info in infos:
        if 'license' in info:
            licenses.append(info['license'])

    unique_licenses = set(licenses)
    unique_licenses = [(l, licenses.count(l) / len(licenses)) for l in unique_licenses]
    unique_licenses.sort(key=lambda x: -x[1])
    unique_licenses = ['- {} ({:.1f}%)\n'.format(x[0], x[1]*100) for x in unique_licenses]
    statistics += 'Used licenses:\n' + ''.join(unique_licenses) + '\n'

    with open(statistics_path, 'w') as f:
        f.write(statistics)



if __name__ == "__main__":

    # paths
    games_path = os.path.abspath(os.path.dirname(__file__))
    readme_path = os.path.join(games_path, os.pardir, 'README.md')

    # recount and write to readme
    update_readme()

    # generate list in toc files
    update_category_tocs()

    # generate report
    generate_statistics()

    # check for unfilled template lines
    # check_template_leftovers()

    # check external links (only rarely)
    #check_validity_external_links()

    # special, only run when needed
    # fix_notation()

    # regular replacements
    #regular_replacements()