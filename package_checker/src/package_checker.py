import json
import semver
import datetime
import subprocess

import click
import termcolor
from dateutil import parser


MAX_VERSIONS_BETWEEN = 10
MAX_PACKAGE_AGE = datetime.timedelta(days=14)
MIN_SURPRISE_AGE = datetime.timedelta(days=365)


class PackageVersionInfo:
    def __init__(self, package_name):
        self.package_name = package_name

        res = subprocess.run(
            f'npm view {self.package_name} time --json',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            check=True,
        )

        self.version_to_time = json.loads(res.stdout)
        self.all_versions = [
            semver.parse(ver, loose=True)
            for ver in self.version_to_time.keys()
            if ver not in ['modified', 'created']
        ]

    def time_of_version(self, version):
        return self.version_to_time[str(version)]

    def find_latest_match(self, version, max_update_to):
        newest_version = version

        if max_update_to == 'minor':
            for candidate in self.all_versions:
                if candidate.major != version.major:
                    continue

                if version.minor < candidate.minor:
                    newest_version = candidate
                elif newest_version.minor == candidate.minor and newest_version.patch < candidate.patch:
                    newest_version = candidate

        elif max_update_to == 'patch':
            for candidate in self.all_versions:
                if candidate.major != newest_version.major and candidate.minor != newest_version.minor:
                    continue

                if newest_version.patch < candidate.patch:
                    newest_version = candidate

        return newest_version

    def version_between(self, first, second):
        versions_between = 0
        for version in self.all_versions:
            if first.compare(version) == -1 and second.compare(version) == 1:
                versions_between += 1

        return versions_between

    def closest_previous(self, version):
        closest_previous = semver.parse('0.0.0', loose=True)
        for candidate in self.all_versions:
            if closest_previous.compare(candidate) == -1 and version.compare(candidate) == 1:
                closest_previous = candidate

        return closest_previous


class Version:
    def __init__(self, package_name, version):
        self.package_name = package_name
        self.original_version = version
        self.version = version

        self.max_update_to = None
        self.package_version_info = None

        if version.startswith('^'):
            self.max_update_to = 'minor'
        elif version.startswith('~'):
            self.max_update_to = 'patch'

        if self.max_update_to:
            self.version = version[1:]

        self.semver = semver.parse(self.version, loose=True)


@click.group()
def cli():
    pass


@cli.command()
@click.argument('package_name')
@click.argument('version')
def scan_single_package(package_name, version):
    parsed_version = Version(package_name, version)
    package_version_info = PackageVersionInfo(package_name)

    newest_version = package_version_info.find_latest_match(parsed_version.semver, parsed_version.max_update_to)
    versions_between = package_version_info.version_between(parsed_version.semver, newest_version)

    if versions_between > MAX_VERSIONS_BETWEEN:
        termcolor.cprint(
            f'[Warning - {package_name}] There are {versions_between} versions between the pinned version and actual version that will be installed. That might be too much',
            'red'
        )

    new_time = parser.parse(package_version_info.time_of_version(newest_version))
    package_age = datetime.datetime.now(tz=datetime.timezone.utc) - new_time

    if package_age < MAX_PACKAGE_AGE:
        termcolor.cprint(
            f'[Warning - {package_name}] Newest package {newest_version} age is {package_age}. It might be too new.',
            'red'
        )

    penultimate = package_version_info.closest_previous(newest_version)
    penultimate_time = parser.parse(package_version_info.time_of_version(penultimate))
    penultimate_age = new_time - penultimate_time

    if penultimate_age > MIN_SURPRISE_AGE:
        termcolor.cprint(
            f'[Warning - {package_name}] Package was recently updated (to {newest_version}) after a long time ({penultimate_age}. This might be a bad sign.',
            'red'
        )



if __name__ == '__main__':
    cli()
