from typing import Dict, List, TypedDict
import requests


class ProjectURLs(TypedDict, total=False):
    """
    Dictionary type for representing various project-related URLs.

    Attributes:
        download: URL for downloading the package.
        homepage: Homepage URL of the package.
        source: Source code URL for the package.
        tracker: URL to the issue tracker for the package.
    """

    download: str
    homepage: str
    source: str
    tracker: str


class Downloads(TypedDict, total=False):
    """
    Dictionary type representing download statistics for a package.

    Attributes:
        last_day: Downloads in the last 24 hours.
        last_week: Downloads in the last 7 days.
        last_month: Downloads in the last 30 days.
    """

    last_day: int
    last_month: int
    last_week: int


class RequiresDist(TypedDict, total=False):
    """
    Dictionary type for package dependencies.

    Attributes:
        requires_dist: List of distribution requirements.
    """

    requires_dist: List[str]


class ReleaseFile(TypedDict, total=False):
    """
    Dictionary type representing a single file in a package release.

    Attributes:
        comment_text: Additional comments about the file.
        digests: File digests (e.g., md5, sha256).
        downloads: Number of downloads of the file.
        filename: Name of the file.
        has_sig: Indicates if the file has a digital signature.
        md5_digest: MD5 hash of the file.
        packagetype: Type of the package (e.g., sdist, bdist_wheel).
        python_version: Python version compatibility.
        requires_python: Required Python version string.
        size: Size of the file in bytes.
        upload_time: File upload timestamp.
        upload_time_iso_8601: File upload timestamp in ISO 8601 format.
        url: URL to download the file.
        yanked: Indicates if the file was yanked from PyPI.
        yanked_reason: Reason for yanking the file, if applicable.
    """

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
    """
    Dictionary type representing metadata for a package.

    Attributes:
        author: Author's name.
        author_email: Author's email address.
        bugtrack_url: URL for bug tracking.
        classifiers: List of classification strings.
        description: Package description.
        description_content_type: Content type for the description.
        docs_url: URL for documentation.
        download_url: URL for downloading the package.
        downloads: Download statistics.
        dynamic: Dynamic fields for the package.
        home_page: Homepage URL.
        keywords: Keywords associated with the package.
        license: License type.
        maintainer: Maintainer's name.
        maintainer_email: Maintainer's email.
        name: Package name.
        package_url: URL to the package.
        platform: Platform(s) the package supports.
        project_url: URL to the project.
        project_urls: Additional project URLs.
        provides_extra: Extra features provided by the package.
        release_url: URL to a specific release.
        requires_dist: List of required distributions.
        requires_python: Required Python version.
        summary: Short summary of the package.
        version: Package version.
        yanked: If the release is yanked from PyPI.
        yanked_reason: Reason for yanking, if applicable.
    """

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
    """
    Dictionary type representing a release of a package.

    Attributes:
        release_files: List of files in the release.
    """

    release_files: List[ReleaseFile]


class Url(TypedDict, total=False):
    """
    Dictionary type representing information about a package URL.

    Attributes:
        comment_text: Comments regarding the URL.
        digests: Digests for the URL.
        downloads: Number of downloads.
        filename: Filename associated with the URL.
        has_sig: Whether the URL has a digital signature.
        md5_digest: MD5 digest of the file.
        packagetype: Type of package (e.g., sdist, bdist_wheel).
        python_version: Compatible Python version.
        requires_python: Required Python version.
        size: Size of the file.
        upload_time: Time the file was uploaded.
        upload_time_iso_8601: Upload time in ISO 8601 format.
        url: The actual URL.
        yanked: If the URL was yanked.
        yanked_reason: Reason for yanking, if applicable.
    """

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
    """
    Dictionary type for holding comprehensive package data.

    Attributes:
        info: Metadata and information about the package.
        last_serial: Last serial number for updates.
        releases: Dictionary of releases with release files.
        urls: List of URLs associated with the package.
        vulnerabilities: List of vulnerabilities, if any.
    """

    info: Info
    last_serial: int
    releases: Dict[str, List[ReleaseFile]]
    urls: List[Url]
    vulnerabilities: List[str]


class PackackeException(Exception):
    """Base exception for package-related errors."""


class GetPackageInfoError(PackackeException):
    """Exception raised when fetching package information fails."""


def get_package_info(package_name) -> PackageData:
    """
    Fetches the package information from PyPI.

    Args:
        package_name: The name of the package to retrieve information for.

    Returns:
        A dictionary of package data conforming to the PackageData type.

    Raises:
        GetPackageInfoError: If an error occurs while fetching data from PyPI.
    """
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise GetPackageInfoError(
            f"Failed to fetch package data for {package_name}."
        ) from exc
