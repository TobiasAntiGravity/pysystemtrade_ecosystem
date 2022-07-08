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
f_handler = logging.FileHandler('backup.log')
f_handler.setLevel(logging_level)
f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s')
f_handler.setFormatter(f_format)
logger.setHandler(f_handler)

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

        success = self.server.connect(self.ip, 139)
        self.logger.info(f'SmbClient connected; {success}')

        return success

    def upload(self, file_path: Path):
        """uploads local file to samba share"""

        with open(str(file_path.resolve()), 'rb') as data:
            file = '/' + file_path.name

        try:
            bytes_uploaded = self.server.storeFile(self.sharename, file, data)

        except OperationFailure as e:
            msg = f'Exception occured. File {file_path.name} upload to samba share probably failed.'
            msg += 'Error is read failure according to documentation'
            self.logger.exception(msg)

        else:
            self.logger.debug(f"{bytes_uploaded} bytes of {file} uploaded to samba")

    def download(self, file: str):

        with open(file, 'wb') as fileobj:
            self.server.retrieveFile(self.sharename, fileobj)

        self.logger.debug(f"file {file} has been downloaded in current dir")

    def delete(self, file):
        """remove file from remote share"""

        file = '/' + file
        self.server.deleteFiles(self.sharename, file)

        self.logger.debug(f'should have deleted file {str(file)}')

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


def backup_csv_files(samba_user: str,
                     samba_password: str,
                     samba_share: str,
                     samba_server_ip: str,
                     samba_remote_name: str,
                     path_local_backup_folder: Path = Path('csv_backup')):

    delete_old_tar_files(path_to_local_backup_dir=path_local_backup_folder)

    path_to_tarfile = make_tarfile(path_to_local_backup_dir=path_local_backup_folder)

    smb = SmbClient(ip=samba_server_ip,
                    username=samba_user,
                    password=samba_password,
                    remote_name=samba_remote_name,
                    sharename=samba_share)

    if smb.connect():

        smb.upload(path_to_tarfile)
        smb.delete_file_not_x_most_recent(subfolder='/csv_backup', threshold=5)

        # delete all csv files backed up recursively.
        for file in path_local_backup_folder.glob('**/*.csv'):
            file.unlink()

    else:
        logger.critical('failed to connect to samba share, could not move to external storage')


if __name__ == '__main__':

    config = dotenv_values(".env")

    samba_user = config['SAMBA_USER']
    samba_password = config['SAMBA_PASSWORD']
    samba_share = config['SAMBA_SHARE']         # share name of remote server
    samba_server_ip = config['SAMBA_SERVER_IP']
    samba_remote_name = config['SAMBA_REMOTE_NAME']

    path_local_backup_folder = Path('csv_backup/')

    backup_csv_files(samba_user=samba_user,
                     samba_password=samba_password,
                     samba_share=samba_share,
                     samba_server_ip=samba_server_ip,
                     samba_remote_name=samba_remote_name,
                     path_local_backup_folder=path_local_backup_folder)
