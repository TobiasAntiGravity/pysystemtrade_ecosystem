from smb.SMBConnection import SMBConnections
from smb.base import SharedFile
import os
import tarfile
import subprocess
import datetime as datetime
from pathlib import Path
from typing import List

client = subprocess.Popen(['hostname'], stdout=subprocess.PIPE).communicate()[0].strip()


class SmbClient(object):
    def __init__(self, ip, username, password, sharename):
        self.ip = ip
        self.username = username
        self.password = password
        self.sharename = sharename

    def connect(self):

        self.server = SMBConnection(self.username,
                                    self.password,
                                    client,
                                    use_ntlm_v2=True)
        self.server.connect(self.ip, 139)

    def upload(self, file_path: Path):

        with open(str(file_path.resolve()), 'rb') as data:
            file = '/' + file_path.name
            self.server.storeFile(self.sharename, file, data)

        print("file has been uploaded")

    def download(self, file):

       with open(file, 'wb') as fileobj:
           self.server.retrieveFile(self.sharename, fileobj)

       print("file has been downloaded in current dir")

    def delete(self, file):
        """remove file from remote share"""
        file = '/' + file
        self.server.deleteFiles(self.sharename, file)

    def get_list_of_files_on_share(self, subfolder: str) -> List[SharedFile]:
        """get list of files of remote share"""

        file_list = self.server.listPath(self.sharename, '/' + subfolder)
        return file_list

    def list_files_not_x_most_recent(self, file_list : List[SharedFile], threshold: int) -> List[SharedFile]:
        """Threshold up to and including. 5 gives all files but the 5 most recent"""

        file_creation_dict = {}

        for a_file in file_list:
            file_creation_dict[a_file] = a_file.create_time

        sorted_dict = dict(sorted(file_creation_dict.items(), key=lambda item: item[1], reverse=True))

        sorted_file_name_list = sorted_dict.keys()
        not_most_recent_files = sorted_file_name_list[threshold - 1:]

        return not_most_recent_files

    def delete_file_not_x_most_recent(self, subfolder: str, threshold: int ):

        subfolder_files = self.get_list_of_files_on_share(subfolder=subfolder)

        list_of_files_to_delete = self.list_files_not_x_most_recent(file_list=subfolder_files,
                                                                    threshold=threshold)

        for file in list_of_files_to_delete:
            self.delete(file.filename)


def list_csv_files_to_backup(path_to_local_backup_dir: Path) -> List[Path]:
    """Finds all .csv files in the given folder (non-recursively)"""

    files_to_backup_list = []

    for file_path in path_to_local_backup_dir.glob("*.csv"):
        files_to_backup_list.append(file_path)

    return files_to_backup_list


def make_tarfile(files_to_tar_list: List[Path]) -> Path:

    backup_time = datetime.now().strftime("%Y-%m%-d %H:%M:%S")
    tar_file_name = f'csv_backup_{backup_time}.tar.gz'
    tar_path = Path(files_to_tar_list[0].parent, tar_file_name)

    with tarfile.open(str(tar_path), "w:gz") as tar:
        for file_path in files_to_tar_list:
            tar.add(str(file_path))

    return tar_file_name


def delete_old_tar_files(path_to_local_backup_dir: Path):

    for file_path in path_to_local_backup_dir.glob("*.tar.gz"):
            file_path.unlink()


def backup_csv_files(samba_user: str,
                     samba_password: str,
                     samba_share: str,
                     samba_server_ip: str,
                     path_local_backup_folder: Path=Path('csv_backup')):

    delete_old_tar_files(path_to_local_backup_dir=path_local_backup_folder)

    files_to_backup = list_csv_files_to_backup(path_local_backup_folder)

    if len(files_to_backup) != 0:
        path_to_tarfile = make_tarfile(files_to_tar_list=files_to_backup)

    smb = SmbClient(ip=samba_server_ip,
                    username=samba_user,
                    password=samba_password,
                    sharename=samba_share)
    smb.connect()

    smb.upload(path_to_tarfile)
    smb.delete_file_not_x_most_recent(subfolder='/csv_backup', threshold=5)

    # delete all csv files backed up
    for file in files_to_backup:
        file.unlink()


if __name__ == '__main__':


# todo: implement error handling
        # if fails to connect - must must handle
        # if subprocess never finishes must handle
        # if subprocess fails must handle
        # if subprocess does a fileNotFound, must handle
        # if connection fails, must handle.
# todo: get credentials from .env.