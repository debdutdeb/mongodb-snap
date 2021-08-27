from snapcraft.plugins.v1 import PluginV1
from snapcraft.internal.repo.apt_key_manager import AptKeyManager
from snapcraft.internal.sources import Tar
from snapcraft.internal import errors

import snapcraft

from typing import Dict, Any, List
import os
import re


REPO_URL = (
    " deb [ arch=amd64,arm64 ] "
    " https://repo.mongodb.org/apt/ubuntu "
    " {ubuntu_codename}/mongodb-org/{version_major_minor} "
    " multiverse "
)
KEY_URL = "https://www.mongodb.org/static/pgp/server-{version_major_minor}.asc"
REPO_FILE = "/etc/apt/sources.list.d/mongodb-{version_major_minor}.list"


def get_ubuntu_codename() -> str:
  with open("/etc/os-release", 'r') as file_handler:
    for line in file_handler:
      match = re.match(r'^UBUNTU_CODENAME=(.+)$', line)
      if match != None:
        return match.group(1)


class MongoRepoWriteError(errors.SnapcraftError):
  pass


class PluginImpl(snapcraft.BasePlugin):

  @classmethod
  def schema(cls) -> Dict[str, Any]:
    return {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "version": {
                "type": "string"
            }
        },
        "required": ["version"]
    }

  @classmethod
  def get_pull_properties(cls) -> List[str]:
    return ["version"]

  def __init__(self, name, options, project=None) -> "PluginImpl":
    super().__init__(name, options, project)

    self.mongodb_version: str = options.version
    version_major_minor: str = '.'.join(self.mongodb_version.split('.')[0:2])
    self.repo_url: str = REPO_URL.format(
        version_major_minor=version_major_minor, ubuntu_codename=get_ubuntu_codename())
    self.repo_file: str = REPO_FILE.format(
        version_major_minor=version_major_minor)
    self.key_url: str = KEY_URL.format(
        version_major_minor=version_major_minor)
    self.key_file: str = os.path.join(
        self.sourcedir, f"server-{version_major_minor}.asc")

  @property
  def stage_packages(self) -> List[str]:
    self._install_key()
    self._install_repository()
    self._stage_packages.append("mongodb-org")
    return self._stage_packages

  def _install_repository(self):
    try:
      with open(self.repo_file, 'w') as file_handler:
        file_handler.write(self.repo_url)
    except Exception as e:
      print(e)

  def _install_key(self):
    # It isn't a tar file
    # but FileBase isn't accessible :p
    key_file_handler: Tar = Tar(self.key_url, self.sourcedir)
    key_file_handler.download()

    apt_key = AptKeyManager(key_assets="")

    with open(self.key_file) as file_handler:
      apt_key.install_key(key=file_handler.read())
