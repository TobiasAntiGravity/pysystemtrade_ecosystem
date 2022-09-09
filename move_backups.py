import tarfile
import subprocess
from datetime import datetime
import logging
from pathlib import Path
from typing import List

from smb.SMBConnection import SMBConnection
from smb.base import SharedFile, NotConnectedError
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

#client = subprocess.Popen(['hostname'], stdout=subprocess.PIPE).communicate()[0].strip()


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
                                    my_name='host_computer',
                          #          domain=client,
                                    remote_name=self.remote_name,
                                    use_ntlm_v2=True,
                                    is_direct_tcp=True)

        try:
            success = self.server.connect(self.ip, 139)

        except Exception as e:
            self.logger.exception(f'Failed to connect to samba share. Nothing uploaded' )
            return False

        else:
            self.logger.info(f'No exception thrown. SmbClient returned bool; {success}')
            return success

    def upload(self, local_file_path: Path, remote_folder_path: Path):
        """uploads local file_path to samba share.
           remote_folder_path: relative path from sharename root folder, to upload folder.
           local_file_path: file_path location on local machine.
        """

        with open(str(local_file_path.resolve()), 'rb') as data:
            remote_path_str = str(remote_folder_path / local_file_path.name)

            try:
                bytes_uploaded = self.server.storeFile(service_name=self.sharename,
                                                       path=remote_path_str,
                                                       file_obj=data)

            except (OperationFailure, NotConnectedError):
                msg = f'Exception occured. File {str(local_file_path)} upload to samba share probably failed.'
                msg += f'Tried to upload to the following remote path; {remote_path_str}'
                self.logger.exception(msg)

            else:
                msg = f"{bytes_uploaded} bytes of {str(local_file_path)} uploaded to"
                msg += f"samba share {self.sharename} in the subfolder {remote_path_str / local_file_path.name}"
                self.logger.debug(msg)

    def download(self, file: str):

        with open(file, 'wb') as fileobj:
            self.server.retrieveFile(self.sharename, fileobj)

        self.logger.debug(f"file_path {file} has been downloaded in current dir")

    def delete(self, file_path: str):
        """remove file_path from remote share.
           file_path: str
             File path relative to share name
        """

        try:
            self.server.deleteFiles(self.sharename, file_path)

        except Exception:
            self.logger.exception(f'Tried to delete {file_path} but failed')

        self.logger.debug(f'should have deleted file_path {str(file_path)}')

    def create_directory(self, directory_name: str, relative_path: Path):
        """Creates new directory on relative path on samba share from share folder (sharename). Note that folders
           in the path must exist as only the directory_name will be created
        """

        try:
            self.logger.debug(f'Will try to create {directory_name}, with path {str(relative_path / directory_name)}')
            self.server.createDirectory(self.sharename, str(relative_path / directory_name))

        except OperationFailure:
            message = f'Got a operation failure notice, saying that directory was not created. Funny thing is '
            message += 'though - it might be created after all. Will therefore ignore and proceed'
            self.logger.warning(message)

    def get_list_of_files_on_share(self, subfolder: str) -> List[SharedFile]:
        """get list of files of remote share"""

        file_list = self.server.listPath(self.sharename, '/' + subfolder)
        self.logger.debug(f'Retrieved list {[file.filename for file in file_list]}')

        return file_list

    def list_files_not_x_most_recent(self, file_list: List[SharedFile], threshold: int) -> List[SharedFile]:
        """Threshold up to and including. 5 gives all files but the 5 most recent"""

        file_creation_dict = {}

        for a_file in file_list:
            file_creation_dict[a_file] = a_file.create_time

        sorted_dict = dict(sorted(file_creation_dict.items(), key=lambda item: item[1], reverse=True))

        sorted_file_name_list = list(sorted_dict.keys())

        self.logger.debug(f'all backup files on share; {[file.filename for file in sorted_file_name_list]}')

        not_most_recent_files = sorted_file_name_list[threshold - 1:]
        self.logger.debug(f'Files to be deleted from share; {[file.filename for file in not_most_recent_files]}')

        return not_most_recent_files

    def delete_file_not_x_most_recent(self, subfolder: str, threshold: int, file_type_includes: str='tar'):

        subfolder_files = self.get_list_of_files_on_share(subfolder=subfolder)

        list_of_files_to_delete = self.list_files_not_x_most_recent(file_list=subfolder_files,
                                                                    threshold=threshold)

        for file in list_of_files_to_delete:
            if file_type_includes in file.filename.split('.')[-2:]:
                self.delete(f'/{subfolder}/{file.filename}')
                self.logger.info(f'deleted {file.filename} from samba share, subfolder {subfolder}')

            else:
                self.logger.debug(f'file_path {file.filename} not deleted as file_path name did not included in file_path ending')


def generate_tar_gz_filename_with_timestamp_suffix(prefix: str):
    """Generates timestamp suffix, appends to passed prefix"""

    backup_time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    tar_file_name = f'{prefix}_{backup_time}.tar.gz'

    return tar_file_name


def make_csv_tarfile(path_to_local_backup_dir: Path) -> Path:
    """Recursively adds all files in passed folder to tar file_path. Returns path to created file_path,
       tarfile is stored in the local backup directory. Will be deleted before new tar file_path is made
    """

    tar_file_name = generate_tar_gz_filename_with_timestamp_suffix(prefix="csv_backup")
    tar_path = Path(path_to_local_backup_dir, tar_file_name)

    with tarfile.open(str(tar_path), "w:gz") as tar:

        for folder_path in path_to_local_backup_dir.iterdir():
            if folder_path.is_dir():
                tar.add(str(folder_path), recursive=True)
                logger.debug(f'added folder; {folder_path} to tar')

    logger.info(f'added created tar archive and created file_path {tar_path}')

    return tar_path


def delete_old_tar_files(path_to_local_backup_dir: Path):

    if len(list(path_to_local_backup_dir.glob('*'))) != 0:

        for file_path in path_to_local_backup_dir.glob("*.tar.gz"):
            file_path.unlink()
            logger.info(f'Old file_path deleted {str(file_path)}')

    else:
        logger.debug(f'There were no files to be deleted')


def move_backup_csv_files(samba_user: str,
                          samba_password: str,
                          samba_share: str,
                          samba_server_ip: str,
                          samba_remote_name: str,
                          path_local_backup_folder: Path = Path('csv_backup'),
                          path_remote_backup_folder: Path = Path('csv_backup')):
    """Creates a tar file_path out of arctic csv backup files and moves it to a to samba share.
       Removes old tar files
       Deletes the csv files, so that folder is ready for new backup files.
       Keeps current tar file_path in backup folder
    """
    smb = SmbClient(ip=samba_server_ip,
                    username=samba_user,
                    password=samba_password,
                    remote_name=samba_remote_name,
                    sharename=samba_share)

    if smb.connect():

        delete_old_tar_files(path_to_local_backup_dir=path_local_backup_folder)

        path_to_tarfile = make_csv_tarfile(path_to_local_backup_dir=path_local_backup_folder)

        smb.upload(local_file_path=path_to_tarfile,
                   remote_folder_path=path_remote_backup_folder)
        smb.delete_file_not_x_most_recent(subfolder=str(path_remote_backup_folder), threshold=5)

        # delete all csv files backed up recursively.
        for file in path_local_backup_folder.glob('**/*.csv'):
            file.unlink()

    else:
        logger.critical('failed to connect to samba share, could not move to external storage')


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

        generator_compressed_files_in_folder = path_local_backup_folder.glob('*.tar.gz')

        try:
            file_path = next(generator_compressed_files_in_folder)

        except StopIteration:
            msg = f"No tar.gz files found in {path_local_backup_folder}. Therefore no db backup moved"
            logger.exception(msg)

        else:
            new_file_name = generate_tar_gz_filename_with_timestamp_suffix(prefix='db_backup')
            path_with_new_file_name = file_path.with_name(new_file_name)
            smb.upload(local_file_path=path_with_new_file_name, remote_folder_path=path_remote_backup_folder)

            if next(generator_compressed_files_in_folder, None) is not None:
                msg = f"It appears that there was more than one tar.gz file in {path_local_backup_folder}"
                msg += f" First item was treated as the correct backup file {file_path}, but might not be"
                msg += " needs to be checked"
                logger.warning(msg)

            #Delete local backup file, so that we know if new backup files is generated next time
            file_path.unlink()


if __name__ == '__main__':

    config = dotenv_values(".env")

    samba_user = config['SAMBA_USER']
    samba_password = config['SAMBA_PASSWORD']
    samba_share = config['SAMBA_SHARE']         # share name of remote server
    samba_server_ip = config['SAMBA_SERVER_IP']
    samba_remote_name = config['SAMBA_REMOTE_NAME']

    move_backup_csv_files(samba_user=samba_user,
                         samba_password=samba_password,
                         samba_share=samba_share,
                         samba_server_ip=samba_server_ip,
                         samba_remote_name=samba_remote_name,
                         path_local_backup_folder=Path('csv_backup'))

#    move_db_backup_files(samba_user=samba_user,
#                        samba_password=samba_password,
#                         samba_share=samba_share,
#                        samba_server_ip=samba_server_ip,
#                         samba_remote_name=samba_remote_name,
#                         path_local_backup_folder=Path('db_backup'),
#                         path_remote_backup_folder=Path('db_backup'))
