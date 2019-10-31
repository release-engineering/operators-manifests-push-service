
import requests

from argparse import ArgumentParser

import logging

from omps.quay import QuayOrganization


logger = logging.getLogger('gc_releases')


def construct_argparser():
    parser = ArgumentParser()
    parser.add_argument(
        '--token-path',
        action='store', required=True, dest='token_path',
        help='path to file with CNR token'
    )
    parser.add_argument(
        '--organization',
        action='store', required=True, dest='organization',
        help='quay.io organization namespace'
    )
    parser.add_argument(
        '--keep',
        type=int, default=3, dest='keep',
        help='how many releases should be kept (newest)'
    )
    return parser


def list_repos(org, token):
    url = 'https://quay.io/cnr/api/v1/packages?namespace={}'.format(org)
    headers = {
        "Authorization": token
    }
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    json_data = r.json()

    for repo in json_data:
        full_name = repo['name']
        namespace, sep, name = full_name.partition('/')
        assert namespace == org
        yield name


def main():
    logging.basicConfig(level='INFO')
    parser = construct_argparser()
    args = parser.parse_args()

    with open(args.token_path) as f:
        token = f.read().strip()

    q_org = QuayOrganization(args.organization, token)

    for reponame in list_repos(args.organization, token):
        logger.info('GC repo: %s/%s', args.organization, reponame)
        releases = q_org.get_releases(reponame)
        releases = sorted(releases, reverse=True)
        if len(releases) <= args.keep:
            logger.info('No need to cleanup: %s/%s', args.organization, reponame)
            continue
        logger.info(
            '%d releases in %s/%s', len(releases), args.organization, reponame)
        to_be_deleted = releases[args.keep:]
        for release in to_be_deleted:
            q_org.delete_release(reponame, release)


if __name__ == '__main__':
    main()
