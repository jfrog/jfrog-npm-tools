try:
    RUNNING_IN_NOTEBOOK = 'ZMQ' in str(get_ipython())   
except NameError:
    RUNNING_IN_NOTEBOOK = False

from os import getenv
import easyargs
import requests
import json
if RUNNING_IN_NOTEBOOK:
    from tqdm.notebook import tqdm
else:
    from tqdm import tqdm
from dataclasses import dataclass
import pickle
from datetime import datetime

from matplotlib.pyplot import text
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from math import pi, erf
from os import getenv


TOKEN = getenv('GITHUB_TOKEN')
if not TOKEN:
    print("GitHub token require")
    exit(1)

QUERY = """
  q%d: repository(name: "%s", owner: "%s") {
    issues(last: 100) {
      edges {
        node {
          createdAt
        }
      }
    }
  }
"""

DEPENDENCY_DB = pickle.load(open("npm_top_packages_data.pcl", "rb"))

HEADERS = {"Authorization": "Bearer " + TOKEN}


DAY = 24 * 3600

RESP_WIDTH = 4 * DAY
RESP_OFFSET = 1 * DAY


def package_version_timestamps(package_name):
    resp = requests.request("GET", f"https://registry.npmjs.org/{package_name}")
    IGNORE_EVENTS = {"created", "modified"}
    if resp.status_code == 200:
        return {
            key: datetime.strptime(val[:-5], "%Y-%m-%dT%H:%M:%S").timestamp()
            for key, val in json.loads(resp.text)["time"].items()
            if key not in IGNORE_EVENTS
        }


def get_github_repo(val):
    if (
        "repository_url" in val
        and val["repository_url"]
        and "github" in val["repository_url"]
    ):
        return val["repository_url"]
    if "homepage" in val and val["homepage"] and "github" in val["homepage"]:
        return val["homepage"]


def repo_name_to_tuple(name):
    if name.endswith(".git"):
        name = name[:-4]
    if "#" in name:
        name = name[: name.index("#")]
    return tuple(name.split("github.com")[1][1:].split("/")[:2])


def dependency_repos(package):
    repo_ids = set()
    for key, package_info in DEPENDENCY_DB.items():
        if "dependencies" in package_info and package_info["dependencies"]:
            if package in package_info["dependencies"]:
                repo_ids.add(key)
    return repo_ids


def build_long_query(repo_ids):
    return (
        "{"
        + "\n".join(
            QUERY % (index, repo_id[1], repo_id[0])
            for index, repo_id in enumerate(repo_ids)
        )
        + "}"
    )


def build_single_query(repo_name):
    if repo_name not in DEPENDENCY_DB:
        raise Exception("Not in DB")
    github_repo = get_github_repo(DEPENDENCY_DB[repo_name])
    if not github_repo:
        raise Exception("No github")
    repo_id = repo_name_to_tuple(github_repo)
    return "{" + QUERY % (0, repo_id[1], repo_id[0]) + "}"


def issue_timestamps(response):
    issue_timestamps = []
    for label, val in response["data"].items():
        if val and "issues" in val:
            if "edges" in val["issues"]:
                for edge in val["issues"]["edges"]:
                    date = edge["node"]["createdAt"]
                    issue_timestamps.append(
                        datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ").timestamp()
                    )
    return issue_timestamps


def run_query(q):
    request = requests.post(
        "https://api.github.com/graphql", json={"query": q}, headers=HEADERS
    )

    if request.status_code == 200:
        return request.json()

    raise Exception(
        f"Query failed to run by returning code of {request.status_code}. {q}"
    )


def package_version_timestamps(package_name):
    resp = requests.request("GET", f"https://registry.npmjs.org/{package_name}")
    IGNORE_EVENTS = {"created", "modified"}
    if resp.status_code == 200:
        return {
            key: datetime.strptime(val[:-5], "%Y-%m-%dT%H:%M:%S").timestamp()
            for key, val in json.loads(resp.text)["time"].items()
            if key not in IGNORE_EVENTS
        }


def half_gaussian_interp(dots, events, width, offset):
    d = dots.reshape(1, -1)
    e = events.reshape(-1, 1) 
    return np.sum(
        (d < e) * np.exp(-(((d - (e - offset)) / width) ** 2)), axis=0
    ) / (np.sqrt(2 * pi) * width * (1 + erf(offset/width)) / 2)



def do_make_plot(
    event_timestamps, self_issue_timestamps, dependent_issue_timestamps, timestamp_start
):
    timestamp_stop = datetime.now().timestamp()
    npoints = int((timestamp_stop - timestamp_start) / 3600 / 12)
    dots = np.linspace(timestamp_start, timestamp_stop, npoints)
    interpolated_issues_self = score_on_events_self(dots, self_issue_timestamps) * DAY
    interpolated_issues_dep = score_on_events_deps(dots, dependent_issue_timestamps) * DAY  
    xaxis_datetimes = [datetime.fromtimestamp(d) for d in dots]

    plt.plot(xaxis_datetimes, interpolated_issues_self)
    ax = plt.gca()

    offset_count = 0
    for label, loc in event_timestamps.items():
        if loc < timestamp_start:
            continue
        label_ts = datetime.fromtimestamp(loc)
        text_pos = max(interpolated_issues_self) * (10 + offset_count % 4)/15
        plt.text(label_ts,  text_pos, label)
        plt.plot([label_ts], [text_pos], '.')
        offset_count += 1

    formatter = mdates.DateFormatter("%Y-%m")
    ax.xaxis.set_major_formatter(formatter)
    locator = mdates.MonthLocator()
    ax.xaxis.set_major_locator(locator)
    minor_locator = mdates.DayLocator()
    minor_locator.MAXTICKS = 2000
    ax.xaxis.set_minor_locator(minor_locator)
    plt.xlabel("Date")
    plt.ylabel("Issues score [issues/day]")
    plt.legend(["Package issues", "Dependants issues"])
    ax2 = ax.twinx()
    ax2.plot(xaxis_datetimes, interpolated_issues_dep, color="tab:orange")

    plt.show()


def get_issues_timestamps(package_name):
    #tqdm.write(f"Fetching issues from {package_name}")
    self_issues_query = build_single_query(package_name)
    response = run_query(self_issues_query)
    issues_timestamps = issue_timestamps(response)
    return issues_timestamps


def dependency_issues_timestamps(package_name):
    issue_timestamps = []
    for dep_package in tqdm(dependency_repos(package_name)):
        if dep_package:
            try:
                issue_timestamps.append(get_issues_timestamps(dep_package))
            except Exception as e:
                pass

    return issue_timestamps



def score_on_events_self(points, issue_timestamps):
    return half_gaussian_interp(
        points, np.array(issue_timestamps), RESP_WIDTH, RESP_OFFSET
        )

def score_on_events_deps(points, issue_timestamps_arr):
    if not issue_timestamps_arr:
        return np.zeros(len(points))
    interpolated_issues_dep = half_gaussian_interp(points, np.array(issue_timestamps_arr[0]), RESP_WIDTH, RESP_OFFSET)
    for timestamps in issue_timestamps_arr[1:]:
        interpolated_issues_dep += half_gaussian_interp(points, np.array(timestamps), RESP_WIDTH, RESP_OFFSET)
    return interpolated_issues_dep


@easyargs
def main(package_name, start_date="2019-01-01", make_plot=True):
    try:
        start_timestamp = datetime.strptime(start_date, "%Y-%m-%d").timestamp()
    except Exception as e:
        print(type(e))
    version_timestamps = package_version_timestamps(package_name)
    self_issues_timestamps = get_issues_timestamps(package_name)
    dep_issues_timestamps = dependency_issues_timestamps(package_name)
    if make_plot:
        do_make_plot(
            version_timestamps,
            self_issues_timestamps,
            dep_issues_timestamps,
            start_timestamp,
        )


if __name__ == "__main__":
    main()
