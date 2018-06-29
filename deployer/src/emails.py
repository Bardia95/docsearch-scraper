import os
import os.path as path
import subprocess as sp
from collections import OrderedDict
import json

from builtins import input
from deployer.src.algolia_internal_api import add_user_to_index


def _prompt_command(emails):
    prompt = '===\na <emails>... (add), d <nb> (delete), c <nb> <new> (change), empty to confirm\n> '

    for i, e in enumerate(emails):
        print('{}) {}'.format(i, e))
    ans = input(prompt).strip().split()

    if len(ans) == 0:
        return emails

    if len(ans) < 2:
        print('/!\ Missing number')
        return _prompt_command(emails)

    if ans[0] == 'a':
        emails += ans[1:]
    elif ans[0] == 'c' or ans[0] == 'd':
        try:
            idx = int(ans[1])
        except ValueError:
            print('/!\ Not a valid integer')
            return _prompt_command(emails)
        if idx >= len(emails):
            print('/!\ Out of bounds')
            return _prompt_command(emails)

        if ans[0] == 'd':
            del emails[idx]
        else:
            if len(ans) < 3:
                print('/!\ Missing new email')
                return _prompt_command(emails)
            emails[idx] = ans[2]
    else:
        print('/!\ Invalid command `%s`'.format(' '.join(ans)))
        return _prompt_command(emails)

    return emails


def _retrieve(config_name, config_dir):
    file_path = path.join(config_dir, 'infos', config_name + '.json')

    if path.isfile(file_path):
        with open(file_path, 'r') as f:
            obj = json.loads(f.read())
            return obj['emails']

    return []


def _commit_push(config_name, action, config_dir):
    txt = path.join('infos', config_name + '.json')
    commit_message = 'deploy: {} emails for {}'.format(action, config_name)

    old_dir = os.getcwd()
    os.chdir(config_dir)

    with open(os.devnull, 'w') as dev_null:
        sp.call(['git', 'pull', '-r', 'origin', 'master'], stdout=dev_null, stderr=sp.STDOUT)
        sp.call(['git', 'add', txt], stdout=dev_null, stderr=sp.STDOUT)
        sp.call(['git', 'commit', '-m', commit_message], stdout=dev_null, stderr=sp.STDOUT)
        sp.call(['git', 'push'], stdout=dev_null, stderr=sp.STDOUT)

    os.chdir(old_dir)


def _write(emails, config_name, config_dir):
    file_path = path.join(config_dir, 'infos', config_name + '.json')
    new_file = True

    obj = OrderedDict((
        ('name', config_name),
        ('url', ''),
        ('emails', emails),
        ('categories', [])
    ))

    if path.isfile(file_path):
        new_file = False
        with open(file_path, 'r') as f:
            obj = json.loads(f.read(), object_pairs_hook=OrderedDict)
            obj['emails'] = emails

    with open(file_path, 'w') as f:
        f.write(json.dumps(obj, separators=(',', ': '), indent=2))

    return new_file


def _prompt_emails(config_name, config_dir):
    emails = _retrieve(config_name, config_dir)

    while True:
        old = emails[:]
        emails = _prompt_command(emails)
        if old == emails:
            break

    return emails


def add(config_name, config_dir, emails_to_add=None):
    """Add email to the config. It also grant the analytics to the emails

        Args:
            config_name: The name of the index
            config_dir: The path to the configuration directory
            (optional) emails_to_add=Arrays of emails to add. If none, an interactive shell will ask for them

        Returns:
            A dict of results regarding the granting operation for every email {email : email's status}
                Status:
                    - True if the user was successfully added
                    - None if the user was already given access to this index
                    - {url} a string pointing to an invitation link if the user does not
                    yet have an Algolia account
        """

    analytics_stastuses={}
    if emails_to_add and len(emails_to_add) > 0:
        new_file = _write(emails_to_add, config_name, config_dir)
        for email in emails_to_add:
            analytics_stastuses[email]=add_user_to_index(config_name, email)
    else:
        emails = _prompt_emails(config_name, config_dir)
        new_file = _write(emails, config_name, config_dir)
        for email in emails:
            analytics_stastuses[email]=add_user_to_index(config_name, email)

    if new_file:
        _commit_push(config_name, 'Add', config_dir)
    else:
        _commit_push(config_name, 'Update', config_dir)

    return analytics_stastuses


# def add_emails(config_name, emails):
#
#     for email in emails:
#         add_user_to_index(config_name, email)


def delete_emails(config_name, emails):
    from deployer.src.algolia_internal_api import remove_user_from_index

    for email in emails:
        remove_user_from_index(config_name, email)


def delete(config_name, config_dir):
    file_path = path.join(config_dir, 'infos', config_name + '.json')
    if path.isfile(file_path):
        emails = _retrieve(config_name, config_dir)
        delete_emails(config_name, emails)
        os.remove(file_path)
        _commit_push(config_name, 'Delete', config_dir)
