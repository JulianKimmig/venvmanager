from typing import Dict, List, TypedDict
import requests


class ProjectURLs(TypedDict, total=False):
    download: str
    homepage: str
    source: str
    tracker: str


class Downloads(TypedDict, total=False):
    last_day: int
    last_month: int
    last_week: int


class RequiresDist(TypedDict, total=False):
    requires_dist: List[str]


class ReleaseFile(TypedDict, total=False):
    comment_text: str
    digests: Dict[str, str]
    downloads: int
    filename: str
    has_sig: bool
    md5_digest: str
    packagetype: str
    python_version: str
    requires_python: str
    size: int
    upload_time: str
    upload_time_iso_8601: str
    url: str
    yanked: bool
    yanked_reason: str


class Info(TypedDict, total=False):
    author: str
    author_email: str
    bugtrack_url: str
    classifiers: List[str]
    description: str
    description_content_type: str
    docs_url: str
    download_url: str
    downloads: Downloads
    dynamic: str
    home_page: str
    keywords: str
    license: str
    maintainer: str
    maintainer_email: str
    name: str
    package_url: str
    platform: str
    project_url: str
    project_urls: ProjectURLs
    provides_extra: str
    release_url: str
    requires_dist: List[str]
    requires_python: str
    summary: str
    version: str
    yanked: bool
    yanked_reason: str


class Release(TypedDict, total=False):
    release_files: List[ReleaseFile]


class Url(TypedDict, total=False):
    comment_text: str
    digests: Dict[str, str]
    downloads: int
    filename: str
    has_sig: bool
    md5_digest: str
    packagetype: str
    python_version: str
    requires_python: str
    size: int
    upload_time: str
    upload_time_iso_8601: str
    url: str
    yanked: bool
    yanked_reason: str


class PackageData(TypedDict, total=False):
    info: Info
    last_serial: int
    releases: Dict[str, List[ReleaseFile]]
    urls: List[Url]
    vulnerabilities: List[str]


class PackackeException(Exception):
    pass


class GetPackageInfoError(PackackeException):
    pass


def get_package_info(package_name) -> PackageData:
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise GetPackageInfoError(
            f"Failed to fetch package data for {package_name}."
        ) from exc
