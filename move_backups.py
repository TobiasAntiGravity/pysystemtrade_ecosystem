import tarfile
import subprocess
from datetime import datetime
import logging
from pathlib import Path
from typing import List

from smb.SMBConnection import SMBConnection
from smb.base import SharedFile
from smb.smb_structs import OperationFailure
from dotenv import dotenv_values

config = dotenv_values(".env")
logging_level = config['LOGGING_LEVEL']

logger = logging.getLogger(name=__name__)
logger.setLevel(logging_level)

f_handler = logging.FileHandler('container_management.log')
f_handler.setLevel(logging_level)

c_handler = logging.StreamHandler()
c_handler.setLevel('INFO')

f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s')

f_handler.setFormatter(f_format)
c_handler.setFormatter(f_format)

logger.addHandler(f_handler)
logger.addHandler(c_handler)

client = subprocess.Popen(['hostname'], stdout=subprocess.PIPE).communicate()[0].strip()


class SmbClient(object):
    def __init__(self, ip, username, password, remote_name, sharename, logger=logger):
        self.ip = ip
        self.username = username
        self.password = password
        self.remote_name = remote_name
        self.sharename = sharename
        self.logger = logger

    def connect(self) -> bool:

        logging.debug(f'user: {self.username}, pass: {self.password}, remote_name: {self.remote_name}, ip: {self.ip}')

        self.server = SMBConnection(username=self.username,
                                    password=self.password,
                                    my_name=client,
                                    remote_name=self.remote_name,
                                    use_ntlm_v2=False)

        try:
            success = self.server.connect(self.ip, 139)

        except Exception as e:
            self.logger.exception(f'Failed to connect to samba share. Nothing uploaded' )
            return False

        else:
            self.logger.info(f'No exception thrown. SmbClient returned bool; {success}')
            return success

    def upload(self, local_file_path: Path, remote_folder_path: Path):
        """uploads local file to samba share.
           remote_folder_path: relative path from sharename root folder, to upload folder.
           local_file_path: file location on local machine.
        """

        with open(str(local_file_path.resolve()), 'rb') as data:
            remote_path_str = str(remote_folder_path / local_file_path.name)

            try:
                bytes_uploaded = self.server.storeFile(service_name=self.sharename,
                                                       path=remote_path_str,
                                                       file_obj=data)

            except OperationFailure as e:
                msg = f'Exception occured. File {str(local_file_path)} upload to samba share probably failed.'
                msg += 'Error is read failure according to documentation'
                self.logger.exception(msg)

            else:
                self.logger.debug(f"{bytes_uploaded} bytes of {str(local_file_path)} uploaded to samba")

    def download(self, file: str):

        with open(file, 'wb') as fileobj:
            self.server.retrieveFile(self.sharename, fileobj)

        self.logger.debug(f"file {file} has been downloaded in current dir")

    def delete(self, file):
        """remove file from remote share"""

        file = '/' + file
        self.server.deleteFiles(self.sharename, file)

        self.logger.debug(f'should have deleted file {str(file)}')

    def create_directory(self, directory_name: str, relative_path: Path):
        """Creates new directory on relative path on samba share from share folder (sharename). Note that folders
           in the path must exist as only the directory_name will be created
        """

        self.server.createDirectory(self.sharename, str(relative_path / directory_name))
        self.logger.debug(f'tried to create {directory_name}, with path {str(relative_path / directory_name)}')


    def get_list_of_files_on_share(self, subfolder: str) -> List[SharedFile]:
        """get list of files of remote share"""

        file_list = self.server.listPath(self.sharename, '/' + subfolder)
        self.logger.debug(f'Retrieved list {file_list}')

        return file_list

    def list_files_not_x_most_recent(self, file_list: List[SharedFile], threshold: int) -> List[SharedFile]:
        """Threshold up to and including. 5 gives all files but the 5 most recent"""

        file_creation_dict = {}

        for a_file in file_list:
            file_creation_dict[a_file] = a_file.create_time

        sorted_dict = dict(sorted(file_creation_dict.items(), key=lambda item: item[1], reverse=True))

        sorted_file_name_list = list(sorted_dict.keys())
        self.logger.debug(f'all backup files on share; {sorted_file_name_list}')

        not_most_recent_files = sorted_file_name_list[threshold - 1:]
        self.logger.debug(f'Files to be deleted from share; {not_most_recent_files}')

        return not_most_recent_files

    def delete_file_not_x_most_recent(self, subfolder: str, threshold: int):

        subfolder_files = self.get_list_of_files_on_share(subfolder=subfolder)

        list_of_files_to_delete = self.list_files_not_x_most_recent(file_list=subfolder_files,
                                                                    threshold=threshold)

        for file in list_of_files_to_delete:
            self.delete(file.filename)
            self.logger.info(f'deleted {file.filename} from samba share, subfolder {subfolder}')


def make_tarfile(path_to_local_backup_dir: Path) -> Path:
    """Recursively adds all files in passed folder to tar file. Returns path to created file,
       tarfile is stored in the local backup directory. Will be deleted before new tar file is made
    """

    backup_time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    tar_file_name = f'csv_backup_{backup_time}.tar.gz'
    tar_path = Path(path_to_local_backup_dir, tar_file_name)

    with tarfile.open(str(tar_path), "w:gz") as tar:
        tar.add(str(path_to_local_backup_dir), recursive=True)

    logger.info(f'added local backup director to tar archive and created file {tar_path}')

    return tar_path


def delete_old_tar_files(path_to_local_backup_dir: Path):

    if len(list(path_to_local_backup_dir.glob('*'))) != 0:

        for file_path in path_to_local_backup_dir.glob("*.tar.gz"):
            file_path.unlink()
            logger.info(f'Old file deleted {str(file_path)}')

    else:
        logger.debug(f'There were no files to be deleted')


def move_backup_csv_files(samba_user: str,
                          samba_password: str,
                          samba_share: str,
                          samba_server_ip: str,
                          samba_remote_name: str,
                          path_local_backup_folder: Path = Path('csv_backup'),
                          path_remote_backup_folder: Path = Path('db_backup')):
    """Creates a tar file out of arctic csv backup files and moves it to a to samba share.
       Removes old tar files
       Deletes the csv files, so that folder is ready for new backup files.
       Keeps current tar file in backup folder
    """
    smb = SmbClient(ip=samba_server_ip,
                    username=samba_user,
                    password=samba_password,
                    remote_name=samba_remote_name,
                    sharename=samba_share)

    if smb.connect():

        delete_old_tar_files(path_to_local_backup_dir=path_local_backup_folder)

        path_to_tarfile = make_tarfile(path_to_local_backup_dir=path_local_backup_folder)

        smb.upload(local_file_path=path_to_tarfile,
                   remote_folder_path=path_remote_backup_folder)
        smb.delete_file_not_x_most_recent(subfolder=str(path_remote_backup_folder), threshold=5)

        # delete all csv files backed up recursively.
        for file in path_local_backup_folder.glob('**/*.csv'):
            file.unlink()

    else:
        logger.critical('failed to connect to samba share, could not move to external storage')


def generate_backup_folder_name() -> str:
    """Generates a backup folder name that includes move time"""

    backup_time = datetime.now().strftime("%Y_%m_%d_%H_%M")
    folder_name = f'db_backup_{backup_time}'
    logger.debug(f"Folder name generated: {folder_name}")

    return folder_name

def move_db_backup_files(samba_user: str,
                         samba_password: str,
                         samba_share: str,
                         samba_server_ip: str,
                         samba_remote_name: str,
                         path_local_backup_folder: Path = Path('db_backup'),
                         path_remote_backup_folder: Path = Path('db_backup')):
    """Moves generated tar files to samba share for external storage.
       Does not remove any files. Files generated will be overwritten on next backup.
       Therefore files in backup folder is always current.
       Renames the backup files when moving them onto external storage.
    """

    smb = SmbClient(ip=samba_server_ip,
                    username=samba_user,
                    password=samba_password,
                    remote_name=samba_remote_name,
                    sharename=samba_share)

    if smb.connect():

        directory_name = generate_backup_folder_name()
        smb.create_directory( directory_name=directory_name, relative_path=path_remote_backup_folder)

        for file_path in path_local_backup_folder.glob('*.tar'):
            smb.upload(local_file_path=file_path, remote_folder_path=path_remote_backup_folder)

    else:
        logger.critical('failed to connect to samba share, could not move to external storage')


if __name__ == '__main__':

    config = dotenv_values(".env")

    samba_user = config['SAMBA_USER']
    samba_password = config['SAMBA_PASSWORD']
    samba_share = config['SAMBA_SHARE']         # share name of remote server
    samba_server_ip = config['SAMBA_SERVER_IP']
    samba_remote_name = config['SAMBA_REMOTE_NAME']

    backup_csv_files(samba_user=samba_user,
                     samba_password=samba_password,
                     samba_share=samba_share,
                     samba_server_ip=samba_server_ip,
                     samba_remote_name=samba_remote_name,
                     path_local_backup_folder=Path('csv_backup/'))


    move_db_backup_files(samba_user=samba_user,
                         samba_password=samba_password,
                         samba_share=samba_share,
                         samba_server_ip=samba_server_ip,
                         samba_remote_name=samba_remote_name,
                         path_local_backup_folder=path_local_backup_folder,
                         path_remote_backup_folder=Path('db_backup'))
